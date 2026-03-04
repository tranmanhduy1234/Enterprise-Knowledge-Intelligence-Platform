from app.core.config import settings
from app.services.retriever import hybridRetriever
from google import genai
import private
from fastapi.concurrency import run_in_threadpool

_llm_local = None
_llm_gemini = None

def _get_llm():
    global _llm_local
    if _llm_local is None:
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer
            import torch
            model = AutoModelForCausalLM.from_pretrained(
                settings.llm_model_name,
                torch_dtype=torch.float16,
                device_map="auto"
            )
            tokenizer = AutoTokenizer.from_pretrained(settings.llm_model_name)
            _llm_local = (model, tokenizer)
        except Exception as e:
            print(e)
            _llm_local = "mock"
    return _llm_local

def _get_llm_gemini():
    global _llm_gemini
    if _llm_gemini is None:
        _llm_gemini = genai.Client(api_key=private.API)
    return _llm_gemini

def build_context(sources: list[dict]) -> str:
    parts = []
    for i, s in enumerate(sources, 1):
        text = s.get("text", "").strip()
        meta = s.get("metadata", {})
        source = meta.get("source", "unknown")
        parts.append(f"Tài liệu [{i}] (Nguồn: {source})\n{text}")
    return "\n\n".join(parts)

async def generate_answer(query: str, context: str) -> str:
    llm = _get_llm()
    if llm == "mock":
        return (
            f"[Demo] Dựa trên ngữ cảnh được truy xuất, "
            f"câu trả lời cho câu hỏi của bạn sẽ được tạo từ model LLM. "
            f"Đã truy xuất {len(context)} ký tự ngữ cảnh."
        )
    
    model, tokenizer = llm
    prompt = f"""<|system|>
        Bạn là trợ lý chuyên gia. Trả lời chỉ dựa trên ngữ cảnh dưới đây. Nếu không tìm thấy thông tin, hãy nói rõ
        <|user|>
        Ngữ cảnh:
        {context}
        
        Câu hỏi: {query}
        <|assistant|>
    """
    
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    outputs = model.generate(
        **inputs,
        max_new_tokens=256,
        do_sample=True,
        temperature=0.7,
        pad_token_id=tokenizer.eos_token_id
    )
    return tokenizer.decode(outputs[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)

async def generate_answer_gemini(query: str, context: str) -> str:
    llm = _get_llm_gemini()
    system_instruction = (
        "Bạn là trợ lý AI chuyên nghiệp. Hãy trả lời câu hỏi CHỈ dựa trên các tài liệu "
        "được cung cấp bên dưới. \n"
        "- Nếu thông tin không có trong tài liệu, hãy nói rõ: 'Tôi không tìm thấy "
        "thông tin này trong cơ sở dữ liệu'. TUYỆT ĐỐI KHÔNG tự bịa thêm thông tin.\n"
        "- Khi trả lời, hãy trích dẫn nguồn bằng định dạng [Tài liệu X]."
    )
    prompt = f"NGỮ CẢNH:\n{context}\n\nCÂU HỎI:\n{query}"
    print("Đang gửi yêu cầu...")
    try: 
        response = llm.models.generate_content(
            model="models/gemini-2.5-flash-lite",
            contents=prompt,
            config={
                "system_instruction": system_instruction,
                "temperature": 0.2, # Giảm xuống 0.2 cho RAG để AI bám sát fact, ít "phiêu"
                "max_output_tokens": 1024,
            }
        )
    except Exception as e:
        print(f"Lỗi gọi Gemini: {e}")
        return "Xin lỗi, tôi gặp sự cố kỹ thuật khi kết nối với bộ não AI."
    return response.text

async def rag_query(
    query: str,
    use_rerank: bool = True
) -> tuple[str, list[dict]]:
    sources = await run_in_threadpool(hybridRetriever.search, query, use_rerank=use_rerank)
    context = build_context(sources)
    answer = await generate_answer_gemini(query, context)
    return answer, sources

import asyncio
async def run_demo():
    print("🚀 Đang khởi tạo hệ thống RAG (Hybrid + Rerank + LLM)...")
    
    # Danh sách câu hỏi test các khía cạnh khác nhau
    test_queries = [
        "Vector database là gì và tại sao cần hybrid search?", # Test kiến thức chung
        "Lỗi 404 khác gì lỗi 500?", # Test khả năng phân biệt mã lỗi (Sparse lợi thế)
        "Làm sao để triển khai FastAPI an toàn?" # Test kiến thức kỹ thuật
    ]

    for query in test_queries:
        print("\n" + "="*50)
        print(f"🤔 CÂU HỎI: {query}")
        
        # Gọi hàm RAG
        answer, sources = await rag_query(query, use_rerank=True)
        
        print(f"🤖 TRẢ LỜI:\n{answer}")
        print("\n📚 NGUỒN TRÍCH DẪN:")
        for idx, src in enumerate(sources, 1):
            score = src.get("score", 0)
            content_preview = src.get("content", "")[:100] + "..."
            print(f"   [{idx}] Score: {score:.4f} | {content_preview}")

if __name__ == "__main__":
    try:
        asyncio.run(run_demo())
    except KeyboardInterrupt:
        print("\nĐã dừng demo.")
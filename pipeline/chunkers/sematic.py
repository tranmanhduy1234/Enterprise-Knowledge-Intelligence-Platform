import re
import numpy as np
from typing import List, Optional
from sentence_transformers import SentenceTransformer
from pipeline.loaders.base import DocumentChunk
from pipeline.chunkers.recursive import RecursiveCharaterChunker

class SemanticChunker:
    def __init__(
        self, 
        chunk_size: int = 1000, 
        chunk_overlap: int = 100, 
        similarity_threshold: float = 0.5, # Ngữ cảnh tiếng Việt/Transformers thường ổn ở mức 0.5-0.6
        model_name: Optional[str] = None,
        buffer_size: int = 1 # Số câu xung quanh để tính toán ngữ cảnh
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.similarity_threshold = similarity_threshold
        self.buffer_size = buffer_size
        self.model_name = model_name or "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2" # Hỗ trợ tiếng Việt tốt hơn
        self._model = None
        self._fallback = RecursiveCharaterChunker(chunk_size, chunk_overlap)

    def _get_model(self) -> Optional[SentenceTransformer]:
        if self._model is None:
            try:
                self._model = SentenceTransformer(self.model_name)
                print(f"Load thành công model: {self.model_name}")
            except Exception as e:
                print(f"Error loading model: {e}")
        return self._model

    def _combine_sentences(self, sentences: List[str]) -> List[str]:
        """Tạo buffer để tính toán embedding mượt hơn, tránh nhiễu do câu quá ngắn."""
        combined = []
        for i in range(len(sentences)):
            start = max(0, i - self.buffer_size)
            end = min(len(sentences), i + self.buffer_size + 1)
            combined.append(" ".join(sentences[start:end]))
        return combined

    def chunk(self, doc: DocumentChunk) -> List[DocumentChunk]:
        model = self._get_model()
        if model is None:
            return self._fallback.chunk(doc)

        # 1. Tách câu thông minh
        sentences = re.split(r'(?<=[.!?])\s+', doc.content.strip())
        if len(sentences) <= 1:
            return self._fallback.chunk(doc)

        # 2. Tạo nội dung kết hợp để embedding hiểu ngữ cảnh rộng hơn
        combined_sentences = self._combine_sentences(sentences)
        embeddings = model.encode(combined_sentences, convert_to_numpy=True)

        # 3. Tính toán khoảng cách Cosine trên toàn bộ mảng (Vectorized)
        # Tính tương đồng giữa câu i và câu i+1
        norm = np.linalg.norm(embeddings, axis=1)
        embeddings_norm = embeddings / (norm[:, np.newaxis] + 1e-9)
        
        similarities = np.sum(embeddings_norm[:-1] * embeddings_norm[1:], axis=1)
        
        # 4. Xác định điểm cắt
        boundaries = [0]
        for i, sim in enumerate(similarities):
            if sim < self.similarity_threshold:
                boundaries.append(i + 1)
        boundaries.append(len(sentences))

        # 5. Đóng gói và Hậu xử lý (Sửa lỗi .split() và giới hạn kích thước)
        final_result: List[DocumentChunk] = []
        for j in range(len(boundaries) - 1):
            chunk_text = " ".join(sentences[boundaries[j]:boundaries[j + 1]]).strip()
            
            if not chunk_text:
                continue

            # Kiểm tra nếu chunk quá lớn thì dùng fallback cắt nhỏ tiếp để an toàn
            temp_chunk = DocumentChunk(
                content=chunk_text,
                metadata=doc.metadata.copy(),
                page=doc.page
            )
            
            if len(chunk_text) > self.chunk_size:
                final_result.extend(self._fallback.chunk(temp_chunk))
            else:
                final_result.append(temp_chunk)

        return final_result if final_result else self._fallback.chunk(doc)
    
from pipeline.loaders.base import DocumentChunk
def demo_semantic_chunking():
    raw_content = (
        "Uống cà phê vào buổi sáng giúp tăng cường sự tỉnh táo và tập trung. "
        "Caffeine kích thích hệ thần kinh trung ương, giúp giảm mệt mỏi và cải thiện hiệu suất làm việc. "
        "Nhiều nghiên cứu cho thấy cà phê còn chứa chất chống oxy hóa bảo vệ gan. "
        "Thị trường chứng khoán là nơi diễn ra các hoạt động mua bán cổ phiếu của các công ty niêm yết. "
        "Nhà đầu tư kỳ vọng kiếm lợi nhuận thông qua chênh lệch giá hoặc cổ tức hàng năm. "
        "Chỉ số VN-Index phản ánh biến động vốn hóa của toàn bộ thị trường tại Việt Nam."
    )

    doc = DocumentChunk(
        content=raw_content,
        metadata={"source": "demo_logic", "author": "Gemini"},
        page=1
    )

    # 2. Khởi tạo Semantic Chunker
    # Ngưỡng 0.5 thường là điểm "ngọt" cho các model multilingual
    chunker = SemanticChunker(
        chunk_size=500,
        similarity_threshold=0.5, 
        buffer_size=1
    )

    print("--- Đang phân tích ngữ nghĩa và chia nhỏ... ---")
    final_chunks = chunker.chunk(doc)

    # 3. Hiển thị kết quả
    print(f"Số lượng mảnh tìm thấy: {len(final_chunks)}\n")

    for i, chunk in enumerate(final_chunks):
        print(f"--- Mảnh #{i+1} ---")
        print(f"Nội dung: {chunk.content}")
        print(f"Độ dài ký tự: {len(chunk.content)}")
        print("-" * 30)

if __name__ == "__main__":
    demo_semantic_chunking()
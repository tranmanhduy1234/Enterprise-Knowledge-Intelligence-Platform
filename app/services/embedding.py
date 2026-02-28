import torch
from sentence_transformers import SentenceTransformer
from fastembed import SparseTextEmbedding
from app.core.config import settings

class EmbeddingService:
    """BGE-M3 orr compatible embedding model"""
    def __init__(self) -> None:
        self._dense_model: SentenceTransformer | None = None
        self._sparse_model: SparseTextEmbedding | None = None
        
    @property
    def dense_model(self) -> SentenceTransformer:
        if self._dense_model is None:
            self._dense_model = SentenceTransformer(settings.embedding_model, 
                                                    device="cuda" if torch.cuda.is_available() else "cpu")
        return self._dense_model
    
    @property
    def sparse_model(self) -> SparseTextEmbedding:
        if self._sparse_model is None:
            self._sparse_model = SparseTextEmbedding(model_name=settings.sparse_embedding_model)
        
        return self._sparse_model
    
    @property
    def dimension_dense(self) -> int:
        return self.dense_model.get_sentence_embedding_dimension()
    
    def embed_hybrid(self, texts: str | list[str]) -> list[list[float]]:
        if isinstance(texts, str):
            texts = [texts]
            
        dense_vecs = self.dense_model.encode(texts, 
                                             convert_to_numpy=True, 
                                             normalize_embeddings=True).tolist()
        
        sparse_vecs = self.sparse_model.embed(texts)
        
        hybrid_vectors = []
        for i, sparse_vec in enumerate(sparse_vecs):
            hybrid_vectors.append({
                "dense": dense_vecs[i],
                "sparse": {
                    "indices": sparse_vec.indices.tolist(),
                    "values": sparse_vec.values.tolist()
                }
            })
        
        return hybrid_vectors

    def embed_query(self, query: str) -> dict:
        return self.embed_hybrid([query])[0]
    
embedding_service = EmbeddingService()

import uuid
from qdrant_client import QdrantClient, models
# Giả sử các class và function trước đó đã được import hoặc định nghĩa ở trên
# from your_module import embedding_service, ensure_collection, settings, get_qdrant_client
from app.services.vectorstore import ensure_collection, delete_qdrant_collection

import hashlib
def generate_id(content: str) -> str:
    return hashlib.md5(content.encode("utf-8")).hexdigest()

def run_demo():
    # 1. Kết nối Qdrant
    client = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
    
    # 2. Khởi tạo Collection (tự động lấy dimension từ model)
    # delete_qdrant_collection(client=client, collection_name=settings.qdrant_collection)
    print("--- Khởi tạo Collection ---")
    ensure_collection(client=client)
    
    # 3. Chuẩn bị dữ liệu mẫu (Tiếng Việt)
    # Lưu ý: Các câu này được thiết kế để test sự khác biệt giữa Dense và Sparse
    documents = [
        "Qdrant là một vector database mạnh mẽ hỗ trợ tìm kiếm hybrid.",
        "Hướng dẫn cài đặt Python và các thư viện AI chuyên sâu.",
        "Mô hình BGE-M3 có khả năng đa nhiệm tuyệt vời cho tiếng Việt.",
        "Lỗi 404 là lỗi không tìm thấy trang web trên máy chủ.",
        "Cách xử lý lỗi 500 khi triển khai ứng dụng FastAPI.",
        "Hybrid search kết hợp tìm kiếm dense và sparse để tăng độ chính xác.",
        "Transformer là kiến trúc nền tảng của nhiều mô hình AI hiện đại.",
        "Redis thường được dùng làm cache trong hệ thống RAG.",
        "Docker giúp đóng gói ứng dụng và môi trường chạy đồng nhất.",
        "FastAPI hỗ trợ xây dựng API hiệu năng cao với Python.",
        "SentenceTransformer dùng để sinh embedding ngữ nghĩa.",
        "BM25 là thuật toán tìm kiếm dựa trên tần suất từ khóa.",
        "Asyncio cho phép xử lý nhiều tác vụ bất đồng bộ trong Python.",
        "GPU giúp tăng tốc quá trình huấn luyện mô hình học sâu.",
        "Qdrant hỗ trợ filtering metadata trong quá trình tìm kiếm vector.",
        "RAG là kỹ thuật kết hợp truy xuất dữ liệu và mô hình ngôn ngữ.",
        "Cross Encoder thường được dùng để rerank kết quả tìm kiếm.",
        "HNSW là thuật toán ANN phổ biến trong vector database.",
        "Embedding giúp chuyển văn bản thành vector số.",
        "Sparse vector giúp cải thiện khả năng tìm kiếm từ khóa chính xác.",
        "LangChain hỗ trợ xây dựng pipeline cho ứng dụng LLM.",
        "OpenAI API cho phép tích hợp mô hình ngôn ngữ vào ứng dụng.",
        "Tokenization là bước tiền xử lý quan trọng trong NLP.",
        "Inference là quá trình suy luận của mô hình đã huấn luyện.",
        "Batch processing giúp tăng hiệu suất xử lý dữ liệu lớn.",
        "Vector similarity thường dùng cosine similarity.",
        "Metadata filtering giúp giới hạn phạm vi tìm kiếm.",
        "Microservice architecture giúp hệ thống dễ mở rộng.",
        "Logging giúp theo dõi lỗi trong hệ thống backend.",
        "Monitoring giúp phát hiện sớm sự cố hệ thống."
    ]
    
    print(f"--- Đang tạo vector cho {len(documents)} văn bản ---")
    hybrid_vectors = embedding_service.embed_hybrid(documents) 

    # 4. Upsert vào Qdrant
    points = [
        models.PointStruct(
            id=generate_id(content=documents[i]), # Hoặc dùng số nguyên
            vector=hybrid_vectors[i],
            payload={"content": documents[i], "metadata": {"source": "demo"}}
        )
        for i in range(len(documents))
    ]
    
    client.upsert(collection_name=settings.qdrant_collection, points=points)
    print("--- Đã đẩy dữ liệu vào Qdrant thành công ---")

    # 5. Thực hiện Hybrid Search (The Retriever)
    # Case 1: Tìm kiếm theo từ khóa chính xác (Lợi thế của Sparse)
    query_1 = "AI chuyên sâu" 
    
    # Case 2: Tìm kiếm theo ý nghĩa (Lợi thế của Dense)
    query_2 = "Cơ sở dữ liệu vector nào tốt cho tìm kiếm kết hợp?"

    for q in [query_1, query_2]:
        print(f"\nTruy vấn: '{q}'")
        
        # Chuyển đổi query sang vector
        q_vec = embedding_service.embed_query(q)
        
        # Thực hiện tìm kiếm RRF
        results = client.query_points(
            collection_name=settings.qdrant_collection,
            prefetch=[
                models.Prefetch(query=q_vec["dense"], using="dense", limit=3),
                models.Prefetch(
                    query=models.SparseVector(
                        indices=q_vec["sparse"]["indices"],
                        values=q_vec["sparse"]["values"]
                    ), 
                    using="sparse", 
                    limit=3
                ),
            ],
            query=models.FusionQuery(fusion=models.Fusion.RRF),
            limit=2
        ).points

        for idx, hit in enumerate(results):
            print(f"  Top {idx+1}: {hit.payload['content']} (Score RRF: {hit.score:.4f})")

if __name__ == "__main__":
    run_demo()
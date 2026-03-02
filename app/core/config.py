"""Application configuration using Pydantic Settings"""
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """Central configuration for EKIP"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # API
    app_name: str = "EKIP - Enterprise Knowledge Intelligence Platform"
    debug: bool = False
    
    # Qdrant
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection: str = "ekip_docs"
    embedding_dim: int = 1024
    sparse_embedding_model: str = "Qdrant/bm25"
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    cache_ttl: int = 3600
    
    # LLM
    llm_model_name: str = "meta-llama/Llama-3-8B-Instruct"
    reranker_model: str = "BAAI/bge-reranker-v2-m3"
    embedding_model: str = "BAAI/bge-m3"
    
    # RAG
    chunk_size: int = 512
    chunk_overlap: int = 64
    top_k_retrieve: int = 20
    top_k_rerank: int = 5
    model_sematic_chunking: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    
settings = Settings()

def check_system_config():
    print(f"Khởi động hệ thống: {settings.app_name}")
    print(f"Chế độ Debug: {'BẬT' if settings.debug else 'TẮT'}")
    
    print("\n--- [ KẾT NỐI QDRANT ] ---")
    qdrant_url = f"http://{settings.qdrant_host}:{settings.qdrant_port}"
    print(f"Đang kết nối tới Vector DB tại: {qdrant_url}")
    print(f"Collection: {settings.qdrant_collection} (Dimension: {settings.embedding_dim})")
    
    print("\n--- [ THUẬT TOÁN RAG ] ---")
    print(f"Cắt văn bản: {settings.chunk_size} tokens, Overlap: {settings.chunk_overlap}")
    print(f"Luồng xử lý: Tìm {settings.top_k_retrieve} văn bản -> Rerank lấy {settings.top_k_rerank} văn bản")
    print(f"Embedding Model: {settings.embedding_model}")
    print(f"LLM Model: {settings.llm_model_name}")

if __name__ == "__main__":
    check_system_config()
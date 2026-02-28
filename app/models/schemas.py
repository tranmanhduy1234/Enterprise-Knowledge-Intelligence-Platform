from pydantic import BaseModel, Field

"""IngestRequest & IngestResponse (Quy trình nạp dữ liệu)"""
class IngestRequest(BaseModel):
    """Request for documemt ingestion"""
    
    document_id: str = Field(..., min_length=1, max_length=256)
    metadata: dict[str, str] = Field(default_factory=dict)
    
class IngestResponse(BaseModel):
    """Response after document ingestion"""
    
    document_id: str
    chunks_created: int
    status: str = "success"
    
"""QueryRequest & QueryResponse (Quy trình truy vấn RAG)"""
class QueryRequest(BaseModel):
    """Request for RAG query"""
    
    query: str = Field(..., min_length=1, max_length=4096)
    top_k: int = Field(default=5, ge=1, le=20)
    use_cache: bool = True
    stream: bool = False
    
class QueryResponse(BaseModel):
    """Response for RAG query"""
    
    answer: str
    sources: list[dict]
    cached: bool = False
    
"""Kiểm tra sức khỏe hệ thống"""
class HealthResponse(BaseModel):
    """Health check response"""
    
    status: str
    qdrant: bool
    redis: bool
    
if __name__=="__main__":
    from fastapi import FastAPI
    
    app = FastAPI(title="RAG System Demo")
    
    @app.post("/ingest", response_model=IngestResponse)
    async def ingest_document(request: IngestRequest):
        return IngestResponse(document_id=request.document_id, chunks_created=42)
    
    @app.post("/query", response_model=QueryResponse)
    async def query_rag(request: QueryRequest):
        return QueryResponse(
            answer=f"Kết quả cho: {request.query}",
            sources=[{"id": "doc_001", "text": "Nội dung tìm thấy..."}],
            cached=False
        )
    
    @app.get("/health", response_model=HealthResponse)
    async def health_check():
        return HealthResponse(status="ok", qdrant=True, redis=True)
    
    # RUN
    import uvicorn
    print("Truy cập http://127.0.0.1:8000/docs để thử nghiệm trực tiếp!")
    uvicorn.run(app, host="127.0.0.1", port=8000)
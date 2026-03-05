"""API route handlers."""

import json
import uuid
from pathlib import Path
import asyncio
from fastapi import APIRouter, File, Form, UploadFile, HTTPException
from sse_starlette.sse import EventSourceResponse
from fastapi.concurrency import run_in_threadpool
from app.core.cache import cache
from app.models.schemas import (
    QueryRequest,
    QueryResponse,
    IngestResponse,
    HealthResponse,
)
from celery.result import AsyncResult
from app.services.rag import rag_query, build_context
from app.services.retriever import hybridRetriever
from app.workers.ingest import ingest_document
from app.workers.celery_app import celery_app
from app.core.querycache import semantic_cache

router = APIRouter(prefix="/api/v1", tags=["EKIP"])
@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check for API, Qdrant, Redis."""
    qdrant_ok = False
    redis_ok = False
    
    try:
        from app.services.vectorstore import get_qdrant_client
        client = get_qdrant_client()
        await asyncio.wait_for(
            run_in_threadpool(client.get_collections), 
            timeout=2.0
        )
        qdrant_ok = True
    except Exception:
        pass
    
    try:
        if cache._client:
            redis_ok = True
    except Exception:
        pass
    
    return HealthResponse(
        status="ok" if (qdrant_ok and redis_ok) else "degraded",
        qdrant=qdrant_ok,
        redis=redis_ok,
    )

@router.post("/ingest", response_model=IngestResponse)
async def ingest(file: UploadFile = File(...), document_id: str | None = Form(None)):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in (".pdf", ".docx", ".doc", ".md", ".markdown"):
        raise HTTPException(400, "Unsupported format. Use: pdf, docx, md")

    tmp = Path("uploads")
    tmp.mkdir(exist_ok=True)
    path = tmp / f"{uuid.uuid4()}{ext}"
    content = await file.read()
    path.write_bytes(content)
    doc_id = document_id or str(uuid.uuid4())
    
    try:
        task = ingest_document.delay(str(path), doc_id)
    except Exception as e:
        raise HTTPException(503, f"Worker không khả dụng. Chạy: celery -A app.workers.celery_app worker. {e}")
    return IngestResponse(
        document_id=str(doc_id),
        task_id=task.id,
        message="Document is being ingested in the background.",
        status="processing",
    )

@router.get("/ingest/status/{task_id}")
async def get_ingest_status(task_id: str):
    task_result = AsyncResult(task_id, app=celery_app)
    
    if not task_result.ready():
        return {
            "task_id": task_id,
            "status": task_result.status,
            "message": "Tài liệu đang được xử lý"
        }
    
    if task_result.successful():
        data = task_result.result
        return {
            "task_id": task_id,
            "status": "SUCCESS",
            "document_id": data.get("document_id"),  # Giả sử worker trả về dict này
            "chunks_created": data.get("chunks_created", 0),
            "message": "Xử lý tài liệu hoàn tất."
        }
    return {
            "task_id": task_id,
            "status": "FAILURE",
            "error": str(task_result.result), # Chứa thông báo Exception từ Celery
            "message": "Có lỗi xảy ra trong quá trình xử lý."
        }

@router.post("/query", response_model=QueryResponse)
async def query(req: QueryRequest):
    if req.use_cache:
        try:
            cached_data = await run_in_threadpool(semantic_cache.get, query=req.query)
            
            if cached_data:
                return QueryResponse(
                    answer=cached_data["answer"],
                    sources=cached_data["sources"],
                    cached=True
                )
        except Exception as e:
            print(f"Cache lookup failed: {e}")

    answer, sources = await rag_query(
        query=req.query,
        use_rerank=True,
    )

    formatted_sources = [
        {"text": s["text"], "metadata": s["metadata"], "score": s.get("score", 0)} 
        for s in sources
    ]
    
    resp = QueryResponse(
        answer=answer,
        sources=formatted_sources,
        cached=False,
    )

    if req.use_cache:
        try:
            await asyncio.wait_for(
                run_in_threadpool(
                    semantic_cache.set, 
                    query=req.query, 
                    answer=answer, 
                    source=formatted_sources
                ),
                timeout=10.0
            )
        except Exception as e:
            print(f"Failed to set cache: {e}")

    return resp
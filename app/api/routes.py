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
from app.services.retriever import HybridRetriever
from app.workers.ingest import ingest_document
from app.workers.celery_app import celery_app
from app.services.vectorstore import get_qdrant_client, ensure_collection 

client = get_qdrant_client()
ensure_collection(client)

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
            await cache.set("__health__", {"ok": 1}, ttl=5)
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
    """Upload document for ingestion (async via Celery worker)."""
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
    """RAG query with optional cache."""
    if req.use_cache:
        hit = await cache.get(req.query, top_k=req.top_k, use_rerank=True)
        if hit:
            return QueryResponse(**hit, cached=True)
        
    answer, sources = await rag_query(
        query=req.query,
        use_rerank=True,
    )
    resp = QueryResponse(
        answer=answer,
        sources=[{"text": s["text"], "metadata": s["metadata"], "score": s["score"]} for s in sources],
        cached=False,
    )
    if req.use_cache:
        await cache.set(req.query, resp.model_dump(), top_k=req.top_k, use_rerank=True)
    return resp

@router.post("/query/stream")
async def query_stream(req: QueryRequest):
    """RAG query with SSE streaming response."""
    if req.use_cache:
        hit = await cache.get(req.query, top_k=req.top_k, use_rerank=True)
        if hit:
            async def cached_stream():
                yield {"event": "answer", "data": json.dumps({"text": hit["answer"], "done": True})}
                yield {"event": "sources", "data": json.dumps(hit["sources"])}
            return EventSourceResponse(cached_stream())

    retriever = HybridRetriever()
    sources = retriever.search(req.query, top_k=req.top_k, use_rerank=True)
    context = build_context(sources)

    async def event_stream():
        # Send sources first
        yield {"event": "sources", "data": json.dumps(sources)}
        # Placeholder: real streaming would yield LLM tokens
        answer, _ = await rag_query(req.query, top_k=req.top_k)
        for i in range(0, len(answer), 50):
            chunk = answer[i : i + 50]
            yield {"event": "answer", "data": json.dumps({"text": chunk, "done": False})}
        yield {"event": "answer", "data": json.dumps({"text": "", "done": True})}

    return EventSourceResponse(event_stream())
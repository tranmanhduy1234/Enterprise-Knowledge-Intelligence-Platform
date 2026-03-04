import uuid
from pathlib import Path

from qdrant_client.http import models

from app.core.config import settings
from app.services.embedding import embedding_service
from app.services.vectorstore import get_qdrant_client, ensure_collection
from app.workers.celery_app import celery_app
from pipeline.chunkers.sematic import SemanticChunker
from pipeline.loaders.factory import load_document

@celery_app.task(name="ingest_document")
def ingest_document(file_path: str, document_id: str | None = None) -> dict:
    path = Path(file_path)
    doc_id = document_id or str(uuid.uuid4())
    
    raw_chunks = load_document(path) # IBM Docling
    
    chunker = SemanticChunker(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        model_name=settings.model_sematic_chunking,
        buffer_size=1
    ) # fallback: RecursiveChunker
    
    all_chunks = []
    for rc in raw_chunks:
        all_chunks.extend(chunker.chunk(rc))

    if not all_chunks:
        return {"document_id": doc_id, "chunks_created": 0, "status": "empty"}

    import time
    
    client = get_qdrant_client()
    BATCH_SIZE = 32
    total_points = 0
    dim = None

    # Quét từng mẻ (batch)
    for i in range(0, len(all_chunks), BATCH_SIZE):
        batch_chunks = all_chunks[i:i + BATCH_SIZE]
        texts = [c.content for c in batch_chunks]
        
        # Xử lý vector từng mẻ nhỏ
        hybrid_vector = embedding_service.embed_hybrid(texts)
        
        if dim is None:
            dim = len(hybrid_vector[0]["dense"])
            ensure_collection(client, dim=dim)
            
        points = []
        for j, (chunk, vec) in enumerate(zip(batch_chunks, hybrid_vector)):
            meta = chunk.metadata.copy()
            meta["document_id"] = doc_id
            meta["chunk_id"] = i + j
            meta["text"] = chunk.content
            if chunk.page:
                meta["page"] = chunk.page
            
            points.append(
                models.PointStruct(id=str(uuid.uuid4()), vector=vec, payload=meta)
            )
            
        client.upsert(
            collection_name=settings.qdrant_collection,
            points=points
        )
        total_points += len(points)
        time.sleep(0.5) 

    print(f"Ingest thành công: {path} (Tổng số: {total_points} chunks)")
    return {
        "document_id": doc_id,
        "chunks_created": total_points,
        "status": "success",
    }
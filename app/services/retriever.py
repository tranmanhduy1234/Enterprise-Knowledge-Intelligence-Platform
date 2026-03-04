from typing import Any
from qdrant_client import QdrantClient
from qdrant_client.http import models
from sentence_transformers import CrossEncoder

from app.core.config import settings
from app.services.embedding import embedding_service
from app.services.vectorstore import get_qdrant_client

class HybridRetriever:
    def __init__(self) -> None:
        self._qdrant: QdrantClient | None = None
        self._reranker: Any = None
    
    @property
    def qdrant(self) -> QdrantClient:
        if self._qdrant is None:
            self._qdrant = get_qdrant_client()
        return self._qdrant
    
    def _get_reranker(self):
        if self._reranker is None:
            self._reranker = CrossEncoder(
                settings.reranker_model
            )
        return self._reranker
    
    def delete(self, metadata: dict = {}):
        self.qdrant.delete(
            collection_name=settings.qdrant_collection,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="metadata.source",
                            match=models.MatchValue(value="value")
                        )
                    ]
                )
            )
        )
    
    def search(self, query: str, top_k_rerank: int = 5, top_k_retrieve: int = 20, use_rerank: bool = True, search_cache=False) -> list[dict]:
        top_k_retrieve = top_k_retrieve or settings.top_k_retrieve
        top_k_rerank = top_k_rerank or settings.top_k_rerank
        
        try:
            hybridEmbedVector = embedding_service.embed_query(query)
        except Exception as e:
            print(f"Embedding Error: {e}")
            return []
        """
        hybridEmbedVector = {
            "dense": dense_vecs[i],
            "sparse": {
                "indices": sparse_vec.indices.tolist(),
                "values": sparse_vec.values.tolist()
            }
        }
        """
        # prefetch cho phép chạy song song luồng tìm kiếm và gộp kết quả bằng RRF
        response = self.qdrant.query_points(
            collection_name=settings.qdrant_collection if search_cache == False else settings.qdrant_collection + "_cache",
            prefetch=[
                models.Prefetch(
                    query=hybridEmbedVector["dense"],
                    using="dense",
                    limit=top_k_retrieve
                ),
                models.Prefetch(
                    query=models.SparseVector(
                        indices=hybridEmbedVector["sparse"]["indices"],
                        values=hybridEmbedVector["sparse"]["values"]
                    ),
                    using="sparse",
                    limit=top_k_retrieve
                )
            ],
            query=models.FusionQuery(fusion=models.Fusion.RRF),
            limit=top_k_retrieve,
            with_payload=True,
            with_vectors=False
        )
        
        candidate_points = response.points
        final_results = []
        candidate_points = [
            p for p in candidate_points
            if p.payload
        ]
        
        if use_rerank and candidate_points:
            reranker = self._get_reranker()
            pairs = [[query, p.payload.get("text", "")] for p in candidate_points]
            if pairs:
                rerank_scores = reranker.predict(pairs)
                
                if isinstance(rerank_scores,(float, int)):
                    rerank_scores = [rerank_scores]
                
                scored = list(zip(candidate_points, rerank_scores))
                scored.sort(key=lambda x: x[1], reverse=True)
                
                for p, s in scored[:top_k_rerank]:
                    final_results.append({
                        "id": str(p.id),
                        "text": p.payload.get("text", ""),
                        "metadata": {k: v for k, v in p.payload.items() if k != "text"},
                        "score": float(s)
                    })
        if not final_results:
            # Nếu không rerank, trả về kết quả từ Qdrant (RRF score)
            for p in candidate_points[:top_k_rerank]:
                final_results.append({
                    "id": str(p.id),
                    "text": p.payload.get("text", ""),
                    "metadata": {k: v for k, v in p.payload.items() if k != "text"},
                    "score": getattr(p, "score", 0.0)
                })
        return final_results

hybridRetriever = HybridRetriever()
if __name__=="__main__":
    hybridRetriever.search("Redis thường dùng để làm gì")
import uuid
import logging
from typing import Any, Dict, Optional

from qdrant_client.http import models
from sentence_transformers import CrossEncoder

from app.core.config import settings
from app.services.embedding import embedding_service
from app.services.vectorstore import get_qdrant_client, ensure_cache_collection

# Cấu hình logging để dễ theo dõi
logger = logging.getLogger(__name__)

class SemanticCache:
    def __init__(self) -> None:
        self._client = get_qdrant_client()
        self._collection_name = f"{settings.qdrant_collection}_cache"
        self._threshold = 0.85  # Ngưỡng tương đồng để chấp nhận cache
        self._reranker = None

    def _get_reranker(self):
        if self._reranker is None:
            self._reranker = CrossEncoder(settings.reranker_model)
        return self._reranker

    def get(self, query: str) -> Optional[Dict[str, Any]]:
        """Tìm kiếm câu trả lời từ cache dựa trên độ tương đồng ngữ nghĩa."""
        if not query or not isinstance(query, str):
            return None

        try:
            # 1. Tạo embedding cho query
            hybrid_vector = embedding_service.embed_query(query)
            
            # 2. Truy vấn Hybrid Search trên Qdrant
            response = self._client.query_points(
                collection_name=self._collection_name,
                prefetch=[
                    models.Prefetch(
                        query=hybrid_vector["dense"],
                        using="dense",
                        limit=3
                    ),
                    models.Prefetch(
                        query=models.SparseVector(
                            indices=hybrid_vector["sparse"]["indices"],
                            values=hybrid_vector["sparse"]["values"]
                        ),
                        using="sparse",
                        limit=3
                    )
                ],
                query=models.FusionQuery(fusion=models.Fusion.RRF),
                limit=1,
                with_payload=True
            )

            if not response.points:
                return None

            best_point = response.points[0]
            
            if best_point.score < 0.5: # Lưu ý: RRF score khác với Cosine Similarity
                return None

            return {
                "answer": best_point.payload.get("answer"),
                "sources": best_point.payload.get("source"),
                "cached": True
            }

        except Exception as e:
            logger.error(f"SemanticCache Get Error: {e}")
            return None

    def set(self, query: str, answer: str, source: Any) -> None:
        """Lưu kết quả mới vào cache."""
        if not query or not answer:
            return

        try:
            query_str = str(query)
            
            hybrid_embed = embedding_service.embed_query(query=query_str)
            
            # Đảm bảo collection đã tồn tại
            ensure_cache_collection(client=self._client, dim=len(hybrid_embed["dense"]))

            self._client.upsert(
                collection_name=self._collection_name,
                points=[
                    models.PointStruct(
                        id=str(uuid.uuid4()),
                        vector=hybrid_embed,
                        payload={
                            "query": query_str,
                            "answer": answer,
                            "source": source,
                        }
                    )
                ]
            )
            logger.info(f"Successfully cached query: {query_str[:50]}...")
        except Exception as e:
            logger.error(f"SemanticCache Set Error: {e}")

semantic_cache = SemanticCache()
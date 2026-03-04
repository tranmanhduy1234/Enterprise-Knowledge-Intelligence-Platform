from qdrant_client import QdrantClient
from qdrant_client.http import models
from app.core.config import settings

def get_qdrant_client() -> QdrantClient:
    return QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)

def delete_qdrant_collection(client: QdrantClient, collection_name: str) -> bool:
    print(f"Tiến hành xóa {collection_name}")
    try:
        success = client.delete_collection(collection_name=collection_name)
        if success:
            print(f"Xóa thành công {collection_name}")
        else:
            print(f"Không thể xóa collection: {collection_name}")
        return success
    
    except Exception as e:
        print(f"Đã xảy ra lỗi khi xóa collection {collection_name}: {e}")
        return False

def ensure_cache_collection(client: QdrantClient, dim: int | None = None) -> None:
    collections = client.get_collections().collections
    names = [c.name for c in collections]
    name_cache = settings.qdrant_collection + "_cache"
    if name_cache in names:
        print(f"Collection {name_cache} exist")
        return
    print(f"Creating collection {name_cache}")
    dim = dim or settings.embedding_dim
    
    client.create_collection(
        collection_name=name_cache,
        vectors_config={
            "dense": models.VectorParams(
                size=dim,
                distance=models.Distance.COSINE
            )
        },
        sparse_vectors_config={
            "sparse": models.SparseVectorParams(
                index=models.SparseIndexParams(
                    on_disk=False
                )
            )
        },
        hnsw_config=models.HnswConfigDiff(
            m=16, # số lượng liên kết tối đa mỗi node trong đồ thị
            ef_construct=100 # độ chính xác khi xây dựng index
        ),
        quantization_config=models.ScalarQuantization(
            scalar=models.ScalarQuantizationConfig(
                type=models.ScalarType.INT8,
                always_ram=True
            )
        )
    )
    
def ensure_collection(client: QdrantClient, dim: int | None = None) -> None:
    collections = client.get_collections().collections
    names = [c.name for c in collections]
    
    if settings.qdrant_collection in names:
        print(f"Collection {settings.qdrant_collection} exist")
        return
    
    print(f"Creating collection {settings.qdrant_collection}")
    dim = dim or settings.embedding_dim
    
    client.create_collection(
        collection_name=settings.qdrant_collection,
        vectors_config={
            "dense": models.VectorParams(
                size=dim,
                distance=models.Distance.COSINE
            )
        },
        sparse_vectors_config={
            "sparse": models.SparseVectorParams(
                index=models.SparseIndexParams(
                    on_disk=False
                )
            )
        },
        hnsw_config=models.HnswConfigDiff(
            m=16, # số lượng liên kết tối đa mỗi node trong đồ thị
            ef_construct=100 # độ chính xác khi xây dựng index
        ),
        quantization_config=models.ScalarQuantization(
            scalar=models.ScalarQuantizationConfig(
                type=models.ScalarType.INT8,
                always_ram=True
            )
        )
    )
    

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
    
if __name__=="__main__":
    client = get_qdrant_client()
    delete_qdrant_collection(client=client, collection_name=settings.qdrant_collection)
    ensure_collection(client)
    
    client.upsert(
        collection_name=settings.qdrant_collection,
        points=[
            models.PointStruct(id=1, vector={"dense": [0.1, 0.2, 0.3, 0.4]}, payload={"text": "Tài liệu về AI", "category": "tech"}),
            models.PointStruct(id=2, vector={"dense": [0.9, 0.8, 0.7, 0.6]}, payload={"text": "Cách nấu ăn ngon", "category": "food"}),
            models.PointStruct(id=3, vector={"dense": [0.15, 0.25, 0.35, 0.45]}, payload={"text": "Review điện thoại mới", "category": "tech"}) 
        ]
    )
    
    print("Insert data completed")
    
    search_result = client.query_points(
        collection_name=settings.qdrant_collection,
        query=[0.12, 0.23, 0.31, 0.45],
        using="dense",
        limit=2,
        query_filter=models.Filter(
            must=[
                models.FieldCondition(
                    key="category",
                    match=models.MatchValue(value="tech")
                )
            ]
        )
    )
    
    for hit in search_result.points:
        print(hit)
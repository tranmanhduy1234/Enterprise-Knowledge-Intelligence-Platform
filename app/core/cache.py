# Cải tiển: Sematic cache
import hashlib
import json
from typing import Any

import redis.asyncio as redis
from app.core.config import settings

class QueryCache:
    def __init__(self) -> None:
        self._client: redis.Redis | None = None
    
    async def connect(self) -> None:
        try:
            self._client = redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
        except Exception:
            self._client = None

    async def disconnect(self) -> None:
        """Close Redis connection"""
        if self._client:
            await self._client.aclose()
            self._client = None
        
    def _hash_query(self, query: str, **kwargs: Any) -> str:
        """Generate cache key from quey and params."""
        payload = {"q": query, **kwargs}
        raw = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()
    
    async def get(self, query: str, **kwargs: Any) -> dict | None:
        if not self._client:
            return None
        key = f"ekip:query:{self._hash_query(query, **kwargs)}"
        data = await self._client.get(key)
        if data:
            return json.loads(data)
        return None
    
    async def set(
        self, query: str, response: dict, ttl: int | None = None, **kwargs: Any
    ) -> None:
        """Store response in cache"""
        if not self._client:
            return 
        key = f"ekip:query:{self._hash_query(query, **kwargs)}"
        ttl = ttl or settings.cache_ttl
        await self._client.setex(
            key,
            ttl, 
            json.dumps(response, ensure_ascii=False)
        )
        
    async def delete(
        self, query: str, **kwargs: Any
    ) -> None:
        if not self._client:
            return
        key = f"ekip:query:{self._hash_query(query, **kwargs)}"
        await self._client.delete(key)
        
    async def ping(self) -> None:
        if not self._client:
            return
        pong = await self._client.ping()
        return pong
cache = QueryCache()

def redisasyncawait():
    import asyncio

    async def fake_redis_get(name, time=2):
        print(f"{name}: gửi request Redis")
        await asyncio.sleep(time)  # giả lập Redis chờ 2 giây
        print(f"{name}: Redis trả về")
        return {"data": 123}

    async def handle_request(name, index):
        print(f"{name}: bắt đầu xử lý")
        result = await fake_redis_get(name, time=index)
        print(f"{name}: xử lý tiếp với {result}")

    async def main():
        await asyncio.gather(
            handle_request("Req-1", index=2),
            handle_request("Req-2", index=4),
            handle_request("Req-3", index=2),
        )

    asyncio.run(main())
if __name__=="__main__":
    import asyncio
    
    async def main():
        await cache.connect()
        
        pong = await cache.ping()
        print(f"Ping result: {pong}")
        
        await cache.disconnect()
    asyncio.run(main())
"""Redis connection and caching utilities"""
import json
from typing import Any, Optional
from redis import asyncio as aioredis
from redis.asyncio import Redis

from app.core.config import settings


class RedisClient:
    """Redis client wrapper for caching and pub/sub"""
    
    def __init__(self):
        self._redis: Optional[Redis] = None
    
    async def connect(self) -> None:
        """Establish Redis connection"""
        self._redis = await aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True
        )
    
    async def disconnect(self) -> None:
        """Close Redis connection"""
        if self._redis:
            await self._redis.close()
    
    @property
    def client(self) -> Redis:
        """Get Redis client instance"""
        if not self._redis:
            raise RuntimeError("Redis not connected. Call connect() first.")
        return self._redis
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        value = await self.client.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return None
    
    async def set(
        self,
        key: str,
        value: Any,
        expire_seconds: int = 3600
    ) -> None:
        """Set value in cache with expiration"""
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        await self.client.set(key, value, ex=expire_seconds)
    
    async def delete(self, key: str) -> None:
        """Delete key from cache"""
        await self.client.delete(key)
    
    async def publish(self, channel: str, message: Any) -> None:
        """Publish message to channel"""
        if isinstance(message, (dict, list)):
            message = json.dumps(message)
        await self.client.publish(channel, message)
    
    async def invalidate_pattern(self, pattern: str) -> None:
        """Delete all keys matching pattern"""
        async for key in self.client.scan_iter(match=pattern):
            await self.client.delete(key)


# Global Redis client instance
redis_client = RedisClient()


async def get_redis() -> Redis:
    """Dependency that provides Redis client"""
    return redis_client.client



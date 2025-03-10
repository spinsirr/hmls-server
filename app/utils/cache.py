import redis.asyncio as redis
from fastapi_limiter import FastAPILimiter
from ..utils.config import get_settings
import json

settings = get_settings()

# Redis connection pool
redis_pool = redis.ConnectionPool.from_url(
    settings.REDIS_URL,
    max_connections=settings.REDIS_POOL_SIZE * 2,  # Double the pool size for high concurrency
    decode_responses=True,
    health_check_interval=30,  # Add health check
    socket_timeout=5,  # Add socket timeout
    socket_connect_timeout=5  # Add connect timeout
)

# Redis client
redis_client = redis.Redis(
    connection_pool=redis_pool,
    socket_keepalive=True,  # Enable keepalive
    retry_on_timeout=True   # Retry on timeout
)

async def init_redis():
    """Initialize Redis connection and rate limiter"""
    await FastAPILimiter.init(redis_client)

async def get_cached_data(key: str) -> str:
    """Get data from Redis cache"""
    return await redis_client.get(key)

async def set_cached_data(key: str, value: str, expire: int = 300):
    """Set data in Redis cache with expiration time in seconds"""
    await redis_client.set(key, value, ex=expire)

async def clear_cached_data(key: str):
    """Clear data from Redis cache"""
    await redis_client.delete(key)

def cache_response(expire: int = 300):
    """Decorator to cache API responses"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Create cache key from function name and arguments
            cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            
            # Try to get from cache
            cached_result = await get_cached_data(cache_key)
            if cached_result:
                return json.loads(cached_result)
            
            # If not in cache, execute function and cache result
            result = await func(*args, **kwargs)
            await set_cached_data(cache_key, json.dumps(result), expire)
            return result
        return wrapper
    return decorator 
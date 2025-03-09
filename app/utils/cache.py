import redis.asyncio as redis
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter
from ..utils.config import get_settings

settings = get_settings()

# Redis connection pool
redis_pool = redis.ConnectionPool.from_url(
    settings.REDIS_URL,
    max_connections=20,
    decode_responses=True
)

# Redis client
redis_client = redis.Redis(connection_pool=redis_pool)

# Rate limiter configuration
rate_limiter = RateLimiter(
    times=100,  # Number of requests
    seconds=60  # Time window in seconds
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

# Cache decorator
def cache_response(expire: int = 300):
    """Decorator to cache API responses"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Create cache key from function name and arguments
            cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            
            # Try to get from cache
            cached_result = await get_cached_data(cache_key)
            if cached_result:
                return cached_result
            
            # If not in cache, execute function and cache result
            result = await func(*args, **kwargs)
            await set_cached_data(cache_key, result, expire)
            return result
        return wrapper
    return decorator 
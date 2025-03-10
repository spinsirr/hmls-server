import redis.asyncio as redis
from fastapi_limiter import FastAPILimiter
from ..utils.config import get_settings
import json

settings = get_settings()

# Redis connection pool with optimized settings for high concurrency
redis_pool = redis.ConnectionPool.from_url(
    settings.REDIS_URL,
    max_connections=settings.REDIS_POOL_SIZE * 4,  # Increased pool size for higher concurrency
    decode_responses=True,
    health_check_interval=30,
    socket_timeout=10,  # Reduced timeout for faster failure detection
    socket_connect_timeout=5,  # Reduced connect timeout
    socket_keepalive=True,  # Enable keepalive
    retry_on_timeout=True,   # Enable retry on timeout
    retry_on_error=[redis.ConnectionError, redis.TimeoutError],  # Retry on specific errors
)

# Redis client with optimized settings
redis_client = redis.Redis(
    connection_pool=redis_pool,
    socket_keepalive=True,
    retry_on_timeout=True,
    health_check_interval=30
)

async def init_redis():
    """Initialize Redis connection and rate limiter"""
    await FastAPILimiter.init(redis_client)

async def get_cached_data(key: str, default=None) -> str:
    """Get data from Redis cache with error handling"""
    try:
        value = await redis_client.get(key)
        return value if value is not None else default
    except (redis.ConnectionError, redis.TimeoutError) as e:
        print(f"Redis error in get_cached_data: {e}")
        return default

async def set_cached_data(key: str, value: str, expire: int = 300):
    """Set data in Redis cache with error handling"""
    try:
        await redis_client.set(key, value, ex=expire)
    except (redis.ConnectionError, redis.TimeoutError) as e:
        print(f"Redis error in set_cached_data: {e}")

async def clear_cached_data(key: str):
    """Clear data from Redis cache with error handling"""
    try:
        await redis_client.delete(key)
    except (redis.ConnectionError, redis.TimeoutError) as e:
        print(f"Redis error in clear_cached_data: {e}")

def cache_response(expire: int = 300):
    """Decorator to cache API responses with improved error handling"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            try:
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
            except Exception as e:
                print(f"Cache error in wrapper: {e}")
                # On cache error, just execute the function
                return await func(*args, **kwargs)
        return wrapper
    return decorator 
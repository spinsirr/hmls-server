from functools import lru_cache
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Database Settings
    DATABASE_URL: str
    DB_ECHO: bool = False  # SQL query logging
    DB_POOL_SIZE: int = 40  # Increased pool size
    DB_MAX_OVERFLOW: int = 20  # Increased max overflow
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800
    DB_STATEMENT_TIMEOUT: int = 60000  # 60 seconds
    
    # Redis Settings
    REDIS_URL: str
    REDIS_POOL_SIZE: int = 100  # Increased pool size
    REDIS_POOL_TIMEOUT: int = 30
    REDIS_MAX_CONNECTIONS: int = 1000  # Maximum number of connections
    REDIS_RETRY_ATTEMPTS: int = 3
    REDIS_RETRY_DELAY: float = 0.1  # 100ms
    
    # JWT Settings
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Rate limiting settings
    RATE_LIMIT_TIMES: int = 1000  # Increased rate limit
    RATE_LIMIT_SECONDS: int = 60
    
    # Cache settings
    CACHE_EXPIRE_SECONDS: int = 300
    CACHE_ENABLED: bool = True
    
    # Worker settings
    WORKER_CONCURRENCY: int = 10
    WORKER_PREFETCH_COUNT: int = 50
    WORKER_TASK_TIMEOUT: int = 60  # 60 seconds
    
    # API settings
    API_TIMEOUT: int = 30  # 30 seconds
    API_MAX_CONNECTIONS: int = 100
    
    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache()
def get_settings() -> Settings:
    return Settings() 
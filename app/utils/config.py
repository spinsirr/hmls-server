from functools import lru_cache
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Database Settings
    DATABASE_URL: str

    # Redis Settings
    REDIS_URL: str

    # JWT Settings
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Rate limiting settings
    RATE_LIMIT_TIMES: int = 100
    RATE_LIMIT_SECONDS: int = 60
    
    # Cache settings
    CACHE_EXPIRE_SECONDS: int = 300
    
    # Connection pool settings
    DB_POOL_SIZE: int = 20  # Pool size set to 20
    DB_MAX_OVERFLOW: int = 10  # Max overflow set to 10
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800
    
    # Redis pool settings
    REDIS_POOL_SIZE: int = 20
    REDIS_POOL_TIMEOUT: int = 30

    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache()
def get_settings() -> Settings:
    return Settings() 
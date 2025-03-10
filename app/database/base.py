from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from ..utils.config import get_settings
import contextlib

settings = get_settings()

# Convert SQLite URL to async
ASYNC_DATABASE_URL = settings.DATABASE_URL.replace(
    'postgresql://', 'postgresql+asyncpg://'
)

# Create async engine with optimized settings for high concurrency
engine = create_async_engine(
    ASYNC_DATABASE_URL,
    echo=settings.DB_ECHO,  # Control SQL logging via settings
    pool_size=settings.DB_POOL_SIZE * 2,  # Double the pool size
    max_overflow=settings.DB_MAX_OVERFLOW * 2,  # Double the max overflow
    pool_timeout=settings.DB_POOL_TIMEOUT,  # Timeout for getting a connection
    pool_recycle=settings.DB_POOL_RECYCLE,  # Recycle connections
    pool_pre_ping=True,  # Enable connection health checks
    connect_args={
        "server_settings": {
            "jit": "off",  # Disable JIT for more predictable performance
            "statement_timeout": "60000",  # 60 second timeout
            "idle_in_transaction_session_timeout": "60000",  # 60 second timeout
        },
        "command_timeout": 60  # 60 second timeout for commands
    }
)

# Create async session factory with optimized settings
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False  # Disable autoflush for better performance
)

Base = declarative_base()

async def get_db():
    """Dependency to get database session with automatic cleanup"""
    session = AsyncSessionLocal()
    try:
        yield session
        await session.commit()
    except Exception as e:
        print(f"Database session error: {e}")
        await session.rollback()
        raise
    finally:
        await session.close() 
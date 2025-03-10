import pytest
import asyncio
from typing import AsyncGenerator, Generator
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import AsyncAdaptedQueuePool, QueuePool
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter
import redis.asyncio as redis
from unittest.mock import AsyncMock, patch
from fastapi import Request, Response

from app.main import app
from app.database.base import Base, get_db
from app.utils.config import get_settings
from app.models.user import User
from app.utils.auth import get_password_hash
from app.utils.queue import AppointmentQueue
from app.workers.appointment_worker import start_appointment_worker
import contextlib

settings = get_settings()

# Test database URL
TEST_DATABASE_URL = "postgresql+asyncpg://hmls:hmls@localhost/hmls_test"

# Test Redis URL (using DB 1 for testing)
TEST_REDIS_URL = "redis://:hmls@localhost:6379/1"

# Create async engine for tests
engine_test = create_async_engine(
    TEST_DATABASE_URL,
    pool_size=20,  # Pool size set to 20
    max_overflow=10,  # Max overflow set to 10
    pool_timeout=30,  # Timeout for getting a connection from pool
    pool_pre_ping=True,  # Enable connection health checks
    pool_recycle=300,  # Recycle connections every 5 minutes
    echo=True  # Enable SQL logging for debugging
)

# Create session factory
async_session_maker = async_sessionmaker(
    engine_test,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)

# Create Redis client for testing
redis_pool = redis.ConnectionPool.from_url(
    TEST_REDIS_URL,
    decode_responses=True,
    max_connections=500,  # Increased for high concurrency testing
    health_check_interval=30,
    socket_timeout=30,  # Increased timeout for tests
    socket_connect_timeout=30,  # Increased connect timeout for tests
    retry_on_timeout=True  # Enable retry on timeout
)
redis_client = redis.Redis(
    connection_pool=redis_pool,
    socket_keepalive=True,  # Enable keepalive
    retry_on_timeout=True   # Retry on timeout
)

# Create appointment queue for testing
appointment_queue_test = AppointmentQueue(redis_client)

async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()

app.dependency_overrides[get_db] = override_get_db

# Mock rate limiter that always allows requests
async def mock_rate_limit_check(request: Request, response: Response):
    return True

# Override rate limiter for tests
app.dependency_overrides[RateLimiter] = lambda *args, **kwargs: mock_rate_limit_check

# Configure rate limiter for tests with higher limits
FastAPILimiter._redis = redis_client
FastAPILimiter._prefix = "test_rate_limit"
FastAPILimiter._times = 1000  # Increase rate limit for tests
FastAPILimiter._seconds = 1  # Short window for tests

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()

@pytest.fixture(scope="session")
def test_app():
    """Create a test FastAPI app."""
    return app

@pytest.fixture(autouse=True)
async def setup_test_db():
    """Set up test database and Redis before each test."""
    # Initialize rate limiter with Redis
    await FastAPILimiter.init(redis_client)
    
    # Drop all tables
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    # Create test user
    async with async_session_maker() as session:
        try:
            test_user = User(
                email="test@example.com",
                first_name="Test",
                last_name="User",
                phone_number="+12345678901",
                hashed_password=get_password_hash("testpass123"),
                is_active=True
            )
            session.add(test_user)
            await session.commit()
        finally:
            await session.close()
    
    # Start appointment worker for tests
    worker_task = await start_appointment_worker()
    
    yield
    
    # Cleanup
    worker_task.cancel()
    try:
        await worker_task
    except asyncio.CancelledError:
        pass
    
    # Clear Redis test database and close connections
    await redis_client.flushdb()
    await redis_client.close()
    await redis_pool.disconnect()
    
    # Close all database connections
    await engine_test.dispose()
    
    # Drop tables
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture
async def async_client(test_app) -> AsyncGenerator[AsyncClient, None]:
    """Create an async client for testing."""
    async with AsyncClient(
        transport=ASGITransport(app=test_app), 
        base_url="http://test",
        timeout=30.0
    ) as client:
        yield client

@pytest.fixture(scope="session")
def client(test_app) -> Generator:
    """Create a TestClient for testing."""
    with TestClient(test_app) as client:
        yield client 
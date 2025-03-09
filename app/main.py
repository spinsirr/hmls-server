from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database.base import Base, engine
from .routers import auth, appointments
from .models import user, appointment  # Import all models to ensure table creation
from .utils.cache import init_redis, redis_client

# Create database tables
async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

app = FastAPI(title="HMLS API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8888"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup event
@app.on_event("startup")
async def startup_event():
    # Initialize database
    await create_tables()
    # Initialize Redis and rate limiter
    await init_redis()

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    # Close Redis connection
    await redis_client.close()

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(appointments.router, prefix="/appointments", tags=["appointments"])

@app.get("/")
async def read_root():
    return {"message": "Welcome to HMLS API"} 
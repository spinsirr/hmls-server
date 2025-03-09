from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database.base import Base, engine
from .routers import auth, appointments
from .models import user, appointment  # Import all models to ensure table creation

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="HMLS API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8888"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(appointments.router, prefix="/appointments", tags=["appointments"])

@app.get("/")
def read_root():
    return {"message": "Welcome to HMLS API"} 
# HMLS Backend Server

This is the backend server for the HMLS project, built with FastAPI and PostgreSQL.

## Prerequisites

- Python 3.8+
- PostgreSQL
- pip (Python package manager)

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a PostgreSQL database named 'hmls'

4. Create a `.env` file in the root directory with the following content:
```
DATABASE_URL=postgresql://postgres:postgres@localhost/hmls
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

5. Run the server:
```bash
uvicorn app.main:app --reload
```

The API will be available at http://localhost:8000

## API Documentation

Once the server is running, you can access:
- Interactive API documentation: http://localhost:8000/docs
- Alternative API documentation: http://localhost:8000/redoc

## Available Endpoints

### Authentication
- POST /auth/register - Register a new user
- POST /auth/token - Login and get access token 
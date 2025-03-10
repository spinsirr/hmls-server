#!/bin/bash

# Activate virtual environment
source venv/bin/activate

# Set Python path
export PYTHONPATH=$PYTHONPATH:.

# Run migrations
echo "Running database migrations..."
alembic upgrade head

# Start the server
echo "Starting development server..."
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 
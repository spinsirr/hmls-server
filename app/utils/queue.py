import json
from datetime import datetime
import redis.asyncio as redis
import pytz
from ..utils.config import get_settings
from ..utils.json_encoder import dumps, loads
from fastapi import HTTPException, status

settings = get_settings()

# Redis queue keys
APPOINTMENT_QUEUE_KEY = "appointment_requests"
APPOINTMENT_PROCESSING_KEY = "appointment_processing"

class AppointmentQueue:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    async def enqueue_appointment(self, appointment_data: dict) -> dict:
        """Add an appointment request to the queue"""
        try:
            # Ensure we have an appointment ID
            if "id" not in appointment_data:
                raise ValueError("Appointment ID is required")
            
            # Add timestamp to track when the request was made
            appointment_data["queued_at"] = datetime.now(pytz.UTC)
            message = dumps(appointment_data)
            await self.redis.lpush(APPOINTMENT_QUEUE_KEY, message)
            
            # Get queue position
            position = await self.get_queue_length()
            
            response = {
                "status": "queued",
                "message": "Your appointment request has been queued for processing",
                "queue_position": position,
                "id": appointment_data["id"]
            }
            
            return response
        except redis.RedisError as e:
            print(f"Redis error in enqueue: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service temporarily unavailable"
            )
        except ValueError as e:
            print(f"Validation error in enqueue: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )

    async def dequeue_appointment(self) -> dict:
        """Get the next appointment request from the queue"""
        try:
            # Atomic operation to move item from queue to processing list
            message = await self.redis.rpoplpush(APPOINTMENT_QUEUE_KEY, APPOINTMENT_PROCESSING_KEY)
            if message:
                return loads(message)
            return None
        except redis.RedisError as e:
            print(f"Redis error in dequeue: {e}")
            return None

    async def complete_processing(self, appointment_data: dict) -> None:
        """Remove the appointment request from the processing list"""
        try:
            message = dumps(appointment_data)
            await self.redis.lrem(APPOINTMENT_PROCESSING_KEY, 1, message)
        except redis.RedisError as e:
            print(f"Redis error in complete_processing: {e}")

    async def requeue_failed(self) -> None:
        """Requeue any failed processing items back to the main queue"""
        try:
            while True:
                message = await self.redis.rpoplpush(APPOINTMENT_PROCESSING_KEY, APPOINTMENT_QUEUE_KEY)
                if not message:
                    break
        except redis.RedisError as e:
            print(f"Redis error in requeue_failed: {e}")

    async def get_queue_length(self) -> int:
        """Get the current length of the queue"""
        try:
            return await self.redis.llen(APPOINTMENT_QUEUE_KEY)
        except redis.RedisError as e:
            print(f"Redis error in get_queue_length: {e}")
            return 0

    async def get_processing_length(self) -> int:
        """Get the number of items being processed"""
        try:
            return await self.redis.llen(APPOINTMENT_PROCESSING_KEY)
        except redis.RedisError as e:
            print(f"Redis error in get_processing_length: {e}")
            return 0 
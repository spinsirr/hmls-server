import asyncio
from datetime import datetime
import pytz
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import redis
import contextlib
from typing import List
import logging

from ..database.base import AsyncSessionLocal, engine
from ..models.appointment import Appointment
from ..utils.queue import AppointmentQueue
from ..utils.cache import redis_client, clear_cached_data
from ..utils.config import get_settings

settings = get_settings()
appointment_queue = AppointmentQueue(redis_client)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def is_time_slot_available(session: AsyncSession, appointment_time: datetime) -> bool:
    """Check if the appointment time slot is available with error handling"""
    try:
        query = select(Appointment).where(
            Appointment.appointment_time == appointment_time,
            Appointment.status != "cancelled"
        )
        result = await session.execute(query)
        return result.scalar_one_or_none() is None
    except Exception as e:
        logger.error(f"Error checking time slot availability: {e}")
        raise

async def process_appointments_batch(appointments: List[dict]) -> List[dict]:
    """Process a batch of appointments concurrently"""
    async def process_single(appointment_data: dict) -> dict:
        try:
            if isinstance(appointment_data["appointment_time"], str):
                appointment_time = datetime.fromisoformat(appointment_data["appointment_time"])
            else:
                appointment_time = appointment_data["appointment_time"]
            
            if appointment_time <= datetime.now(pytz.UTC):
                return {"id": appointment_data.get("id"), "success": False, "error": "Appointment time must be in the future"}
            
            async with AsyncSessionLocal() as session:
                try:
                    appointment_id = appointment_data.get("id")
                    if not appointment_id:
                        return {"success": False, "error": "Appointment ID not provided"}
                    
                    query = select(Appointment).where(Appointment.id == appointment_id)
                    result = await session.execute(query)
                    db_appointment = result.scalar_one_or_none()
                    
                    if not db_appointment:
                        return {"id": appointment_id, "success": False, "error": "Appointment not found"}
                    
                    # Check time slot availability
                    if not await is_time_slot_available(session, appointment_time):
                        return {"id": appointment_id, "success": False, "error": "Time slot is not available"}
                    
                    # Update appointment
                    db_appointment.status = "confirmed"
                    await session.commit()
                    return {"id": appointment_id, "success": True}
                except Exception as e:
                    await session.rollback()
                    logger.error(f"Database error processing appointment {appointment_id}: {e}")
                    return {"id": appointment_id, "success": False, "error": str(e)}
        except Exception as e:
            logger.error(f"Error processing appointment: {e}")
            return {"id": appointment_data.get("id"), "success": False, "error": str(e)}

    return await asyncio.gather(*[process_single(appt) for appt in appointments])

async def appointment_worker():
    """Background worker to process appointment requests with improved concurrency"""
    cleanup_interval = 300  # Cleanup every 5 minutes
    last_cleanup = datetime.now()
    batch_size = settings.WORKER_PREFETCH_COUNT
    
    while True:
        try:
            # Periodic cleanup
            if (datetime.now() - last_cleanup).seconds >= cleanup_interval:
                await engine.dispose()
                last_cleanup = datetime.now()
                logger.info("Performed periodic connection cleanup")
            
            # Get batch of appointments
            appointments = []
            for _ in range(batch_size):
                appointment_data = await appointment_queue.dequeue_appointment()
                if appointment_data:
                    appointments.append(appointment_data)
                else:
                    break
            
            if not appointments:
                await asyncio.sleep(1)
                continue
            
            # Process batch
            results = await process_appointments_batch(appointments)
            
            # Handle results
            for appointment_data, result in zip(appointments, results):
                if result["success"]:
                    await appointment_queue.complete_processing(appointment_data)
                else:
                    logger.error(f"Failed to process appointment: {result.get('error', 'Unknown error')}")
                    await appointment_queue.requeue_failed()
        
        except redis.RedisError as e:
            logger.error(f"Redis error in worker: {e}")
            await asyncio.sleep(5)
            try:
                await appointment_queue.requeue_failed()
            except Exception as e:
                logger.error(f"Error requeuing failed appointments: {e}")
        
        except Exception as e:
            logger.error(f"Worker error: {e}")
            await asyncio.sleep(1)

async def start_appointment_worker():
    """Start multiple appointment processing workers"""
    worker_tasks = []
    for _ in range(settings.WORKER_CONCURRENCY):
        worker_task = asyncio.create_task(appointment_worker())
        worker_tasks.append(worker_task)
    return worker_tasks 
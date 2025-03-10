import asyncio
from datetime import datetime
import pytz
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import redis
import contextlib

from ..database.base import AsyncSessionLocal, engine
from ..models.appointment import Appointment
from ..utils.queue import AppointmentQueue
from ..utils.cache import redis_client, clear_cached_data

appointment_queue = AppointmentQueue(redis_client)

async def is_time_slot_available(session: AsyncSession, appointment_time: datetime) -> bool:
    """Check if the appointment time slot is available"""
    query = select(Appointment).where(
        Appointment.appointment_time == appointment_time,
        Appointment.status != "cancelled"
    )
    result = await session.execute(query)
    return result.scalar_one_or_none() is None

async def process_appointment_request(appointment_data: dict) -> dict:
    """Process a single appointment request"""
    try:
        # Convert appointment time string to datetime if it's not already a datetime
        if isinstance(appointment_data["appointment_time"], str):
            appointment_time = datetime.fromisoformat(appointment_data["appointment_time"])
        else:
            appointment_time = appointment_data["appointment_time"]
        
        # Validate appointment time is in the future
        if appointment_time <= datetime.now(pytz.UTC):
            return {"success": False, "error": "Appointment time must be in the future"}
        
        async with AsyncSessionLocal() as session:
            try:
                # Get existing appointment if ID is provided
                appointment_id = appointment_data.get("id")
                if appointment_id:
                    query = select(Appointment).where(Appointment.id == appointment_id)
                    result = await session.execute(query)
                    db_appointment = result.scalar_one_or_none()
                    
                    if not db_appointment:
                        return {"success": False, "error": "Appointment not found"}
                    
                    # Check if time slot is available (excluding this appointment)
                    query = select(Appointment).where(
                        Appointment.appointment_time == appointment_time,
                        Appointment.status != "cancelled",
                        Appointment.id != appointment_id
                    )
                    result = await session.execute(query)
                    if result.scalar_one_or_none():
                        return {"success": False, "error": "Time slot is not available"}
                    
                    # Update appointment status to confirmed
                    db_appointment.status = "confirmed"
                    await session.commit()
                    await session.refresh(db_appointment)
                    
                    return {"success": True, "id": db_appointment.id}
                
                # For new appointments (should not happen anymore as we create them in the endpoint)
                return {"success": False, "error": "Appointment ID not provided"}
            except Exception as e:
                await session.rollback()
                raise e
            finally:
                await session.close()
    except Exception as e:
        print(f"Error processing appointment: {e}")
        return {"success": False, "error": str(e)}

async def appointment_worker():
    """Background worker to process appointment requests"""
    cleanup_interval = 300  # Cleanup every 5 minutes
    last_cleanup = datetime.now()
    
    while True:
        try:
            # Periodic connection cleanup
            if (datetime.now() - last_cleanup).seconds >= cleanup_interval:
                await engine.dispose()
                last_cleanup = datetime.now()
                print("Performed periodic connection cleanup")
            
            # Get next appointment request from queue
            appointment_data = await appointment_queue.dequeue_appointment()
            if appointment_data:
                # Process the appointment request
                result = await process_appointment_request(appointment_data)
                if result["success"]:
                    # Remove from processing list if successful
                    await appointment_queue.complete_processing(appointment_data)
                else:
                    # Log error and requeue failed requests
                    print(f"Failed to process appointment: {result.get('error', 'Unknown error')}")
                    await appointment_queue.requeue_failed()
            else:
                # No requests to process, wait a bit
                await asyncio.sleep(1)
        except redis.RedisError as e:
            print(f"Redis error in worker: {e}")
            await asyncio.sleep(5)  # Wait longer on Redis errors
            # Try to requeue any failed items
            try:
                await appointment_queue.requeue_failed()
            except:
                pass
        except Exception as e:
            print(f"Worker error: {e}")
            await asyncio.sleep(1)
        finally:
            # Ensure we don't accumulate connections
            if 'session' in locals():
                await session.close()

# Function to start the worker
async def start_appointment_worker():
    """Start the appointment processing worker"""
    worker_task = asyncio.create_task(appointment_worker())
    return worker_task 
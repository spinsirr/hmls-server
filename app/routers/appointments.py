from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.future import select
from typing import List
from datetime import datetime, timedelta
import pytz
import json

from ..database.base import get_db
from ..models.appointment import Appointment
from ..schemas.appointment import AppointmentCreate, Appointment as AppointmentSchema, AppointmentUpdate
from ..utils.cache import cache_response, clear_cached_data
from ..utils.queue import AppointmentQueue
from ..utils.cache import redis_client
from fastapi_limiter.depends import RateLimiter

router = APIRouter()
appointment_queue = AppointmentQueue(redis_client)

@router.post("/", response_model=dict)
async def create_appointment(
    appointment: AppointmentCreate,
    db: AsyncSession = Depends(get_db),
    rate_limit: bool = Depends(RateLimiter(times=100, seconds=60))
):
    # Validate appointment time is in the future
    current_time = datetime.now(pytz.UTC)
    if appointment.appointment_time <= current_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Appointment time must be in the future"
        )
    
    # Queue the appointment request
    appointment_data = appointment.model_dump()
    try:
        # Create appointment in database first
        db_appointment = Appointment(
            email=appointment_data["email"],
            phone_number=appointment_data["phone_number"],
            appointment_time=appointment_data["appointment_time"],
            vehicle_year=appointment_data["vehicle_year"],
            vehicle_make=appointment_data["vehicle_make"],
            vehicle_model=appointment_data["vehicle_model"],
            problem_description=appointment_data["problem_description"],
            status="pending"
        )
        db.add(db_appointment)
        await db.commit()
        await db.refresh(db_appointment)
        
        # Add appointment ID to the data before queuing
        appointment_data["id"] = db_appointment.id
        
        # Queue the appointment for processing
        queue_response = await appointment_queue.enqueue_appointment(appointment_data)
        queue_response["id"] = db_appointment.id
        return queue_response
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/", response_model=List[AppointmentSchema])
async def get_appointments(
    email: str = None,
    phone: str = None,
    status: str = None,
    db: AsyncSession = Depends(get_db),
    rate_limit: bool = Depends(RateLimiter(times=100, seconds=60))
):
    query = select(Appointment)
    
    if email:
        query = query.where(Appointment.email == email)
    if phone:
        query = query.where(Appointment.phone_number == phone)
    if status:
        query = query.where(Appointment.status == status)
    
    result = await db.execute(query.order_by(Appointment.appointment_time.desc()))
    return result.scalars().all()

@router.get("/{appointment_id}", response_model=AppointmentSchema)
async def get_appointment(
    appointment_id: int,
    db: AsyncSession = Depends(get_db),
    rate_limit: bool = Depends(RateLimiter(times=100, seconds=60))
):
    query = select(Appointment).where(Appointment.id == appointment_id)
    result = await db.execute(query)
    appointment = result.scalar_one_or_none()
    
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )
    return appointment

@router.put("/{appointment_id}", response_model=AppointmentSchema)
async def update_appointment_status(
    appointment_id: int,
    update_data: AppointmentUpdate,
    db: AsyncSession = Depends(get_db),
    rate_limit: bool = Depends(RateLimiter(times=50, seconds=60))
):
    # Check if appointment exists
    query = select(Appointment).where(Appointment.id == appointment_id)
    result = await db.execute(query)
    appointment = result.scalar_one_or_none()
    
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )
    
    valid_statuses = ["pending", "confirmed", "completed", "cancelled"]
    if update_data.status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
        )
    
    # Update appointment status
    stmt = update(Appointment).where(Appointment.id == appointment_id).values(status=update_data.status)
    await db.execute(stmt)
    await db.commit()
    
    # Clear cached data
    await clear_cached_data(f"get_appointment:{appointment_id}")
    await clear_cached_data("get_appointments")
    
    # Refresh and return updated appointment
    result = await db.execute(query)
    return result.scalar_one()

@router.delete("/{appointment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_appointment(
    appointment_id: int,
    db: AsyncSession = Depends(get_db),
    rate_limit: bool = Depends(RateLimiter(times=50, seconds=60))
):
    # Check if appointment exists
    query = select(Appointment).where(Appointment.id == appointment_id)
    result = await db.execute(query)
    appointment = result.scalar_one_or_none()
    
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )
    
    # Update status to cancelled
    stmt = update(Appointment).where(Appointment.id == appointment_id).values(status="cancelled")
    await db.execute(stmt)
    await db.commit()
    
    # Clear cached data
    await clear_cached_data(f"get_appointment:{appointment_id}")
    await clear_cached_data("get_appointments")
    
    return None 
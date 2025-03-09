from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.future import select
from typing import List
from datetime import datetime
import pytz
from datetime import datetime, timedelta
import json

from ..database.base import get_db
from ..models.appointment import Appointment
from ..schemas.appointment import AppointmentCreate, Appointment as AppointmentSchema, AppointmentUpdate
from ..utils.cache import cache_response, rate_limiter, clear_cached_data

router = APIRouter()

@router.post("/", response_model=AppointmentSchema)
@rate_limiter(times=20, seconds=60)  # Limit to 20 requests per minute
async def create_appointment(
    appointment: AppointmentCreate,
    db: AsyncSession = Depends(get_db)
):
    # Validate appointment time is in the future
    current_time = datetime.now(pytz.UTC)
    if appointment.appointment_time <= current_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Appointment time must be in the future"
        )
    
    # Check if the time slot is available
    query = select(Appointment).where(
        Appointment.appointment_time == appointment.appointment_time,
        Appointment.status != "cancelled"
    )
    result = await db.execute(query)
    existing_appointment = result.scalar_one_or_none()
    
    if existing_appointment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This time slot is already booked"
        )
    
    db_appointment = Appointment(
        email=appointment.email,
        phone_number=appointment.phone_number,
        appointment_time=appointment.appointment_time,
        vehicle_year=appointment.vehicle_year,
        vehicle_make=appointment.vehicle_make,
        vehicle_model=appointment.vehicle_model,
        problem_description=appointment.problem_description
    )
    db.add(db_appointment)
    await db.commit()
    await db.refresh(db_appointment)
    
    # Clear cached appointment list
    await clear_cached_data("get_appointments")
    return db_appointment

@router.get("/", response_model=List[AppointmentSchema])
@rate_limiter(times=100, seconds=60)  # Limit to 100 requests per minute
@cache_response(expire=60)  # Cache results for 60 seconds
async def get_appointments(
    email: str = None,
    phone: str = None,
    status: str = None,
    db: AsyncSession = Depends(get_db)
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
@rate_limiter(times=100, seconds=60)
@cache_response(expire=60)
async def get_appointment(
    appointment_id: int,
    db: AsyncSession = Depends(get_db)
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
@rate_limiter(times=50, seconds=60)
async def update_appointment_status(
    appointment_id: int,
    update_data: AppointmentUpdate,
    db: AsyncSession = Depends(get_db)
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
@rate_limiter(times=50, seconds=60)
async def cancel_appointment(
    appointment_id: int,
    db: AsyncSession = Depends(get_db)
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
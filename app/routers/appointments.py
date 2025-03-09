from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
import pytz
from datetime import datetime, timedelta

from ..database.base import get_db
from ..models.appointment import Appointment
from ..schemas.appointment import AppointmentCreate, Appointment as AppointmentSchema, AppointmentUpdate

router = APIRouter()

@router.post("/", response_model=AppointmentSchema)
def create_appointment(appointment: AppointmentCreate, db: Session = Depends(get_db)):
    # Validate appointment time is in the future
    current_time = datetime.now(pytz.UTC)
    if appointment.appointment_time <= current_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Appointment time must be in the future"
        )
    
    # Check if the time slot is available
    existing_appointment = db.query(Appointment).filter(
        Appointment.appointment_time == appointment.appointment_time,
        Appointment.status != "cancelled"
    ).first()
    
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
    db.commit()
    db.refresh(db_appointment)
    return db_appointment

@router.get("/", response_model=List[AppointmentSchema])
def get_appointments(
    email: str = None,
    phone: str = None,
    status: str = None,
    db: Session = Depends(get_db)
):
    query = db.query(Appointment)
    
    if email:
        query = query.filter(Appointment.email == email)
    if phone:
        query = query.filter(Appointment.phone_number == phone)
    if status:
        query = query.filter(Appointment.status == status)
    
    return query.order_by(Appointment.appointment_time.desc()).all()

@router.get("/{appointment_id}", response_model=AppointmentSchema)
def get_appointment(appointment_id: int, db: Session = Depends(get_db)):
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )
    return appointment

@router.put("/{appointment_id}", response_model=AppointmentSchema)
def update_appointment_status(
    appointment_id: int,
    update_data: AppointmentUpdate,
    db: Session = Depends(get_db)
):
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
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
    
    appointment.status = update_data.status
    db.commit()
    db.refresh(appointment)
    return appointment

@router.delete("/{appointment_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_appointment(appointment_id: int, db: Session = Depends(get_db)):
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )
    
    appointment.status = "cancelled"
    db.commit()
    return None 
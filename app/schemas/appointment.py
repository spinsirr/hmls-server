from pydantic import BaseModel, EmailStr, constr
from datetime import datetime
from typing import Optional

class AppointmentBase(BaseModel):
    email: EmailStr
    phone_number: constr(pattern=r'^\+?1?\d{9,15}$')
    appointment_time: datetime
    vehicle_year: str
    vehicle_make: str
    vehicle_model: str
    problem_description: str

class AppointmentCreate(AppointmentBase):
    pass

class AppointmentUpdate(BaseModel):
    status: str

class Appointment(AppointmentBase):
    id: int
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True 
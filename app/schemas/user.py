from pydantic import BaseModel, EmailStr, constr
from typing import Optional
from datetime import datetime

class VehicleInfo(BaseModel):
    year: Optional[str] = None
    make: Optional[str] = None
    model: Optional[str] = None
    vin: Optional[str] = None

class UserBase(BaseModel):
    email: EmailStr
    first_name: str
    last_name: str
    phone_number: constr(pattern=r'^\+?1?\d{9,15}$')  # Basic phone number validation

class UserCreate(UserBase):
    password: str
    vehicle_year: Optional[str] = None
    vehicle_make: Optional[str] = None
    vehicle_model: Optional[str] = None
    vehicle_vin: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

class User(UserBase):
    id: int
    is_active: bool
    vehicle_year: Optional[str] = None
    vehicle_make: Optional[str] = None
    vehicle_model: Optional[str] = None
    vehicle_vin: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True 
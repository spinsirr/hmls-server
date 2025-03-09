from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from ..database.base import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    phone_number = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    
    # Optional vehicle information
    vehicle_year = Column(String, nullable=True)
    vehicle_make = Column(String, nullable=True)
    vehicle_model = Column(String, nullable=True)
    vehicle_vin = Column(String, nullable=True)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now()) 
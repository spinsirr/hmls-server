from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database.base import Base

class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, nullable=False)
    phone_number = Column(String, nullable=False)
    appointment_time = Column(DateTime(timezone=True), nullable=False)
    vehicle_year = Column(String, nullable=False)
    vehicle_make = Column(String, nullable=False)
    vehicle_model = Column(String, nullable=False)
    problem_description = Column(Text, nullable=False)
    status = Column(String, default="pending")  # pending, confirmed, completed, cancelled
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now()) 
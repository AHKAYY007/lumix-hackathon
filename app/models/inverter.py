"""
Inverter model - represents a solar inverter installation.
"""

from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime
from sqlalchemy.orm import Mapped

if TYPE_CHECKING:
    from app.models.reading import InverterReading
    from app.models.credit import CarbonCredit

class InverterBase(SQLModel):
    """Base inverter schema."""
    gps_lat: float = Field(..., description="GPS latitude")
    gps_lon: float = Field(..., description="GPS longitude")
    capacity_kw: float = Field(..., description="Inverter capacity in kilowatts")


class Inverter(InverterBase, table=True):
    """Inverter database table."""
    __tablename__ = "inverters"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    readings: List["InverterReading"] = Relationship(back_populates="inverter")
    credits: List["CarbonCredit"] = Relationship(back_populates="inverter")


class InverterCreate(InverterBase):
    """Schema for creating an inverter."""
    pass


class InverterRead(InverterBase):
    """Schema for reading an inverter."""
    id: int
    created_at: datetime


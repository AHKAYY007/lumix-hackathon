"""
Inverter reading model - stores kWh production data from inverters.
"""

from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, TYPE_CHECKING
from datetime import datetime
from sqlalchemy.orm import Mapped


if TYPE_CHECKING:
    from app.models.inverter import Inverter


class InverterReadingBase(SQLModel):
    """Base inverter reading schema."""
    inverter_id: int = Field(..., foreign_key="inverters.id")
    timestamp: datetime = Field(..., description="Timestamp of the reading")
    kwh: float = Field(..., description="Energy produced in kilowatt-hours", ge=0)


class InverterReading(InverterReadingBase, table=True):
    """Inverter reading database table."""
    
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationship
    inverter: "Inverter" = Relationship(back_populates="readings")


class InverterReadingCreate(InverterReadingBase):
    """Schema for creating an inverter reading."""
    pass


class InverterReadingRead(InverterReadingBase):
    """Schema for reading an inverter reading."""
    id: int
    created_at: datetime


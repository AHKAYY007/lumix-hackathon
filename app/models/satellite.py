"""
Satellite reading model - stores NASA POWER irradiance data.
"""

from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime, date


class SatelliteReadingBase(SQLModel):
    """Base satellite reading schema."""
    lat: float = Field(..., description="Latitude")
    lon: float = Field(..., description="Longitude")
    timestamp: datetime = Field(..., description="Timestamp of the reading")
    irradiance: float = Field(..., description="Solar irradiance (W/m²)", ge=0)


class SatelliteReading(SatelliteReadingBase, table=True):
    """Satellite reading database table."""
    
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SatelliteReadingCreate(SatelliteReadingBase):
    """Schema for creating a satellite reading."""
    pass


class SatelliteReadingRead(SatelliteReadingBase):
    """Schema for reading a satellite reading."""
    id: int
    created_at: datetime


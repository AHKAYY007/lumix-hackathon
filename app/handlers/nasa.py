"""
NASA POWER API handler for fetching satellite irradiance data.
"""

import httpx
from datetime import date, datetime
from typing import List, Dict, Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from app.models.satellite import SatelliteReading, SatelliteReadingCreate
from app.models.inverter import Inverter
from app.core.config import get_settings
from app.core.constants import NASA_PARAMETER

settings = get_settings()


async def fetch_nasa_power_data(
    lat: float,
    lon: float,
    start_date: date,
    end_date: date
) -> Dict[str, Any]:
    """
    Fetch NASA POWER data for a location and date range.
    
    Args:
        lat: Latitude
        lon: Longitude
        start_date: Start date
        end_date: End date
        
    Returns:
        NASA POWER API response as dictionary
    """
    params = {
        "parameters": NASA_PARAMETER,
        "community": "RE",
        "longitude": lon,
        "latitude": lat,
        "start": start_date.isoformat(),
        "end": end_date.isoformat(),
        "format": "JSON"
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(settings.nasa_power_base_url, params=params)
        response.raise_for_status()
        return response.json()


def parse_nasa_response(response: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Parse NASA POWER response into list of readings.
    
    Returns:
        List of dicts with keys: date, irradiance (W/m²)
    """
    readings = []
    
    try:
        # NASA POWER response structure
        properties = response.get("properties", {})
        parameter_data = properties.get("parameter", {}).get(NASA_PARAMETER, {})
        
        for date_str, value in parameter_data.items():
            # NASA returns dates as YYYYMMDD
            if len(date_str) == 8:
                year = int(date_str[:4])
                month = int(date_str[4:6])
                day = int(date_str[6:8])
                reading_date = date(year, month, day)
                
                # Value is in W/m²/day, convert to hourly average for comparison
                # Assuming 12 hours of daylight
                daily_irradiance = float(value) if value is not None else 0.0
                # Convert kWh/m²/day to W/m² (divide by 24 hours, then multiply by 1000)
                # Actually, NASA POWER returns kWh/m²/day, so we need to convert
                # 1 kWh/m² = 1000 Wh/m², divide by 24 to get average W/m²
                irradiance_w_per_m2 = (daily_irradiance * 1000) / 24.0
                
                readings.append({
                    "date": reading_date,
                    "irradiance": irradiance_w_per_m2
                })
    except (KeyError, ValueError, TypeError) as e:
        raise ValueError(f"Failed to parse NASA POWER response: {e}")
    
    return readings


async def store_satellite_readings(
    session: AsyncSession,
    lat: float,
    lon: float,
    readings: List[Dict[str, Any]]
) -> List[SatelliteReading]:
    """
    Store satellite readings in database.
    
    Args:
        session: Database session
        lat: Latitude
        lon: Longitude
        readings: List of readings with date and irradiance
    """
    stored = []
    
    for reading_data in readings:
        # Create datetime at noon for the date
        timestamp = datetime.combine(reading_data["date"], datetime.min.time().replace(hour=12))
        
        satellite_reading = SatelliteReading(
            lat=lat,
            lon=lon,
            timestamp=timestamp,
            irradiance=reading_data["irradiance"]
        )
        session.add(satellite_reading)
        stored.append(satellite_reading)
    
    await session.commit()
    
    for reading in stored:
        await session.refresh(reading)
    
    return stored


async def get_satellite_readings(
    session: AsyncSession,
    lat: float,
    lon: float,
    start_date: date,
    end_date: date
) -> List[SatelliteReading]:
    """
    Get stored satellite readings, or fetch from NASA if not available.
    """
    from sqlmodel import select, and_
    
    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time())
    
    statement = select(SatelliteReading).where(
        and_(
            SatelliteReading.lat == lat,
            SatelliteReading.lon == lon,
            SatelliteReading.timestamp >= start_datetime,
            SatelliteReading.timestamp <= end_datetime
        )
    ).order_by(SatelliteReading.timestamp)
    
    result = await session.execute(statement)
    return list(result.scalars().all())


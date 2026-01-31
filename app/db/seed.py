"""
Optional development seeding script.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from datetime import date, datetime, timedelta
from app.core.database import async_engine, init_db
from app.models.inverter import Inverter
from app.models.reading import InverterReading
from sqlalchemy.ext.asyncio import AsyncSession


async def seed_data():
    """Seed database with sample data for development."""
    await init_db()
    
    async with AsyncSession(async_engine) as session:
        # Create sample inverter (Lagos, Nigeria)
        inverter = Inverter(
            gps_lat=6.5244,
            gps_lon=3.3792,
            capacity_kw=10.0
        )
        session.add(inverter)
        await session.commit()
        await session.refresh(inverter)
        
        print(f"Created inverter: {inverter.id}")
        
        # Create sample readings for the last 7 days
        today = date.today()
        for i in range(7):
            reading_date = today - timedelta(days=i)
            # Simulate hourly readings (8 AM to 6 PM)
            for hour in range(8, 19):
                timestamp = datetime.combine(reading_date, datetime.min.time().replace(hour=hour))
                # Simulate production: peak at noon, tapering off
                production_factor = 1.0 - abs(hour - 13) / 5.0
                kwh = inverter.capacity_kw * production_factor * 0.8  # 80% efficiency
                
                reading = InverterReading(
                    inverter_id=inverter.id,
                    timestamp=timestamp,
                    kwh=kwh
                )
                session.add(reading)
        
        await session.commit()
        print("Created sample readings")
        
        print("Seed data created successfully!")


if __name__ == "__main__":
    asyncio.run(seed_data())


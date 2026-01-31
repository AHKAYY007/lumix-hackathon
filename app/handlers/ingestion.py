"""
Inverter data ingestion handler.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from typing import List, Dict, Any
from datetime import datetime

from app.models.inverter import Inverter, InverterCreate
from app.models.reading import InverterReading, InverterReadingCreate
from app.models.audit import AuditLog, AuditLogCreate
from app.utils.hashing import hash_payload
from app.utils.time import utc_now


async def create_inverter(
    session: AsyncSession,
    inverter_data: InverterCreate
) -> Inverter:
    """Create a new inverter."""
    inverter = Inverter(**inverter_data.model_dump())
    session.add(inverter)
    await session.commit()
    await session.refresh(inverter)
    
    # Audit log
    audit = AuditLog(
        payload_hash=hash_payload(inverter_data.model_dump()),
        action="inverter_created",
        entity_type="inverter",
        entity_id=inverter.id
    )
    session.add(audit)
    await session.commit()
    
    return inverter


async def ingest_readings(
    session: AsyncSession,
    readings: List[Dict[str, Any]]
) -> List[InverterReading]:
    """
    Ingest inverter readings (from CSV or JSON).
    
    Expected format:
    [
        {"inverter_id": 1, "timestamp": "2025-01-15T10:00:00", "kwh": 5.5},
        ...
    ]
    """
    created_readings = []
    
    for reading_data in readings:
        # Validate inverter exists
        inverter = await session.get(Inverter, reading_data["inverter_id"])
        if not inverter:
            raise ValueError(f"Inverter {reading_data['inverter_id']} not found")
        
        # Parse timestamp if string
        if isinstance(reading_data["timestamp"], str):
            timestamp = datetime.fromisoformat(reading_data["timestamp"].replace("Z", "+00:00"))
        else:
            timestamp = reading_data["timestamp"]
        
        reading = InverterReading(
            inverter_id=reading_data["inverter_id"],
            timestamp=timestamp,
            kwh=reading_data["kwh"]
        )
        session.add(reading)
        created_readings.append(reading)
        
        # Audit log
        audit = AuditLog(
            payload_hash=hash_payload(reading_data),
            action="reading_ingested",
            entity_type="inverter_reading",
            entity_id=None  # Will be set after commit
        )
        session.add(audit)
    
    await session.commit()
    
    # Refresh to get IDs
    for reading in created_readings:
        await session.refresh(reading)
    
    return created_readings


async def ingest_readings_stream(
    session: AsyncSession,
    rows_iter,
    batch_size: int = 1000
) -> List[InverterReading]:
    """Ingest readings from an iterator of reading dicts in batches.

    rows_iter yields dicts with keys: inverter_id, timestamp (ISO str or datetime), kwh
    Commits every `batch_size` rows to keep memory and transaction sizes bounded.
    Returns the list of created InverterReading objects.
    """
    created_readings: List[InverterReading] = []
    batch: List[Dict[str, Any]] = []

    async def _process_batch(batch_rows: List[Dict[str, Any]]):
        added: List[InverterReading] = []
        for reading_data in batch_rows:
            inverter = await session.get(Inverter, reading_data["inverter_id"])
            if not inverter:
                raise ValueError(f"Inverter {reading_data['inverter_id']} not found")

            # Parse timestamp if string
            if isinstance(reading_data["timestamp"], str):
                timestamp = datetime.fromisoformat(reading_data["timestamp"].replace("Z", "+00:00"))
            else:
                timestamp = reading_data["timestamp"]

            reading = InverterReading(
                inverter_id=reading_data["inverter_id"],
                timestamp=timestamp,
                kwh=float(reading_data["kwh"])
            )
            session.add(reading)
            added.append(reading)

            # Audit log
            audit = AuditLog(
                payload_hash=hash_payload(reading_data),
                action="reading_ingested",
                entity_type="inverter_reading",
                entity_id=None
            )
            session.add(audit)

        await session.commit()
        for r in added:
            await session.refresh(r)
        return added

    try:
        for row in rows_iter:
            batch.append(row)
            if len(batch) >= batch_size:
                added = await _process_batch(batch)
                created_readings.extend(added)
                batch = []

        # process remaining
        if batch:
            added = await _process_batch(batch)
            created_readings.extend(added)

    except Exception:
        # Let caller handle HTTP exceptions / error reporting
        raise

    return created_readings


async def get_inverter(session: AsyncSession, inverter_id: int) -> Inverter | None:
    """Get inverter by ID."""
    return await session.get(Inverter, inverter_id)


async def get_inverters(session: AsyncSession) -> List[Inverter]:
    """Return all inverters."""
    statement = select(Inverter)
    result = await session.execute(statement)
    return list(result.scalars().all())

async def get_inverter_readings(
    session: AsyncSession,
    inverter_id: int,
    start_date: datetime | None = None,
    end_date: datetime | None = None
) -> List[InverterReading]:
    """Get readings for an inverter, optionally filtered by date range."""
    statement = select(InverterReading).where(
        InverterReading.inverter_id == inverter_id
    )
    
    if start_date:
        statement = statement.where(InverterReading.timestamp >= start_date)
    if end_date:
        statement = statement.where(InverterReading.timestamp <= end_date)
    
    statement = statement.order_by(InverterReading.timestamp)
    
    result = await session.execute(statement)
    return list(result.scalars().all())


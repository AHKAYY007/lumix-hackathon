"""
Inverter management endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any
from datetime import datetime
import csv
import io

from app.core.database import get_session
from app.models.inverter import Inverter, InverterCreate, InverterRead
from app.models.reading import InverterReading, InverterReadingRead
from app.handlers.ingestion import (
    create_inverter,
    ingest_readings,
    ingest_readings_stream,
    get_inverter,
    get_inverters,
    get_inverter_readings
)

router = APIRouter(prefix="/inverters", tags=["inverters"])


@router.post("/", response_model=InverterRead, status_code=status.HTTP_201_CREATED)
async def create_inverter_endpoint(
    inverter: InverterCreate,
    session: AsyncSession = Depends(get_session)
):
    """Create a new inverter."""
    return await create_inverter(session, inverter)



@router.get("", response_model=List[InverterRead])
async def list_inverters_endpoint(
    session: AsyncSession = Depends(get_session)
):
    """List all inverters."""
    inverters = await get_inverters(session)
    return inverters


@router.get("/{inverter_id}", response_model=InverterRead)
async def get_inverter_endpoint(
    inverter_id: int,
    session: AsyncSession = Depends(get_session)
):
    """Get inverter by ID."""
    inverter = await get_inverter(session, inverter_id)
    if not inverter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inverter {inverter_id} not found"
        )
    return inverter


@router.post("/{inverter_id}/readings", response_model=List[InverterReadingRead])
async def ingest_inverter_readings(
    inverter_id: int,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session)
):
    """
    Ingest inverter readings from CSV file upload.
    
    CSV format expected:
    timestamp,kwh
    2025-01-15T10:00:00,5.5
    2025-01-15T11:00:00,6.2
    ...
    
    The endpoint will parse the CSV and create readings for the specified inverter.
    """
    # Verify the file is CSV
    if not file.filename.endswith('.csv'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a CSV file"
        )
    
    try:
        # Stream-parse CSV from the uploaded file to avoid loading whole file into memory.
        # Use the underlying file buffer and a TextIOWrapper for line-by-line parsing.
        file.file.seek(0)
        text_stream = io.TextIOWrapper(file.file, encoding="utf-8")
        reader = csv.DictReader(text_stream)

        def rows_generator():
            for row_num, row in enumerate(reader, start=2):
                if not row:
                    continue
                try:
                    yield {
                        "inverter_id": inverter_id,
                        "timestamp": row.get("timestamp", "").strip(),
                        "kwh": float(row.get("kwh", 0))
                    }
                except ValueError as e:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid data in row {row_num}: {str(e)}"
                    )

        # Use the streaming ingest handler which commits in batches
        created_readings = await ingest_readings_stream(session, rows_generator())
        return created_readings

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error processing CSV file: {str(e)}"
        )


@router.get("/{inverter_id}/readings", response_model=List[InverterReadingRead])
async def get_inverter_readings_endpoint(
    inverter_id: int,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    session: AsyncSession = Depends(get_session)
):
    """Get readings for an inverter, optionally filtered by date range."""
    readings = await get_inverter_readings(
        session,
        inverter_id,
        start_date,
        end_date
    )
    return readings


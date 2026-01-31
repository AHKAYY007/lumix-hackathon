"""
Report and aggregation handlers.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, func, and_
from datetime import date, datetime
from typing import List, Dict, Any, Optional

from app.models.credit import CarbonCredit, CreditStatus
from app.models.inverter import Inverter
from app.models.reading import InverterReading


async def get_fleet_summary(session: AsyncSession) -> Dict[str, Any]:
    """
    Get fleet-level aggregation summary.
    
    Returns:
        Dictionary with total credits, verified credits, flagged credits, etc.
    """
    # Total inverters
    total_inverters = await session.execute(select(func.count(Inverter.id)))
    inverter_count = total_inverters.scalar() or 0
    
    # Total credits by status
    total_credits = await session.execute(select(func.count(CarbonCredit.id)))
    credit_count = total_credits.scalar() or 0
    
    verified_credits = await session.execute(
        select(func.count(CarbonCredit.id)).where(
            CarbonCredit.status == CreditStatus.VERIFIED
        )
    )
    verified_count = verified_credits.scalar() or 0
    
    flagged_credits = await session.execute(
        select(func.count(CarbonCredit.id)).where(
            CarbonCredit.status == CreditStatus.FLAGGED
        )
    )
    flagged_count = flagged_credits.scalar() or 0
    
    pending_credits = await session.execute(
        select(func.count(CarbonCredit.id)).where(
            CarbonCredit.status == CreditStatus.PENDING
        )
    )
    pending_count = pending_credits.scalar() or 0
    
    # Total tonnes CO2 avoided
    total_tonnes = await session.execute(
        select(func.sum(CarbonCredit.tonnes))
    )
    total_tonnes_value = total_tonnes.scalar() or 0.0
    
    # Verified tonnes
    verified_tonnes = await session.execute(
        select(func.sum(CarbonCredit.tonnes)).where(
            CarbonCredit.status == CreditStatus.VERIFIED
        )
    )
    verified_tonnes_value = verified_tonnes.scalar() or 0.0
    
    return {
        "total_inverters": inverter_count,
        "total_credits": credit_count,
        "verified_credits": verified_count,
        "flagged_credits": flagged_count,
        "pending_credits": pending_count,
        "total_tonnes_co2": round(total_tonnes_value, 2),
        "verified_tonnes_co2": round(verified_tonnes_value, 2)
    }


async def get_inverter_auditor_view(
    session: AsyncSession,
    inverter_id: int
) -> Dict[str, Any]:
    """
    Get single-inverter "auditor view" with all relevant data.
    
    Returns:
        Dictionary with inverter details, readings, credits, and verification status
    """
    # Get inverter
    inverter = await session.get(Inverter, inverter_id)
    if not inverter:
        raise ValueError(f"Inverter {inverter_id} not found")
    
    # Get all readings
    readings_statement = select(InverterReading).where(
        InverterReading.inverter_id == inverter_id
    ).order_by(InverterReading.timestamp.desc())
    
    readings_result = await session.execute(readings_statement)
    readings = list(readings_result.scalars().all())
    
    # Get all credits
    credits_statement = select(CarbonCredit).where(
        CarbonCredit.inverter_id == inverter_id
    ).order_by(CarbonCredit.credit_date.desc())
    
    credits_result = await session.execute(credits_statement)
    credits = list(credits_result.scalars().all())
    
    # Calculate totals
    total_kwh = sum(r.kwh for r in readings)
    total_tonnes = sum(c.tonnes for c in credits)
    verified_tonnes = sum(c.tonnes for c in credits if c.status == CreditStatus.VERIFIED)
    
    return {
        "inverter": {
            "id": inverter.id,
            "gps_lat": inverter.gps_lat,
            "gps_lon": inverter.gps_lon,
            "capacity_kw": inverter.capacity_kw,
            "created_at": inverter.created_at.isoformat()
        },
        "readings_count": len(readings),
        "total_kwh": round(total_kwh, 2),
        "credits_count": len(credits),
        "total_tonnes_co2": round(total_tonnes, 2),
        "verified_tonnes_co2": round(verified_tonnes, 2),
        "credits": [
            {
                "id": c.id,
                "date": c.credit_date.isoformat(),
                "tonnes": c.tonnes,
                "status": c.status.value,
                "correlation": c.correlation,
                "flagged_reason": c.flagged_reason,
                "created_at": c.created_at.isoformat(),
                "updated_at": c.updated_at.isoformat()
            }
            for c in credits
        ],
        "recent_readings": [
            {
                "id": r.id,
                "timestamp": r.timestamp.isoformat(),
                "kwh": r.kwh
            }
            for r in readings[:10]  # Last 10 readings
        ]
    }


async def get_credits_by_status(
    session: AsyncSession,
    status: Optional[CreditStatus] = None
) -> List[CarbonCredit]:
    """Get credits filtered by status."""
    statement = select(CarbonCredit)
    
    if status:
        statement = statement.where(CarbonCredit.status == status)
    
    statement = statement.order_by(CarbonCredit.credit_date.desc())
    
    result = await session.execute(statement)
    return list(result.scalars().all())


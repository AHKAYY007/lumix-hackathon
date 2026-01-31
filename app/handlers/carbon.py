"""
Carbon credit calculation handler.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, func
from datetime import date, datetime
from typing import List, Optional

from app.models.credit import CarbonCredit, CarbonCreditCreate, CreditStatus
from app.models.reading import InverterReading
from app.core.constants import EMISSION_FACTOR_KG_PER_KWH
from app.utils.time import datetime_to_date


def calculate_co2_avoided(kwh: float) -> float:
    """
    Calculate CO2 avoided in metric tonnes.
    
    Formula: (kWh * 1.2 kg CO2/kWh) / 1000 = tonnes CO2
    
    Args:
        kwh: Energy produced in kilowatt-hours
        
    Returns:
        CO2 avoided in metric tonnes
    """
    kg_co2 = kwh * EMISSION_FACTOR_KG_PER_KWH
    tonnes = kg_co2 / 1000.0
    return tonnes


async def calculate_daily_credit(
    session: AsyncSession,
    inverter_id: int,
    credit_date: date
) -> CarbonCredit:
    """
    Calculate daily CO2 avoided for an inverter on a specific date.
    
    Creates or updates a carbon credit record.
    """
    # Get all readings for the date
    start_datetime = datetime.combine(credit_date, datetime.min.time())
    end_datetime = datetime.combine(credit_date, datetime.max.time())
    
    statement = select(func.sum(InverterReading.kwh)).where(
        InverterReading.inverter_id == inverter_id,
        InverterReading.timestamp >= start_datetime,
        InverterReading.timestamp <= end_datetime
    )
    
    result = await session.execute(statement)
    total_kwh = result.scalar() or 0.0
    
    # Calculate tonnes
    tonnes = calculate_co2_avoided(total_kwh)
    
    # Check if credit already exists
    existing_credit = await session.execute(
        select(CarbonCredit).where(
            CarbonCredit.inverter_id == inverter_id,
            CarbonCredit.credit_date == credit_date
        )
    )
    credit = existing_credit.scalars().first()
    
    if credit:
        # Update existing credit
        credit.tonnes = tonnes
        credit.updated_at = datetime.utcnow()
        # Don't overwrite status if already verified/flagged
        if credit.status == CreditStatus.PENDING:
            credit.status = CreditStatus.PENDING
    else:
        # Create new credit
        credit = CarbonCredit(
            credit_date=credit_date,
            inverter_id=inverter_id,
            tonnes=tonnes,
            status=CreditStatus.PENDING
        )
        session.add(credit)
    
    await session.commit()
    await session.refresh(credit)
    
    return credit


async def get_credit(
    session: AsyncSession,
    inverter_id: int,
    credit_date: date
) -> Optional[CarbonCredit]:
    """Get carbon credit for an inverter on a specific date."""
    statement = select(CarbonCredit).where(
        CarbonCredit.inverter_id == inverter_id,
        CarbonCredit.credit_date == credit_date
    )
    result = await session.execute(statement)
    return result.scalars().first()


async def get_credits_by_inverter(
    session: AsyncSession,
    inverter_id: int
) -> List[CarbonCredit]:
    """Get all credits for an inverter."""
    statement = select(CarbonCredit).where(
        CarbonCredit.inverter_id == inverter_id
    ).order_by(CarbonCredit.credit_date.desc())
    
    result = await session.execute(statement)
    return list(result.scalars().all())


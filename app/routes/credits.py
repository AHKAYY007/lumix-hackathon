"""
Carbon credit endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date
from typing import List

from app.core.database import get_session
from app.models.credit import CarbonCredit, CarbonCreditCreate, CarbonCreditRead, CreditStatus
from app.handlers.carbon import (
    calculate_daily_credit,
    get_credit,
    get_credits_by_inverter
)
from app.handlers.verification import verify_credit

router = APIRouter(prefix="/credits", tags=["credits"])


@router.post("/calculate", response_model=CarbonCreditRead)
async def calculate_credit_endpoint(
    inverter_id: int,
    credit_date: date,
    session: AsyncSession = Depends(get_session)
):
    """
    Calculate daily CO2 avoided for an inverter on a specific date.
    Creates or updates a carbon credit record.
    """
    try:
        credit = await calculate_daily_credit(session, inverter_id, credit_date)
        return credit
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/{inverter_id}/{credit_date}", response_model=CarbonCreditRead)
async def get_credit_endpoint(
    inverter_id: int,
    credit_date: date,
    session: AsyncSession = Depends(get_session)
):
    """Get carbon credit for an inverter on a specific date."""
    credit = await get_credit(session, inverter_id, credit_date)
    if not credit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Credit not found for inverter {inverter_id} on {credit_date}"
        )
    return credit


@router.get("/{inverter_id}", response_model=List[CarbonCreditRead])
async def get_inverter_credits_endpoint(
    inverter_id: int,
    session: AsyncSession = Depends(get_session)
):
    """Get all credits for an inverter."""
    credits = await get_credits_by_inverter(session, inverter_id)
    return credits


@router.post("/{inverter_id}/{credit_date}/verify", response_model=CarbonCreditRead)
async def verify_credit_endpoint(
    inverter_id: int,
    credit_date: date,
    session: AsyncSession = Depends(get_session)
):
    """
    Verify a carbon credit by comparing inverter data with NASA POWER satellite data.
    
    Verification logic:
    - Fetches NASA POWER data for inverter location
    - Calculates theoretical output from satellite irradiance
    - Compares inverter curve vs satellite curve
    - Calculates correlation
    - If correlation > 90% and no fraud → VERIFIED
    - If inverter output > theoretical output → FLAGGED
    """
    try:
        credit = await verify_credit(session, inverter_id, credit_date)
        return credit
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Verification failed: {str(e)}"
        )


@router.patch("/{inverter_id}/{credit_date}/status", response_model=CarbonCreditRead)
async def update_credit_status_endpoint(
    inverter_id: int,
    credit_date: date,
    new_status: CreditStatus,
    session: AsyncSession = Depends(get_session)
):
    """
    Update credit status (e.g., mark as SUBMITTED).
    Note: Cannot change from VERIFIED/FLAGGED to PENDING without re-verification.
    """
    credit = await get_credit(session, inverter_id, credit_date)
    if not credit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Credit not found for inverter {inverter_id} on {credit_date}"
        )
    
    # Allow status updates (e.g., to SUBMITTED)
    credit.status = new_status
    from datetime import datetime
    credit.updated_at = datetime.utcnow()
    
    await session.commit()
    await session.refresh(credit)
    
    return credit



@router.post("/", response_model=CarbonCreditRead, status_code=status.HTTP_201_CREATED)
async def create_credit_endpoint(
    credit: CarbonCreditCreate,
    session: AsyncSession = Depends(get_session)
):
    """Create a new carbon credit record."""
    new_credit = CarbonCredit(**credit.model_dump())
    session.add(new_credit)
    await session.commit()
    await session.refresh(new_credit)
    return new_credit


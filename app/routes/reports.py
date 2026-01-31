"""
Report and aggregation endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from app.core.database import get_session
from app.models.credit import CreditStatus
from app.handlers.reports import (
    get_fleet_summary,
    get_inverter_auditor_view,
    get_credits_by_status
)
from app.models.credit import CarbonCreditRead

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/fleet/summary")
async def fleet_summary_endpoint(
    session: AsyncSession = Depends(get_session)
) -> Dict[str, Any]:
    """
    Get fleet-level aggregation summary.
    
    Returns:
        - total_inverters
        - total_credits
        - verified_credits
        - flagged_credits
        - pending_credits
        - total_tonnes_co2
        - verified_tonnes_co2
    """
    return await get_fleet_summary(session)


@router.get("/inverters/{inverter_id}/audit")
async def inverter_auditor_view_endpoint(
    inverter_id: int,
    session: AsyncSession = Depends(get_session)
) -> Dict[str, Any]:
    """
    Get single-inverter "auditor view" with all relevant data.
    
    Returns:
        - inverter details
        - readings count and total kWh
        - credits count and total tonnes
        - verified tonnes
        - list of all credits with status
        - recent readings
    """
    try:
        return await get_inverter_auditor_view(session, inverter_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get("/credits", response_model=list[CarbonCreditRead])
async def get_credits_by_status_endpoint(
    status: CreditStatus | None = None,
    session: AsyncSession = Depends(get_session)
):
    """Get credits filtered by status."""
    credits = await get_credits_by_status(session, status)
    return credits


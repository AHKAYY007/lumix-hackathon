"""
Verification and fraud detection handler.
Compares inverter data with NASA POWER satellite data.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, func, and_
from datetime import date, datetime
from typing import List, Tuple, Optional
import math

from app.models.credit import CarbonCredit, CreditStatus
from app.models.reading import InverterReading
from app.models.satellite import SatelliteReading
from app.models.inverter import Inverter
from app.models.audit import AuditLog
from app.handlers.nasa import fetch_nasa_power_data, parse_nasa_response, store_satellite_readings
from app.core.constants import MIN_CORRELATION_THRESHOLD, FRAUD_FLAG_THRESHOLD
from app.utils.hashing import hash_payload


def calculate_theoretical_output(
    irradiance_w_per_m2: float,
    capacity_kw: float,
    panel_efficiency: float = 0.20
) -> float:
    """
    Calculate maximum theoretical solar output in kWh.
    
    Formula: irradiance (W/m²) * panel_area (m²) * efficiency * hours
    
    Assumptions:
    - Panel efficiency: 20% (typical for commercial panels)
    - Panel area calculated from capacity: 1 kW ≈ 5 m² (at 20% efficiency)
    - Hourly calculation, so hours = 1
    
    Args:
        irradiance_w_per_m2: Solar irradiance in W/m²
        capacity_kw: Inverter capacity in kW
        panel_efficiency: Panel efficiency (default 0.20 = 20%)
        
    Returns:
        Theoretical output in kWh
    """
    # Calculate panel area: capacity_kw / (1 kW per 5 m² at 20% efficiency)
    # At 1000 W/m² irradiance and 20% efficiency: 1 kW = 5 m²
    panel_area_m2 = capacity_kw * 5.0
    
    # Convert W/m² to kW/m²
    irradiance_kw_per_m2 = irradiance_w_per_m2 / 1000.0
    
    # Theoretical output = irradiance * area * efficiency * hours (1 hour)
    theoretical_kwh = irradiance_kw_per_m2 * panel_area_m2 * panel_efficiency * 1.0
    
    return theoretical_kwh


def calculate_correlation(
    inverter_values: List[float],
    satellite_values: List[float]
) -> float:
    """
    Calculate Pearson correlation coefficient between two time series.
    
    Args:
        inverter_values: List of inverter kWh values
        satellite_values: List of theoretical kWh values from satellite
        
    Returns:
        Correlation coefficient (0-1)
    """
    if len(inverter_values) != len(satellite_values) or len(inverter_values) == 0:
        return 0.0
    
    # Calculate means
    mean_inv = sum(inverter_values) / len(inverter_values)
    mean_sat = sum(satellite_values) / len(satellite_values)
    
    # Calculate numerator and denominators for Pearson correlation
    numerator = sum((inv - mean_inv) * (sat - mean_sat) for inv, sat in zip(inverter_values, satellite_values))
    
    sum_sq_inv = sum((inv - mean_inv) ** 2 for inv in inverter_values)
    sum_sq_sat = sum((sat - mean_sat) ** 2 for sat in satellite_values)
    
    denominator = math.sqrt(sum_sq_inv * sum_sq_sat)
    
    if denominator == 0:
        return 0.0
    
    correlation = numerator / denominator
    
    # Return absolute value (we care about strength of relationship, not direction)
    return abs(correlation)


async def verify_credit(
    session: AsyncSession,
    inverter_id: int,
    credit_date: date
) -> CarbonCredit:
    """
    Verify a carbon credit by comparing inverter data with NASA POWER satellite data.
    
    Verification logic:
    1. Fetch inverter readings for the date
    2. Fetch NASA POWER data for inverter location and date
    3. Calculate theoretical output from satellite irradiance
    4. Compare inverter curve vs satellite curve
    5. Calculate correlation
    6. If correlation > 90% and no fraud detected → VERIFIED
    7. If inverter output > theoretical output → FLAGGED
    8. Otherwise → PENDING
    
    Args:
        session: Database session
        inverter_id: Inverter ID
        credit_date: Date to verify
        
    Returns:
        Updated CarbonCredit with verification status
    """
    # Get inverter
    inverter = await session.get(Inverter, inverter_id)
    if not inverter:
        raise ValueError(f"Inverter {inverter_id} not found")
    
    # Get credit
    credit = await session.execute(
        select(CarbonCredit).where(
            CarbonCredit.inverter_id == inverter_id,
            CarbonCredit.credit_date == credit_date
        )
    )
    credit = credit.scalars().first()
    
    if not credit:
        raise ValueError(f"Credit not found for inverter {inverter_id} on {credit_date}")
    
    # Get inverter readings for the date
    start_datetime = datetime.combine(credit_date, datetime.min.time())
    end_datetime = datetime.combine(credit_date, datetime.max.time())
    
    readings_statement = select(InverterReading).where(
        and_(
            InverterReading.inverter_id == inverter_id,
            InverterReading.timestamp >= start_datetime,
            InverterReading.timestamp <= end_datetime
        )
    ).order_by(InverterReading.timestamp)
    
    readings_result = await session.execute(readings_statement)
    inverter_readings = list(readings_result.scalars().all())
    
    if not inverter_readings:
        credit.status = CreditStatus.PENDING
        credit.flagged_reason = "No inverter readings available for verification"
        await session.commit()
        await session.refresh(credit)
        return credit
    
    # Fetch NASA POWER data
    try:
        nasa_response = await fetch_nasa_power_data(
            lat=inverter.gps_lat,
            lon=inverter.gps_lon,
            start_date=credit_date,
            end_date=credit_date
        )
        nasa_readings = parse_nasa_response(nasa_response)
        
        # Store satellite readings
        await store_satellite_readings(
            session,
            inverter.gps_lat,
            inverter.gps_lon,
            nasa_readings
        )
        
    except Exception as e:
        credit.status = CreditStatus.PENDING
        credit.flagged_reason = f"Failed to fetch NASA POWER data: {str(e)}"
        await session.commit()
        await session.refresh(credit)
        return credit
    
    if not nasa_readings:
        credit.status = CreditStatus.PENDING
        credit.flagged_reason = "No satellite data available for verification"
        await session.commit()
        await session.refresh(credit)
        return credit
    
    # Get satellite reading for the date (should be one)
    satellite_data = nasa_readings[0]
    satellite_irradiance = satellite_data["irradiance"]
    
    # Calculate theoretical output for each hour
    # For simplicity, we'll use the daily average irradiance
    # In production, you'd want hourly satellite data
    theoretical_kwh = calculate_theoretical_output(
        irradiance_w_per_m2=satellite_irradiance,
        capacity_kw=inverter.capacity_kw
    )
    
    # Get total inverter output for the day
    total_inverter_kwh = sum(r.kwh for r in inverter_readings)
    
    # Check for fraud: if inverter output exceeds theoretical maximum
    # We multiply theoretical by a safety factor (e.g., 1.2) to account for variations
    max_theoretical = theoretical_kwh * 24 * 1.2  # Daily theoretical max with safety margin
    
    if total_inverter_kwh > max_theoretical:
        credit.status = CreditStatus.FLAGGED
        credit.correlation = 0.0
        credit.flagged_reason = (
            f"Inverter output ({total_inverter_kwh:.2f} kWh) exceeds "
            f"theoretical maximum ({max_theoretical:.2f} kWh)"
        )
        await session.commit()
        await session.refresh(credit)
        
        # Audit log
        audit = AuditLog(
            payload_hash=hash_payload({
                "inverter_id": inverter_id,
                "date": credit_date.isoformat(),
                "reason": credit.flagged_reason
            }),
            action="credit_flagged",
            entity_type="carbon_credit",
            entity_id=credit.id
        )
        session.add(audit)
        await session.commit()
        
        return credit
    
    # Calculate correlation between inverter readings and theoretical curve
    # For daily comparison, we'll use hourly averages
    # Create hourly buckets for inverter readings
    hourly_inverter = {}
    for reading in inverter_readings:
        hour = reading.timestamp.hour
        if hour not in hourly_inverter:
            hourly_inverter[hour] = []
        hourly_inverter[hour].append(reading.kwh)
    
    # Average hourly values
    inverter_hourly = [sum(hourly_inverter.get(h, [0])) / max(len(hourly_inverter.get(h, [0])), 1) 
                       for h in range(24)]
    
    # Theoretical hourly values (assuming constant irradiance for simplicity)
    # In production, use hourly satellite data
    satellite_hourly = [theoretical_kwh] * 24
    
    # Calculate correlation
    correlation = calculate_correlation(inverter_hourly, satellite_hourly)
    credit.correlation = correlation
    
    # Verify if correlation > 90%
    if correlation >= MIN_CORRELATION_THRESHOLD:
        credit.status = CreditStatus.VERIFIED
        credit.flagged_reason = None
    else:
        credit.status = CreditStatus.PENDING
        credit.flagged_reason = f"Correlation ({correlation:.2%}) below threshold ({MIN_CORRELATION_THRESHOLD:.2%})"
    
    credit.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(credit)
    
    # Audit log
    audit = AuditLog(
        payload_hash=hash_payload({
            "inverter_id": inverter_id,
            "date": credit_date.isoformat(),
            "status": credit.status.value,
            "correlation": correlation
        }),
        action="credit_verified" if credit.status == CreditStatus.VERIFIED else "credit_pending",
        entity_type="carbon_credit",
        entity_id=credit.id
    )
    session.add(audit)
    await session.commit()
    
    return credit


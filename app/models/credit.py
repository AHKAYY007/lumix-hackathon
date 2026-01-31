"""
Carbon credit model - tracks daily CO2 avoided and verification status.
"""

from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, TYPE_CHECKING
from datetime import date, datetime
from enum import Enum
from sqlalchemy.orm import Mapped


if TYPE_CHECKING:
    from app.models.inverter import Inverter

class CreditStatus(str, Enum):
    """Carbon credit status lifecycle."""
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    FLAGGED = "FLAGGED"
    SUBMITTED = "SUBMITTED"


class CarbonCreditBase(SQLModel):
    """Base carbon credit schema."""
    credit_date: date = Field(..., description="Date of the credit", serialization_alias="date")
    inverter_id: int = Field(..., foreign_key="inverters.id")
    tonnes: float = Field(..., description="CO2 avoided in metric tonnes", ge=0)
    status: "CreditStatus" = Field(default=CreditStatus.PENDING)
    correlation: Optional[float] = Field(
        default=None,
        description="Correlation between inverter and satellite data (0-1)",
        ge=0,
        le=1
    )
    flagged_reason: Optional[str] = Field(
        default=None,
        description="Reason for flagging if status is FLAGGED"
    )


class CarbonCredit(CarbonCreditBase, table=True):
    """Carbon credit database table."""
    __tablename__ = "carbon_credits"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationship
    inverter: "Inverter" = Relationship(back_populates="credits")


class CarbonCreditCreate(CarbonCreditBase):
    """Schema for creating a carbon credit."""
    pass


class CarbonCreditRead(CarbonCreditBase):
    """Schema for reading a carbon credit."""
    id: int
    created_at: datetime
    updated_at: datetime


"""
Audit log model - append-only tamper-evident audit trail.
"""

from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime


class AuditLogBase(SQLModel):
    """Base audit log schema."""
    payload_hash: str = Field(..., description="SHA-256 hash of the audited payload")
    action: str = Field(..., description="Action type (e.g., 'credit_created', 'credit_verified')")
    entity_type: str = Field(..., description="Entity type (e.g., 'carbon_credit', 'inverter_reading')")
    entity_id: Optional[int] = Field(default=None, description="ID of the entity")
    extra_data: Optional[str] = Field(
        default=None,
        description="JSON string of additional metadata"
    )


class AuditLog(AuditLogBase, table=True):
    """Audit log database table - append-only."""
    
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AuditLogCreate(AuditLogBase):
    """Schema for creating an audit log entry."""
    pass


class AuditLogRead(AuditLogBase):
    """Schema for reading an audit log entry."""
    id: int
    created_at: datetime


"""
Health check endpoints.
"""

from fastapi import APIRouter
from app.core.config import get_settings

router = APIRouter(prefix="/health", tags=["health"])
settings = get_settings()


@router.get("/")
async def health_check():
    """Root health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version
    }


@router.get("/live")
async def liveness():
    """Liveness probe endpoint."""
    return {"status": "alive"}


@router.get("/ready")
async def readiness():
    """Readiness probe endpoint."""
    return {"status": "ready"}


"""
FastAPI application entry point with async lifespan.
"""
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.database import init_db, close_db
from app.routes import health, inverters, credits, reports

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Async lifespan manager for startup and shutdown."""
    # Startup
    await init_db()
    yield
    # Shutdown
    await close_db()


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Digital MRV (dMRV) engine for carbon credits",
    lifespan=lifespan
)

# CORS middleware (for Streamlit dashboard)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(health.router)
app.include_router(inverters.router)
app.include_router(credits.router)
app.include_router(reports.router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/health"
    }


if __name__ == "__main__":
    uvicorn.run(
        app,
        host='0.0.0.0',
        port=settings.port,
        debug=settings.debug
    )
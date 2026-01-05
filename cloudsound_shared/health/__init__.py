"""Health check endpoint template."""
from fastapi import APIRouter, status
from pydantic import BaseModel
from typing import Dict, Any, Optional
from datetime import datetime

router = APIRouter(prefix="/health", tags=["health"])

class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    timestamp: datetime
    version: str
    checks: Dict[str, Any]

@router.get("", response_model=HealthResponse)
@router.get("/", response_model=HealthResponse)
async def health_check(version: str = "1.0.0") -> HealthResponse:
    """Basic health check endpoint."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow(),
        version=version,
        checks={}
    )

@router.get("/ready", response_model=HealthResponse)
async def readiness_check(version: str = "1.0.0") -> HealthResponse:
    """Readiness check endpoint - override in services to check dependencies."""
    return HealthResponse(
        status="ready",
        timestamp=datetime.utcnow(),
        version=version,
        checks={}
    )

@router.get("/live", response_model=HealthResponse)
async def liveness_check(version: str = "1.0.0") -> HealthResponse:
    """Liveness check endpoint."""
    return HealthResponse(
        status="alive",
        timestamp=datetime.utcnow(),
        version=version,
        checks={}
    )


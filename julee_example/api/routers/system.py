"""
System API router for the julee_example CEAP system.

This module provides system-level API endpoints including health checks,
status information, and other operational endpoints.

Routes defined at root level:
- GET /health - Health check endpoint

These routes are mounted at the root level in the main app.
"""

import logging
from datetime import datetime, timezone
from fastapi import APIRouter

from julee_example.api.responses import HealthCheckResponse

logger = logging.getLogger(__name__)

# Create the router for system endpoints
router = APIRouter()


@router.get("/health", response_model=HealthCheckResponse)
async def health_check() -> HealthCheckResponse:
    """Health check endpoint."""
    return HealthCheckResponse(
        status="healthy",
        version="0.1.0",
        timestamp=datetime.now(timezone.utc),
    )

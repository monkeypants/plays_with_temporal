"""
System API router for the julee_example CEAP system.

This module provides system-level API endpoints including health checks,
status information, and other operational endpoints.

Routes defined at root level:
- GET /health - Health check endpoint

These routes are mounted at the root level in the main app.
"""

import logging
import asyncio
from datetime import datetime, timezone
from fastapi import APIRouter
from temporalio.client import Client
from minio import Minio
import os

from julee_example.api.responses import (
    HealthCheckResponse,
    ServiceHealthStatus,
    ServiceStatus,
    SystemStatus,
)

logger = logging.getLogger(__name__)

# Create the router for system endpoints
router = APIRouter()


async def check_temporal_health() -> ServiceStatus:
    """Check if Temporal service is available."""
    try:
        # Get Temporal server address from environment or use default
        temporal_address = os.getenv(
            "TEMPORAL_ENDPOINT", os.getenv("TEMPORAL_HOST", "localhost:7233")
        )

        # Create a client and try to connect
        _ = await Client.connect(temporal_address, namespace="default")
        # Simple check - if we can connect, assume it's working
        return ServiceStatus.UP
    except Exception as e:
        logger.warning("Temporal health check failed: %s", e)
        return ServiceStatus.DOWN


async def check_storage_health() -> ServiceStatus:
    """Check if storage service (Minio) is available."""
    try:
        # Get Minio configuration (prioritize Docker network address)
        endpoint = os.environ.get("MINIO_ENDPOINT", "localhost:9000")
        access_key = os.environ.get("MINIO_ACCESS_KEY", "minioadmin")
        secret_key = os.environ.get("MINIO_SECRET_KEY", "minioadmin")
        secure = os.environ.get("MINIO_SECURE", "false").lower() == "true"

        # Create Minio client
        client = Minio(
            endpoint=endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure,
        )

        # Test connection by listing buckets
        _ = list(client.list_buckets())
        return ServiceStatus.UP
    except Exception as e:
        logger.warning("Storage health check failed: %s", e)
        return ServiceStatus.DOWN


async def check_api_health() -> ServiceStatus:
    """Check if API service is available (self-check)."""
    # Since we're responding, API is up
    return ServiceStatus.UP


def determine_overall_status(services: ServiceHealthStatus) -> SystemStatus:
    """Determine overall system status based on service statuses."""
    service_statuses = [services.api, services.temporal, services.storage]

    if all(status == ServiceStatus.UP for status in service_statuses):
        return SystemStatus.HEALTHY
    elif any(status == ServiceStatus.UP for status in service_statuses):
        return SystemStatus.DEGRADED
    else:
        return SystemStatus.UNHEALTHY


@router.get("/health", response_model=HealthCheckResponse)
async def health_check() -> HealthCheckResponse:
    """Comprehensive health check endpoint that checks all services."""
    logger.info("Performing health check")

    # Check all services concurrently
    results = await asyncio.gather(
        check_api_health(),
        check_temporal_health(),
        check_storage_health(),
        return_exceptions=True,
    )

    # Handle any exceptions from the health checks
    api_status = results[0]
    temporal_status = results[1]
    storage_status = results[2]

    if isinstance(api_status, Exception):
        logger.error("API health check error: %s", api_status)
        api_status = ServiceStatus.DOWN
    if isinstance(temporal_status, Exception):
        logger.error("Temporal health check error: %s", temporal_status)
        temporal_status = ServiceStatus.DOWN
    if isinstance(storage_status, Exception):
        logger.error("Storage health check error: %s", storage_status)
        storage_status = ServiceStatus.DOWN

    # Create service health status with proper typing
    services = ServiceHealthStatus(
        api=ServiceStatus(api_status),
        temporal=ServiceStatus(temporal_status),
        storage=ServiceStatus(storage_status),
    )

    # Determine overall status
    overall_status = determine_overall_status(services)

    # Return response with string timestamp as expected by frontend
    return HealthCheckResponse(
        status=overall_status,
        timestamp=datetime.now(timezone.utc).isoformat(),
        services=services,
    )

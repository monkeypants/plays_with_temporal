"""
Pydantic models for API responses.
These define the contract between the API and external clients.

Following clean architecture principles, most endpoints return domain models
directly rather than creating wrapper response models. This file contains
only response models that are specific to API concerns and not represented
by existing domain models.
"""

from pydantic import BaseModel
from enum import Enum


class ServiceStatus(str, Enum):
    """Service status enumeration."""

    UP = "up"
    DOWN = "down"


class SystemStatus(str, Enum):
    """Overall system status enumeration."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class ServiceHealthStatus(BaseModel):
    """Health status for individual services."""

    api: ServiceStatus
    temporal: ServiceStatus
    storage: ServiceStatus


class HealthCheckResponse(BaseModel):
    """Response for health check endpoint."""

    status: SystemStatus
    timestamp: str
    services: ServiceHealthStatus

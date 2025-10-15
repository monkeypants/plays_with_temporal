"""
Pydantic models for API responses.
These define the contract between the API and external clients.

Following clean architecture principles, most endpoints return domain models
directly rather than creating wrapper response models. This file contains
only response models that are specific to API concerns and not represented
by existing domain models.
"""

from pydantic import BaseModel
from datetime import datetime


class HealthCheckResponse(BaseModel):
    """Response for health check endpoint."""

    status: str
    version: str
    timestamp: datetime

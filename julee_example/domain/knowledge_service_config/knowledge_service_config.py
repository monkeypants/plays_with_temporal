"""
KnowledgeService domain models for the Capture, Extract, Assemble,
Publish workflow.

This module contains the KnowledgeService domain object that represents
knowledge services in the CEAP workflow system.

A KnowledgeService defines a service that can store documents and execute
queries against them. It acts as an interface to external AI/ML services
that can analyze and extract information from documents.

All domain models use Pydantic BaseModel for validation, serialization,
and type safety, following the patterns established in the sample project.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime, timezone
from enum import Enum


class ServiceApi(str, Enum):
    """Supported knowledge service APIs."""

    ANTHROPIC = "anthropic"


class KnowledgeServiceConfig(BaseModel):
    """Knowledge service configuration that defines how to interact with
    an external knowledge/AI service.

    A KnowledgeServiceConfig represents a service endpoint that can store
    documents and execute queries against them. This could be an AI service,
    vector database, search engine, or any other service that can analyze
    documents and answer questions about them.
    """

    # Core service identification
    knowledge_service_id: str = Field(
        description="Unique identifier for this knowledge service"
    )
    name: str = Field(
        description="Human-readable name for the knowledge service"
    )
    description: str = Field(
        description="Description of what this knowledge service does"
    )
    service_api: ServiceApi = Field(
        description="The external API/service this knowledge service uses"
    )

    # Timestamps
    created_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    @field_validator("knowledge_service_id")
    @classmethod
    def knowledge_service_id_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Knowledge service ID cannot be empty")
        return v.strip()

    @field_validator("name")
    @classmethod
    def name_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Knowledge service name cannot be empty")
        return v.strip()

    @field_validator("description")
    @classmethod
    def description_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Knowledge service description cannot be empty")
        return v.strip()

    @field_validator("service_api")
    @classmethod
    def service_api_must_be_valid(cls, v: ServiceApi) -> ServiceApi:
        if v not in ServiceApi:
            raise ValueError(
                f"Invalid service API: {v}. Must be one of {list(ServiceApi)}"
            )
        return v

"""
KnowledgeServiceQuery domain models for the Capture, Extract, Assemble,
Publish
workflow.

This module contains the KnowledgeServiceQuery domain object that represents
specific queries to knowledge services for data extraction in the CEAP
workflow system.

A KnowledgeServiceQuery defines a specific extraction operation that can be
performed against a knowledge service to extract data for a particular part
of an AssemblySpecification's JSON schema.

All domain models use Pydantic BaseModel for validation, serialization,
and type safety, following the patterns established in the sample project.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime, timezone


class KnowledgeServiceQuery(BaseModel):
    """Knowledge service query configuration for extracting specific data.

    A KnowledgeServiceQuery represents a specific extraction operation that
    can be performed against a knowledge service. It defines which knowledge
    service to use and what prompt to send for data extraction.

    When executed, the relevant section of the AssemblySpecification's JSON
    schema will be
    passed along with the prompt to ensure the knowledge service response
    conforms to the expected structure and validation requirements.

    The mapping between queries and schema sections is handled by the
    AssemblySpecification's knowledge_service_queries field.
    """

    # Core query identification
    query_id: str = Field(description="Unique identifier for this query")
    name: str = Field(
        description="Human-readable name describing the query purpose"
    )

    # Knowledge service configuration
    knowledge_service_id: str = Field(
        description="Identifier of the knowledge service to query"
    )
    prompt: str = Field(
        description="The specific prompt to send to the knowledge service "
        "for this extraction"
    )

    created_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    @field_validator("query_id")
    @classmethod
    def query_id_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Query ID cannot be empty")
        return v.strip()

    @field_validator("name")
    @classmethod
    def name_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Query name cannot be empty")
        return v.strip()

    @field_validator("knowledge_service_id")
    @classmethod
    def knowledge_service_id_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Knowledge service ID cannot be empty")
        return v.strip()

    @field_validator("prompt")
    @classmethod
    def prompt_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Query prompt cannot be empty")
        return v.strip()

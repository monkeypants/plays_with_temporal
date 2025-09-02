"""
Extractor domain models for the Capture, Extract, Assemble, Publish workflow.

This module contains the Extractor domain object that represents
data extraction configurations in the CEAP workflow system.

An Extractor defines how to extract specific pieces of structured data
from documents registered with the knowledge service.

All domain models use Pydantic BaseModel for validation, serialization,
and type safety, following the patterns established in the sample project.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from enum import Enum


class ExtractorStatus(str, Enum):
    """Status of an extractor configuration."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    DRAFT = "draft"
    DEPRECATED = "deprecated"


class ExtractorType(str, Enum):
    """Type of data extraction to perform."""

    METADATA = "metadata"  # Document metadata extraction
    STRUCTURED = "structured"  # Structured data extraction (e.g., tables, forms)
    SEMANTIC = "semantic"  # Semantic content extraction (e.g., topics, entities)
    COMPOSITE = "composite"  # Complex extraction that may use multiple approaches


class Extractor(BaseModel):
    """Extractor configuration that defines how to extract specific data from documents.

    An Extractor represents a specific type of data extraction operation
    that can be performed on documents in the knowledge service. This is
    a stub implementation - the full extractor system will be designed
    separately with proper extraction logic, parameters, and validation rules.
    """

    # Core extractor identification
    extractor_id: str = Field(description="Unique identifier for this extractor")
    name: str = Field(description="Human-readable name like 'meeting metadata'")
    extractor_type: ExtractorType = Field(description="Type of extraction to perform")

    # Extractor configuration
    status: ExtractorStatus = ExtractorStatus.ACTIVE
    description: Optional[str] = Field(
        default=None,
        description="Detailed description of what this extractor does"
    )

    # Version and compatibility
    version: str = Field(default="1.0.0", description="Extractor version")

    # Timestamps
    created_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    # Additional configuration for future expansion
    additional_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional extractor-specific configuration"
    )

    @field_validator("extractor_id")
    @classmethod
    def extractor_id_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Extractor ID cannot be empty")
        return v.strip()

    @field_validator("name")
    @classmethod
    def name_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Extractor name cannot be empty")
        return v.strip()

    @field_validator("version")
    @classmethod
    def version_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Extractor version cannot be empty")
        return v.strip()

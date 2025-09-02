"""
Assembly domain models for the Capture, Extract, Assemble, Publish workflow.

This module contains the Assembly domain object that represents
assembly configurations in the CEAP workflow system.

An Assembly defines a type of document output (like "meeting minutes"), includes
information about its applicability and and specifies which extractors are
needed to collect the data for that output.

All domain models use Pydantic BaseModel for validation, serialization,
and type safety, following the patterns established in the sample project.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from enum import Enum


class AssemblyStatus(str, Enum):
    """Status of an assembly configuration."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    DRAFT = "draft"
    DEPRECATED = "deprecated"


class Assembly(BaseModel):
    """Assembly configuration that defines how to assemble documents of a specific type.

    An Assembly represents a type of document output (like "meeting minutes",
    "project report", etc.) and defines which extractors should be used to
    collect the necessary data from source documents.

    The Assembly does not contain the template itself - templates will be
    handled separately during the assembly rendering (or publishing?) phase.
    This separation allows the same Assembly definition to be used with
    different templates over time.
    """

    # Core assembly identification
    assembly_id: str = Field(description="Unique identifier for this assembly")
    name: str = Field(description="Human-readable name like 'meeting minutes'")
    applicability: str = Field(
        description="Text description identifying to what type of information this "
                   "assembly applies, such as an online transcript of a video meeting. "
                   "This information may be used by knowledge service for "
                   "document-assembly matching"
    )

    # Assembly configuration
    status: AssemblyStatus = AssemblyStatus.ACTIVE
    extractor_ids: List[str] = Field(
        default_factory=list,
        description="List of top-level extractor IDs required for this assembly"
    )

    # Assembly metadata
    version: str = Field(default="0.1.0", description="Assembly definition version")
    created_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    # May later add a detailed description, change log, additional metadata etc.
    # Timestamps


    @field_validator("assembly_id")
    @classmethod
    def assembly_id_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Assembly ID cannot be empty")
        return v.strip()

    @field_validator("name")
    @classmethod
    def name_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Assembly name cannot be empty")
        return v.strip()

    @field_validator("applicability")
    @classmethod
    def applicability_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Assembly applicability cannot be empty")
        return v.strip()

    @field_validator("extractor_ids")
    @classmethod
    def extractor_ids_must_be_valid(cls, v: List[str]) -> List[str]:
        if not isinstance(v, list):
            raise ValueError("Extractor IDs must be a list")

        # Remove empty strings and strip whitespace
        cleaned_ids = []
        for extractor_id in v:
            if isinstance(extractor_id, str) and extractor_id.strip():
                cleaned_ids.append(extractor_id.strip())
            elif extractor_id:  # Non-empty, non-string values
                raise ValueError(f"All extractor IDs must be strings, got {type(extractor_id)}")

        return cleaned_ids

    @field_validator("version")
    @classmethod
    def version_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Assembly version cannot be empty")
        return v.strip()

"""
Assembly domain models for the Capture, Extract, Assemble, Publish workflow.

This module contains the Assembly domain object that represents the actual
assembly process/instance in the CEAP workflow system.

An Assembly represents a specific instance of assembling a document using
an AssemblySpecification. It links an input document with an assembly
specification and produces a single assembled document as output.

All domain models use Pydantic BaseModel for validation, serialization,
and type safety, following the patterns established in the sample project.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime, timezone
from enum import Enum


class AssemblyStatus(str, Enum):
    """Status of an assembly process."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Assembly(BaseModel):
    """Assembly process that links a specification with input document and
    produces an assembled document.

    An Assembly represents a specific instance of the document assembly
    process. It connects an AssemblySpecification (which defines how to
    assemble) with an input Document (what to assemble from) and produces
    a single assembled document as output.
    """

    # Core assembly identification
    assembly_id: str = Field(
        description="Unique identifier for this assembly instance"
    )
    assembly_specification_id: str = Field(
        description="ID of the AssemblySpecification defining how to assemble"
    )
    input_document_id: str = Field(
        description="ID of the input document to assemble from"
    )
    workflow_id: str = Field(
        description="Temporal workflow ID that created this assembly"
    )

    # Assembly process tracking
    status: AssemblyStatus = AssemblyStatus.PENDING
    assembled_document_id: Optional[str] = Field(
        default=None,
        description="ID of the assembled document produced by this assembly",
    )

    # Assembly metadata
    created_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    @field_validator("assembly_id")
    @classmethod
    def assembly_id_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Assembly ID cannot be empty")
        return v.strip()

    @field_validator("assembly_specification_id")
    @classmethod
    def assembly_specification_id_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Assembly specification ID cannot be empty")
        return v.strip()

    @field_validator("input_document_id")
    @classmethod
    def input_document_id_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Input document ID cannot be empty")
        return v.strip()

    @field_validator("assembled_document_id")
    @classmethod
    def assembled_document_id_must_not_be_empty_if_provided(
        cls, v: Optional[str]
    ) -> Optional[str]:
        if v is not None and (not v or not v.strip()):
            raise ValueError("Assembled document ID cannot be empty string")
        return v.strip() if v else None

    @field_validator("workflow_id")
    @classmethod
    def workflow_id_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Workflow ID cannot be empty")
        return v.strip()

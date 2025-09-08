"""
AssemblyIteration domain models for the Capture, Extract, Assemble, Publish
workflow.

This module contains the AssemblyIteration domain object that represents
individual assembly attempts/iterations within an Assembly process in the CEAP
workflow system.

An AssemblyIteration tracks a single attempt at assembling a document,
including the output document that was produced by that iteration.

All domain models use Pydantic BaseModel for validation, serialization,
and type safety, following the patterns established in the sample project.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime, timezone


class AssemblyIteration(BaseModel):
    """Assembly iteration that represents a single attempt at document
    assembly.

    An AssemblyIteration tracks one attempt at assembling a document within
    an Assembly process. Each iteration produces an output document, which
    may be refined through subsequent iterations.

    This allows for iterative improvement of assembled documents, with each
    iteration building on previous attempts or incorporating new information.

    Each iteration will later have associated scorecards that evaluate the
    quality and accuracy of the output document produced by that iteration.
    """

    # Core iteration identification
    iteration_id: int = Field(
        description="Sequential iteration number within this assembly "
        "(1, 2, 3, ...)"
    )
    assembly_id: str = Field(
        description="ID of the Assembly this iteration belongs to"
    )
    document_id: str = Field(
        description="ID of the output document produced by this iteration"
    )

    # Iteration metadata
    created_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    @field_validator("iteration_id")
    @classmethod
    def iteration_id_must_be_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Iteration ID must be a positive integer")
        return v

    @field_validator("assembly_id")
    @classmethod
    def assembly_id_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Assembly ID cannot be empty")
        return v.strip()

    @field_validator("document_id")
    @classmethod
    def document_id_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Document ID cannot be empty")
        return v.strip()

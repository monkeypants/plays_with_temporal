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
from typing import Optional, List, Tuple
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
    iteration_id: Optional[int] = Field(
        default=None,
        description="Sequential iteration number within this assembly "
        "(1, 2, 3, ...). None for unsaved iterations.",
    )
    document_id: str = Field(
        description="ID of the output document produced by this iteration"
    )
    scorecard_results: List[Tuple[str, int]] = Field(
        default_factory=list,
        description="List of 2-tuples containing "
        "(scorecard_query_id, actual_score_out_of_100) "
        "for the actual scores achieved by this iteration",
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
    def iteration_id_must_be_positive(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v <= 0:
            raise ValueError("Iteration ID must be a positive integer")
        return v

    @field_validator("document_id")
    @classmethod
    def document_id_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Document ID cannot be empty")
        return v.strip()

    @field_validator("scorecard_results")
    @classmethod
    def scorecard_results_must_be_valid(
        cls, v: List[Tuple[str, int]]
    ) -> List[Tuple[str, int]]:
        if not isinstance(v, list):
            raise ValueError("Scorecard results must be a list")

        validated_results = []
        for item in v:
            if not isinstance(item, tuple) or len(item) != 2:
                raise ValueError(
                    "Each scorecard result must be a 2-tuple of "
                    "(scorecard_query_id, actual_score_out_of_100)"
                )

            query_id, score = item

            # Validate query ID
            if not isinstance(query_id, str) or not query_id.strip():
                raise ValueError(
                    "Scorecard query ID must be a non-empty string"
                )

            # Validate score
            if not isinstance(score, int):
                raise ValueError("Score must be an integer")
            if not (0 <= score <= 100):
                raise ValueError("Score must be between 0 and 100 inclusive")

            validated_results.append((query_id.strip(), score))

        return validated_results

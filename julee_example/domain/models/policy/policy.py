"""
Policy domain models for the Capture, Extract, Assemble,
Publish workflow.

This module contains the Policy domain object that represents
policy configurations in the CEAP workflow system.

A Policy defines validation criteria and optional transformations
for documents. It includes validation scores that must be met and optional
transformation queries that can be applied to improve document quality.

All domain models use Pydantic BaseModel for validation, serialization,
and type safety, following the patterns established in the sample project.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Tuple
from datetime import datetime, timezone
from enum import Enum


class PolicyStatus(str, Enum):
    """Status of a policy configuration."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    DRAFT = "draft"
    DEPRECATED = "deprecated"


class Policy(BaseModel):
    """Policy configuration that defines validation and
    transformation criteria for documents.

    A Policy represents a set of quality criteria that documents
    must meet. It includes validation scores that are calculated using
    knowledge service queries, and optional transformation queries that can
    be applied to improve document quality before re-validation.

    The policy operates in two modes:
    1. Validation-only: Calculates scores and passes/fails based on criteria
    2. Validation with transformation: Calculates scores, applies
       transformations, then re-calculates scores for final pass/fail
    """

    # Core policy identification
    policy_id: str = Field(description="Unique identifier for this policy")
    title: str = Field(description="Human-readable title for the policy")
    description: str = Field(
        description="Detailed description of what this policy validates "
        "and optionally transforms"
    )

    # Policy configuration
    status: PolicyStatus = PolicyStatus.ACTIVE
    validation_scores: List[Tuple[str, int]] = Field(
        description="List of (knowledge_service_query_id, required_score) "
        "tuples where required_score is between 0 and 100. All scores "
        "must be met or exceeded for the policy to pass"
    )
    transformation_queries: Optional[List[str]] = Field(
        default=None,
        description="Optional list of knowledge service query IDs for "
        "transformations to apply before re-validation. If not provided "
        "or empty, policy operates in validation-only mode",
    )

    # Policy metadata
    version: str = Field(default="0.1.0", description="Policy version")
    created_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: Optional[datetime] = Field(default=None)

    @field_validator("policy_id")
    @classmethod
    def policy_id_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Policy ID cannot be empty")
        return v.strip()

    @field_validator("title")
    @classmethod
    def title_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Policy title cannot be empty")
        return v.strip()

    @field_validator("description")
    @classmethod
    def description_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Policy description cannot be empty")
        return v.strip()

    @field_validator("validation_scores")
    @classmethod
    def validation_scores_must_be_valid(
        cls, v: List[Tuple[str, int]]
    ) -> List[Tuple[str, int]]:
        if not isinstance(v, list):
            raise ValueError("Validation scores must be a list")

        if not v:
            raise ValueError("Validation scores list cannot be empty")

        validated_scores = []
        query_ids_seen = set()

        for item in v:
            if not isinstance(item, tuple) or len(item) != 2:
                raise ValueError(
                    "Each validation score must be a 2-tuple of "
                    "(query_id, required_score)"
                )

            query_id, required_score = item

            # Validate query ID
            if not isinstance(query_id, str) or not query_id.strip():
                raise ValueError(
                    "Query ID in validation scores must be a non-empty string"
                )
            query_id = query_id.strip()

            # Check for duplicate query IDs
            if query_id in query_ids_seen:
                raise ValueError(
                    f"Duplicate query ID '{query_id}' in validation scores"
                )
            query_ids_seen.add(query_id)

            # Validate required score
            if not isinstance(required_score, int):
                raise ValueError(
                    "Required score must be an integer between 0 and 100"
                )
            if required_score < 0 or required_score > 100:
                raise ValueError(
                    f"Required score {required_score} must be between "
                    f"0 and 100"
                )

            validated_scores.append((query_id, required_score))

        return validated_scores

    @field_validator("transformation_queries")
    @classmethod
    def transformation_queries_must_be_valid(
        cls, v: Optional[List[str]]
    ) -> Optional[List[str]]:
        if v is None:
            return v

        if not isinstance(v, list):
            raise ValueError("Transformation queries must be a list or None")

        # Empty list is valid - means no transformations
        if not v:
            return v

        validated_queries = []
        query_ids_seen = set()

        for query_id in v:
            if not isinstance(query_id, str) or not query_id.strip():
                raise ValueError(
                    "Each transformation query ID must be a non-empty string"
                )
            query_id = query_id.strip()

            # Check for duplicate query IDs
            if query_id in query_ids_seen:
                raise ValueError(
                    f"Duplicate query ID '{query_id}' in transformation "
                    f"queries"
                )
            query_ids_seen.add(query_id)

            validated_queries.append(query_id)

        return validated_queries

    @field_validator("version")
    @classmethod
    def version_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Policy version cannot be empty")
        return v.strip()

    @property
    def is_validation_only(self) -> bool:
        """Check if this policy operates in validation-only mode.

        Returns True if no transformation queries are defined or if the
        transformation queries list is empty.
        """
        return not self.transformation_queries

    @property
    def has_transformations(self) -> bool:
        """Check if this policy includes transformation queries.

        Returns True if transformation queries are defined and non-empty.
        """
        return not self.is_validation_only

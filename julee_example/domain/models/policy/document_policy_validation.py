"""
DocumentPolicyValidation domain models for the Capture, Extract, Assemble,
Publish workflow.

This module contains the DocumentPolicyValidation domain object that
represents
the result of validating a document against a policy configuration in the CEAP
workflow system.

A DocumentPolicyValidation captures the complete validation process including:
- The document being validated and the policy used
- Actual validation scores achieved against policy criteria
- Optional transformation results and post-transformation scores
- Status tracking throughout the validation lifecycle

All domain models use Pydantic BaseModel for validation, serialization,
and type safety, following the patterns established in the sample project.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Tuple
from datetime import datetime, timezone
from enum import Enum


class DocumentPolicyValidationStatus(str, Enum):
    """Status of a document policy validation process."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    VALIDATION_COMPLETE = "validation_complete"
    TRANSFORMATION_REQUIRED = "transformation_required"
    TRANSFORMATION_IN_PROGRESS = "transformation_in_progress"
    TRANSFORMATION_COMPLETE = "transformation_complete"
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"


class DocumentPolicyValidation(BaseModel):
    """Represents the validation of a document against a policy configuration.

    A DocumentPolicyValidation tracks the complete lifecycle of validating
    a document against policy criteria. It includes:

    1. Initial validation: Document is scored against policy validation
       queries
    2. Optional transformation: If policy includes transformation queries and
       initial validation fails, transformations are applied
    3. Re-validation: Transformed document is re-scored against policy
       criteria
    4. Final determination: Pass/fail based on final validation scores

    The validation process supports both validation-only policies and policies
    that include transformations for document quality improvement.
    """

    # Core validation identification
    validation_id: str = Field(
        description="Unique identifier for this validation instance"
    )
    input_document_id: str = Field(
        description="ID of the document being validated against the policy"
    )
    policy_id: str = Field(
        description="ID of the policy configuration used for validation"
    )

    # Validation process status
    status: DocumentPolicyValidationStatus = (
        DocumentPolicyValidationStatus.PENDING
    )

    # Initial validation results
    validation_scores: List[Tuple[str, int]] = Field(
        default_factory=list,
        description="List of (knowledge_service_query_id, actual_score) "
        "tuples representing the scores achieved during initial validation. "
        "Scores are between 0 and 100",
    )

    # Transformation results (if applicable)
    transformed_document_id: Optional[str] = Field(
        default=None,
        description="ID of the document after transformations have been "
        "applied. Only present if the policy includes transformation queries "
        "and they were executed",
    )
    post_transform_validation_scores: Optional[List[Tuple[str, int]]] = Field(
        default=None,
        description="List of (knowledge_service_query_id, actual_score) "
        "tuples representing scores achieved after transformation. "
        "Only present if transformations were applied and re-validation "
        "occurred",
    )

    # Validation metadata
    started_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the validation process was initiated",
    )
    completed_at: Optional[datetime] = Field(
        default=None, description="When the validation process completed"
    )
    error_message: Optional[str] = Field(
        default=None, description="Error message if validation process failed"
    )

    # Results summary
    passed: Optional[bool] = Field(
        default=None,
        description="Whether the document passed policy validation. "
        "None while validation is in progress, True/False when complete",
    )

    @field_validator("input_document_id")
    @classmethod
    def input_document_id_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Input document ID cannot be empty")
        return v.strip()

    @field_validator("policy_id")
    @classmethod
    def policy_id_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Policy ID cannot be empty")
        return v.strip()

    @field_validator("validation_scores")
    @classmethod
    def validation_scores_must_be_valid(
        cls, v: List[Tuple[str, int]]
    ) -> List[Tuple[str, int]]:
        if not isinstance(v, list):
            raise ValueError("Validation scores must be a list")

        # Empty list is valid for pending validations
        if not v:
            return v

        return cls._validate_score_tuples(v, "validation_scores")

    @field_validator("post_transform_validation_scores")
    @classmethod
    def post_transform_scores_must_be_valid(
        cls, v: Optional[List[Tuple[str, int]]]
    ) -> Optional[List[Tuple[str, int]]]:
        if v is None:
            return v

        if not isinstance(v, list):
            raise ValueError(
                "Post-transform validation scores must be a list or None"
            )

        # Empty list is valid
        if not v:
            return v

        return cls._validate_score_tuples(
            v, "post_transform_validation_scores"
        )

    @field_validator("error_message")
    @classmethod
    def error_message_must_be_valid(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not isinstance(v, str):
            raise ValueError("Error message must be a string or None")
        return v.strip() if v.strip() else None

    @field_validator("transformed_document_id")
    @classmethod
    def transformed_document_id_must_be_valid(
        cls, v: Optional[str]
    ) -> Optional[str]:
        if v is None:
            return v
        if not isinstance(v, str) or not v.strip():
            raise ValueError(
                "Transformed document ID must be a non-empty string or None"
            )
        return v.strip()

    @classmethod
    def _validate_score_tuples(
        cls, scores: List[Tuple[str, int]], field_name: str
    ) -> List[Tuple[str, int]]:
        """Helper method to validate score tuple lists."""
        validated_scores = []
        query_ids_seen = set()

        for item in scores:
            if not isinstance(item, tuple) or len(item) != 2:
                raise ValueError(
                    f"Each item in {field_name} must be a 2-tuple of "
                    f"(query_id, actual_score)"
                )

            query_id, actual_score = item

            # Validate query ID
            if not isinstance(query_id, str) or not query_id.strip():
                raise ValueError(
                    f"Query ID in {field_name} must be a non-empty string"
                )
            query_id = query_id.strip()

            # Check for duplicate query IDs within this field
            if query_id in query_ids_seen:
                raise ValueError(
                    f"Duplicate query ID '{query_id}' in {field_name}"
                )
            query_ids_seen.add(query_id)

            # Validate actual score
            if not isinstance(actual_score, int):
                raise ValueError(
                    f"Actual score in {field_name} must be an integer "
                    f"between 0 and 100"
                )
            if actual_score < 0 or actual_score > 100:
                raise ValueError(
                    f"Actual score {actual_score} in {field_name} must be "
                    f"between 0 and 100"
                )

            validated_scores.append((query_id, actual_score))

        return validated_scores

"""
Tests for DocumentPolicyValidation domain model.

This module tests the DocumentPolicyValidation domain object validation,
field requirements, and business rules following the same testing patterns
as the Policy model tests.

Tests focus on:
- Required field validation
- Field format validation
- Score tuple validation
- Status enum validation
- Edge cases and error conditions
"""

import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

from julee_example.domain.models.policy import (
    DocumentPolicyValidation,
    DocumentPolicyValidationStatus,
)
from .factories import DocumentPolicyValidationFactory


class TestDocumentPolicyValidationValidation:
    """Test validation rules for DocumentPolicyValidation model."""

    def test_minimal_valid_validation(self) -> None:
        """Test creating a minimal valid DocumentPolicyValidation."""
        validation = DocumentPolicyValidationFactory()

        assert validation.input_document_id is not None
        assert validation.policy_id is not None
        assert validation.status == DocumentPolicyValidationStatus.PENDING
        assert validation.validation_scores == []
        assert validation.transformed_document_id is None
        assert validation.post_transform_validation_scores is None
        assert validation.validation_id is not None
        assert validation.passed is None
        assert validation.error_message is None
        assert validation.completed_at is None
        assert isinstance(validation.started_at, datetime)

    def test_full_valid_validation(self) -> None:
        """Test creating a fully populated DocumentPolicyValidation."""
        started_at = datetime.now(timezone.utc)
        completed_at = datetime.now(timezone.utc)

        validation = DocumentPolicyValidation(
            validation_id="val-789",
            input_document_id="doc-123",
            policy_id="policy-456",
            status=DocumentPolicyValidationStatus.PASSED,
            validation_scores=[("query1", 85), ("query2", 92)],
            transformed_document_id="doc-123-transformed",
            post_transform_validation_scores=[("query1", 95), ("query2", 88)],
            started_at=started_at,
            completed_at=completed_at,
            error_message=None,
            passed=True,
        )

        assert validation.validation_id == "val-789"
        assert validation.input_document_id == "doc-123"
        assert validation.policy_id == "policy-456"
        assert validation.status == DocumentPolicyValidationStatus.PASSED
        assert validation.validation_scores == [
            ("query1", 85),
            ("query2", 92),
        ]
        assert validation.transformed_document_id == "doc-123-transformed"
        assert validation.post_transform_validation_scores == [
            ("query1", 95),
            ("query2", 88),
        ]
        assert validation.started_at == started_at
        assert validation.completed_at == completed_at
        assert validation.passed is True


class TestDocumentPolicyValidationRequiredFields:
    """Test required field validation."""

    def test_required_fields_present_in_factory(self) -> None:
        """Test that factory creates validation with required fields."""
        validation = DocumentPolicyValidationFactory()
        assert validation.input_document_id is not None
        assert validation.policy_id is not None
        assert isinstance(validation.input_document_id, str)
        assert isinstance(validation.policy_id, str)


class TestDocumentPolicyValidationFieldValidation:
    """Test individual field validation rules."""

    def test_input_document_id_cannot_be_empty(self) -> None:
        """Test that input_document_id cannot be empty or whitespace."""
        test_cases = ["", "   ", "\t", "\n"]

        for empty_value in test_cases:
            with pytest.raises(ValidationError) as exc_info:
                DocumentPolicyValidation(
                    validation_id="val-123",
                    input_document_id=empty_value,
                    policy_id="policy-456",
                )

            errors = exc_info.value.errors()
            assert any(
                "Input document ID cannot be empty" in str(error)
                for error in errors
            )

    def test_input_document_id_strips_whitespace(self) -> None:
        """Test that input_document_id strips whitespace."""
        validation = DocumentPolicyValidation(
            validation_id="val-123",
            input_document_id="  doc-123  ",
            policy_id="policy-456",
        )
        assert validation.input_document_id == "doc-123"

    def test_policy_id_cannot_be_empty(self) -> None:
        """Test that policy_id cannot be empty or whitespace."""
        test_cases = ["", "   ", "\t", "\n"]

        for empty_value in test_cases:
            with pytest.raises(ValidationError) as exc_info:
                DocumentPolicyValidation(
                    validation_id="val-123",
                    input_document_id="doc-123",
                    policy_id=empty_value,
                )

            errors = exc_info.value.errors()
            assert any(
                "Policy ID cannot be empty" in str(error) for error in errors
            )

    def test_policy_id_strips_whitespace(self) -> None:
        """Test that policy_id strips whitespace."""
        validation = DocumentPolicyValidation(
            validation_id="val-123",
            input_document_id="doc-123",
            policy_id="  policy-456  ",
        )
        assert validation.policy_id == "policy-456"

    def test_transformed_document_id_validation(self) -> None:
        """Test transformed_document_id field validation."""
        # None is valid
        validation = DocumentPolicyValidation(
            validation_id="val-123",
            input_document_id="doc-123",
            policy_id="policy-456",
            transformed_document_id=None,
        )
        assert validation.transformed_document_id is None

        # Non-empty string is valid
        validation = DocumentPolicyValidation(
            validation_id="val-123",
            input_document_id="doc-123",
            policy_id="policy-456",
            transformed_document_id="doc-123-transformed",
        )
        assert validation.transformed_document_id == "doc-123-transformed"

        # Empty string should be invalid
        with pytest.raises(ValidationError) as exc_info:
            DocumentPolicyValidation(
                validation_id="val-123",
                input_document_id="doc-123",
                policy_id="policy-456",
                transformed_document_id="",
            )

        errors = exc_info.value.errors()
        assert any(
            "must be a non-empty string or None" in str(error)
            for error in errors
        )

    def test_error_message_validation(self) -> None:
        """Test error_message field validation."""
        # None is valid
        validation = DocumentPolicyValidation(
            validation_id="val-123",
            input_document_id="doc-123",
            policy_id="policy-456",
            error_message=None,
        )
        assert validation.error_message is None

        # Non-empty string is valid
        validation = DocumentPolicyValidation(
            validation_id="val-123",
            input_document_id="doc-123",
            policy_id="policy-456",
            error_message="Something went wrong",
        )
        assert validation.error_message == "Something went wrong"

        # Empty/whitespace string becomes None
        validation = DocumentPolicyValidation(
            validation_id="val-123",
            input_document_id="doc-123",
            policy_id="policy-456",
            error_message="   ",
        )
        assert validation.error_message is None


class TestValidationScores:
    """Test validation_scores field validation."""

    def test_empty_validation_scores_valid(self) -> None:
        """Test that empty validation_scores list is valid."""
        validation = DocumentPolicyValidation(
            validation_id="val-123",
            input_document_id="doc-123",
            policy_id="policy-456",
            validation_scores=[],
        )
        assert validation.validation_scores == []

    def test_valid_validation_scores(self) -> None:
        """Test valid validation_scores."""
        scores = [("query1", 85), ("query2", 92), ("query3", 78)]
        validation = DocumentPolicyValidation(
            validation_id="val-123",
            input_document_id="doc-123",
            policy_id="policy-456",
            validation_scores=scores,
        )
        assert validation.validation_scores == scores

    def test_validation_scores_with_valid_integers(self) -> None:
        """Test that validation_scores work with valid integer scores."""
        validation = DocumentPolicyValidation(
            validation_id="val-123",
            input_document_id="doc-123",
            policy_id="policy-456",
            validation_scores=[("query1", 85), ("query2", 92)],
        )
        assert validation.validation_scores == [
            ("query1", 85),
            ("query2", 92),
        ]

    def test_validation_scores_query_id_validation(self) -> None:
        """Test validation_scores query_id validation."""
        # Empty query_id should fail
        with pytest.raises(ValidationError) as exc_info:
            DocumentPolicyValidation(
                validation_id="val-123",
                input_document_id="doc-123",
                policy_id="policy-456",
                validation_scores=[("", 85)],
            )

        errors = exc_info.value.errors()
        assert any(
            "must be a non-empty string" in str(error) for error in errors
        )

        # Whitespace-only query_id should fail
        with pytest.raises(ValidationError) as exc_info:
            DocumentPolicyValidation(
                validation_id="val-123",
                input_document_id="doc-123",
                policy_id="policy-456",
                validation_scores=[("   ", 85)],
            )

        errors = exc_info.value.errors()
        assert any(
            "must be a non-empty string" in str(error) for error in errors
        )

    def test_validation_scores_score_range(self) -> None:
        """Test validation_scores score range validation."""
        # Score too low
        with pytest.raises(ValidationError) as exc_info:
            DocumentPolicyValidation(
                validation_id="val-123",
                input_document_id="doc-123",
                policy_id="policy-456",
                validation_scores=[("query1", -1)],
            )

        errors = exc_info.value.errors()
        assert any(
            "must be between 0 and 100" in str(error) for error in errors
        )

        # Score too high
        with pytest.raises(ValidationError) as exc_info:
            DocumentPolicyValidation(
                validation_id="val-123",
                input_document_id="doc-123",
                policy_id="policy-456",
                validation_scores=[("query1", 101)],
            )

        errors = exc_info.value.errors()
        assert any(
            "must be between 0 and 100" in str(error) for error in errors
        )

        # Valid edge cases
        validation = DocumentPolicyValidation(
            validation_id="val-123",
            input_document_id="doc-123",
            policy_id="policy-456",
            validation_scores=[("query1", 0), ("query2", 100)],
        )
        assert validation.validation_scores == [
            ("query1", 0),
            ("query2", 100),
        ]

    def test_validation_scores_no_duplicates(self) -> None:
        """Test that validation_scores cannot have duplicate query_ids."""
        with pytest.raises(ValidationError) as exc_info:
            DocumentPolicyValidation(
                validation_id="val-123",
                input_document_id="doc-123",
                policy_id="policy-456",
                validation_scores=[("query1", 85), ("query1", 92)],
            )

        errors = exc_info.value.errors()
        assert any(
            "Duplicate query ID 'query1'" in str(error) for error in errors
        )


class TestPostTransformValidationScores:
    """Test post_transform_validation_scores field validation."""

    def test_none_post_transform_scores_valid(self) -> None:
        """Test that None post_transform_validation_scores is valid."""
        validation = DocumentPolicyValidation(
            validation_id="val-123",
            input_document_id="doc-123",
            policy_id="policy-456",
            post_transform_validation_scores=None,
        )
        assert validation.post_transform_validation_scores is None

    def test_empty_post_transform_scores_valid(self) -> None:
        """Test that empty post_transform_validation_scores list is valid."""
        validation = DocumentPolicyValidation(
            validation_id="val-123",
            input_document_id="doc-123",
            policy_id="policy-456",
            post_transform_validation_scores=[],
        )
        assert validation.post_transform_validation_scores == []

    def test_valid_post_transform_scores(self) -> None:
        """Test valid post_transform_validation_scores."""
        scores = [("query1", 95), ("query2", 88)]
        validation = DocumentPolicyValidation(
            validation_id="val-123",
            input_document_id="doc-123",
            policy_id="policy-456",
            post_transform_validation_scores=scores,
        )
        assert validation.post_transform_validation_scores == scores

    def test_post_transform_scores_validation_rules(self) -> None:
        """Test that post_transform_validation_scores follows same rules as
        validation_scores."""
        # Same score range validation
        with pytest.raises(ValidationError) as exc_info:
            DocumentPolicyValidation(
                validation_id="val-123",
                input_document_id="doc-123",
                policy_id="policy-456",
                post_transform_validation_scores=[("query1", -5)],
            )

        errors = exc_info.value.errors()
        assert any(
            "must be between 0 and 100" in str(error) for error in errors
        )

        # Same duplicate detection
        with pytest.raises(ValidationError) as exc_info:
            DocumentPolicyValidation(
                validation_id="val-123",
                input_document_id="doc-123",
                policy_id="policy-456",
                post_transform_validation_scores=[
                    ("query1", 85),
                    ("query1", 92),
                ],
            )

        errors = exc_info.value.errors()
        assert any(
            "Duplicate query ID 'query1'" in str(error) for error in errors
        )


class TestDocumentPolicyValidationStatusEnum:
    """Test DocumentPolicyValidationStatus enum usage."""

    def test_default_status_is_pending(self) -> None:
        """Test that default status is PENDING."""
        validation = DocumentPolicyValidation(
            validation_id="val-123",
            input_document_id="doc-123",
            policy_id="policy-456",
        )
        assert validation.status == DocumentPolicyValidationStatus.PENDING

    def test_all_valid_statuses_work(self) -> None:
        """Test that all valid status enum values work correctly."""
        valid_statuses = [
            DocumentPolicyValidationStatus.PENDING,
            DocumentPolicyValidationStatus.IN_PROGRESS,
            DocumentPolicyValidationStatus.PASSED,
            DocumentPolicyValidationStatus.FAILED,
        ]

        for status in valid_statuses:
            validation = DocumentPolicyValidation(
                validation_id="val-123",
                input_document_id="doc-123",
                policy_id="policy-456",
                status=status,
            )
            assert validation.status == status

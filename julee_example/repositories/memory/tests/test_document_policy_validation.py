"""
Tests for MemoryDocumentPolicyValidationRepository implementation.

This module provides tests for the memory-based document policy validation
repository implementation, focusing on functionality specific to this
repository that differs from the inherited mixins.
"""

import pytest
from datetime import datetime, timezone
from typing import Any

from julee_example.domain.models.policy import (
    DocumentPolicyValidation,
    DocumentPolicyValidationStatus,
)
from julee_example.repositories.memory.document_policy_validation import (
    MemoryDocumentPolicyValidationRepository,
)


@pytest.fixture
def validation_repo() -> MemoryDocumentPolicyValidationRepository:
    """Create a fresh validation repository for each test."""
    return MemoryDocumentPolicyValidationRepository()


@pytest.fixture
def sample_validation() -> DocumentPolicyValidation:
    """Create a sample document policy validation for testing."""
    return DocumentPolicyValidation(
        validation_id="validation-test-123",
        input_document_id="doc-123",
        policy_id="policy-456",
        status=DocumentPolicyValidationStatus.PASSED,
        validation_scores=[
            ("quality-check-query", 85),
            ("completeness-check", 92),
        ],
        transformed_document_id="doc-123-transformed",
        post_transform_validation_scores=[
            ("quality-check-query", 95),
            ("completeness-check", 88),
        ],
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
        passed=True,
    )


class TestMemoryDocumentPolicyValidationRepositorySpecific:
    """Test functionality specific to DocumentPolicyValidation repository."""

    @pytest.mark.asyncio
    async def test_generate_id_prefix(
        self, validation_repo: MemoryDocumentPolicyValidationRepository
    ) -> None:
        """Test that generated IDs use the correct prefix for validations."""
        id1 = await validation_repo.generate_id()
        id2 = await validation_repo.generate_id()

        assert isinstance(id1, str)
        assert isinstance(id2, str)
        assert id1 != id2
        assert len(id1) > 0
        assert len(id2) > 0
        assert id1.startswith("validation-")
        assert id2.startswith("validation-")

    @pytest.mark.asyncio
    async def test_entity_specific_logging_data(
        self,
        validation_repo: MemoryDocumentPolicyValidationRepository,
        sample_validation: DocumentPolicyValidation,
    ) -> None:
        """Test that entity-specific logging data is added correctly."""
        log_data: dict[str, Any] = {}
        validation_repo._add_entity_specific_log_data(
            sample_validation, log_data
        )

        # Check validation-specific fields are added
        assert log_data["input_document_id"] == "doc-123"
        assert log_data["policy_id"] == "policy-456"
        assert log_data["validation_scores_count"] == 2
        assert log_data["has_transformations"] is True
        assert log_data["passed"] is True
        assert "has_error" not in log_data  # No error message

    @pytest.mark.asyncio
    async def test_entity_specific_logging_data_with_error(
        self, validation_repo: MemoryDocumentPolicyValidationRepository
    ) -> None:
        """Test logging data includes error flag when error_message is
        present."""
        validation_with_error = DocumentPolicyValidation(
            validation_id="validation-error-123",
            input_document_id="doc-456",
            policy_id="policy-789",
            status=DocumentPolicyValidationStatus.ERROR,
            validation_scores=[],
            error_message="Something went wrong",
            passed=False,
        )

        log_data: dict[str, Any] = {}
        validation_repo._add_entity_specific_log_data(
            validation_with_error, log_data
        )

        assert log_data["has_error"] is True
        assert log_data["passed"] is False

    @pytest.mark.asyncio
    async def test_entity_specific_logging_data_no_transformations(
        self, validation_repo: MemoryDocumentPolicyValidationRepository
    ) -> None:
        """Test logging data correctly identifies validations without
        transformations."""
        validation_no_transform = DocumentPolicyValidation(
            validation_id="validation-no-transform-123",
            input_document_id="doc-789",
            policy_id="policy-abc",
            status=DocumentPolicyValidationStatus.VALIDATION_COMPLETE,
            validation_scores=[("basic-check", 75)],
            transformed_document_id=None,
            post_transform_validation_scores=None,
        )

        log_data: dict[str, Any] = {}
        validation_repo._add_entity_specific_log_data(
            validation_no_transform, log_data
        )

        assert log_data["has_transformations"] is False
        assert log_data["validation_scores_count"] == 1

    @pytest.mark.asyncio
    async def test_entity_specific_logging_data_passed_none(
        self, validation_repo: MemoryDocumentPolicyValidationRepository
    ) -> None:
        """Test logging data handles None passed value correctly."""
        validation_in_progress = DocumentPolicyValidation(
            validation_id="validation-progress-123",
            input_document_id="doc-progress",
            policy_id="policy-progress",
            status=DocumentPolicyValidationStatus.IN_PROGRESS,
            validation_scores=[],
            passed=None,  # Still in progress
        )

        log_data: dict[str, Any] = {}
        validation_repo._add_entity_specific_log_data(
            validation_in_progress, log_data
        )

        # passed field should not be added when None
        assert "passed" not in log_data
        assert log_data["has_transformations"] is False

    @pytest.mark.asyncio
    async def test_initialization_sets_correct_attributes(
        self, validation_repo: MemoryDocumentPolicyValidationRepository
    ) -> None:
        """Test that repository initialization sets the correct attributes."""
        assert validation_repo.entity_name == "DocumentPolicyValidation"
        assert isinstance(validation_repo.storage_dict, dict)
        assert len(validation_repo.storage_dict) == 0
        assert validation_repo.logger is not None

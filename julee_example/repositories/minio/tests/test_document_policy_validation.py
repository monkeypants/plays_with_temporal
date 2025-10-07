"""
Tests for MinioDocumentPolicyValidationRepository implementation.

This module provides tests for the Minio-based document policy validation
repository implementation, focusing on functionality specific to this
repository that differs from the inherited mixins. Uses the fake client to
avoid external dependencies during testing.
"""

import pytest
from datetime import datetime, timezone

from julee_example.domain.models.policy import (
    DocumentPolicyValidation,
    DocumentPolicyValidationStatus,
)
from julee_example.repositories.minio.document_policy_validation import (
    MinioDocumentPolicyValidationRepository,
)
from .fake_client import FakeMinioClient


@pytest.fixture
def fake_client() -> FakeMinioClient:
    """Create a fresh fake Minio client for each test."""
    return FakeMinioClient()


@pytest.fixture
def validation_repo(
    fake_client: FakeMinioClient,
) -> MinioDocumentPolicyValidationRepository:
    """Create validation repository with fake client."""
    return MinioDocumentPolicyValidationRepository(fake_client)


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


class TestMinioDocumentPolicyValidationRepositorySpecific:
    """Test functionality specific to DocumentPolicyValidation Minio
    repository."""

    @pytest.mark.asyncio
    async def test_initialization_creates_correct_bucket(
        self, fake_client: FakeMinioClient
    ) -> None:
        """Test that repository initialization creates the correct bucket."""
        # Check bucket doesn't exist initially
        assert "document-policy-validations" not in fake_client._buckets

        # Create repository - should create bucket
        repo = MinioDocumentPolicyValidationRepository(fake_client)

        # Check bucket was created
        assert "document-policy-validations" in fake_client._buckets
        assert repo.validations_bucket == "document-policy-validations"

    @pytest.mark.asyncio
    async def test_generate_id_prefix(
        self, validation_repo: MinioDocumentPolicyValidationRepository
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
    async def test_save_and_retrieve_validation(
        self,
        validation_repo: MinioDocumentPolicyValidationRepository,
        sample_validation: DocumentPolicyValidation,
    ) -> None:
        """Test that save and retrieve operations work correctly."""
        # Save the validation
        await validation_repo.save(sample_validation)

        # Retrieve and verify all fields are preserved
        retrieved = await validation_repo.get(sample_validation.validation_id)

        assert retrieved is not None
        assert retrieved.validation_id == sample_validation.validation_id
        assert (
            retrieved.input_document_id == sample_validation.input_document_id
        )
        assert retrieved.policy_id == sample_validation.policy_id
        assert retrieved.status == sample_validation.status
        assert (
            retrieved.validation_scores == sample_validation.validation_scores
        )
        assert (
            retrieved.transformed_document_id
            == sample_validation.transformed_document_id
        )
        assert (
            retrieved.post_transform_validation_scores
            == sample_validation.post_transform_validation_scores
        )
        assert retrieved.passed == sample_validation.passed

    @pytest.mark.asyncio
    async def test_get_nonexistent_validation_returns_none(
        self, validation_repo: MinioDocumentPolicyValidationRepository
    ) -> None:
        """Test retrieving a non-existent validation returns None."""
        result = await validation_repo.get("nonexistent-validation")
        assert result is None

    @pytest.mark.asyncio
    async def test_save_preserves_timestamps(
        self, validation_repo: MinioDocumentPolicyValidationRepository
    ) -> None:
        """Test that save operation preserves existing timestamps."""
        # Create validation with specific timestamps
        original_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        validation = DocumentPolicyValidation(
            validation_id="validation-timestamp-test",
            input_document_id="doc-timestamp",
            policy_id="policy-timestamp",
            status=DocumentPolicyValidationStatus.PENDING,
            validation_scores=[],
            started_at=original_time,
            completed_at=None,
        )

        # Save and retrieve the validation
        await validation_repo.save(validation)
        retrieved = await validation_repo.get("validation-timestamp-test")

        # Check that timestamps are preserved correctly
        assert retrieved is not None
        assert retrieved.started_at == original_time
        assert retrieved.completed_at is None

    @pytest.mark.asyncio
    async def test_save_with_transformation_data(
        self, validation_repo: MinioDocumentPolicyValidationRepository
    ) -> None:
        """Test saving and retrieving validation with transformation data."""
        validation_with_transforms = DocumentPolicyValidation(
            validation_id="validation-transform-test",
            input_document_id="doc-original",
            policy_id="policy-transform",
            status=DocumentPolicyValidationStatus.TRANSFORMATION_COMPLETE,
            validation_scores=[("initial-check", 70)],
            transformed_document_id="doc-transformed",
            post_transform_validation_scores=[("final-check", 85)],
            passed=True,
        )

        # Save and retrieve the validation
        await validation_repo.save(validation_with_transforms)
        retrieved = await validation_repo.get("validation-transform-test")

        # Verify transformation data is preserved
        assert retrieved is not None
        assert retrieved.transformed_document_id == "doc-transformed"
        assert retrieved.post_transform_validation_scores == [
            ("final-check", 85)
        ]
        assert retrieved.passed is True
        assert retrieved.validation_scores == [("initial-check", 70)]

    @pytest.mark.asyncio
    async def test_repository_logger_configuration(
        self, validation_repo: MinioDocumentPolicyValidationRepository
    ) -> None:
        """Test that repository logger is configured correctly."""
        assert validation_repo.logger is not None
        # Logger name should reflect the repository class
        assert (
            "MinioDocumentPolicyValidationRepository"
            in validation_repo.logger.name
        )

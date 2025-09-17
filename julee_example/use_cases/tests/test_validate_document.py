"""
Tests for ValidateDocumentUseCase.

This module provides tests for the validate document use case,
ensuring proper business logic execution and repository interaction patterns
following the Clean Architecture principles.
"""

import io
import pytest
from unittest.mock import AsyncMock
from datetime import datetime, timezone

from julee_example.use_cases.validate_document import ValidateDocumentUseCase

from julee_example.domain import (
    Document,
    DocumentStatus,
    ContentStream,
    KnowledgeServiceConfig,
    KnowledgeServiceQuery,
)
from julee_example.domain.policy import (
    Policy,
    PolicyStatus,
    DocumentPolicyValidation,
    DocumentPolicyValidationStatus,
)
from julee_example.domain.knowledge_service_config import ServiceApi
from julee_example.repositories.memory import (
    MemoryDocumentRepository,
    MemoryKnowledgeServiceConfigRepository,
    MemoryKnowledgeServiceQueryRepository,
    MemoryPolicyRepository,
    MemoryDocumentPolicyValidationRepository,
)
from julee_example.services.knowledge_service.memory import (
    MemoryKnowledgeService,
)
from julee_example.services.knowledge_service import QueryResult
import julee_example.use_cases.validate_document


class TestValidateDocumentUseCase:
    """Test cases for ValidateDocumentUseCase business logic."""

    @pytest.fixture
    def document_repo(self) -> MemoryDocumentRepository:
        """Create a memory DocumentRepository for testing."""
        return MemoryDocumentRepository()

    @pytest.fixture
    def knowledge_service_query_repo(
        self,
    ) -> MemoryKnowledgeServiceQueryRepository:
        """Create a memory KnowledgeServiceQueryRepository for testing."""
        return MemoryKnowledgeServiceQueryRepository()

    @pytest.fixture
    def knowledge_service_config_repo(
        self,
    ) -> MemoryKnowledgeServiceConfigRepository:
        """Create a memory KnowledgeServiceConfigRepository for testing."""
        return MemoryKnowledgeServiceConfigRepository()

    @pytest.fixture
    def policy_repo(self) -> MemoryPolicyRepository:
        """Create a memory PolicyRepository for testing."""
        return MemoryPolicyRepository()

    @pytest.fixture
    def document_policy_validation_repo(
        self,
    ) -> MemoryDocumentPolicyValidationRepository:
        """Create a memory DocumentPolicyValidationRepository for testing."""
        return MemoryDocumentPolicyValidationRepository()

    @pytest.fixture
    def use_case(
        self,
        document_repo: MemoryDocumentRepository,
        knowledge_service_query_repo: MemoryKnowledgeServiceQueryRepository,
        knowledge_service_config_repo: MemoryKnowledgeServiceConfigRepository,
        policy_repo: MemoryPolicyRepository,
        document_policy_validation_repo: (
            MemoryDocumentPolicyValidationRepository
        ),
    ) -> ValidateDocumentUseCase:
        """Create ValidateDocumentUseCase with memory repository
        dependencies."""
        return ValidateDocumentUseCase(
            document_repo=document_repo,
            knowledge_service_query_repo=knowledge_service_query_repo,
            knowledge_service_config_repo=knowledge_service_config_repo,
            policy_repo=policy_repo,
            document_policy_validation_repo=document_policy_validation_repo,
        )

    @pytest.mark.asyncio
    async def test_validate_document_fails_without_document(
        self, use_case: ValidateDocumentUseCase
    ) -> None:
        """Test that validate_document fails when document doesn't exist."""
        # Arrange
        document_id = "nonexistent-doc"
        policy_id = "policy-123"

        # Act & Assert
        with pytest.raises(ValueError, match="Document not found"):
            await use_case.validate_document(
                document_id=document_id, policy_id=policy_id
            )

    @pytest.mark.asyncio
    async def test_validate_document_fails_without_policy(
        self,
        use_case: ValidateDocumentUseCase,
        document_repo: MemoryDocumentRepository,
    ) -> None:
        """Test that validate_document fails when policy doesn't exist."""
        # Arrange - Create document but no policy
        content_text = "Sample document for testing"
        content_bytes = content_text.encode("utf-8")
        document = Document(
            document_id="doc-123",
            original_filename="test_document.txt",
            content_type="text/plain",
            size_bytes=len(content_bytes),
            content_multihash="test-hash-123",
            status=DocumentStatus.CAPTURED,
            content=ContentStream(io.BytesIO(content_bytes)),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        await document_repo.save(document)

        document_id = "doc-123"
        policy_id = "nonexistent-policy"

        # Act & Assert
        with pytest.raises(ValueError, match="Policy not found"):
            await use_case.validate_document(
                document_id=document_id, policy_id=policy_id
            )

    @pytest.mark.asyncio
    async def test_validate_document_propagates_id_generation_error(
        self,
        use_case: ValidateDocumentUseCase,
        document_policy_validation_repo: (
            MemoryDocumentPolicyValidationRepository
        ),
    ) -> None:
        """Test that ID generation errors are properly propagated."""
        # Arrange
        document_id = "doc-456"
        policy_id = "policy-789"
        expected_error = RuntimeError("ID generation failed")

        # Mock the generate_id method to raise an error
        document_policy_validation_repo.generate_id = AsyncMock(  # type: ignore[method-assign]
            side_effect=expected_error
        )

        # Act & Assert
        with pytest.raises(RuntimeError, match="ID generation failed"):
            await use_case.validate_document(
                document_id=document_id, policy_id=policy_id
            )

    @pytest.mark.asyncio
    async def test_validate_document_fails_when_query_not_found(
        self,
        use_case: ValidateDocumentUseCase,
        document_repo: MemoryDocumentRepository,
        policy_repo: MemoryPolicyRepository,
    ) -> None:
        """Test that validation fails when query is not found."""
        # Arrange - Create document and policy with non-existent query
        content_text = "Sample content"
        content_bytes = content_text.encode("utf-8")
        document = Document(
            document_id="doc-123",
            original_filename="test.txt",
            content_type="text/plain",
            size_bytes=len(content_bytes),
            content_multihash="test-hash",
            status=DocumentStatus.CAPTURED,
            content=ContentStream(io.BytesIO(content_bytes)),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        await document_repo.save(document)

        policy = Policy(
            policy_id="policy-123",
            title="Test Policy",
            description="Policy with non-existent query",
            status=PolicyStatus.ACTIVE,
            validation_scores=[("nonexistent-query", 80)],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        await policy_repo.save(policy)

        # Act & Assert
        with pytest.raises(
            ValueError, match="Knowledge service query not found"
        ):
            await use_case.validate_document(
                document_id="doc-123", policy_id="policy-123"
            )

    @pytest.mark.asyncio
    async def test_validate_document_fails_with_score_parse_error(
        self,
        use_case: ValidateDocumentUseCase,
        document_repo: MemoryDocumentRepository,
        policy_repo: MemoryPolicyRepository,
        knowledge_service_query_repo: MemoryKnowledgeServiceQueryRepository,
        knowledge_service_config_repo: MemoryKnowledgeServiceConfigRepository,
    ) -> None:
        """Test that validation fails when score cannot be parsed."""
        # Arrange - Create test document
        content_text = "Sample document content"
        content_bytes = content_text.encode("utf-8")
        document = Document(
            document_id="doc-123",
            original_filename="test.txt",
            content_type="text/plain",
            size_bytes=len(content_bytes),
            content_multihash="test-hash",
            status=DocumentStatus.CAPTURED,
            content=ContentStream(io.BytesIO(content_bytes)),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        await document_repo.save(document)

        # Create policy
        policy = Policy(
            policy_id="policy-123",
            title="Test Policy",
            description="Policy for testing score parsing",
            status=PolicyStatus.ACTIVE,
            validation_scores=[("query-1", 80)],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        await policy_repo.save(policy)

        # Create knowledge service config and query
        ks_config = KnowledgeServiceConfig(
            knowledge_service_id="ks-123",
            name="Test Knowledge Service",
            description="Test service",
            service_api=ServiceApi.ANTHROPIC,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        await knowledge_service_config_repo.save(ks_config)

        query = KnowledgeServiceQuery(
            query_id="query-1",
            name="Quality Check",
            knowledge_service_id="ks-123",
            prompt="Rate the quality of this document",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        await knowledge_service_query_repo.save(query)

        # Create memory service that returns unparseable score
        memory_service = MemoryKnowledgeService(ks_config)
        memory_service.add_canned_query_result(
            QueryResult(
                query_id="result-1",
                query_text="Rate the quality of this document",
                result_data={
                    "response": "not a number"
                },  # Invalid score format
                execution_time_ms=100,
                created_at=datetime.now(timezone.utc),
            )
        )

        # Patch the factory to return our configured memory service
        module = julee_example.use_cases.validate_document
        original_factory = module.knowledge_service_factory
        module.knowledge_service_factory = (
            lambda config: memory_service  # type: ignore[assignment]
        )

        try:
            # Act & Assert
            with pytest.raises(
                ValueError,
                match="Failed to parse numeric score from response",
            ):
                await use_case.validate_document(
                    document_id="doc-123", policy_id="policy-123"
                )
        finally:
            # Restore original factory
            module.knowledge_service_factory = original_factory

    @pytest.mark.asyncio
    async def test_full_validation_workflow_success_pass(
        self,
        use_case: ValidateDocumentUseCase,
        document_repo: MemoryDocumentRepository,
        policy_repo: MemoryPolicyRepository,
        knowledge_service_query_repo: MemoryKnowledgeServiceQueryRepository,
        knowledge_service_config_repo: MemoryKnowledgeServiceConfigRepository,
        document_policy_validation_repo: (
            MemoryDocumentPolicyValidationRepository
        ),
    ) -> None:
        """Test complete validation workflow that passes validation."""
        # Arrange - Create test document
        content_text = "High quality document for testing validation"
        content_bytes = content_text.encode("utf-8")
        document = Document(
            document_id="doc-123",
            original_filename="test_document.txt",
            content_type="text/plain",
            size_bytes=len(content_bytes),
            content_multihash="test-hash-123",
            status=DocumentStatus.CAPTURED,
            content=ContentStream(io.BytesIO(content_bytes)),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        await document_repo.save(document)

        # Create policy with validation criteria
        policy = Policy(
            policy_id="policy-123",
            title="Quality Policy",
            description="Validates document quality",
            status=PolicyStatus.ACTIVE,
            validation_scores=[
                ("quality-query", 80),
                ("clarity-query", 70),
            ],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        await policy_repo.save(policy)

        # Create knowledge service config
        ks_config = KnowledgeServiceConfig(
            knowledge_service_id="ks-123",
            name="Test Knowledge Service",
            description="Test service",
            service_api=ServiceApi.ANTHROPIC,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        await knowledge_service_config_repo.save(ks_config)

        # Create knowledge service queries
        quality_query = KnowledgeServiceQuery(
            query_id="quality-query",
            name="Quality Check",
            knowledge_service_id="ks-123",
            prompt="Rate the quality of this document on a scale of 0-100",
            query_metadata={"max_tokens": 10},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        clarity_query = KnowledgeServiceQuery(
            query_id="clarity-query",
            name="Clarity Check",
            knowledge_service_id="ks-123",
            prompt="Rate the clarity of this document on a scale of 0-100",
            query_metadata={"max_tokens": 10},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        await knowledge_service_query_repo.save(quality_query)
        await knowledge_service_query_repo.save(clarity_query)

        # Create memory service with passing scores
        memory_service = MemoryKnowledgeService(ks_config)
        memory_service.add_canned_query_results(
            [
                QueryResult(
                    query_id="result-1",
                    query_text="Rate the quality of this document on a "
                    "scale of 0-100",
                    result_data={
                        "response": "85"
                    },  # Passes requirement of 80
                    execution_time_ms=100,
                    created_at=datetime.now(timezone.utc),
                ),
                QueryResult(
                    query_id="result-2",
                    query_text="Rate the clarity of this document on a "
                    "scale of 0-100",
                    result_data={
                        "response": "75"
                    },  # Passes requirement of 70
                    execution_time_ms=150,
                    created_at=datetime.now(timezone.utc),
                ),
            ]
        )

        # Patch the factory to return our configured memory service
        module = julee_example.use_cases.validate_document
        original_factory = module.knowledge_service_factory
        module.knowledge_service_factory = (
            lambda config: memory_service  # type: ignore[assignment]
        )

        try:
            # Act
            result = await use_case.validate_document(
                document_id="doc-123", policy_id="policy-123"
            )
        finally:
            # Restore original factory
            module.knowledge_service_factory = original_factory

        # Assert
        assert isinstance(result, DocumentPolicyValidation)
        assert result.status == DocumentPolicyValidationStatus.PASSED
        assert result.passed is True
        assert result.validation_scores == [
            ("quality-query", 85),
            ("clarity-query", 75),
        ]
        assert result.completed_at is not None
        assert result.error_message is None

        # Verify validation was saved to repository
        saved_validation = await document_policy_validation_repo.get(
            result.validation_id
        )
        assert saved_validation is not None
        assert (
            saved_validation.status == DocumentPolicyValidationStatus.PASSED
        )
        assert saved_validation.passed is True

    @pytest.mark.asyncio
    async def test_full_validation_workflow_success_fail(
        self,
        use_case: ValidateDocumentUseCase,
        document_repo: MemoryDocumentRepository,
        policy_repo: MemoryPolicyRepository,
        knowledge_service_query_repo: MemoryKnowledgeServiceQueryRepository,
        knowledge_service_config_repo: MemoryKnowledgeServiceConfigRepository,
        document_policy_validation_repo: (
            MemoryDocumentPolicyValidationRepository
        ),
    ) -> None:
        """Test complete validation workflow that fails validation."""
        # Arrange - Create test document
        content_text = "Poor quality document"
        content_bytes = content_text.encode("utf-8")
        document = Document(
            document_id="doc-456",
            original_filename="poor_document.txt",
            content_type="text/plain",
            size_bytes=len(content_bytes),
            content_multihash="test-hash-456",
            status=DocumentStatus.CAPTURED,
            content=ContentStream(io.BytesIO(content_bytes)),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        await document_repo.save(document)

        # Create policy with high standards
        policy = Policy(
            policy_id="policy-456",
            title="High Standards Policy",
            description="Requires high quality scores",
            status=PolicyStatus.ACTIVE,
            validation_scores=[("quality-query", 90)],  # High requirement
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        await policy_repo.save(policy)

        # Create knowledge service config and query
        ks_config = KnowledgeServiceConfig(
            knowledge_service_id="ks-456",
            name="Test Knowledge Service",
            description="Test service",
            service_api=ServiceApi.ANTHROPIC,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        await knowledge_service_config_repo.save(ks_config)

        quality_query = KnowledgeServiceQuery(
            query_id="quality-query",
            name="Quality Check",
            knowledge_service_id="ks-456",
            prompt="Rate the quality of this document on a scale of 0-100",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        await knowledge_service_query_repo.save(quality_query)

        # Create memory service with failing score
        memory_service = MemoryKnowledgeService(ks_config)
        memory_service.add_canned_query_result(
            QueryResult(
                query_id="result-1",
                query_text="Rate the quality of this document on a "
                "scale of 0-100",
                result_data={"response": "60"},  # Fails requirement of 90
                execution_time_ms=100,
                created_at=datetime.now(timezone.utc),
            )
        )

        # Patch the factory to return our configured memory service
        module = julee_example.use_cases.validate_document
        original_factory = module.knowledge_service_factory
        module.knowledge_service_factory = (
            lambda config: memory_service  # type: ignore[assignment]
        )

        try:
            # Act
            result = await use_case.validate_document(
                document_id="doc-456", policy_id="policy-456"
            )
        finally:
            # Restore original factory
            module.knowledge_service_factory = original_factory

        # Assert
        assert isinstance(result, DocumentPolicyValidation)
        assert result.status == DocumentPolicyValidationStatus.FAILED
        assert result.passed is False
        assert result.validation_scores == [("quality-query", 60)]
        assert result.completed_at is not None
        assert result.error_message is None

    @pytest.mark.asyncio
    async def test_validation_fails_with_out_of_range_scores(
        self,
        use_case: ValidateDocumentUseCase,
        document_repo: MemoryDocumentRepository,
        policy_repo: MemoryPolicyRepository,
        knowledge_service_query_repo: MemoryKnowledgeServiceQueryRepository,
        knowledge_service_config_repo: MemoryKnowledgeServiceConfigRepository,
    ) -> None:
        """Test that validation fails when domain model rejects out-of-range
        scores."""
        # Arrange - Create test document
        content_text = "Test document"
        content_bytes = content_text.encode("utf-8")
        document = Document(
            document_id="doc-789",
            original_filename="test.txt",
            content_type="text/plain",
            size_bytes=len(content_bytes),
            content_multihash="test-hash-789",
            status=DocumentStatus.CAPTURED,
            content=ContentStream(io.BytesIO(content_bytes)),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        await document_repo.save(document)

        # Create policy
        policy = Policy(
            policy_id="policy-789",
            title="Test Policy",
            description="Test policy for out-of-range scores",
            status=PolicyStatus.ACTIVE,
            validation_scores=[("test-query", 80)],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        await policy_repo.save(policy)

        # Create knowledge service config and query
        ks_config = KnowledgeServiceConfig(
            knowledge_service_id="ks-789",
            name="Test Knowledge Service",
            description="Test service",
            service_api=ServiceApi.ANTHROPIC,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        await knowledge_service_config_repo.save(ks_config)

        test_query = KnowledgeServiceQuery(
            query_id="test-query",
            name="Test Query",
            knowledge_service_id="ks-789",
            prompt="Rate this document",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        await knowledge_service_query_repo.save(test_query)

        # Create memory service with out-of-range score
        memory_service = MemoryKnowledgeService(ks_config)
        memory_service.add_canned_query_result(
            QueryResult(
                query_id="result-1",
                query_text="Rate this document",
                result_data={"response": "150"},  # Out of normal 0-100 range
                execution_time_ms=100,
                created_at=datetime.now(timezone.utc),
            )
        )

        # Patch the factory to return our configured memory service
        module = julee_example.use_cases.validate_document
        original_factory = module.knowledge_service_factory
        module.knowledge_service_factory = (
            lambda config: memory_service  # type: ignore[assignment]
        )

        try:
            # Act & Assert - Domain model should reject out-of-range score
            with pytest.raises(
                ValueError,
                match="must be between 0 and 100",
            ):
                await use_case.validate_document(
                    document_id="doc-789", policy_id="policy-789"
                )
        finally:
            # Restore original factory
            module.knowledge_service_factory = original_factory

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
from pydantic import ValidationError

from julee_example.domain.use_cases import ValidateDocumentUseCase

from julee_example.domain.models import (
    Document,
    DocumentStatus,
    ContentStream,
    KnowledgeServiceConfig,
    KnowledgeServiceQuery,
)
from julee_example.domain.models.policy import (
    Policy,
    PolicyStatus,
    DocumentPolicyValidation,
    DocumentPolicyValidationStatus,
)
from julee_example.domain.models.knowledge_service_config import ServiceApi
from julee_example.repositories.memory import (
    MemoryDocumentRepository,
    MemoryKnowledgeServiceQueryRepository,
    MemoryKnowledgeServiceConfigRepository,
    MemoryPolicyRepository,
    MemoryDocumentPolicyValidationRepository,
)
from julee_example.services.knowledge_service.memory import (
    MemoryKnowledgeService,
)
from julee_example.services.knowledge_service import QueryResult


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
    def knowledge_service(self) -> MemoryKnowledgeService:
        """Create a memory KnowledgeService for testing."""
        ks_config = KnowledgeServiceConfig(
            knowledge_service_id="ks-test",
            name="Test Knowledge Service",
            description="Test service",
            service_api=ServiceApi.ANTHROPIC,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        return MemoryKnowledgeService(ks_config)

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
        knowledge_service: MemoryKnowledgeService,
    ) -> ValidateDocumentUseCase:
        """Create ValidateDocumentUseCase with memory repository
        dependencies."""
        return ValidateDocumentUseCase(
            document_repo=document_repo,
            knowledge_service_query_repo=knowledge_service_query_repo,
            knowledge_service_config_repo=knowledge_service_config_repo,
            policy_repo=policy_repo,
            document_policy_validation_repo=document_policy_validation_repo,
            knowledge_service=knowledge_service,
            now_fn=lambda: datetime.now(timezone.utc),
        )

    def _create_configured_use_case(
        self,
        document_repo: MemoryDocumentRepository,
        knowledge_service_query_repo: MemoryKnowledgeServiceQueryRepository,
        knowledge_service_config_repo: MemoryKnowledgeServiceConfigRepository,
        policy_repo: MemoryPolicyRepository,
        document_policy_validation_repo: (
            MemoryDocumentPolicyValidationRepository
        ),
        memory_service: MemoryKnowledgeService,
    ) -> ValidateDocumentUseCase:
        """Helper to create ValidateDocumentUseCase with configured memory
        service."""
        return ValidateDocumentUseCase(
            document_repo=document_repo,
            knowledge_service_query_repo=knowledge_service_query_repo,
            knowledge_service_config_repo=knowledge_service_config_repo,
            policy_repo=policy_repo,
            document_policy_validation_repo=document_policy_validation_repo,
            knowledge_service=memory_service,
            now_fn=lambda: datetime.now(timezone.utc),
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
        with pytest.raises(ValueError, match="Validation query not found"):
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
        document_policy_validation_repo: (
            MemoryDocumentPolicyValidationRepository
        ),
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

        # Create use case with configured memory service
        configured_use_case = self._create_configured_use_case(
            document_repo=document_repo,
            knowledge_service_query_repo=knowledge_service_query_repo,
            knowledge_service_config_repo=knowledge_service_config_repo,
            policy_repo=policy_repo,
            document_policy_validation_repo=document_policy_validation_repo,
            memory_service=memory_service,
        )

        # Act & Assert
        with pytest.raises(
            ValueError,
            match="Failed to parse numeric score from response",
        ):
            await configured_use_case.validate_document(
                document_id="doc-123", policy_id="policy-123"
            )

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

        # Create use case with configured memory service
        configured_use_case = self._create_configured_use_case(
            document_repo=document_repo,
            knowledge_service_query_repo=knowledge_service_query_repo,
            knowledge_service_config_repo=knowledge_service_config_repo,
            policy_repo=policy_repo,
            document_policy_validation_repo=document_policy_validation_repo,
            memory_service=memory_service,
        )

        # Act
        result = await configured_use_case.validate_document(
            document_id="doc-123", policy_id="policy-123"
        )

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

        # Create use case with configured memory service
        configured_use_case = self._create_configured_use_case(
            document_repo=document_repo,
            knowledge_service_query_repo=knowledge_service_query_repo,
            knowledge_service_config_repo=knowledge_service_config_repo,
            policy_repo=policy_repo,
            document_policy_validation_repo=document_policy_validation_repo,
            memory_service=memory_service,
        )

        # Act
        await configured_use_case.validate_document(
            document_id="doc-456", policy_id="policy-456"
        )

    @pytest.mark.asyncio
    async def test_validation_with_transformation_success(
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
        """Test validation with transformation that results in passing."""
        # Arrange - Create test document
        content_text = "Poor quality document that can be improved"
        content_bytes = content_text.encode("utf-8")
        document = Document(
            document_id="doc-transform-1",
            original_filename="transform_test.txt",
            content_type="text/plain",
            size_bytes=len(content_bytes),
            content_multihash="test-hash-transform-1",
            status=DocumentStatus.CAPTURED,
            content=ContentStream(io.BytesIO(content_bytes)),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        await document_repo.save(document)

        # Create policy with transformation queries
        policy = Policy(
            policy_id="policy-transform-1",
            title="Transformation Policy",
            description="Policy with transformation capabilities",
            status=PolicyStatus.ACTIVE,
            validation_scores=[("quality-query", 80)],
            transformation_queries=["improvement-query"],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        await policy_repo.save(policy)

        # Create knowledge service config
        ks_config = KnowledgeServiceConfig(
            knowledge_service_id="ks-transform-1",
            name="Transform Knowledge Service",
            description="Service with transformation capability",
            service_api=ServiceApi.ANTHROPIC,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        await knowledge_service_config_repo.save(ks_config)

        # Create validation and transformation queries
        quality_query = KnowledgeServiceQuery(
            query_id="quality-query",
            name="Quality Check",
            knowledge_service_id="ks-transform-1",
            prompt="Rate the quality of this document on a scale of 0-100",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        improvement_query = KnowledgeServiceQuery(
            query_id="improvement-query",
            name="Document Improvement",
            knowledge_service_id="ks-transform-1",
            prompt="Improve this document to make it higher quality",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        await knowledge_service_query_repo.save(quality_query)
        await knowledge_service_query_repo.save(improvement_query)

        # Create memory service that simulates transformation workflow
        memory_service = MemoryKnowledgeService(ks_config)

        # First validation (fails with score 60)
        memory_service.add_canned_query_result(
            QueryResult(
                query_id="initial-validation",
                query_text="Rate the quality of this document on a scale "
                "of 0-100",
                result_data={"response": "60"},  # Initial score fails
                execution_time_ms=100,
                created_at=datetime.now(timezone.utc),
            )
        )

        # Transformation query returns improved content
        memory_service.add_canned_query_result(
            QueryResult(
                query_id="transformation",
                query_text="Improve this document to make it higher quality",
                result_data={
                    "response": '{"improved_content": "This is a much '
                    "higher quality document with better structure and "
                    'clarity."}'
                },
                execution_time_ms=200,
                created_at=datetime.now(timezone.utc),
            )
        )

        # Post-transformation validation (passes with score 85)
        memory_service.add_canned_query_result(
            QueryResult(
                query_id="post-transform-validation",
                query_text="Rate the quality of this document on a scale "
                "of 0-100",
                result_data={"response": "85"},  # Post-transform score passes
                execution_time_ms=100,
                created_at=datetime.now(timezone.utc),
            )
        )

        # Create use case with configured memory service
        configured_use_case = self._create_configured_use_case(
            document_repo=document_repo,
            knowledge_service_query_repo=knowledge_service_query_repo,
            knowledge_service_config_repo=knowledge_service_config_repo,
            policy_repo=policy_repo,
            document_policy_validation_repo=document_policy_validation_repo,
            memory_service=memory_service,
        )

        # Act
        result = await configured_use_case.validate_document(
            document_id="doc-transform-1", policy_id="policy-transform-1"
        )

        # Assert
        assert isinstance(result, DocumentPolicyValidation)
        assert result.status == DocumentPolicyValidationStatus.PASSED
        assert result.passed is True
        assert result.validation_scores == [
            ("quality-query", 60)
        ]  # Initial scores
        assert result.post_transform_validation_scores == [
            ("quality-query", 85)
        ]  # Final scores
        assert result.transformed_document_id is not None
        assert result.completed_at is not None

        # Verify transformed document was created and saved
        transformed_document = await document_repo.get(
            result.transformed_document_id
        )
        assert transformed_document is not None
        assert transformed_document.original_filename.startswith(
            "transformed_"
        )
        assert transformed_document.content_type == "text/plain"

        # Verify validation was saved to repository
        saved_validation = await document_policy_validation_repo.get(
            result.validation_id
        )
        assert saved_validation is not None
        assert (
            saved_validation.status == DocumentPolicyValidationStatus.PASSED
        )
        assert saved_validation.transformed_document_id is not None

    @pytest.mark.asyncio
    async def test_validation_with_transformation_still_fails(
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
        """Test validation with transformation that still fails after
        transformation."""
        # Arrange - Create test document
        content_text = "Very poor quality document"
        content_bytes = content_text.encode("utf-8")
        document = Document(
            document_id="doc-transform-2",
            original_filename="poor_transform_test.txt",
            content_type="text/plain",
            size_bytes=len(content_bytes),
            content_multihash="test-hash-transform-2",
            status=DocumentStatus.CAPTURED,
            content=ContentStream(io.BytesIO(content_bytes)),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        await document_repo.save(document)

        # Create policy with high standards and transformation
        policy = Policy(
            policy_id="policy-transform-2",
            title="High Standards Transform Policy",
            description="Policy with very high standards even after "
            "transformation",
            status=PolicyStatus.ACTIVE,
            validation_scores=[
                ("quality-query", 95)
            ],  # Very high requirement
            transformation_queries=["improvement-query"],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        await policy_repo.save(policy)

        # Create knowledge service config
        ks_config = KnowledgeServiceConfig(
            knowledge_service_id="ks-transform-2",
            name="Transform Knowledge Service",
            description="Service with transformation capability",
            service_api=ServiceApi.ANTHROPIC,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        await knowledge_service_config_repo.save(ks_config)

        # Create validation and transformation queries
        quality_query = KnowledgeServiceQuery(
            query_id="quality-query",
            name="Quality Check",
            knowledge_service_id="ks-transform-2",
            prompt="Rate the quality of this document on a scale of 0-100",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        improvement_query = KnowledgeServiceQuery(
            query_id="improvement-query",
            name="Document Improvement",
            knowledge_service_id="ks-transform-2",
            prompt="Try to improve this document",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        await knowledge_service_query_repo.save(quality_query)
        await knowledge_service_query_repo.save(improvement_query)

        # Create memory service that simulates failed transformation
        memory_service = MemoryKnowledgeService(ks_config)

        # Initial validation fails
        memory_service.add_canned_query_result(
            QueryResult(
                query_id="initial-validation",
                query_text="Rate the quality of this document on a scale "
                "of 0-100",
                result_data={"response": "40"},  # Initial score fails
                execution_time_ms=100,
                created_at=datetime.now(timezone.utc),
            )
        )

        # Transformation attempt
        memory_service.add_canned_query_result(
            QueryResult(
                query_id="transformation",
                query_text="Try to improve this document",
                result_data={
                    "response": '{"improved_content": "Slightly improved '
                    'but still poor quality document."}'
                },
                execution_time_ms=200,
                created_at=datetime.now(timezone.utc),
            )
        )

        # Post-transformation validation still fails
        memory_service.add_canned_query_result(
            QueryResult(
                query_id="post-transform-validation",
                query_text="Rate the quality of this document on a scale "
                "of 0-100",
                result_data={
                    "response": "70"
                },  # Still fails requirement of 95
                execution_time_ms=100,
                created_at=datetime.now(timezone.utc),
            )
        )

        # Create use case with configured memory service
        configured_use_case = self._create_configured_use_case(
            document_repo=document_repo,
            knowledge_service_query_repo=knowledge_service_query_repo,
            knowledge_service_config_repo=knowledge_service_config_repo,
            policy_repo=policy_repo,
            document_policy_validation_repo=document_policy_validation_repo,
            memory_service=memory_service,
        )

        # Act
        result = await configured_use_case.validate_document(
            document_id="doc-transform-2", policy_id="policy-transform-2"
        )

        # Assert
        assert isinstance(result, DocumentPolicyValidation)
        assert result.status == DocumentPolicyValidationStatus.FAILED
        assert result.passed is False
        assert result.validation_scores == [
            ("quality-query", 40)
        ]  # Initial scores
        assert result.post_transform_validation_scores == [
            ("quality-query", 70)
        ]  # Final scores still fail
        assert result.transformed_document_id is not None
        assert result.completed_at is not None

    @pytest.mark.asyncio
    async def test_validation_no_transformation_when_initially_passes(
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
        """Test that transformation is skipped when initial validation
        passes."""
        # Arrange - Create high quality document
        content_text = "Excellent high quality document"
        content_bytes = content_text.encode("utf-8")
        document = Document(
            document_id="doc-no-transform",
            original_filename="excellent_doc.txt",
            content_type="text/plain",
            size_bytes=len(content_bytes),
            content_multihash="test-hash-no-transform",
            status=DocumentStatus.CAPTURED,
            content=ContentStream(io.BytesIO(content_bytes)),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        await document_repo.save(document)

        # Create policy with transformation available but not needed
        policy = Policy(
            policy_id="policy-no-transform",
            title="Policy with Unnecessary Transform",
            description="Policy with transformation that won't be used",
            status=PolicyStatus.ACTIVE,
            validation_scores=[("quality-query", 80)],
            transformation_queries=[
                "improvement-query"
            ],  # Available but unused
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        await policy_repo.save(policy)

        # Create knowledge service config
        ks_config = KnowledgeServiceConfig(
            knowledge_service_id="ks-no-transform",
            name="Knowledge Service",
            description="Service description",
            service_api=ServiceApi.ANTHROPIC,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        await knowledge_service_config_repo.save(ks_config)

        # Create queries (transformation query won't be used)
        quality_query = KnowledgeServiceQuery(
            query_id="quality-query",
            name="Quality Check",
            knowledge_service_id="ks-no-transform",
            prompt="Rate the quality of this document on a scale of 0-100",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        improvement_query = KnowledgeServiceQuery(
            query_id="improvement-query",
            name="Document Improvement",
            knowledge_service_id="ks-no-transform",
            prompt="This query should not be called",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        await knowledge_service_query_repo.save(quality_query)
        await knowledge_service_query_repo.save(improvement_query)

        # Create memory service with only validation result (no
        # transformation)
        memory_service = MemoryKnowledgeService(ks_config)
        memory_service.add_canned_query_result(
            QueryResult(
                query_id="validation-only",
                query_text="Rate the quality of this document on a scale "
                "of 0-100",
                result_data={"response": "90"},  # Passes initial validation
                execution_time_ms=100,
                created_at=datetime.now(timezone.utc),
            )
        )

        # Create use case with configured memory service
        configured_use_case = self._create_configured_use_case(
            document_repo=document_repo,
            knowledge_service_query_repo=knowledge_service_query_repo,
            knowledge_service_config_repo=knowledge_service_config_repo,
            policy_repo=policy_repo,
            document_policy_validation_repo=document_policy_validation_repo,
            memory_service=memory_service,
        )

        # Act
        result = await configured_use_case.validate_document(
            document_id="doc-no-transform", policy_id="policy-no-transform"
        )

        # Assert
        assert isinstance(result, DocumentPolicyValidation)
        assert result.status == DocumentPolicyValidationStatus.PASSED
        assert result.passed is True
        assert result.validation_scores == [("quality-query", 90)]
        assert (
            result.post_transform_validation_scores is None
        )  # No transformation
        assert result.transformed_document_id is None  # No transformation
        assert result.completed_at is not None

    @pytest.mark.asyncio
    async def test_transformation_fails_with_invalid_json(
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
        """Test that transformation fails when result is not valid JSON."""
        # Arrange - Create test document
        content_text = "Document needing transformation"
        content_bytes = content_text.encode("utf-8")
        document = Document(
            document_id="doc-invalid-json",
            original_filename="invalid_json_test.txt",
            content_type="text/plain",
            size_bytes=len(content_bytes),
            content_multihash="test-hash-invalid-json",
            status=DocumentStatus.CAPTURED,
            content=ContentStream(io.BytesIO(content_bytes)),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        await document_repo.save(document)

        # Create policy with transformation
        policy = Policy(
            policy_id="policy-invalid-json",
            title="Invalid JSON Transform Policy",
            description="Policy that will get invalid JSON from "
            "transformation",
            status=PolicyStatus.ACTIVE,
            validation_scores=[("quality-query", 80)],
            transformation_queries=["bad-transform-query"],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        await policy_repo.save(policy)

        # Create knowledge service config
        ks_config = KnowledgeServiceConfig(
            knowledge_service_id="ks-invalid-json",
            name="Invalid JSON Service",
            description="Service that returns invalid JSON",
            service_api=ServiceApi.ANTHROPIC,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        await knowledge_service_config_repo.save(ks_config)

        # Create queries
        quality_query = KnowledgeServiceQuery(
            query_id="quality-query",
            name="Quality Check",
            knowledge_service_id="ks-invalid-json",
            prompt="Rate the quality of this document on a scale of 0-100",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        bad_transform_query = KnowledgeServiceQuery(
            query_id="bad-transform-query",
            name="Bad Transform Query",
            knowledge_service_id="ks-invalid-json",
            prompt="Transform this document",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        await knowledge_service_query_repo.save(quality_query)
        await knowledge_service_query_repo.save(bad_transform_query)

        # Create memory service that returns invalid JSON
        memory_service = MemoryKnowledgeService(ks_config)

        # Initial validation fails
        memory_service.add_canned_query_result(
            QueryResult(
                query_id="initial-validation",
                query_text="Rate the quality of this document on a scale "
                "of 0-100",
                result_data={
                    "response": "50"
                },  # Fails, triggers transformation
                execution_time_ms=100,
                created_at=datetime.now(timezone.utc),
            )
        )

        # Transformation returns invalid JSON
        memory_service.add_canned_query_result(
            QueryResult(
                query_id="bad-transformation",
                query_text="Transform this document",
                result_data={"response": "This is not valid JSON at all!"},
                execution_time_ms=200,
                created_at=datetime.now(timezone.utc),
            )
        )

        # Create use case with configured memory service
        configured_use_case = self._create_configured_use_case(
            document_repo=document_repo,
            knowledge_service_query_repo=knowledge_service_query_repo,
            knowledge_service_config_repo=knowledge_service_config_repo,
            policy_repo=policy_repo,
            document_policy_validation_repo=document_policy_validation_repo,
            memory_service=memory_service,
        )

        # Act & Assert
        with pytest.raises(
            ValueError,
            match="Transformation result must be valid JSON",
        ):
            await configured_use_case.validate_document(
                document_id="doc-invalid-json",
                policy_id="policy-invalid-json",
            )

    @pytest.mark.asyncio
    async def test_transformation_query_not_found(
        self,
        use_case: ValidateDocumentUseCase,
        document_repo: MemoryDocumentRepository,
        policy_repo: MemoryPolicyRepository,
        knowledge_service_query_repo: MemoryKnowledgeServiceQueryRepository,
        knowledge_service_config_repo: MemoryKnowledgeServiceConfigRepository,
    ) -> None:
        """Test that validation fails when transformation query is not
        found."""
        # Arrange - Create test document
        content_text = "Document needing transformation"
        content_bytes = content_text.encode("utf-8")
        document = Document(
            document_id="doc-missing-query",
            original_filename="missing_query_test.txt",
            content_type="text/plain",
            size_bytes=len(content_bytes),
            content_multihash="test-hash-missing-query",
            status=DocumentStatus.CAPTURED,
            content=ContentStream(io.BytesIO(content_bytes)),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        await document_repo.save(document)

        # Create policy with non-existent transformation query
        policy = Policy(
            policy_id="policy-missing-query",
            title="Missing Query Policy",
            description="Policy with missing transformation query",
            status=PolicyStatus.ACTIVE,
            validation_scores=[("quality-query", 80)],
            transformation_queries=["nonexistent-transform-query"],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        await policy_repo.save(policy)

        # Create knowledge service config
        ks_config = KnowledgeServiceConfig(
            knowledge_service_id="ks-missing-query",
            name="Missing Query Service",
            description="Service config",
            service_api=ServiceApi.ANTHROPIC,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        await knowledge_service_config_repo.save(ks_config)

        # Create only the validation query (transformation query is missing)
        quality_query = KnowledgeServiceQuery(
            query_id="quality-query",
            name="Quality Check",
            knowledge_service_id="ks-missing-query",
            prompt="Rate the quality of this document on a scale of 0-100",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        await knowledge_service_query_repo.save(quality_query)
        # Note: NOT saving the transformation query

        # Act & Assert
        with pytest.raises(
            ValueError, match="Transformation query not found"
        ):
            await use_case.validate_document(
                document_id="doc-missing-query",
                policy_id="policy-missing-query",
            )

    @pytest.mark.asyncio
    async def test_validation_fails_with_out_of_range_scores(
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

        # Create use case with configured memory service
        configured_use_case = self._create_configured_use_case(
            document_repo=document_repo,
            knowledge_service_query_repo=knowledge_service_query_repo,
            knowledge_service_config_repo=knowledge_service_config_repo,
            policy_repo=policy_repo,
            document_policy_validation_repo=document_policy_validation_repo,
            memory_service=memory_service,
        )

        # Act & Assert
        with pytest.raises(
            ValidationError,
            match="must be between 0 and 100",
        ):
            await configured_use_case.validate_document(
                document_id="doc-789", policy_id="policy-789"
            )

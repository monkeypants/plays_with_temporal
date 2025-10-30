"""
Tests for ExtractAssembleDataUseCase.

This module provides tests for the extract and assemble data use case,
ensuring proper business logic execution and repository interaction patterns
following the Clean Architecture principles.
"""

import io
import json
import pytest

from unittest.mock import AsyncMock
from datetime import datetime, timezone

from julee_example.domain.use_cases import ExtractAssembleDataUseCase
from julee_example.domain.models import (
    Assembly,
    AssemblyStatus,
    Document,
    DocumentStatus,
    ContentStream,
    AssemblySpecification,
    AssemblySpecificationStatus,
    KnowledgeServiceQuery,
    KnowledgeServiceConfig,
)
from julee_example.domain.models.knowledge_service_config import ServiceApi
from julee_example.repositories.memory import (
    MemoryDocumentRepository,
    MemoryAssemblyRepository,
    MemoryAssemblySpecificationRepository,
    MemoryKnowledgeServiceConfigRepository,
    MemoryKnowledgeServiceQueryRepository,
)
from julee_example.services.knowledge_service.memory import (
    MemoryKnowledgeService,
)
from julee_example.services.knowledge_service import QueryResult


class TestExtractAssembleDataUseCase:
    """Test cases for ExtractAssembleDataUseCase business logic."""

    @pytest.fixture
    def document_repo(self) -> MemoryDocumentRepository:
        """Create a memory DocumentRepository for testing."""
        return MemoryDocumentRepository()

    @pytest.fixture
    def assembly_repo(self) -> MemoryAssemblyRepository:
        """Create a memory AssemblyRepository for testing."""
        return MemoryAssemblyRepository()

    @pytest.fixture
    def assembly_specification_repo(
        self,
    ) -> MemoryAssemblySpecificationRepository:
        """Create a memory AssemblySpecificationRepository for testing."""
        return MemoryAssemblySpecificationRepository()

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
    def configured_knowledge_service(self) -> MemoryKnowledgeService:
        """Create a configured memory KnowledgeService for full workflow
        tests."""
        ks_config = KnowledgeServiceConfig(
            knowledge_service_id="ks-123",
            name="Test Knowledge Service",
            description="Test service",
            service_api=ServiceApi.ANTHROPIC,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        memory_service = MemoryKnowledgeService(ks_config)
        memory_service.add_canned_query_results(
            [
                QueryResult(
                    query_id="result-1",
                    query_text="Extract the title from this document",
                    result_data={"response": '"Test Meeting"'},
                    execution_time_ms=100,
                    created_at=datetime.now(timezone.utc),
                ),
                QueryResult(
                    query_id="result-2",
                    query_text="Extract a summary from this document",
                    result_data={
                        "response": (
                            '"This was a test meeting about important topics"'
                        )
                    },
                    execution_time_ms=150,
                    created_at=datetime.now(timezone.utc),
                ),
            ]
        )
        return memory_service

    @pytest.fixture
    def use_case(
        self,
        document_repo: MemoryDocumentRepository,
        assembly_repo: MemoryAssemblyRepository,
        assembly_specification_repo: MemoryAssemblySpecificationRepository,
        knowledge_service_query_repo: MemoryKnowledgeServiceQueryRepository,
        knowledge_service_config_repo: MemoryKnowledgeServiceConfigRepository,
        knowledge_service: MemoryKnowledgeService,
    ) -> ExtractAssembleDataUseCase:
        """Create ExtractAssembleDataUseCase with memory repository
        dependencies."""
        return ExtractAssembleDataUseCase(
            document_repo=document_repo,
            assembly_repo=assembly_repo,
            assembly_specification_repo=assembly_specification_repo,
            knowledge_service_query_repo=knowledge_service_query_repo,
            knowledge_service_config_repo=knowledge_service_config_repo,
            knowledge_service=knowledge_service,
        )

    @pytest.fixture
    def configured_use_case(
        self,
        document_repo: MemoryDocumentRepository,
        assembly_repo: MemoryAssemblyRepository,
        assembly_specification_repo: MemoryAssemblySpecificationRepository,
        knowledge_service_query_repo: MemoryKnowledgeServiceQueryRepository,
        knowledge_service_config_repo: MemoryKnowledgeServiceConfigRepository,
        configured_knowledge_service: MemoryKnowledgeService,
    ) -> ExtractAssembleDataUseCase:
        """Create ExtractAssembleDataUseCase with configured knowledge service
        for full workflow tests."""
        return ExtractAssembleDataUseCase(
            document_repo=document_repo,
            assembly_repo=assembly_repo,
            assembly_specification_repo=assembly_specification_repo,
            knowledge_service_query_repo=knowledge_service_query_repo,
            knowledge_service_config_repo=knowledge_service_config_repo,
            knowledge_service=configured_knowledge_service,
        )

    @pytest.mark.asyncio
    async def test_assemble_data_fails_without_specification(
        self, use_case: ExtractAssembleDataUseCase
    ) -> None:
        """Test that assemble_data fails when specification doesn't exist."""
        # Arrange
        document_id = "doc-456"
        assembly_specification_id = "spec-789"

        # Act & Assert
        with pytest.raises(
            ValueError, match="Assembly specification not found"
        ):
            await use_case.assemble_data(
                document_id=document_id,
                assembly_specification_id=assembly_specification_id,
                workflow_id="test-workflow-123",
            )

    @pytest.mark.asyncio
    async def test_assemble_data_fails_without_document(
        self,
        use_case: ExtractAssembleDataUseCase,
        assembly_specification_repo: MemoryAssemblySpecificationRepository,
    ) -> None:
        """Test that assemble_data fails when document doesn't exist."""
        # Arrange - Create assembly specification but no document
        assembly_spec = AssemblySpecification(
            assembly_specification_id="spec-123",
            name="Test Assembly",
            applicability="Test documents",
            jsonschema={"type": "object", "properties": {}},
            status=AssemblySpecificationStatus.ACTIVE,
            knowledge_service_queries={},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        await assembly_specification_repo.save(assembly_spec)

        document_id = "nonexistent-doc"
        assembly_specification_id = "spec-123"

        # Act & Assert
        with pytest.raises(ValueError, match="Document not found"):
            await use_case.assemble_data(
                document_id=document_id,
                assembly_specification_id=assembly_specification_id,
                workflow_id="test-workflow-123",
            )

    @pytest.mark.asyncio
    async def test_assemble_data_propagates_id_generation_error(
        self,
        use_case: ExtractAssembleDataUseCase,
        assembly_repo: MemoryAssemblyRepository,
    ) -> None:
        """Test that ID generation errors are properly propagated."""
        # Arrange
        document_id = "doc-456"
        assembly_specification_id = "spec-789"
        expected_error = RuntimeError("ID generation failed")

        # Mock the generate_id method to raise an error
        assembly_repo.generate_id = AsyncMock(  # type: ignore[method-assign]
            side_effect=expected_error
        )

        # Act & Assert
        with pytest.raises(RuntimeError, match="ID generation failed"):
            await use_case.assemble_data(
                document_id=document_id,
                assembly_specification_id=assembly_specification_id,
                workflow_id="test-workflow-123",
            )

    @pytest.mark.asyncio
    async def test_full_assembly_workflow_success(
        self,
        configured_use_case: ExtractAssembleDataUseCase,
        document_repo: MemoryDocumentRepository,
        assembly_repo: MemoryAssemblyRepository,
        assembly_specification_repo: MemoryAssemblySpecificationRepository,
        knowledge_service_query_repo: MemoryKnowledgeServiceQueryRepository,
        knowledge_service_config_repo: MemoryKnowledgeServiceConfigRepository,
    ) -> None:
        """Test complete assembly workflow with knowledge service."""
        # Arrange - Create test document
        content_text = "Sample meeting transcript for testing"
        content_bytes = content_text.encode("utf-8")
        document = Document(
            document_id="doc-123",
            original_filename="test_transcript.txt",
            content_type="text/plain",
            size_bytes=len(content_bytes),
            content_multihash="test-hash-123",
            status=DocumentStatus.CAPTURED,
            content=ContentStream(io.BytesIO(content_bytes)),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        await document_repo.save(document)

        # Create assembly specification with simple schema
        schema = {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "summary": {"type": "string"},
            },
            "required": ["title", "summary"],
        }

        assembly_spec = AssemblySpecification(
            assembly_specification_id="spec-123",
            name="Test Assembly",
            applicability="Test documents",
            jsonschema=schema,
            status=AssemblySpecificationStatus.ACTIVE,
            knowledge_service_queries={
                "/properties/title": "query-1",
                "/properties/summary": "query-2",
            },
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        await assembly_specification_repo.save(assembly_spec)

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
        query1 = KnowledgeServiceQuery(
            query_id="query-1",
            name="Extract Title",
            knowledge_service_id="ks-123",
            prompt="Extract the title from this document",
            query_metadata={"max_tokens": 100},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        query2 = KnowledgeServiceQuery(
            query_id="query-2",
            name="Extract Summary",
            knowledge_service_id="ks-123",
            prompt="Extract a summary from this document",
            query_metadata={"max_tokens": 200},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        await knowledge_service_query_repo.save(query1)
        await knowledge_service_query_repo.save(query2)

        # Act - use configured_use_case which already has the configured
        # memory service
        result = await configured_use_case.assemble_data(
            document_id="doc-123",
            assembly_specification_id="spec-123",
            workflow_id="test-workflow-success",
        )

        # Assert
        assert isinstance(result, Assembly)
        assert result.status == AssemblyStatus.COMPLETED
        assert result.assembled_document_id is not None

        # Verify assembled document was created
        assembled_doc = await document_repo.get(result.assembled_document_id)
        assert assembled_doc is not None
        assert assembled_doc.status == DocumentStatus.ASSEMBLED

        # Check assembled content
        if assembled_doc.content is None:
            raise ValueError("Assembled document content is required")
        assembled_doc.content.seek(0)
        content = assembled_doc.content.read().decode("utf-8")
        assembled_data = json.loads(content)

        assert "title" in assembled_data
        assert "summary" in assembled_data
        assert assembled_data["title"] == "Test Meeting"
        assert (
            assembled_data["summary"]
            == "This was a test meeting about important topics"
        )

    @pytest.mark.asyncio
    async def test_assembly_fails_when_specification_not_found(
        self, use_case: ExtractAssembleDataUseCase
    ) -> None:
        """Test that assembly fails when specification is not found."""
        # Act & Assert
        with pytest.raises(
            ValueError, match="Assembly specification not found"
        ):
            await use_case.assemble_data(
                document_id="doc-123",
                assembly_specification_id="nonexistent-spec",
                workflow_id="test-workflow-123",
            )

    @pytest.mark.asyncio
    async def test_assembly_fails_when_document_not_found(
        self,
        use_case: ExtractAssembleDataUseCase,
        assembly_specification_repo: MemoryAssemblySpecificationRepository,
    ) -> None:
        """Test that assembly fails when input document is not found."""
        # Arrange - Create assembly specification but no document
        assembly_spec = AssemblySpecification(
            assembly_specification_id="spec-123",
            name="Test Assembly",
            applicability="Test documents",
            jsonschema={"type": "object", "properties": {}},
            status=AssemblySpecificationStatus.ACTIVE,
            knowledge_service_queries={},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        await assembly_specification_repo.save(assembly_spec)

        # Act & Assert
        with pytest.raises(ValueError, match="Document not found"):
            await use_case.assemble_data(
                document_id="nonexistent-doc",
                assembly_specification_id="spec-123",
                workflow_id="test-workflow-123",
            )

    @pytest.mark.asyncio
    async def test_assembly_fails_when_query_not_found(
        self,
        use_case: ExtractAssembleDataUseCase,
        document_repo: MemoryDocumentRepository,
        assembly_specification_repo: MemoryAssemblySpecificationRepository,
    ) -> None:
        """Test that assembly fails when query is not found."""
        # Arrange - Create document and spec with non-existent query
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

        assembly_spec = AssemblySpecification(
            assembly_specification_id="spec-123",
            name="Test Assembly",
            applicability="Test documents",
            jsonschema={
                "type": "object",
                "properties": {"title": {"type": "string"}},
            },
            status=AssemblySpecificationStatus.ACTIVE,
            knowledge_service_queries={
                "/properties/title": "nonexistent-query"
            },
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        await assembly_specification_repo.save(assembly_spec)

        # Act & Assert
        with pytest.raises(
            ValueError, match="Knowledge service query not found"
        ):
            await use_case.assemble_data(
                document_id="doc-123",
                assembly_specification_id="spec-123",
                workflow_id="test-workflow-123",
            )

    @pytest.mark.asyncio
    async def test_assembly_fails_with_invalid_json_schema(
        self,
        document_repo: MemoryDocumentRepository,
        assembly_repo: MemoryAssemblyRepository,
        assembly_specification_repo: MemoryAssemblySpecificationRepository,
        knowledge_service_query_repo: MemoryKnowledgeServiceQueryRepository,
        knowledge_service_config_repo: MemoryKnowledgeServiceConfigRepository,
    ) -> None:
        """Test that assembly fails when data doesn't match JSON schema."""
        # Arrange - Create test document
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

        # Create assembly specification with strict schema
        schema = {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "count": {"type": "integer"},  # Require integer
            },
            "required": ["title", "count"],
        }

        assembly_spec = AssemblySpecification(
            assembly_specification_id="spec-123",
            name="Test Assembly",
            applicability="Test documents",
            jsonschema=schema,
            status=AssemblySpecificationStatus.ACTIVE,
            knowledge_service_queries={"/properties/title": "query-1"},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        await assembly_specification_repo.save(assembly_spec)

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
            name="Extract Title",
            knowledge_service_id="ks-123",
            prompt="Extract the title",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        await knowledge_service_query_repo.save(query)

        # Create memory service that returns invalid data (missing count)
        memory_service = MemoryKnowledgeService(ks_config)
        memory_service.add_canned_query_result(
            QueryResult(
                query_id="result-1",
                query_text="Extract the title",
                result_data={
                    "response": '"Test"'
                },  # Only returns title, missing "count" field
                execution_time_ms=100,
                created_at=datetime.now(timezone.utc),
            )
        )

        # Create use case with configured memory service
        test_use_case = ExtractAssembleDataUseCase(
            document_repo=document_repo,
            assembly_repo=assembly_repo,
            assembly_specification_repo=assembly_specification_repo,
            knowledge_service_query_repo=knowledge_service_query_repo,
            knowledge_service_config_repo=knowledge_service_config_repo,
            knowledge_service=memory_service,
        )

        # Act & Assert
        with pytest.raises(
            ValueError,
            match="Assembled data does not conform to JSON schema",
        ):
            await test_use_case.assemble_data(
                document_id="doc-123",
                assembly_specification_id="spec-123",
                workflow_id="test-workflow-123",
            )

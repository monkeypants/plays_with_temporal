"""
Tests for MemoryKnowledgeService implementation.

This module contains tests for the in-memory implementation of the
KnowledgeService protocol, verifying file registration storage and
canned query response functionality.
"""

import pytest
from datetime import datetime, timezone
from julee_example.domain.models.knowledge_service_config import (
    KnowledgeServiceConfig,
)
from julee_example.domain.models.document import Document, DocumentStatus
from julee_example.domain.models.knowledge_service_config import ServiceApi
from julee_example.domain.models.custom_fields.content_stream import (
    ContentStream,
)
from ..knowledge_service import QueryResult
from .knowledge_service import MemoryKnowledgeService
import io


@pytest.fixture
def test_document() -> Document:
    """Create a test Document for testing."""
    content_text = (
        "This is test document content for knowledge service testing."
    )
    content_bytes = content_text.encode("utf-8")
    content_stream = ContentStream(io.BytesIO(content_bytes))

    return Document(
        document_id="test-doc-123",
        original_filename="test_document.txt",
        content_type="text/plain",
        size_bytes=len(content_bytes),
        content_multihash="test-hash-123",
        status=DocumentStatus.CAPTURED,
        content=content_stream,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def knowledge_service_config() -> KnowledgeServiceConfig:
    """Create a test KnowledgeServiceConfig."""
    return KnowledgeServiceConfig(
        knowledge_service_id="ks-memory-test",
        name="Test Memory Service",
        description="Memory service for testing",
        service_api=ServiceApi.ANTHROPIC,
    )


@pytest.fixture
def memory_service(
    knowledge_service_config: KnowledgeServiceConfig,
) -> MemoryKnowledgeService:
    """Create a MemoryKnowledgeService instance for testing."""
    return MemoryKnowledgeService(knowledge_service_config)


@pytest.fixture
def sample_query_result() -> QueryResult:
    """Create a sample QueryResult for testing."""
    return QueryResult(
        query_id="test-query-123",
        query_text="What is the main topic?",
        result_data={
            "response": "The main topic is testing",
            "confidence": 0.95,
        },
        execution_time_ms=150,
    )


class TestMemoryKnowledgeService:
    """Test cases for MemoryKnowledgeService."""

    async def test_register_file_creates_new_registration(
        self,
        memory_service: MemoryKnowledgeService,
        knowledge_service_config: KnowledgeServiceConfig,
        test_document: Document,
    ) -> None:
        """Test that register_file creates a new file registration."""
        result = await memory_service.register_file(
            knowledge_service_config, test_document
        )

        assert result.document_id == test_document.document_id
        assert result.knowledge_service_file_id.startswith(
            f"memory_{test_document.document_id}_"
        )
        assert result.registration_metadata["service"] == "memory"
        assert result.registration_metadata["registered_via"] == (
            "in_memory_storage"
        )
        assert result.registration_metadata["knowledge_service_id"] == (
            knowledge_service_config.knowledge_service_id
        )
        assert isinstance(result.created_at, datetime)

    async def test_register_file_idempotent(
        self,
        memory_service: MemoryKnowledgeService,
        knowledge_service_config: KnowledgeServiceConfig,
        test_document: Document,
    ) -> None:
        """Test that registering the same document returns same result."""
        # Register twice
        result1 = await memory_service.register_file(
            knowledge_service_config, test_document
        )
        result2 = await memory_service.register_file(
            knowledge_service_config, test_document
        )

        # Should get the exact same result
        assert result1 == result2
        assert result1.knowledge_service_file_id == (
            result2.knowledge_service_file_id
        )

    async def test_register_file_stores_in_memory(
        self,
        memory_service: MemoryKnowledgeService,
        knowledge_service_config: KnowledgeServiceConfig,
        test_document: Document,
    ) -> None:
        """Test that register_file stores the result in memory."""
        result = await memory_service.register_file(
            knowledge_service_config, test_document
        )
        file_id = result.knowledge_service_file_id

        # Should be able to retrieve the registration
        retrieved = memory_service.get_registered_file(file_id)
        assert retrieved == result

    def test_get_registered_file_nonexistent(
        self, memory_service: MemoryKnowledgeService
    ) -> None:
        """Test getting a non-existent registered file returns None."""
        result = memory_service.get_registered_file("nonexistent-file-id")
        assert result is None

    def test_get_all_registered_files_empty_initially(
        self, memory_service: MemoryKnowledgeService
    ) -> None:
        """Test that get_all_registered_files returns empty dict initially."""
        result = memory_service.get_all_registered_files()
        assert result == {}

    async def test_get_all_registered_files_after_registration(
        self,
        memory_service: MemoryKnowledgeService,
        knowledge_service_config: KnowledgeServiceConfig,
        test_document: Document,
    ) -> None:
        """Test get_all_registered_files after registering files."""
        # Create a second test document
        content_text = "Second test document content."
        content_bytes = content_text.encode("utf-8")
        content_stream = ContentStream(io.BytesIO(content_bytes))

        doc2 = Document(
            document_id="test-doc-2",
            original_filename="test_document_2.txt",
            content_type="text/plain",
            size_bytes=len(content_bytes),
            content_multihash="test-hash-2",
            status=DocumentStatus.CAPTURED,
            content=content_stream,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        result1 = await memory_service.register_file(
            knowledge_service_config, test_document
        )
        result2 = await memory_service.register_file(
            knowledge_service_config, doc2
        )

        all_files = memory_service.get_all_registered_files()

        # Should have both registrations
        assert len(all_files) == 2
        assert result1.knowledge_service_file_id in all_files
        assert result2.knowledge_service_file_id in all_files

        # Verify the registrations are correct
        assert all_files[result1.knowledge_service_file_id] == result1
        assert all_files[result2.knowledge_service_file_id] == result2

    def test_add_canned_query_result(
        self,
        memory_service: MemoryKnowledgeService,
        sample_query_result: QueryResult,
    ) -> None:
        """Test adding canned query results."""
        memory_service.add_canned_query_result(sample_query_result)

        # Should have one canned result available
        assert len(memory_service._canned_query_results) == 1

    def test_clear_canned_query_results(
        self,
        memory_service: MemoryKnowledgeService,
        sample_query_result: QueryResult,
    ) -> None:
        """Test clearing canned query results."""
        memory_service.add_canned_query_result(sample_query_result)
        memory_service.add_canned_query_result(sample_query_result)

        assert len(memory_service._canned_query_results) == 2

        memory_service.clear_canned_query_results()
        assert len(memory_service._canned_query_results) == 0

    async def test_execute_query_no_canned_results_raises_error(
        self,
        memory_service: MemoryKnowledgeService,
        knowledge_service_config: KnowledgeServiceConfig,
    ) -> None:
        """Test that execute_query raises error when no canned results."""
        with pytest.raises(
            ValueError,
            match="No canned query results available",
        ):
            await memory_service.execute_query(
                knowledge_service_config, "What is this?"
            )

    async def test_execute_query_returns_canned_result(
        self,
        memory_service: MemoryKnowledgeService,
        sample_query_result: QueryResult,
        knowledge_service_config: KnowledgeServiceConfig,
    ) -> None:
        """Test that execute_query returns and pops canned result."""
        query_text = "Custom query text"
        document_ids = ["doc-1", "doc-2"]

        memory_service.add_canned_query_result(sample_query_result)

        result = await memory_service.execute_query(
            knowledge_service_config, query_text, document_ids
        )

        # Should return updated result with actual query parameters
        assert result.query_id == sample_query_result.query_id
        assert result.query_text == query_text  # Updated to actual query
        assert (
            result.execution_time_ms == sample_query_result.execution_time_ms
        )
        assert result.result_data["queried_documents"] == document_ids
        assert result.result_data["service"] == "memory"
        assert result.result_data["knowledge_service_id"] == (
            knowledge_service_config.knowledge_service_id
        )
        # Should preserve original result_data
        assert result.result_data["response"] == "The main topic is testing"
        assert result.result_data["confidence"] == 0.95

        # Canned result should be consumed (popped)
        assert len(memory_service._canned_query_results) == 0

    async def test_execute_query_fifo_order(
        self,
        memory_service: MemoryKnowledgeService,
        knowledge_service_config: KnowledgeServiceConfig,
    ) -> None:
        """Test that execute_query returns canned results in FIFO order."""
        result1 = QueryResult(
            query_id="query-1",
            query_text="First query",
            result_data={"response": "First response"},
        )
        result2 = QueryResult(
            query_id="query-2",
            query_text="Second query",
            result_data={"response": "Second response"},
        )

        memory_service.add_canned_query_result(result1)
        memory_service.add_canned_query_result(result2)

        # First execute_query should return first added result
        first_returned = await memory_service.execute_query(
            knowledge_service_config, "test query 1"
        )
        assert first_returned.query_id == "query-1"
        assert first_returned.result_data["response"] == "First response"

        # Second execute_query should return second added result
        second_returned = await memory_service.execute_query(
            knowledge_service_config, "test query 2"
        )
        assert second_returned.query_id == "query-2"
        assert second_returned.result_data["response"] == "Second response"

        # No more results should be available
        assert len(memory_service._canned_query_results) == 0

    async def test_execute_query_with_none_document_ids(
        self,
        memory_service: MemoryKnowledgeService,
        knowledge_service_config: KnowledgeServiceConfig,
        sample_query_result: QueryResult,
    ) -> None:
        """Test execute_query with None document_ids parameter."""
        memory_service.add_canned_query_result(sample_query_result)

        result = await memory_service.execute_query(
            knowledge_service_config, "test query", None
        )

        assert result.result_data["queried_documents"] == []

    async def test_execute_query_updates_created_at(
        self,
        memory_service: MemoryKnowledgeService,
        knowledge_service_config: KnowledgeServiceConfig,
        sample_query_result: QueryResult,
    ) -> None:
        """Test that execute_query updates created_at timestamp."""
        original_created_at = sample_query_result.created_at
        memory_service.add_canned_query_result(sample_query_result)

        result = await memory_service.execute_query(
            knowledge_service_config, "test query"
        )

        # created_at should be updated to current time
        assert result.created_at is not None
        assert original_created_at is not None
        assert result.created_at > original_created_at
        assert (
            datetime.now(timezone.utc) - result.created_at
        ).total_seconds() < 5  # Should be very recent

    def test_initialization_with_config(
        self,
        knowledge_service_config: KnowledgeServiceConfig,
    ) -> None:
        """Test proper initialization with config."""
        service = MemoryKnowledgeService(knowledge_service_config)

        assert service.config == knowledge_service_config
        assert service._registered_files == {}
        assert len(service._canned_query_results) == 0

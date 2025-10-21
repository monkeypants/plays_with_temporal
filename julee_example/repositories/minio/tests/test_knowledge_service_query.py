"""
Tests for MinioKnowledgeServiceQueryRepository implementation.

This module provides comprehensive tests for the Minio-based knowledge service
query repository implementation, using the fake client to avoid external
dependencies during testing.
"""

import pytest

from datetime import datetime, timezone

from julee_example.domain.models.assembly_specification import (
    KnowledgeServiceQuery,
)
from julee_example.repositories.minio.knowledge_service_query import (
    MinioKnowledgeServiceQueryRepository,
)
from .fake_client import FakeMinioClient


@pytest.fixture
def fake_client() -> FakeMinioClient:
    """Create a fresh fake Minio client for each test."""
    return FakeMinioClient()


@pytest.fixture
def query_repo(
    fake_client: FakeMinioClient,
) -> MinioKnowledgeServiceQueryRepository:
    """Create knowledge service query repository with fake client."""
    return MinioKnowledgeServiceQueryRepository(fake_client)


@pytest.fixture
def sample_query() -> KnowledgeServiceQuery:
    """Create a sample knowledge service query for testing."""
    return KnowledgeServiceQuery(
        query_id="test-query-123",
        name="Test Query",
        knowledge_service_id="anthropic-claude",
        prompt="Extract key information from the document",
        assistant_prompt="Format the response as JSON",
        query_metadata={"temperature": 0.2, "max_tokens": 1000},
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def sample_queries() -> list[KnowledgeServiceQuery]:
    """Create multiple sample queries for testing list operations."""
    now = datetime.now(timezone.utc)
    return [
        KnowledgeServiceQuery(
            query_id="query-001",
            name="Meeting Summary Query",
            knowledge_service_id="anthropic-claude",
            prompt="Extract meeting summary",
            assistant_prompt="Format as bullet points",
            query_metadata={},
            created_at=now,
            updated_at=now,
        ),
        KnowledgeServiceQuery(
            query_id="query-002",
            name="Document Analysis Query",
            knowledge_service_id="openai-gpt4",
            prompt="Analyze document content",
            assistant_prompt=None,
            query_metadata={"temperature": 0.1},
            created_at=now,
            updated_at=now,
        ),
        KnowledgeServiceQuery(
            query_id="query-003",
            name="Risk Assessment Query",
            knowledge_service_id="memory-service",
            prompt="Identify risks in the document",
            assistant_prompt="Categorize by severity",
            query_metadata={"max_tokens": 500},
            created_at=now,
            updated_at=now,
        ),
    ]


class TestMinioKnowledgeServiceQueryRepositoryBasicOperations:
    """Test basic CRUD operations on knowledge service queries."""

    @pytest.mark.asyncio
    async def test_save_and_get_query(
        self,
        query_repo: MinioKnowledgeServiceQueryRepository,
        sample_query: KnowledgeServiceQuery,
    ) -> None:
        """Test saving and retrieving a knowledge service query."""
        # Save query
        await query_repo.save(sample_query)

        # Retrieve query
        retrieved = await query_repo.get(sample_query.query_id)

        assert retrieved is not None
        assert retrieved.query_id == sample_query.query_id
        assert retrieved.name == sample_query.name
        assert (
            retrieved.knowledge_service_id
            == sample_query.knowledge_service_id
        )
        assert retrieved.prompt == sample_query.prompt
        assert retrieved.assistant_prompt == sample_query.assistant_prompt
        assert retrieved.query_metadata == sample_query.query_metadata

    @pytest.mark.asyncio
    async def test_get_nonexistent_query(
        self, query_repo: MinioKnowledgeServiceQueryRepository
    ) -> None:
        """Test retrieving a non-existent query returns None."""
        result = await query_repo.get("nonexistent-query")
        assert result is None

    @pytest.mark.asyncio
    async def test_generate_id(
        self, query_repo: MinioKnowledgeServiceQueryRepository
    ) -> None:
        """Test generating unique query IDs."""
        id1 = await query_repo.generate_id()
        id2 = await query_repo.generate_id()

        assert isinstance(id1, str)
        assert isinstance(id2, str)
        assert id1 != id2
        assert len(id1) > 0
        assert len(id2) > 0
        assert id1.startswith("query-")
        assert id2.startswith("query-")

    @pytest.mark.asyncio
    async def test_save_updates_timestamp(
        self,
        query_repo: MinioKnowledgeServiceQueryRepository,
        sample_query: KnowledgeServiceQuery,
    ) -> None:
        """Test that save operations update the updated_at timestamp."""
        original_updated_at = sample_query.updated_at

        # Save query
        await query_repo.save(sample_query)

        # Retrieve and check timestamp was updated
        retrieved = await query_repo.get(sample_query.query_id)
        assert retrieved is not None
        assert retrieved.updated_at is not None
        assert original_updated_at is not None
        assert retrieved.updated_at > original_updated_at


class TestMinioKnowledgeServiceQueryRepositoryListAll:
    """Test list_all functionality."""

    @pytest.mark.asyncio
    async def test_list_all_empty(
        self, query_repo: MinioKnowledgeServiceQueryRepository
    ) -> None:
        """Test list_all returns empty list when no queries exist."""
        queries = await query_repo.list_all()
        assert queries == []

    @pytest.mark.asyncio
    async def test_list_all_multiple_queries(
        self,
        query_repo: MinioKnowledgeServiceQueryRepository,
        sample_queries: list[KnowledgeServiceQuery],
    ) -> None:
        """Test list_all with multiple queries."""
        # Save all queries
        for query in sample_queries:
            await query_repo.save(query)

        # List all queries
        queries = await query_repo.list_all()

        assert len(queries) == len(sample_queries)

        # Check that all queries are returned
        returned_ids = {query.query_id for query in queries}
        expected_ids = {query.query_id for query in sample_queries}
        assert returned_ids == expected_ids

    @pytest.mark.asyncio
    async def test_list_all_after_updates(
        self,
        query_repo: MinioKnowledgeServiceQueryRepository,
        sample_query: KnowledgeServiceQuery,
    ) -> None:
        """Test list_all after updating a query."""
        # Save original query
        await query_repo.save(sample_query)

        # Update the query
        sample_query.name = "Updated Query Name"
        sample_query.prompt = "Updated prompt"
        await query_repo.save(sample_query)

        # List all queries
        queries = await query_repo.list_all()

        assert len(queries) == 1
        assert queries[0].query_id == sample_query.query_id
        assert queries[0].name == "Updated Query Name"
        assert queries[0].prompt == "Updated prompt"


class TestMinioKnowledgeServiceQueryRepositoryGetMany:
    """Test get_many functionality."""

    @pytest.mark.asyncio
    async def test_get_many_empty_list(
        self, query_repo: MinioKnowledgeServiceQueryRepository
    ) -> None:
        """Test get_many with empty list of IDs."""
        result = await query_repo.get_many([])
        assert result == {}

    @pytest.mark.asyncio
    async def test_get_many_single_query(
        self,
        query_repo: MinioKnowledgeServiceQueryRepository,
        sample_query: KnowledgeServiceQuery,
    ) -> None:
        """Test get_many with a single query ID."""
        # Save query
        await query_repo.save(sample_query)

        # Get many with single ID
        result = await query_repo.get_many([sample_query.query_id])

        assert len(result) == 1
        assert sample_query.query_id in result
        retrieved_query = result[sample_query.query_id]
        assert retrieved_query is not None
        assert retrieved_query.query_id == sample_query.query_id

    @pytest.mark.asyncio
    async def test_get_many_multiple_queries(
        self,
        query_repo: MinioKnowledgeServiceQueryRepository,
        sample_queries: list[KnowledgeServiceQuery],
    ) -> None:
        """Test get_many with multiple query IDs."""
        # Save all queries
        for query in sample_queries:
            await query_repo.save(query)

        # Get many with all IDs
        query_ids = [query.query_id for query in sample_queries]
        result = await query_repo.get_many(query_ids)

        assert len(result) == len(sample_queries)
        for query_id in query_ids:
            assert query_id in result
            assert result[query_id] is not None

    @pytest.mark.asyncio
    async def test_get_many_with_nonexistent_ids(
        self,
        query_repo: MinioKnowledgeServiceQueryRepository,
        sample_query: KnowledgeServiceQuery,
    ) -> None:
        """Test get_many with mix of existing and non-existing IDs."""
        # Save one query
        await query_repo.save(sample_query)

        # Try to get existing and non-existing queries
        query_ids = [sample_query.query_id, "nonexistent-1", "nonexistent-2"]
        result = await query_repo.get_many(query_ids)

        assert len(result) == 3
        assert result[sample_query.query_id] is not None
        assert result["nonexistent-1"] is None
        assert result["nonexistent-2"] is None


class TestMinioKnowledgeServiceQueryRepositoryEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.mark.asyncio
    async def test_query_with_none_assistant_prompt(
        self, query_repo: MinioKnowledgeServiceQueryRepository
    ) -> None:
        """Test handling query with None assistant_prompt."""
        query = KnowledgeServiceQuery(
            query_id="test-query-no-assistant",
            name="Query without assistant prompt",
            knowledge_service_id="test-service",
            prompt="Main prompt only",
            assistant_prompt=None,
            query_metadata={},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        await query_repo.save(query)
        retrieved = await query_repo.get(query.query_id)

        assert retrieved is not None
        assert retrieved.assistant_prompt is None

    @pytest.mark.asyncio
    async def test_query_with_empty_metadata(
        self, query_repo: MinioKnowledgeServiceQueryRepository
    ) -> None:
        """Test handling query with empty metadata."""
        query = KnowledgeServiceQuery(
            query_id="test-query-empty-metadata",
            name="Query with empty metadata",
            knowledge_service_id="test-service",
            prompt="Test prompt",
            assistant_prompt="Test assistant prompt",
            query_metadata={},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        await query_repo.save(query)
        retrieved = await query_repo.get(query.query_id)

        assert retrieved is not None
        assert retrieved.query_metadata == {}

    @pytest.mark.asyncio
    async def test_query_with_complex_metadata(
        self, query_repo: MinioKnowledgeServiceQueryRepository
    ) -> None:
        """Test handling query with complex metadata."""
        complex_metadata = {
            "temperature": 0.7,
            "max_tokens": 2000,
            "stop_sequences": ["END", "STOP"],
            "nested": {"key": "value", "number": 42, "list": [1, 2, 3]},
        }

        query = KnowledgeServiceQuery(
            query_id="test-query-complex-metadata",
            name="Query with complex metadata",
            knowledge_service_id="test-service",
            prompt="Test prompt",
            assistant_prompt="Test assistant prompt",
            query_metadata=complex_metadata,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        await query_repo.save(query)
        retrieved = await query_repo.get(query.query_id)

        assert retrieved is not None
        assert retrieved.query_metadata == complex_metadata


class TestMinioKnowledgeServiceQueryRepositoryFullWorkflow:
    """Test complete workflow scenarios."""

    @pytest.mark.asyncio
    async def test_create_update_list_workflow(
        self, query_repo: MinioKnowledgeServiceQueryRepository
    ) -> None:
        """Test complete workflow: create, update, and list queries."""
        # Generate and create initial query
        query_id = await query_repo.generate_id()

        query = KnowledgeServiceQuery(
            query_id=query_id,
            name="Initial Query",
            knowledge_service_id="initial-service",
            prompt="Initial prompt",
            assistant_prompt="Initial assistant prompt",
            query_metadata={"version": 1},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        # Save initial query
        await query_repo.save(query)

        # Verify it appears in list
        queries = await query_repo.list_all()
        assert len(queries) == 1
        assert queries[0].name == "Initial Query"

        # Update the query
        query.name = "Updated Query"
        query.knowledge_service_id = "updated-service"
        query.prompt = "Updated prompt"
        query.query_metadata = {"version": 2}
        await query_repo.save(query)

        # Verify updated query in list
        queries = await query_repo.list_all()
        assert len(queries) == 1
        assert queries[0].name == "Updated Query"
        assert queries[0].knowledge_service_id == "updated-service"
        assert queries[0].query_metadata == {"version": 2}

        # Verify individual get returns same data
        retrieved = await query_repo.get(query_id)
        assert retrieved is not None
        assert retrieved.name == "Updated Query"

    @pytest.mark.asyncio
    async def test_bulk_operations_workflow(
        self,
        query_repo: MinioKnowledgeServiceQueryRepository,
        sample_queries: list[KnowledgeServiceQuery],
    ) -> None:
        """Test workflow with bulk operations."""
        # Save all queries
        for query in sample_queries:
            await query_repo.save(query)

        # Verify all appear in list_all
        all_queries = await query_repo.list_all()
        assert len(all_queries) == len(sample_queries)

        # Test get_many with subset
        subset_ids = [sample_queries[0].query_id, sample_queries[2].query_id]
        subset_result = await query_repo.get_many(subset_ids)
        assert len(subset_result) == 2
        assert all(result is not None for result in subset_result.values())

        # Update one query and verify list is updated
        sample_queries[1].name = "Modified Query"
        await query_repo.save(sample_queries[1])

        updated_queries = await query_repo.list_all()
        modified_query = next(
            q
            for q in updated_queries
            if q.query_id == sample_queries[1].query_id
        )
        assert modified_query.name == "Modified Query"

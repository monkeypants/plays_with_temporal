"""
Tests for the knowledge service queries API router.

This module provides comprehensive tests for the knowledge service queries
endpoints, focusing on testing the router behavior with proper dependency
injection and mocking patterns.
"""

import pytest
from typing import Generator
from fastapi.testclient import TestClient
from fastapi import FastAPI
from fastapi_pagination import add_pagination

from julee_example.api.routers.knowledge_service_queries import router
from julee_example.api.dependencies import (
    get_knowledge_service_query_repository,
)
from julee_example.domain.models import KnowledgeServiceQuery
from julee_example.repositories.memory import (
    MemoryKnowledgeServiceQueryRepository,
)


@pytest.fixture
def memory_repo() -> MemoryKnowledgeServiceQueryRepository:
    """Create a memory knowledge service query repository for testing."""
    return MemoryKnowledgeServiceQueryRepository()


@pytest.fixture
def app_with_router(
    memory_repo: MemoryKnowledgeServiceQueryRepository,
) -> FastAPI:
    """Create a FastAPI app with just the knowledge service queries router."""
    app = FastAPI()

    # Override the dependency with our memory repository
    app.dependency_overrides[get_knowledge_service_query_repository] = (
        lambda: memory_repo
    )

    # Add pagination support (required for the paginate function)
    add_pagination(app)

    # Include the router with the prefix
    app.include_router(
        router,
        prefix="/knowledge_service_queries",
        tags=["Knowledge Service Queries"],
    )

    return app


@pytest.fixture
def client(
    app_with_router: FastAPI,
) -> Generator[TestClient, None, None]:
    """Create a test client with the router app."""
    with TestClient(app_with_router) as test_client:
        yield test_client


@pytest.fixture
def sample_knowledge_service_query() -> KnowledgeServiceQuery:
    """Create a sample knowledge service query for testing."""
    return KnowledgeServiceQuery(
        query_id="test-query-123",
        name="Extract Meeting Summary",
        knowledge_service_id="anthropic-claude",
        prompt="Extract the main summary from this meeting transcript",
        query_metadata={"model": "claude-3", "temperature": 0.2},
        assistant_prompt="Please format as JSON",
    )


class TestGetKnowledgeServiceQueries:
    """Test the GET / endpoint for knowledge service queries."""

    def test_get_knowledge_service_queries_empty_list(
        self,
        client: TestClient,
        memory_repo: MemoryKnowledgeServiceQueryRepository,
    ) -> None:
        """Test getting queries when repository is empty."""
        response = client.get("/knowledge_service_queries/")

        assert response.status_code == 200
        data = response.json()

        # Verify pagination structure
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "size" in data
        assert "pages" in data

        # Should return empty list when repository is empty
        assert data["items"] == []
        assert data["total"] == 0

    def test_get_knowledge_service_queries_with_pagination_params(
        self,
        client: TestClient,
        memory_repo: MemoryKnowledgeServiceQueryRepository,
    ) -> None:
        """Test getting queries with pagination parameters."""
        response = client.get("/knowledge_service_queries/?page=2&size=10")

        assert response.status_code == 200
        data = response.json()

        # Verify pagination parameters are handled
        assert "items" in data
        assert "page" in data
        assert "size" in data

        # Even with pagination params, should work with empty repository
        assert data["items"] == []

    async def test_get_knowledge_service_queries_with_data(
        self,
        client: TestClient,
        memory_repo: MemoryKnowledgeServiceQueryRepository,
        sample_knowledge_service_query: KnowledgeServiceQuery,
    ) -> None:
        """Test getting queries when repository contains data."""
        # Create a second query for testing
        query2 = KnowledgeServiceQuery(
            query_id="test-query-456",
            name="Extract Attendees",
            knowledge_service_id="openai-service",
            prompt="Extract all attendees from this meeting",
            query_metadata={"model": "gpt-4", "temperature": 0.1},
            assistant_prompt="Format as JSON array",
        )

        # Save queries to the repository
        await memory_repo.save(sample_knowledge_service_query)
        await memory_repo.save(query2)

        response = client.get("/knowledge_service_queries/")

        assert response.status_code == 200
        data = response.json()

        # Verify pagination structure
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "size" in data

        # Should return both queries
        assert data["total"] == 2
        assert len(data["items"]) == 2

        # Verify the queries are returned (order may vary)
        returned_ids = {item["query_id"] for item in data["items"]}
        expected_ids = {
            sample_knowledge_service_query.query_id,
            query2.query_id,
        }
        assert returned_ids == expected_ids

        # Verify query data structure
        for item in data["items"]:
            assert "query_id" in item
            assert "name" in item
            assert "knowledge_service_id" in item
            assert "prompt" in item

    async def test_get_knowledge_service_queries_pagination(
        self,
        client: TestClient,
        memory_repo: MemoryKnowledgeServiceQueryRepository,
    ) -> None:
        """Test pagination with multiple queries."""
        # Create several queries
        queries = []
        for i in range(5):
            query = KnowledgeServiceQuery(
                query_id=f"query-{i:03d}",
                name=f"Query {i}",
                knowledge_service_id="test-service",
                prompt=f"Test prompt {i}",
            )
            queries.append(query)
            await memory_repo.save(query)

        # Test first page with size 2
        response = client.get("/knowledge_service_queries/?page=1&size=2")
        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 5
        assert data["page"] == 1
        assert data["size"] == 2
        assert len(data["items"]) == 2

        # Test second page
        response = client.get("/knowledge_service_queries/?page=2&size=2")
        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 5
        assert data["page"] == 2
        assert data["size"] == 2
        assert len(data["items"]) == 2


class TestCreateKnowledgeServiceQuery:
    """Test the POST / endpoint for creating knowledge service queries."""

    def test_create_knowledge_service_query_success(
        self,
        client: TestClient,
        memory_repo: MemoryKnowledgeServiceQueryRepository,
    ) -> None:
        """Test successful creation of a knowledge service query."""
        request_data = {
            "name": "Extract Meeting Summary",
            "knowledge_service_id": "anthropic-claude",
            "prompt": "Extract the main summary from this meeting transcript",
            "query_metadata": {"model": "claude-3", "temperature": 0.2},
            "assistant_prompt": "Please format as JSON",
        }

        response = client.post(
            "/knowledge_service_queries/", json=request_data
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "query_id" in data
        assert data["name"] == request_data["name"]
        assert (
            data["knowledge_service_id"]
            == request_data["knowledge_service_id"]
        )
        assert data["prompt"] == request_data["prompt"]
        assert data["query_metadata"] == request_data["query_metadata"]
        assert data["assistant_prompt"] == request_data["assistant_prompt"]
        assert "created_at" in data
        assert "updated_at" in data

        # Verify the query was saved to repository
        query_id = data["query_id"]
        assert query_id is not None
        assert query_id != ""

    async def test_create_knowledge_service_query_persisted(
        self,
        client: TestClient,
        memory_repo: MemoryKnowledgeServiceQueryRepository,
    ) -> None:
        """Test that created query is persisted in repository."""
        request_data = {
            "name": "Extract Action Items",
            "knowledge_service_id": "openai-gpt4",
            "prompt": "List all action items from this meeting",
        }

        response = client.post(
            "/knowledge_service_queries/", json=request_data
        )
        assert response.status_code == 200

        query_id = response.json()["query_id"]

        # Verify query was saved by retrieving it
        saved_query = await memory_repo.get(query_id)
        assert saved_query is not None
        assert saved_query.name == request_data["name"]
        assert (
            saved_query.knowledge_service_id
            == request_data["knowledge_service_id"]
        )
        assert saved_query.prompt == request_data["prompt"]

    def test_create_knowledge_service_query_minimal_fields(
        self,
        client: TestClient,
        memory_repo: MemoryKnowledgeServiceQueryRepository,
    ) -> None:
        """Test creation with only required fields."""
        request_data = {
            "name": "Minimal Query",
            "knowledge_service_id": "test-service",
            "prompt": "Test prompt",
        }

        response = client.post(
            "/knowledge_service_queries/", json=request_data
        )

        assert response.status_code == 200
        data = response.json()

        assert data["name"] == request_data["name"]
        assert (
            data["knowledge_service_id"]
            == request_data["knowledge_service_id"]
        )
        assert data["prompt"] == request_data["prompt"]
        assert data["query_metadata"] == {}
        assert data["assistant_prompt"] is None

    def test_create_knowledge_service_query_validation_errors(
        self,
        client: TestClient,
        memory_repo: MemoryKnowledgeServiceQueryRepository,
    ) -> None:
        """Test validation error handling."""
        # Test empty name
        request_data = {
            "name": "",
            "knowledge_service_id": "test-service",
            "prompt": "Test prompt",
        }

        response = client.post(
            "/knowledge_service_queries/", json=request_data
        )
        assert response.status_code == 422

        # Test empty knowledge_service_id
        request_data = {
            "name": "Test Query",
            "knowledge_service_id": "",
            "prompt": "Test prompt",
        }

        response = client.post(
            "/knowledge_service_queries/", json=request_data
        )
        assert response.status_code == 422

        # Test empty prompt
        request_data = {
            "name": "Test Query",
            "knowledge_service_id": "test-service",
            "prompt": "",
        }

        response = client.post(
            "/knowledge_service_queries/", json=request_data
        )
        assert response.status_code == 422

    def test_create_knowledge_service_query_missing_required_fields(
        self,
        client: TestClient,
        memory_repo: MemoryKnowledgeServiceQueryRepository,
    ) -> None:
        """Test handling of missing required fields."""
        # Missing name
        request_data = {
            "knowledge_service_id": "test-service",
            "prompt": "Test prompt",
        }

        response = client.post(
            "/knowledge_service_queries/", json=request_data
        )
        assert response.status_code == 422

        # Missing knowledge_service_id
        request_data = {
            "name": "Test Query",
            "prompt": "Test prompt",
        }

        response = client.post(
            "/knowledge_service_queries/", json=request_data
        )
        assert response.status_code == 422

        # Missing prompt
        request_data = {
            "name": "Test Query",
            "knowledge_service_id": "test-service",
        }

        response = client.post(
            "/knowledge_service_queries/", json=request_data
        )
        assert response.status_code == 422

    def test_post_and_get_integration(
        self,
        client: TestClient,
        memory_repo: MemoryKnowledgeServiceQueryRepository,
    ) -> None:
        """Test that POST and GET endpoints work together."""
        # Create a query via POST
        request_data = {
            "name": "Integration Test Query",
            "knowledge_service_id": "test-integration-service",
            "prompt": "This is an integration test prompt",
            "query_metadata": {"test": True, "integration": "yes"},
            "assistant_prompt": "Integration test response format",
        }

        post_response = client.post(
            "/knowledge_service_queries/", json=request_data
        )
        assert post_response.status_code == 200
        created_query = post_response.json()

        # Verify the query appears in GET response
        get_response = client.get("/knowledge_service_queries/")
        assert get_response.status_code == 200
        get_data = get_response.json()

        # Should find our created query in the list
        assert get_data["total"] == 1
        assert len(get_data["items"]) == 1

        returned_query = get_data["items"][0]
        assert returned_query["query_id"] == created_query["query_id"]
        assert returned_query["name"] == request_data["name"]
        assert (
            returned_query["knowledge_service_id"]
            == request_data["knowledge_service_id"]
        )
        assert returned_query["prompt"] == request_data["prompt"]
        assert (
            returned_query["query_metadata"] == request_data["query_metadata"]
        )
        assert (
            returned_query["assistant_prompt"]
            == request_data["assistant_prompt"]
        )

        # Create another query to test multiple items
        request_data2 = {
            "name": "Second Integration Query",
            "knowledge_service_id": "another-service",
            "prompt": "Another test prompt",
        }

        post_response2 = client.post(
            "/knowledge_service_queries/", json=request_data2
        )
        assert post_response2.status_code == 200

        # Verify both queries appear in GET response
        get_response2 = client.get("/knowledge_service_queries/")
        assert get_response2.status_code == 200
        get_data2 = get_response2.json()

        assert get_data2["total"] == 2
        assert len(get_data2["items"]) == 2

        # Verify both query IDs are present
        returned_ids = {item["query_id"] for item in get_data2["items"]}
        expected_ids = {
            created_query["query_id"],
            post_response2.json()["query_id"],
        }
        assert returned_ids == expected_ids


class TestBulkGetKnowledgeServiceQueries:
    """Test the bulk GET functionality with IDs parameter."""

    async def test_bulk_get_queries_success(
        self,
        client: TestClient,
        memory_repo: MemoryKnowledgeServiceQueryRepository,
    ) -> None:
        """Test successful bulk retrieval of queries by IDs."""
        # Create test queries
        queries = []
        for i in range(3):
            query = KnowledgeServiceQuery(
                query_id=f"bulk-query-{i}",
                name=f"Bulk Query {i}",
                knowledge_service_id="test-service",
                prompt=f"Test prompt {i}",
            )
            queries.append(query)
            await memory_repo.save(query)

        # Test bulk get with all IDs
        ids_param = ",".join([q.query_id for q in queries])
        response = client.get(f"/knowledge_service_queries/?ids={ids_param}")

        assert response.status_code == 200
        data = response.json()

        # Verify pagination structure
        assert "items" in data
        assert "total" in data
        assert data["total"] == 3
        assert len(data["items"]) == 3

        # Verify all queries are returned
        returned_ids = {item["query_id"] for item in data["items"]}
        expected_ids = {query.query_id for query in queries}
        assert returned_ids == expected_ids

    async def test_bulk_get_queries_partial_found(
        self,
        client: TestClient,
        memory_repo: MemoryKnowledgeServiceQueryRepository,
    ) -> None:
        """Test bulk retrieval when only some IDs are found."""
        # Create one query
        query = KnowledgeServiceQuery(
            query_id="existing-query",
            name="Existing Query",
            knowledge_service_id="test-service",
            prompt="Test prompt",
        )
        await memory_repo.save(query)

        # Request both existing and non-existing IDs
        ids_param = "existing-query,non-existing-1,non-existing-2"
        response = client.get(f"/knowledge_service_queries/?ids={ids_param}")

        assert response.status_code == 200
        data = response.json()

        # Should return only the found query
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["query_id"] == "existing-query"

    def test_bulk_get_queries_empty_ids(
        self,
        client: TestClient,
        memory_repo: MemoryKnowledgeServiceQueryRepository,
    ) -> None:
        """Test bulk retrieval with empty IDs parameter."""
        response = client.get("/knowledge_service_queries/?ids=")

        assert response.status_code == 400
        data = response.json()
        assert "Invalid ids parameter" in data["detail"]

    def test_bulk_get_queries_whitespace_only_ids(
        self,
        client: TestClient,
        memory_repo: MemoryKnowledgeServiceQueryRepository,
    ) -> None:
        """Test bulk retrieval with whitespace-only IDs."""
        response = client.get("/knowledge_service_queries/?ids=   ,  , ")

        assert response.status_code == 400
        data = response.json()
        assert "Invalid ids parameter" in data["detail"]

    def test_bulk_get_queries_too_many_ids(
        self,
        client: TestClient,
        memory_repo: MemoryKnowledgeServiceQueryRepository,
    ) -> None:
        """Test bulk retrieval with too many IDs."""
        # Create 101 IDs (exceeds limit of 100)
        ids = [f"query-{i}" for i in range(101)]
        ids_param = ",".join(ids)

        response = client.get(f"/knowledge_service_queries/?ids={ids_param}")

        assert response.status_code == 400
        data = response.json()
        assert "Too many IDs requested" in data["detail"]
        assert "maximum 100" in data["detail"]

    async def test_bulk_get_queries_with_spaces_and_commas(
        self,
        client: TestClient,
        memory_repo: MemoryKnowledgeServiceQueryRepository,
    ) -> None:
        """Test bulk retrieval with various comma and space combinations."""
        # Create test queries
        queries = []
        for i in range(2):
            query = KnowledgeServiceQuery(
                query_id=f"space-query-{i}",
                name=f"Space Query {i}",
                knowledge_service_id="test-service",
                prompt=f"Test prompt {i}",
            )
            queries.append(query)
            await memory_repo.save(query)

        # Test with various spacing and comma patterns
        test_cases = [
            "space-query-0,space-query-1",
            "space-query-0, space-query-1",
            " space-query-0 , space-query-1 ",
            "space-query-0,  space-query-1  ,",
        ]

        for ids_param in test_cases:
            response = client.get(
                f"/knowledge_service_queries/?ids={ids_param}"
            )
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 2
            returned_ids = {item["query_id"] for item in data["items"]}
            expected_ids = {q.query_id for q in queries}
            assert returned_ids == expected_ids

    async def test_bulk_get_queries_single_id(
        self,
        client: TestClient,
        memory_repo: MemoryKnowledgeServiceQueryRepository,
    ) -> None:
        """Test bulk retrieval with a single ID."""
        query = KnowledgeServiceQuery(
            query_id="single-query",
            name="Single Query",
            knowledge_service_id="test-service",
            prompt="Single test prompt",
        )
        await memory_repo.save(query)

        response = client.get("/knowledge_service_queries/?ids=single-query")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["query_id"] == "single-query"
        assert data["items"][0]["name"] == "Single Query"

    def test_bulk_get_queries_no_ids_falls_back_to_list_all(
        self,
        client: TestClient,
        memory_repo: MemoryKnowledgeServiceQueryRepository,
    ) -> None:
        """Test that without IDs parameter, it falls back to list all."""
        response = client.get("/knowledge_service_queries/")

        assert response.status_code == 200
        data = response.json()

        # Should have pagination structure from list all
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "size" in data
        assert "pages" in data

    async def test_bulk_get_queries_integration_with_assembly_spec_use_case(
        self,
        client: TestClient,
        memory_repo: MemoryKnowledgeServiceQueryRepository,
    ) -> None:
        """Test the typical use case: getting queries referenced by spec."""
        # Create queries that would be referenced by an assembly spec
        query_mappings = {
            "/properties/attendees": "attendee-extractor",
            "/properties/summary": "summary-extractor",
            "/properties/action_items": "action-extractor",
        }

        queries = []
        for json_pointer, query_id in query_mappings.items():
            query = KnowledgeServiceQuery(
                query_id=query_id,
                name=f"Query for {json_pointer}",
                knowledge_service_id="test-service",
                prompt=f"Extract data for {json_pointer}",
            )
            queries.append(query)
            await memory_repo.save(query)

        # Simulate getting all queries referenced by an assembly spec
        query_ids = list(query_mappings.values())
        ids_param = ",".join(query_ids)

        response = client.get(f"/knowledge_service_queries/?ids={ids_param}")

        assert response.status_code == 200
        data = response.json()

        # Should get all referenced queries
        assert data["total"] == 3
        returned_ids = {item["query_id"] for item in data["items"]}
        assert returned_ids == set(query_ids)

        # Verify query details are complete
        for item in data["items"]:
            assert "query_id" in item
            assert "name" in item
            assert "knowledge_service_id" in item
            assert "prompt" in item
            assert "query_metadata" in item


class TestGetIndividualKnowledgeServiceQuery:
    """Tests for the GET /knowledge_service_queries/{query_id} endpoint."""

    async def test_get_query_success(
        self,
        client: TestClient,
        memory_repo: MemoryKnowledgeServiceQueryRepository,
    ) -> None:
        """Test successfully retrieving an individual query."""
        # Create a test query
        query = KnowledgeServiceQuery(
            query_id="test-query-123",
            name="Test Query",
            knowledge_service_id="test-service",
            prompt="Extract test data",
            assistant_prompt="Assistant instructions",
            query_metadata={"max_tokens": 100, "temperature": 0.7},
        )
        await memory_repo.save(query)

        # Get the query
        response = client.get("/knowledge_service_queries/test-query-123")

        assert response.status_code == 200
        data = response.json()

        assert data["query_id"] == "test-query-123"
        assert data["name"] == "Test Query"
        assert data["knowledge_service_id"] == "test-service"
        assert data["prompt"] == "Extract test data"
        assert data["assistant_prompt"] == "Assistant instructions"
        assert data["query_metadata"] == {
            "max_tokens": 100,
            "temperature": 0.7,
        }
        assert "created_at" in data
        assert "updated_at" in data

    def test_get_query_not_found(self, client: TestClient) -> None:
        """Test retrieving a non-existent query returns 404."""
        response = client.get("/knowledge_service_queries/nonexistent-query")

        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()
        assert "nonexistent-query" in data["detail"]

    def test_get_query_empty_id(self, client: TestClient) -> None:
        """Test that empty query ID in URL is handled properly."""
        # FastAPI will treat this as a different route, test edge case
        response = client.get("/knowledge_service_queries/")
        # This should hit the list endpoint instead
        assert response.status_code == 200

    async def test_get_query_without_optional_fields(
        self,
        client: TestClient,
        memory_repo: MemoryKnowledgeServiceQueryRepository,
    ) -> None:
        """Test retrieving a query that doesn't have optional fields."""
        # Create a minimal query without assistant_prompt
        query = KnowledgeServiceQuery(
            query_id="minimal-query",
            name="Minimal Query",
            knowledge_service_id="test-service",
            prompt="Basic prompt",
            query_metadata={},
        )
        await memory_repo.save(query)

        response = client.get("/knowledge_service_queries/minimal-query")

        assert response.status_code == 200
        data = response.json()

        assert data["query_id"] == "minimal-query"
        assert data["name"] == "Minimal Query"
        assert data["assistant_prompt"] is None
        assert data["query_metadata"] == {}

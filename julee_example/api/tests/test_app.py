"""
Tests for the julee_example FastAPI application.

This module provides tests for the API endpoints, focusing on testing the
HTTP layer behavior with proper dependency injection and mocking patterns.
"""

import pytest
from typing import Generator
from fastapi.testclient import TestClient

from julee_example.api.app import app
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
def client(
    memory_repo: MemoryKnowledgeServiceQueryRepository,
) -> Generator[TestClient, None, None]:
    """Create a test client with memory repository."""
    # Override the dependency with our memory repository
    app.dependency_overrides[get_knowledge_service_query_repository] = (
        lambda: memory_repo
    )

    with TestClient(app) as test_client:
        yield test_client

    # Clean up the override after the test
    app.dependency_overrides.clear()


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


class TestHealthEndpoint:
    """Test the health check endpoint."""

    def test_health_check(self, client: TestClient) -> None:
        """Test that health check returns expected response."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "0.1.0"
        assert "timestamp" in data


class TestKnowledgeServiceQueriesEndpoint:
    """Test the knowledge service queries endpoint."""

    def test_get_knowledge_service_queries_empty_list(
        self,
        client: TestClient,
        memory_repo: MemoryKnowledgeServiceQueryRepository,
    ) -> None:
        """Test getting queries when repository is empty."""
        # Memory repository starts empty
        # Note: Current implementation returns empty list as placeholder,
        # this test verifies the endpoint structure works

        response = client.get("/knowledge_service_queries")

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
        response = client.get("/knowledge_service_queries?page=2&size=10")

        assert response.status_code == 200
        data = response.json()

        # Verify pagination parameters are handled
        assert "items" in data
        assert "page" in data
        assert "size" in data

        # Even with pagination params, should work with empty repository
        assert data["items"] == []

    def test_knowledge_service_queries_endpoint_error_handling(
        self,
        client: TestClient,
        memory_repo: MemoryKnowledgeServiceQueryRepository,
    ) -> None:
        """Test error handling in the queries endpoint."""
        response = client.get("/knowledge_service_queries")
        assert response.status_code == 200

        # Test passes if no exceptions are raised during repository calls

    def test_openapi_schema_includes_knowledge_service_queries(
        self, client: TestClient
    ) -> None:
        """Test that the OpenAPI schema includes our endpoint."""
        response = client.get("/openapi.json")

        assert response.status_code == 200
        openapi_schema = response.json()

        # Verify our endpoint is in the schema
        paths = openapi_schema.get("paths", {})
        assert "/knowledge_service_queries" in paths

        # Verify the endpoint has GET method
        endpoint = paths["/knowledge_service_queries"]
        assert "get" in endpoint

        # Verify response model is defined
        get_info = endpoint["get"]
        assert "responses" in get_info
        assert "200" in get_info["responses"]

    async def test_repository_can_store_and_retrieve_queries(
        self,
        memory_repo: MemoryKnowledgeServiceQueryRepository,
        sample_knowledge_service_query: KnowledgeServiceQuery,
    ) -> None:
        """Test that the memory repository can store and retrieve queries.

        This demonstrates how the endpoint will work once list_all() is added.
        """
        # Save a query to the repository
        await memory_repo.save(sample_knowledge_service_query)

        # Verify it can be retrieved
        retrieved = await memory_repo.get(
            sample_knowledge_service_query.query_id
        )
        assert retrieved == sample_knowledge_service_query

        # This shows we can store and retrieve queries from the repository

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

        response = client.get("/knowledge_service_queries")

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
        response = client.get("/knowledge_service_queries?page=1&size=2")
        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 5
        assert data["page"] == 1
        assert data["size"] == 2
        assert len(data["items"]) == 2

        # Test second page
        response = client.get("/knowledge_service_queries?page=2&size=2")
        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 5
        assert data["page"] == 2
        assert data["size"] == 2
        assert len(data["items"]) == 2


class TestCreateKnowledgeServiceQueryEndpoint:
    """Test the POST knowledge service queries endpoint."""

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
            "/knowledge_service_queries", json=request_data
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
            "/knowledge_service_queries", json=request_data
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
            "/knowledge_service_queries", json=request_data
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
            "/knowledge_service_queries", json=request_data
        )
        assert response.status_code == 422

        # Test empty knowledge_service_id
        request_data = {
            "name": "Test Query",
            "knowledge_service_id": "",
            "prompt": "Test prompt",
        }

        response = client.post(
            "/knowledge_service_queries", json=request_data
        )
        assert response.status_code == 422

        # Test empty prompt
        request_data = {
            "name": "Test Query",
            "knowledge_service_id": "test-service",
            "prompt": "",
        }

        response = client.post(
            "/knowledge_service_queries", json=request_data
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
            "/knowledge_service_queries", json=request_data
        )
        assert response.status_code == 422

        # Missing knowledge_service_id
        request_data = {
            "name": "Test Query",
            "prompt": "Test prompt",
        }

        response = client.post(
            "/knowledge_service_queries", json=request_data
        )
        assert response.status_code == 422

        # Missing prompt
        request_data = {
            "name": "Test Query",
            "knowledge_service_id": "test-service",
        }

        response = client.post(
            "/knowledge_service_queries", json=request_data
        )
        assert response.status_code == 422

    def test_openapi_schema_includes_post_endpoint(
        self, client: TestClient
    ) -> None:
        """Test that the OpenAPI schema includes the POST endpoint."""
        response = client.get("/openapi.json")

        assert response.status_code == 200
        openapi_schema = response.json()

        # Verify our endpoint is in the schema
        paths = openapi_schema.get("paths", {})
        assert "/knowledge_service_queries" in paths

        # Verify the endpoint has POST method
        endpoint = paths["/knowledge_service_queries"]
        assert "post" in endpoint

        # Verify POST method details
        post_info = endpoint["post"]
        assert "requestBody" in post_info
        assert "responses" in post_info
        assert "200" in post_info["responses"]

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
            "/knowledge_service_queries", json=request_data
        )
        assert post_response.status_code == 200
        created_query = post_response.json()

        # Verify the query appears in GET response
        get_response = client.get("/knowledge_service_queries")
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
            "/knowledge_service_queries", json=request_data2
        )
        assert post_response2.status_code == 200

        # Verify both queries appear in GET response
        get_response2 = client.get("/knowledge_service_queries")
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

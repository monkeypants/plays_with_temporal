"""
Tests for the julee_example FastAPI application.

This module provides tests for the API endpoints, focusing on testing the
HTTP layer behavior with proper dependency injection and mocking patterns.
"""

import pytest
from typing import Generator
from unittest.mock import patch
from fastapi.testclient import TestClient

from julee_example.api.app import app
from julee_example.api.dependencies import (
    get_knowledge_service_query_repository,
    get_knowledge_service_config_repository,
)
from julee_example.domain.models import KnowledgeServiceQuery
from julee_example.repositories.memory import (
    MemoryKnowledgeServiceQueryRepository,
)
from julee_example.repositories.memory.knowledge_service_config import (
    MemoryKnowledgeServiceConfigRepository,
)
from julee_example.api.responses import ServiceStatus


@pytest.fixture
def memory_repo() -> MemoryKnowledgeServiceQueryRepository:
    """Create a memory knowledge service query repository for testing."""
    return MemoryKnowledgeServiceQueryRepository()


@pytest.fixture
def memory_config_repo() -> MemoryKnowledgeServiceConfigRepository:
    """Create a memory knowledge service config repository for testing."""
    return MemoryKnowledgeServiceConfigRepository()


@pytest.fixture
def client(
    memory_repo: MemoryKnowledgeServiceQueryRepository,
    memory_config_repo: MemoryKnowledgeServiceConfigRepository,
) -> Generator[TestClient, None, None]:
    """Create a test client with memory repository."""
    # Override the dependencies with our memory repositories
    app.dependency_overrides[get_knowledge_service_query_repository] = (
        lambda: memory_repo
    )
    app.dependency_overrides[get_knowledge_service_config_repository] = (
        lambda: memory_config_repo
    )

    with (
        patch(
            "julee_example.api.routers.system.check_temporal_health"
        ) as mock_temporal,
        patch(
            "julee_example.api.routers.system.check_storage_health"
        ) as mock_storage,
    ):
        # Mock health checks to return UP status
        mock_temporal.return_value = ServiceStatus.UP
        mock_storage.return_value = ServiceStatus.UP

        with TestClient(app) as test_client:
            yield test_client

    # Clean up the overrides after the test
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
        assert "timestamp" in data
        assert "services" in data
        assert data["services"]["api"] == "up"
        assert data["services"]["temporal"] == "up"
        assert data["services"]["storage"] == "up"


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
        assert "/knowledge_service_queries/" in paths

        # Verify the endpoint has GET method
        endpoint = paths["/knowledge_service_queries/"]
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

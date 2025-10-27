"""
Tests for knowledge service configurations API endpoints.

This module tests the API endpoints for knowledge service configurations,
ensuring they follow consistent patterns with proper error handling,
pagination, and response formats.
"""

import pytest
from unittest.mock import AsyncMock
from fastapi.testclient import TestClient
from typing import Generator

from julee_example.api.app import app
from julee_example.domain.models.knowledge_service_config import (
    KnowledgeServiceConfig,
    ServiceApi,
)
from julee_example.api.dependencies import (
    get_knowledge_service_config_repository,
)
from datetime import datetime, timezone


@pytest.fixture
def mock_repository() -> AsyncMock:
    """Create mock knowledge service config repository."""
    return AsyncMock()


@pytest.fixture
def client(mock_repository: AsyncMock) -> Generator[TestClient, None, None]:
    """Create test client with mocked dependencies."""
    app.dependency_overrides[get_knowledge_service_config_repository] = (
        lambda: mock_repository
    )

    with TestClient(app) as test_client:
        yield test_client

    # Clean up
    app.dependency_overrides.clear()


@pytest.fixture
def sample_configs() -> list[KnowledgeServiceConfig]:
    """Sample knowledge service configurations for testing."""
    return [
        KnowledgeServiceConfig(
            knowledge_service_id="anthropic-claude",
            name="Anthropic Claude",
            description="Claude 3 for general text analysis and extraction",
            service_api=ServiceApi.ANTHROPIC,
            created_at=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            updated_at=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        ),
        KnowledgeServiceConfig(
            knowledge_service_id="openai-gpt4",
            name="OpenAI GPT-4",
            description="GPT-4 for comprehensive text understanding",
            service_api=ServiceApi.ANTHROPIC,  # Only enum value available
            created_at=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            updated_at=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        ),
        KnowledgeServiceConfig(
            knowledge_service_id="memory-service",
            name="Memory Service",
            description="In-memory service for testing and development",
            service_api=ServiceApi.ANTHROPIC,  # Only enum value available
            created_at=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            updated_at=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        ),
    ]


class TestGetKnowledgeServiceConfigs:
    """Test GET /knowledge_service_configs/ endpoint."""

    def test_get_configs_success(
        self,
        client: TestClient,
        mock_repository: AsyncMock,
        sample_configs: list[KnowledgeServiceConfig],
    ) -> None:
        """Test successful retrieval of knowledge service configurations."""
        # Setup mock
        mock_repository.list_all.return_value = sample_configs

        # Make request
        response = client.get("/knowledge_service_configs/")

        # Assert response
        assert response.status_code == 200
        data = response.json()

        # Check pagination structure
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "size" in data

        # Check data content
        assert len(data["items"]) == 3
        assert data["total"] == 3

        # Verify first config details
        first_config = data["items"][0]
        assert first_config["knowledge_service_id"] == "anthropic-claude"
        assert first_config["name"] == "Anthropic Claude"
        assert (
            first_config["description"]
            == "Claude 3 for general text analysis and extraction"
        )
        assert first_config["service_api"] == "anthropic"

        # Verify repository was called
        mock_repository.list_all.assert_called_once()

    def test_get_configs_empty_list(
        self, client: TestClient, mock_repository: AsyncMock
    ) -> None:
        """Test successful retrieval when no configurations exist."""
        # Setup mock
        mock_repository.list_all.return_value = []

        # Make request
        response = client.get("/knowledge_service_configs/")

        # Assert response
        assert response.status_code == 200
        data = response.json()

        assert data["items"] == []
        assert data["total"] == 0

        # Verify repository was called
        mock_repository.list_all.assert_called_once()

    def test_get_configs_single_config(
        self,
        client: TestClient,
        mock_repository: AsyncMock,
        sample_configs: list[KnowledgeServiceConfig],
    ) -> None:
        """Test successful retrieval with a single configuration."""
        # Setup mock with single config
        single_config = [sample_configs[0]]
        mock_repository.list_all.return_value = single_config

        # Make request
        response = client.get("/knowledge_service_configs/")

        # Assert response
        assert response.status_code == 200
        data = response.json()

        assert len(data["items"]) == 1
        assert data["total"] == 1
        assert data["items"][0]["knowledge_service_id"] == "anthropic-claude"

        # Verify repository was called
        mock_repository.list_all.assert_called_once()

    def test_get_configs_repository_error(
        self, client: TestClient, mock_repository: AsyncMock
    ) -> None:
        """Test handling of repository errors."""
        # Setup mock to raise exception
        mock_repository.list_all.side_effect = Exception(
            "Database connection failed"
        )

        # Make request
        response = client.get("/knowledge_service_configs/")

        # Assert error response
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "internal error" in data["detail"].lower()

        # Verify repository was called
        mock_repository.list_all.assert_called_once()

    def test_get_configs_response_structure(
        self,
        client: TestClient,
        mock_repository: AsyncMock,
        sample_configs: list[KnowledgeServiceConfig],
    ) -> None:
        """Test that response follows expected pagination structure."""
        # Setup mock
        mock_repository.list_all.return_value = sample_configs

        # Make request
        response = client.get("/knowledge_service_configs/")

        # Assert response structure
        assert response.status_code == 200
        data = response.json()

        # Check required pagination fields
        required_fields = ["items", "total", "page", "size", "pages"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

        # Check item structure
        if data["items"]:
            item = data["items"][0]
            required_item_fields = [
                "knowledge_service_id",
                "name",
                "description",
                "service_api",
                "created_at",
                "updated_at",
            ]
            for field in required_item_fields:
                assert field in item, f"Missing required item field: {field}"

    def test_get_configs_content_type(
        self,
        client: TestClient,
        mock_repository: AsyncMock,
        sample_configs: list[KnowledgeServiceConfig],
    ) -> None:
        """Test that response has correct content type."""
        # Setup mock
        mock_repository.list_all.return_value = sample_configs

        # Make request
        response = client.get("/knowledge_service_configs/")

        # Assert content type
        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]

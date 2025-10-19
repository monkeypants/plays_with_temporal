"""
Tests for the system API router.

This module provides tests for system-level endpoints including health checks
and other operational endpoints.
"""

import pytest
from typing import Generator
from fastapi.testclient import TestClient
from fastapi import FastAPI

from julee_example.api.routers.system import router


@pytest.fixture
def app_with_router() -> FastAPI:
    """Create a FastAPI app with just the system router."""
    app = FastAPI()

    # Include the router (system routes are typically at root level)
    app.include_router(router, tags=["System"])

    return app


@pytest.fixture
def client(
    app_with_router: FastAPI,
) -> Generator[TestClient, None, None]:
    """Create a test client with the system router app."""
    with TestClient(app_with_router) as test_client:
        yield test_client


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

    def test_health_check_response_structure(
        self, client: TestClient
    ) -> None:
        """Test that health check response has correct structure."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()

        # Verify all required fields are present
        required_fields = ["status", "version", "timestamp"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

        # Verify field types
        assert isinstance(data["status"], str)
        assert isinstance(data["version"], str)
        assert isinstance(data["timestamp"], str)

        # Verify status value
        assert data["status"] == "healthy"

    def test_health_check_timestamp_format(self, client: TestClient) -> None:
        """Test that health check timestamp is in ISO format."""
        from datetime import datetime

        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        timestamp_str = data["timestamp"]

        # Should be able to parse as ISO format datetime
        try:
            parsed_timestamp = datetime.fromisoformat(
                timestamp_str.replace("Z", "+00:00")
            )
            assert parsed_timestamp is not None
        except ValueError:
            pytest.fail(
                f"Timestamp '{timestamp_str}' is not in valid ISO format"
            )

    def test_health_check_multiple_calls_consistent(
        self, client: TestClient
    ) -> None:
        """Test multiple health check calls return consistent structure."""
        # Make multiple calls
        responses = [client.get("/health") for _ in range(3)]

        # All should be successful
        for response in responses:
            assert response.status_code == 200

        # All should have the same structure
        data_list = [response.json() for response in responses]

        for data in data_list:
            assert data["status"] == "healthy"
            assert data["version"] == "0.1.0"
            assert "timestamp" in data

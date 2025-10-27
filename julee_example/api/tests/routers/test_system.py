"""
Tests for the system API router.

This module provides tests for system-level endpoints including health checks
and other operational endpoints.
"""

import pytest
import time
from datetime import datetime
from typing import Generator
from unittest.mock import patch
from fastapi.testclient import TestClient
from fastapi import FastAPI

from julee_example.api.routers.system import router
from julee_example.api.responses import ServiceStatus


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

        with TestClient(app_with_router) as test_client:
            yield test_client


class TestHealthEndpoint:
    """Test the health check endpoint."""

    def test_health_check(self, client: TestClient) -> None:
        """Test that health check returns expected response."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["healthy", "degraded", "unhealthy"]
        assert "timestamp" in data
        assert "services" in data

    def test_health_check_response_structure(
        self, client: TestClient
    ) -> None:
        """Test that health check response has correct structure."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()

        # Verify all required fields are present
        required_fields = ["status", "timestamp", "services"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

        # Verify field types
        assert isinstance(data["status"], str)
        assert isinstance(data["timestamp"], str)
        assert isinstance(data["services"], dict)

        # Verify status value
        assert data["status"] in ["healthy", "degraded", "unhealthy"]

        # Verify services structure
        services = data["services"]
        required_services = ["api", "temporal", "storage"]
        for service in required_services:
            assert service in services, f"Missing service: {service}"
            assert services[service] in [
                "up",
                "down",
            ], f"Invalid status for {service}: {services[service]}"

    def test_health_check_timestamp_format(self, client: TestClient) -> None:
        """Test that health check timestamp is in ISO format."""

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

    def test_health_check_services_status(self, client: TestClient) -> None:
        """Test that health check includes all service statuses."""
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        services = data["services"]

        # API should always be up since we're responding
        assert services["api"] == "up"

        # Temporal and storage may be up or down depending on environment
        assert services["temporal"] in ["up", "down"]
        assert services["storage"] in ["up", "down"]

    def test_health_check_overall_status_logic(
        self, client: TestClient
    ) -> None:
        """Test that overall status reflects service health correctly."""
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        overall_status = data["status"]
        services = data["services"]

        # Count up services
        up_services = sum(1 for status in services.values() if status == "up")
        total_services = len(services)

        # Validate logic
        if up_services == total_services:
            assert overall_status == "healthy"
        elif up_services > 0:
            assert overall_status == "degraded"
        else:
            assert overall_status == "unhealthy"

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
            assert data["status"] in ["healthy", "degraded", "unhealthy"]
            assert "timestamp" in data
            assert "services" in data

            # Services structure should be consistent
            services = data["services"]
            required_services = ["api", "temporal", "storage"]
            for service in required_services:
                assert service in services
                assert services[service] in ["up", "down"]

    def test_health_check_response_time(self, client: TestClient) -> None:
        """Test that health check responds quickly."""

        start_time = time.time()
        response = client.get("/health")
        end_time = time.time()

        assert response.status_code == 200
        # Health check should complete within 10 seconds even with external
        # service checks
        assert end_time - start_time < 10.0

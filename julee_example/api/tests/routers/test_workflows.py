"""
Tests for workflows API router.

This module provides unit tests for the workflows API endpoints,
focusing on workflow triggering, status monitoring, and error handling.
"""

import pytest
from typing import Generator
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI
from fastapi_pagination import add_pagination

from julee_example.api.routers.workflows import router
from julee_example.api.dependencies import get_temporal_client


@pytest.fixture
def mock_temporal_client() -> MagicMock:
    """Create mock Temporal client."""
    mock_client = MagicMock()
    mock_client.start_workflow = AsyncMock()
    mock_client.get_workflow_handle = MagicMock()  # Synchronous method
    return mock_client


@pytest.fixture
def app_with_router(mock_temporal_client: MagicMock) -> FastAPI:
    """Create a FastAPI app with just the workflows router."""
    app = FastAPI()

    # Override the dependency with our mock temporal client
    app.dependency_overrides[get_temporal_client] = (
        lambda: mock_temporal_client
    )

    # Add pagination support (required for potential future endpoints)
    add_pagination(app)

    app.include_router(router, prefix="/workflows", tags=["Workflows"])

    return app


@pytest.fixture
def client(
    app_with_router: FastAPI,
) -> Generator[TestClient, None, None]:
    """Create a test client with the workflows router app."""
    with TestClient(app_with_router) as test_client:
        yield test_client


class TestStartExtractAssembleWorkflow:
    """Test cases for the start extract-assemble workflow endpoint."""

    def test_start_workflow_success_with_auto_generated_id(
        self,
        client: TestClient,
        mock_temporal_client: MagicMock,
    ) -> None:
        """Test successful workflow start with auto-generated workflow ID."""
        # Setup mock
        mock_handle = MagicMock()
        mock_handle.run_id = "test-run-id-123"
        mock_temporal_client.start_workflow.return_value = mock_handle

        # Make request
        request_data = {
            "document_id": "doc-123",
            "assembly_specification_id": "spec-456",
        }
        response = client.post(
            "/workflows/extract-assemble", json=request_data
        )

        # Assertions
        assert response.status_code == 200
        data = response.json()

        assert data["run_id"] == "test-run-id-123"
        assert data["status"] == "RUNNING"
        assert data["message"] == "Workflow started successfully"
        assert "extract-assemble-doc-123-spec-456" in data["workflow_id"]

        # Verify temporal client was called correctly
        mock_temporal_client.start_workflow.assert_called_once()
        call_args = mock_temporal_client.start_workflow.call_args

        # Check positional arguments
        assert call_args[1]["args"] == ["doc-123", "spec-456"]
        assert call_args[1]["task_queue"] == "julee-extract-assemble-queue"
        assert "extract-assemble-doc-123-spec-456" in call_args[1]["id"]

    def test_start_workflow_success_with_custom_id(
        self,
        client: TestClient,
        mock_temporal_client: MagicMock,
    ) -> None:
        """Test successful workflow start with custom workflow ID."""
        # Setup mock
        mock_handle = MagicMock()
        mock_handle.run_id = "custom-run-id"
        mock_temporal_client.start_workflow.return_value = mock_handle

        # Make request
        request_data = {
            "document_id": "doc-789",
            "assembly_specification_id": "spec-101",
            "workflow_id": "my-custom-workflow-id",
        }
        response = client.post(
            "/workflows/extract-assemble", json=request_data
        )

        # Assertions
        assert response.status_code == 200
        data = response.json()

        assert data["workflow_id"] == "my-custom-workflow-id"
        assert data["run_id"] == "custom-run-id"
        assert data["status"] == "RUNNING"

        # Verify temporal client was called with custom ID
        mock_temporal_client.start_workflow.assert_called_once()
        call_args = mock_temporal_client.start_workflow.call_args
        assert call_args[1]["id"] == "my-custom-workflow-id"

    def test_start_workflow_missing_document_id(
        self, client: TestClient
    ) -> None:
        """Test workflow start with missing document_id."""
        request_data = {
            "assembly_specification_id": "spec-456",
        }
        response = client.post(
            "/workflows/extract-assemble", json=request_data
        )

        assert response.status_code == 422  # Validation error
        data = response.json()
        assert "document_id" in str(data["detail"])

    def test_start_workflow_missing_assembly_specification_id(
        self, client: TestClient
    ) -> None:
        """Test workflow start with missing assembly_specification_id."""
        request_data = {
            "document_id": "doc-123",
        }
        response = client.post(
            "/workflows/extract-assemble", json=request_data
        )

        assert response.status_code == 422  # Validation error
        data = response.json()
        assert "assembly_specification_id" in str(data["detail"])

    def test_start_workflow_empty_string_ids(
        self,
        client: TestClient,
        mock_temporal_client: MagicMock,
    ) -> None:
        """Test workflow start with empty string IDs."""
        # Setup mock (though it shouldn't be called due to validation)
        mock_handle = MagicMock()
        mock_handle.run_id = "should-not-be-called"
        mock_temporal_client.start_workflow.return_value = mock_handle

        request_data = {
            "document_id": "",
            "assembly_specification_id": "",
        }
        response = client.post(
            "/workflows/extract-assemble", json=request_data
        )

        assert response.status_code == 422  # Validation error

    def test_start_workflow_temporal_client_error(
        self,
        client: TestClient,
        mock_temporal_client: MagicMock,
    ) -> None:
        """Test workflow start when Temporal client raises exception."""
        # Setup mock to raise exception
        mock_temporal_client.start_workflow.side_effect = Exception(
            "Temporal connection failed"
        )

        # Make request
        request_data = {
            "document_id": "doc-123",
            "assembly_specification_id": "spec-456",
        }
        response = client.post(
            "/workflows/extract-assemble", json=request_data
        )

        # Assertions
        assert response.status_code == 500
        data = response.json()
        assert "Failed to start workflow" in data["detail"]


class TestGetWorkflowStatus:
    """Test cases for the get workflow status endpoint."""

    def test_get_workflow_status_success(
        self,
        client: TestClient,
        mock_temporal_client: MagicMock,
    ) -> None:
        """Test successful workflow status retrieval."""
        # Setup mocks
        mock_handle = MagicMock()
        mock_description = MagicMock()
        mock_description.run_id = "test-run-123"
        mock_description.status.name = "RUNNING"

        mock_handle.describe = AsyncMock(return_value=mock_description)
        mock_handle.query = AsyncMock(
            side_effect=[
                "extracting_data",  # current_step
                "assembly-789",  # assembly_id
            ]
        )

        mock_temporal_client.get_workflow_handle.return_value = mock_handle

        # Make request
        response = client.get("/workflows/test-workflow-id/status")

        # Assertions
        assert response.status_code == 200
        data = response.json()

        assert data["workflow_id"] == "test-workflow-id"
        assert data["run_id"] == "test-run-123"
        assert data["status"] == "RUNNING"
        assert data["current_step"] == "extracting_data"
        assert data["assembly_id"] == "assembly-789"

        # Verify temporal client calls
        mock_temporal_client.get_workflow_handle.assert_called_once_with(
            "test-workflow-id"
        )
        mock_handle.describe.assert_called_once()
        assert mock_handle.query.call_count == 2

    def test_get_workflow_status_completed(
        self,
        client: TestClient,
        mock_temporal_client: MagicMock,
    ) -> None:
        """Test workflow status for completed workflow."""
        # Setup mocks
        mock_handle = MagicMock()
        mock_description = MagicMock()
        mock_description.run_id = "completed-run-456"
        mock_description.status.name = "COMPLETED"

        mock_handle.describe = AsyncMock(return_value=mock_description)
        mock_handle.query = AsyncMock(
            side_effect=[
                "completed",  # current_step
                "final-assembly",  # assembly_id
            ]
        )

        mock_temporal_client.get_workflow_handle.return_value = mock_handle

        # Make request
        response = client.get("/workflows/completed-workflow/status")

        # Assertions
        assert response.status_code == 200
        data = response.json()

        assert data["workflow_id"] == "completed-workflow"
        assert data["status"] == "COMPLETED"
        assert data["current_step"] == "completed"
        assert data["assembly_id"] == "final-assembly"

    def test_get_workflow_status_query_failure(
        self,
        client: TestClient,
        mock_temporal_client: MagicMock,
    ) -> None:
        """Test workflow status when queries fail (returns basic status)."""
        # Setup mocks
        mock_handle = MagicMock()
        mock_description = MagicMock()
        mock_description.run_id = "no-query-run"
        mock_description.status.name = "RUNNING"

        mock_handle.describe = AsyncMock(return_value=mock_description)
        mock_handle.query = AsyncMock(
            side_effect=Exception("Query not supported")
        )

        mock_temporal_client.get_workflow_handle.return_value = mock_handle

        # Make request
        response = client.get("/workflows/no-query-workflow/status")

        # Assertions
        assert response.status_code == 200
        data = response.json()

        assert data["workflow_id"] == "no-query-workflow"
        assert data["status"] == "RUNNING"
        assert data["current_step"] is None  # Query failed gracefully
        assert data["assembly_id"] is None  # Query failed gracefully

    def test_get_workflow_status_not_found(
        self,
        client: TestClient,
        mock_temporal_client: MagicMock,
    ) -> None:
        """Test workflow status for non-existent workflow."""
        # Setup mock to raise a generic Exception (workflow not found)
        mock_temporal_client.get_workflow_handle.side_effect = Exception(
            "Workflow not found"
        )

        # Make request
        response = client.get("/workflows/non-existent-workflow/status")

        # Assertions
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    def test_get_workflow_status_temporal_error(
        self,
        client: TestClient,
        mock_temporal_client: MagicMock,
    ) -> None:
        """Test workflow status when Temporal client raises exception."""
        # Setup mock to raise exception
        mock_temporal_client.get_workflow_handle.side_effect = Exception(
            "Temporal service unavailable"
        )

        # Make request
        response = client.get("/workflows/error-workflow/status")

        # Assertions
        assert response.status_code == 500
        data = response.json()
        assert "Failed to retrieve workflow handle" in data["detail"]

    def test_get_workflow_status_describe_error(
        self,
        client: TestClient,
        mock_temporal_client: MagicMock,
    ) -> None:
        """Test workflow status when describe fails."""
        # Setup mocks
        mock_handle = MagicMock()
        mock_handle.describe = AsyncMock(
            side_effect=Exception("Describe failed")
        )
        mock_temporal_client.get_workflow_handle.return_value = mock_handle

        # Make request
        response = client.get("/workflows/describe-error-workflow/status")

        # Assertions
        assert response.status_code == 500
        data = response.json()
        assert "Failed to retrieve workflow description" in data["detail"]


class TestWorkflowValidation:
    """Test cases for workflow request validation."""

    def test_start_workflow_invalid_json(self, client: TestClient) -> None:
        """Test workflow start with invalid JSON."""
        response = client.post(
            "/workflows/extract-assemble",
            content="invalid json",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 422

    def test_start_workflow_extra_fields_ignored(
        self,
        client: TestClient,
        mock_temporal_client: MagicMock,
    ) -> None:
        """Test that extra fields in request are ignored."""
        # Setup mock
        mock_handle = MagicMock()
        mock_handle.run_id = "extra-fields-run"
        mock_temporal_client.start_workflow.return_value = mock_handle

        # Make request with extra fields
        request_data = {
            "document_id": "doc-123",
            "assembly_specification_id": "spec-456",
            "extra_field": "should_be_ignored",
            "another_extra": 42,
        }
        response = client.post(
            "/workflows/extract-assemble", json=request_data
        )

        # Should succeed and ignore extra fields
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "RUNNING"

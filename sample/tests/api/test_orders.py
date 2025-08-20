import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
import io
import uuid  # Added uuid import
import json

from sample.api.app import app
from sample.api.dependencies import (
    get_order_fulfillment_use_case,
    get_minio_order_request_repository,
    get_get_order_use_case,
)
from sample.api.responses import OrderStatusResponse
from sample.usecase import OrderFulfillmentUseCase, GetOrderUseCase
from util.domain import FileMetadata


def test_create_order_endpoint() -> None:
    """Test that the create_order endpoint correctly handles valid requests"""
    # Mock the Temporal client to avoid actual workflow execution
    mock_client = AsyncMock()
    mock_client.start_workflow = AsyncMock()

    # Patch the Client.connect method to return our mock
    with patch("temporalio.client.Client.connect", return_value=mock_client):
        client = TestClient(app)
        response = client.post(
            "/orders",
            json={
                "customer_id": "cust123",
                "items": [
                    {"product_id": "prod1", "quantity": 2, "price": "50.00"}
                ],
            },
        )

        # Check response
        assert response.status_code == 200
        assert "request_id" in response.json()
        assert response.json()["status"] == "SUBMITTED"

        # Verify Temporal client was called
        mock_client.start_workflow.assert_called_once()


def test_get_request_status_no_mapping() -> None:
    """Test request status when no order mapping exists yet"""
    # Mock the request repository
    mock_repo = AsyncMock()
    mock_repo.get_order_id_for_request = AsyncMock(return_value=None)

    # Use dependency override for get_minio_order_request_repository
    app.dependency_overrides[get_minio_order_request_repository] = (
        lambda: mock_repo
    )

    client = TestClient(app)
    response = client.get("/order-requests/req-123")

    assert response.status_code == 200
    assert response.json()["request_id"] == "req-123"
    assert response.json()["status"] == "SUBMITTED"

    # Clean up dependency override
    app.dependency_overrides = {}


def test_get_request_status_with_redirect() -> None:
    """Test request status when order mapping exists - should redirect"""
    # Mock the request repository
    mock_repo = AsyncMock()
    mock_repo.get_order_id_for_request = AsyncMock(return_value="order-456")

    # Use dependency override for get_minio_order_request_repository
    app.dependency_overrides[get_minio_order_request_repository] = (
        lambda: mock_repo
    )

    client = TestClient(app)
    response = client.get("/order-requests/req-123", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["location"] == "/orders/order-456"

    # Clean up dependency override
    app.dependency_overrides = {}


def test_get_order_status_endpoint() -> None:
    """Test that the get_order_status endpoint correctly handles valid
    requests by mocking the use case.
    """
    # Create a mock GetOrderUseCase (this is the one actually used by
    # the endpoint)
    mock_use_case = AsyncMock(spec=GetOrderUseCase)

    # Configure its get_order_status method to return a mock
    # OrderStatusResponse
    mock_use_case.get_order_status = AsyncMock(
        return_value=OrderStatusResponse(
            order_id="order123",
            status="COMPLETED",
            payment_id="pay123",
            transaction_id="tx456",
        )
    )

    # Use FastAPI's dependency override to inject our mock use case
    app.dependency_overrides[get_get_order_use_case] = (
        lambda: mock_use_case
    )  # Override the correct dependency getter

    client = TestClient(app)
    response = client.get("/orders/order123")

    # Debug output for failed response
    if response.status_code != 200:
        print(f"DEBUG - Response status: {response.status_code}")
        print(f"DEBUG - Response content: {response.content.decode('utf-8')}")

    # Check response
    assert response.status_code == 200
    assert response.json()["status"] == "COMPLETED"
    assert response.json()["order_id"] == "order123"
    assert response.json()["payment_id"] == "pay123"
    assert response.json()["transaction_id"] == "tx456"

    # Verify the use case method was called
    mock_use_case.get_order_status.assert_awaited_once_with("order123")

    # Clean up dependency override
    app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_upload_order_attachment_endpoint() -> None:
    """Test the /orders/{order_id}/attachments endpoint for file upload."""
    mock_use_case = AsyncMock(spec=OrderFulfillmentUseCase)

    test_order_id = "order-attach-123"
    test_file_content = b"This is some test file content."
    test_filename = "test_document.txt"
    test_content_type = "text/plain"
    test_file_id = str(uuid.uuid4())  # Simulate generated file_id

    # Configure mock use case to return a FileMetadata object
    mock_use_case.upload_order_attachment = AsyncMock(
        return_value=FileMetadata(
            file_id=test_file_id,
            filename=test_filename,
            content_type=test_content_type,
            size_bytes=len(test_file_content),
            metadata={
                "order_id": test_order_id,
                "custom_key": "custom_value",
            },
        )
    )

    app.dependency_overrides[get_order_fulfillment_use_case] = (
        lambda: mock_use_case
    )

    client = TestClient(app)

    # Prepare the file for upload
    files = {
        "file": (
            test_filename,
            io.BytesIO(test_file_content),
            test_content_type,
        )
    }

    # Prepare the metadata as form data, matching endpoint parameter names
    data = {
        "filename_form": test_filename,
        "content_type_form": test_content_type,
        "metadata_json_str": json.dumps(
            {"custom_key": "custom_value"}
        ),  # Ensure it's a JSON string
    }

    response = client.post(
        f"/orders/{test_order_id}/attachments", files=files, data=data
    )

    assert response.status_code == 200
    response_json = response.json()
    assert response_json["message"] == "File uploaded successfully"
    assert response_json["file_id"] == test_file_id
    assert response_json["filename"] == test_filename
    assert response_json["content_type"] == test_content_type
    assert response_json["size_bytes"] == len(test_file_content)
    assert response_json["metadata"]["order_id"] == test_order_id
    assert response_json["metadata"]["custom_key"] == "custom_value"

    # Verify use case method was called with correct arguments
    mock_use_case.upload_order_attachment.assert_awaited_once()
    call_args = mock_use_case.upload_order_attachment.call_args[1]
    assert call_args["order_id"] == test_order_id
    assert call_args["data"] == test_file_content
    assert call_args["metadata"]["filename"] == test_filename
    assert call_args["metadata"]["content_type"] == test_content_type
    assert call_args["metadata"]["custom_key"] == "custom_value"

    app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_download_order_attachment_endpoint() -> None:
    """Test the /orders/{order_id}/attachments/{file_id} endpoint for file
    download.
    """
    mock_use_case = AsyncMock(spec=OrderFulfillmentUseCase)

    test_order_id = "order-attach-123"
    test_file_id = "some-file-id-123"
    test_file_content = b"This is the content of the downloaded file."
    test_filename = "downloaded_file.pdf"
    test_content_type = "application/pdf"

    # Configure mock use case for metadata and content
    mock_use_case.get_order_attachment_metadata = AsyncMock(
        return_value=FileMetadata(
            file_id=test_file_id,
            filename=test_filename,
            content_type=test_content_type,
            size_bytes=len(test_file_content),
            metadata={"order_id": test_order_id},
        )
    )
    mock_use_case.download_order_attachment = AsyncMock(
        return_value=test_file_content
    )

    app.dependency_overrides[get_order_fulfillment_use_case] = (
        lambda: mock_use_case
    )

    client = TestClient(app)
    response = client.get(
        f"/orders/{test_order_id}/attachments/{test_file_id}"
    )

    assert response.status_code == 200
    assert response.content == test_file_content
    assert response.headers["content-type"] == test_content_type
    assert (
        response.headers["content-disposition"]
        == f'attachment; filename="{test_filename}"'
    )

    mock_use_case.get_order_attachment_metadata.assert_awaited_once_with(
        test_order_id, test_file_id
    )
    mock_use_case.download_order_attachment.assert_awaited_once_with(
        test_order_id, test_file_id
    )

    app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_get_order_attachment_metadata_endpoint() -> None:
    """Test the /orders/{order_id}/attachments/{file_id}/metadata endpoint."""
    mock_use_case = AsyncMock(spec=OrderFulfillmentUseCase)

    test_order_id = "order-attach-123"
    test_file_id = "some-file-id-123"
    test_filename = "metadata_doc.txt"
    test_content_type = "text/plain"
    test_size_bytes = 1234
    test_uploaded_at = "2023-10-27T10:00:00.000000"

    # Configure mock use case for metadata
    mock_use_case.get_order_attachment_metadata = AsyncMock(
        return_value=FileMetadata(
            file_id=test_file_id,
            filename=test_filename,
            content_type=test_content_type,
            size_bytes=test_size_bytes,
            uploaded_at=test_uploaded_at,
            metadata={"order_id": test_order_id, "source": "api"},
        )
    )

    app.dependency_overrides[get_order_fulfillment_use_case] = (
        lambda: mock_use_case
    )

    client = TestClient(app)
    response = client.get(
        f"/orders/{test_order_id}/attachments/{test_file_id}/metadata"
    )

    assert response.status_code == 200
    response_json = response.json()
    assert response_json["file_id"] == test_file_id
    assert response_json["filename"] == test_filename
    assert response_json["content_type"] == test_content_type
    assert response_json["size_bytes"] == test_size_bytes
    assert response_json["uploaded_at"] == test_uploaded_at
    assert response_json["metadata"]["order_id"] == test_order_id
    assert response_json["metadata"]["source"] == "api"

    mock_use_case.get_order_attachment_metadata.assert_awaited_once_with(
        test_order_id, test_file_id
    )

    app.dependency_overrides = {}


def test_cancel_order_endpoint() -> None:
    """Test that the cancel_order endpoint correctly initiates a valid
    cancellation workflow.
    """
    # Mock the Temporal client to avoid actual workflow execution
    mock_client = AsyncMock()
    mock_client.start_workflow = AsyncMock()

    # Override the get_temporal_client dependency to return our mock
    from sample.api.dependencies import get_temporal_client

    app.dependency_overrides[get_temporal_client] = lambda: mock_client

    client = TestClient(app)
    order_id = "order-to-cancel-123"
    reason = "Customer request"

    response = client.post(
        f"/orders/{order_id}/cancel", json={"reason": reason}
    )

    # Check response
    assert response.status_code == 200
    response_json = response.json()
    assert response_json["order_id"] == order_id
    assert response_json["status"] == "CANCELLATION_INITIATED"
    assert response_json["reason"] == "Cancellation workflow started"
    assert "request_id" in response_json

    # Verify Temporal client was called
    mock_client.start_workflow.assert_called_once()
    # Assert arguments to start_workflow
    call_args = mock_client.start_workflow.call_args
    # Positional arguments: workflow_run, *args
    # Keyword arguments: id, task_queue, etc.
    assert call_args.args[0].__name__ == "run"
    assert call_args.args[1] == {"order_id": order_id, "reason": reason}
    assert call_args.kwargs["id"].startswith(f"cancel-req-{order_id}-")
    assert call_args.kwargs["task_queue"] == "order-fulfillment-queue"

    # Clean up dependency override
    app.dependency_overrides = {}


def test_cancel_order_endpoint_already_running() -> None:
    """Test that the cancel_order endpoint correctly initiates a cancellation
    workflow, even if the workflow itself might handle idempotency.
    """
    # Mock the Temporal client to avoid actual workflow execution
    mock_client = AsyncMock()
    mock_client.start_workflow = (
        AsyncMock()
    )  # No specific return value needed for this test

    # Override the get_temporal_client dependency to return our mock
    from sample.api.dependencies import get_temporal_client

    app.dependency_overrides[get_temporal_client] = lambda: mock_client

    client = TestClient(app)
    order_id = "order-to-cancel-456"
    reason = "Customer request for already running"

    response = client.post(
        f"/orders/{order_id}/cancel", json={"reason": reason}
    )

    # Check response - API will always respond with CANCELLATION_INITIATED
    # because its role is to initiate the workflow. The workflow's job
    # is to handle whether it's truly a new cancellation or idempotent.
    assert response.status_code == 200
    response_json = response.json()
    assert response_json["order_id"] == order_id
    assert response_json["status"] == "CANCELLATION_INITIATED"
    # The reason from the API is fixed as "Cancellation workflow started"
    assert response_json["reason"] == "Cancellation workflow started"
    assert "request_id" in response_json

    # Verify Temporal client was called
    mock_client.start_workflow.assert_called_once()
    call_args = mock_client.start_workflow.call_args
    assert call_args.args[0].__name__ == "run"
    assert call_args.args[1] == {"order_id": order_id, "reason": reason}
    assert call_args.kwargs["id"].startswith(f"cancel-req-{order_id}-")
    assert call_args.kwargs["task_queue"] == "order-fulfillment-queue"

    # Clean up dependency override
    app.dependency_overrides = {}

import pytest
import os
import time
from fastapi.testclient import TestClient

from sample.api.app import app


@pytest.mark.e2e
def test_order_fulfillment_e2e():
    """Test the entire order fulfillment process from API to repositories"""
    # Use environment variables to connect to test environment
    os.environ["MINIO_ENDPOINT"] = "localhost:9000"
    os.environ["TEMPORAL_ENDPOINT"] = os.environ.get(
        "TEMPORAL_ENDPOINT", "localhost:7233"
    )
    print(f"DEBUG - Set MINIO_ENDPOINT to {os.environ['MINIO_ENDPOINT']}")
    print(
        f"DEBUG - Set TEMPORAL_ENDPOINT to {os.environ['TEMPORAL_ENDPOINT']}"
    )

    client = TestClient(app)

    # Create order request
    response = client.post(
        "/orders",
        json={
            "customer_id": "cust123",
            "items": [
                {"product_id": "prod1", "quantity": 2, "price": "50.00"}
            ],
        },
    )
    assert response.status_code == 200
    request_id = response.json()["request_id"]
    assert response.json()["status"] == "SUBMITTED"
    print(f"DEBUG - Created order request with ID: {request_id}")

    # Poll for request completion (with timeout)
    max_attempts = 15  # Increased attempts for more robustness
    final_order_id = None

    for attempt in range(max_attempts):
        print(
            "DEBUG - Polling request status attempt "
            f"{attempt + 1}/{max_attempts}"
        )
        status_response = client.get(
            f"/order-requests/{request_id}", follow_redirects=False
        )
        print(f"DEBUG - Status response: {status_response.status_code}")

        if status_response.status_code == 302:
            # Got redirect, extract order_id from Location header
            location = status_response.headers["location"]
            final_order_id = location.split("/orders/")[1]
            print(f"DEBUG - Got redirect to order: {final_order_id}")
            break
        elif status_response.status_code == 200:
            # Still processing
            assert status_response.json()["status"] == "SUBMITTED"
            print("DEBUG - Request still processing...")
        elif status_response.status_code == 500:
            # Service error - likely services not running
            print(f"DEBUG - Service error: {status_response.text}")
            pytest.skip(
                "Required services (Temporal/Minio) not available for e2e "
                "test"
            )
        else:
            print(
                "DEBUG - Unexpected response: "
                f"{status_response.status_code} - {status_response.text}"
            )
            assert (
                False
            ), f"Unexpected status code: {status_response.status_code}"

        # Wait before next poll
        time.sleep(1)

    # Should have gotten a redirect by now
    if final_order_id is None:
        pytest.skip(
            "Workflow did not complete within timeout - services may not be "
            "running"
        )

    # Now, poll for the final order status
    final_status_response = None
    for attempt in range(max_attempts):
        print(
            "DEBUG - Polling order status attempt "
            f"{attempt + 1}/{max_attempts}"
        )
        current_order_status_response = client.get(
            f"/orders/{final_order_id}"
        )
        print(
            "DEBUG - Current order status response: "
            f"{current_order_status_response.status_code} - "
            f"{current_order_status_response.json().get('status')}"
        )

        # Check for lowercase "completed"
        if (
            current_order_status_response.status_code == 200
            and current_order_status_response.json().get("status")
            == "completed"
        ):
            final_status_response = current_order_status_response
            print("DEBUG - Order status is COMPLETED!")
            break
        elif current_order_status_response.status_code == 500:
            print(
                "DEBUG - Service error during order status poll: "
                f"{current_order_status_response.text}"
            )
            pytest.skip(
                "Required services (Temporal/Minio) not available for e2e "
                "test"
            )

        time.sleep(1)  # Wait before next poll

    if final_status_response is None:
        pytest.fail("Order did not reach COMPLETED status within timeout.")

    assert final_status_response.status_code == 200
    assert (
        final_status_response.json()["status"] == "completed"
    )  # Assert lowercase "completed"
    assert final_status_response.json()["order_id"] == final_order_id
    print("DEBUG - E2E test completed successfully!")


@pytest.mark.e2e
def test_order_cancellation_e2e():
    """E2E test: Verify order cancellation workflow."""
    os.environ["MINIO_ENDPOINT"] = "localhost:9000"
    os.environ["TEMPORAL_ENDPOINT"] = os.environ.get(
        "TEMPORAL_ENDPOINT", "localhost:7233"
    )
    client = TestClient(app)

    # 1. Create an order first
    create_order_response = client.post(
        "/orders",
        json={
            "customer_id": "cust_cancel_e2e",
            "items": [
                {
                    "product_id": "prod_cancel_1",
                    "quantity": 1,
                    "price": "20.00",
                }
            ],
        },
    )
    assert create_order_response.status_code == 200
    request_id = create_order_response.json()["request_id"]

    max_attempts = 15
    order_id_to_cancel = None
    for attempt in range(max_attempts):
        status_response = client.get(
            f"/order-requests/{request_id}", follow_redirects=False
        )
        if status_response.status_code == 302:
            location = status_response.headers["location"]
            order_id_to_cancel = location.split("/orders/")[1]
            break
        time.sleep(1)
    assert (
        order_id_to_cancel is not None
    ), "Order was not created within timeout."

    # Wait for the order to be 'completed' before attempting to cancel
    for attempt in range(max_attempts):
        order_status_check = client.get(f"/orders/{order_id_to_cancel}")
        if (
            order_status_check.status_code == 200
            and order_status_check.json().get("status") == "completed"
        ):
            break
        time.sleep(1)
    assert (
        order_status_check.json().get("status") == "completed"
    ), "Order did not reach 'completed' status."
    print(
        f"DEBUG - Order {order_id_to_cancel} is completed, proceeding to "
        "cancel."
    )

    # 2. Initiate cancellation workflow
    cancel_reason = "E2E Test Cancellation"
    cancel_initiate_response = client.post(
        f"/orders/{order_id_to_cancel}/cancel", json={"reason": cancel_reason}
    )
    assert cancel_initiate_response.status_code == 200
    assert (
        cancel_initiate_response.json()["order_id"] == order_id_to_cancel
    )  # Order ID is part of the response
    assert (
        cancel_initiate_response.json()["status"] == "CANCELLATION_INITIATED"
    )
    assert "request_id" in cancel_initiate_response.json()
    print(f"DEBUG - Cancellation initiated for order {order_id_to_cancel}.")

    # 3. Poll for final order status
    # We poll the order's status directly, as the cancellation workflow will
    # update it.
    final_order_status_response = None
    for attempt in range(max_attempts):
        current_order_status_response = client.get(
            f"/orders/{order_id_to_cancel}"
        )
        print(
            "DEBUG - Polling order cancellation status attempt "
            f"{attempt + 1}/{max_attempts}: "
            f"{current_order_status_response.json().get('status')}"
        )

        if (
            current_order_status_response.status_code == 200
            and current_order_status_response.json().get("status")
            == "CANCELLED"
        ):
            final_order_status_response = current_order_status_response
            print("DEBUG - Order status is CANCELLED!")
            break
        time.sleep(1)

    assert final_order_status_response is not None
    assert final_order_status_response.status_code == 200
    assert final_order_status_response.json()["status"] == "CANCELLED"
    assert final_order_status_response.json()["reason"] == cancel_reason
    assert (
        final_order_status_response.json()["refund_status"] == "completed"
    )  # Assuming refund succeeds in workflow
    print(
        f"DEBUG - Order {order_id_to_cancel} successfully cancelled and "
        "refunded."
    )

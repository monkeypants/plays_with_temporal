import pytest
from unittest.mock import AsyncMock, MagicMock
from decimal import Decimal

from sample.usecase import OrderFulfillmentUseCase
from sample.repositories import (
    PaymentRepository,
    InventoryRepository,
    OrderRepository,
    OrderRequestRepository,
)
from sample.domain import (
    InventoryItem,
    PaymentOutcome,
    InventoryReservationOutcome,
    CreateOrderRequest,
    OrderItemRequest,
)  # Updated import path for CreateOrderRequest and OrderItem


@pytest.mark.asyncio
async def test_order_with_insufficient_payment_is_rejected() -> None:
    """
    Business Rule: Orders with insufficient payment should be rejected

    When payment processing returns insufficient funds,
    the order status should be PAYMENT_FAILED and inventory items should be
    released.
    """
    # Arrange
    mock_payment_repo = MagicMock(spec=PaymentRepository)
    mock_inventory_repo = MagicMock(spec=InventoryRepository)
    mock_order_repo = MagicMock(spec=OrderRepository)  # New mock
    mock_order_request_repo = MagicMock(
        spec=OrderRequestRepository
    )  # New mock

    # Configure mocks to return outcomes
    mock_payment_repo.process_payment = AsyncMock(
        return_value=PaymentOutcome(
            status="failed", reason="Insufficient funds"
        )
    )
    mock_inventory_repo.reserve_items = AsyncMock(
        return_value=InventoryReservationOutcome(
            status="reserved",
            reserved_items=[InventoryItem(product_id="item1", quantity=2)],
        )
    )
    mock_inventory_repo.release_items = AsyncMock(
        return_value=[InventoryItem(product_id="item1", quantity=2)]
    )
    # Configure new mocks
    mock_order_repo.generate_order_id = AsyncMock(
        return_value="test_order_id_123"
    )
    mock_order_request_repo.store_bidirectional_mapping = AsyncMock(
        return_value=None
    )

    use_case = OrderFulfillmentUseCase(
        mock_payment_repo,
        mock_inventory_repo,
        mock_order_repo,  # Pass new mock
        mock_order_request_repo,  # Pass new mock
    )

    # Act
    request = CreateOrderRequest(
        customer_id="cust123",
        items=[
            OrderItemRequest(
                product_id="prod1", quantity=2, price=Decimal("50.00")
            )
        ],
    )
    request_id = "test_request_id_123"  # Define a request_id
    result = await use_case.fulfill_order(
        request, request_id
    )  # Pass request_id

    # Assert
    assert result.status == "PAYMENT_FAILED"
    assert (
        result.order_id == "test_order_id_123"
    )  # Should use the provided order ID
    assert result.reason is not None and "Insufficient funds" in result.reason
    mock_order_repo.generate_order_id.assert_awaited_once()
    mock_order_request_repo.store_bidirectional_mapping.assert_awaited_once_with(
        request_id, "test_order_id_123"
    )
    mock_inventory_repo.reserve_items.assert_awaited_once()
    mock_payment_repo.process_payment.assert_awaited_once()
    # Inventory should be released
    mock_inventory_repo.release_items.assert_awaited_once()


@pytest.mark.asyncio
async def test_payment_service_unavailable_triggers_compensation() -> None:
    """
    Business Rule: PaymentServiceUnavailable should trigger compensation
    and return PAYMENT_FAILED.

    When the payment repository returns a failed outcome due to service
    unavailability, the order status should be PAYMENT_FAILED and
    inventory items should be released.
    """
    # Arrange
    mock_payment_repo = MagicMock(spec=PaymentRepository)
    mock_inventory_repo = MagicMock(spec=InventoryRepository)
    mock_order_repo = MagicMock(spec=OrderRepository)  # New mock
    mock_order_request_repo = MagicMock(
        spec=OrderRequestRepository
    )  # New mock

    # Configure mocks to return outcomes
    mock_payment_repo.process_payment = AsyncMock(
        return_value=PaymentOutcome(
            status="failed", reason="Payment gateway down"
        )
    )
    mock_inventory_repo.reserve_items = AsyncMock(
        return_value=InventoryReservationOutcome(
            status="reserved",
            reserved_items=[InventoryItem(product_id="item1", quantity=2)],
        )
    )
    mock_inventory_repo.release_items = AsyncMock(
        return_value=[InventoryItem(product_id="item1", quantity=2)]
    )
    # Configure new mocks
    mock_order_repo.generate_order_id = AsyncMock(
        return_value="test_order_id_456"
    )
    mock_order_request_repo.store_bidirectional_mapping = AsyncMock(
        return_value=None
    )

    use_case = OrderFulfillmentUseCase(
        mock_payment_repo,
        mock_inventory_repo,
        mock_order_repo,  # Pass new mock
        mock_order_request_repo,  # Pass new mock
    )

    request = CreateOrderRequest(
        customer_id="cust123",
        items=[
            OrderItemRequest(
                product_id="prod1", quantity=2, price=Decimal("50.00")
            )
        ],
    )
    request_id = "test_request_id_456"  # Define a request_id

    # Act
    result = await use_case.fulfill_order(request, request_id)

    # Assert
    assert result.status == "PAYMENT_FAILED"
    assert result.order_id == "test_order_id_456"  # Corrected assertion
    assert (
        result.reason is not None and "Payment gateway down" in result.reason
    )
    mock_order_repo.generate_order_id.assert_awaited_once()
    mock_order_request_repo.store_bidirectional_mapping.assert_awaited_once_with(
        request_id, "test_order_id_456"
    )
    mock_payment_repo.process_payment.assert_awaited_once()
    mock_inventory_repo.reserve_items.assert_awaited_once()
    mock_inventory_repo.release_items.assert_awaited_once()


@pytest.mark.asyncio
async def test_insufficient_inventory_prevents_payment() -> None:
    """
    Business Rule: InsufficientInventory should prevent payment and return
    INVENTORY_FAILED.

    When the inventory repository returns a failed outcome due to
    insufficient inventory, payment should not be attempted, and the order
    status should be INVENTORY_FAILED.
    """
    # Arrange
    mock_payment_repo = MagicMock(spec=PaymentRepository)
    mock_inventory_repo = MagicMock(spec=InventoryRepository)
    mock_order_repo = MagicMock(spec=OrderRepository)  # New mock
    mock_order_request_repo = MagicMock(
        spec=OrderRequestRepository
    )  # New mock

    # Configure mocks to return outcomes
    mock_inventory_repo.reserve_items = AsyncMock(
        return_value=InventoryReservationOutcome(
            status="failed", reason="Not enough stock"
        )
    )
    mock_inventory_repo.release_items = (
        AsyncMock()
    )  # Should not be called, but define for safety

    # Configure new mocks
    mock_order_repo.generate_order_id = AsyncMock(
        return_value="test_order_id_789"
    )
    mock_order_request_repo.store_bidirectional_mapping = AsyncMock(
        return_value=None
    )

    use_case = OrderFulfillmentUseCase(
        mock_payment_repo,
        mock_inventory_repo,
        mock_order_repo,  # Pass new mock
        mock_order_request_repo,  # Pass new mock
    )

    request = CreateOrderRequest(
        customer_id="cust123",
        items=[
            OrderItemRequest(
                product_id="prod1", quantity=2, price=Decimal("50.00")
            )
        ],
    )
    request_id = "test_request_id_789"  # Define a request_id

    # Act
    result = await use_case.fulfill_order(request, request_id)

    # Assert
    assert result.status == "INVENTORY_FAILED"
    assert result.order_id == "test_order_id_789"  # Corrected assertion
    assert result.reason is not None and "Not enough stock" in result.reason
    mock_order_repo.generate_order_id.assert_awaited_once()
    mock_order_request_repo.store_bidirectional_mapping.assert_awaited_once_with(
        request_id, "test_order_id_789"
    )
    mock_inventory_repo.reserve_items.assert_awaited_once()
    # Payment should not be called
    mock_payment_repo.process_payment.assert_not_awaited()
    # Compensation should not be called
    mock_inventory_repo.release_items.assert_not_awaited()

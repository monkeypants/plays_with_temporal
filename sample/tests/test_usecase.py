import pytest
from unittest.mock import AsyncMock, MagicMock
from decimal import Decimal

from sample.usecase import (
    OrderFulfillmentUseCase,
    GetOrderUseCase,
)  # Added GetOrderUseCase
from sample.repositories import (
    PaymentRepository,
    InventoryRepository,
    OrderRepository,
    OrderRequestRepository,
)
from sample.domain import (
    Payment,
    Order,
    OrderItem,
    InventoryItem,
    PaymentOutcome,
    InventoryReservationOutcome,
    CreateOrderRequest,
    OrderItemRequest,
)


@pytest.mark.asyncio
async def test_fulfill_order_successful_payment():
    """Test that an order with valid payment is processed successfully"""
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
            status="completed",
            payment=Payment(
                payment_id="payment123",
                order_id="order123",
                amount=Decimal("100.00"),
                status="completed",
            ),
        )
    )
    mock_inventory_repo.reserve_items = AsyncMock(
        return_value=InventoryReservationOutcome(
            status="reserved",
            reserved_items=[InventoryItem(product_id="item1", quantity=2)],
        )
    )
    # Configure new mocks for order ID generation and mapping storage
    mock_order_repo.generate_order_id = AsyncMock(
        return_value="test-order-123"
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
    request_id = "test-request-123"  # Define a request_id
    result = await use_case.fulfill_order(
        request, request_id
    )  # Pass request_id

    # Assert
    assert result.status == "completed"  # Assert lowercase "completed"
    assert (
        result.order_id == "test-order-123"
    )  # Should use the provided order ID
    mock_order_repo.generate_order_id.assert_awaited_once()
    mock_order_request_repo.store_bidirectional_mapping.assert_awaited_once_with(
        request_id, "test-order-123"
    )
    mock_payment_repo.process_payment.assert_awaited_once()
    mock_inventory_repo.reserve_items.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_order_status_returns_from_order_repo():
    """Test that get_order_status prioritizes order repository."""
    # Arrange
    mock_order_repo = AsyncMock(spec=OrderRepository)
    mock_payment_repo = AsyncMock(spec=PaymentRepository)

    order_id = "test-order-123"
    test_order = Order(
        order_id=order_id,
        customer_id="cust123",
        items=[
            OrderItem(product_id="prod1", quantity=1, price=Decimal("10.00"))
        ],
        total_amount=Decimal("10.00"),
        status="completed",
        reason="fulfilled",
        refund_id="ref-456",
        refund_status="completed",
    )
    mock_order_repo.get_order = AsyncMock(return_value=test_order)

    # Use GetOrderUseCase for status checks
    use_case = GetOrderUseCase(mock_order_repo, mock_payment_repo)

    # Act
    result = await use_case.get_order_status(order_id)

    # Assert
    assert result.order_id == order_id
    assert result.status == "completed"
    assert result.reason == "fulfilled"
    assert result.refund_id == "ref-456"
    assert result.refund_status == "completed"
    mock_order_repo.get_order.assert_awaited_once_with(order_id)
    mock_payment_repo.get_payment.assert_not_awaited()  # Should not be called


@pytest.mark.asyncio
async def test_get_order_status_falls_back_to_payment_repo():
    """Test that get_order_status falls back to payment repository if order
    not found."""
    # Arrange
    mock_order_repo = AsyncMock(spec=OrderRepository)
    mock_payment_repo = AsyncMock(spec=PaymentRepository)

    order_id = "test-order-456"
    test_payment = Payment(
        payment_id=f"pmt_{order_id}",
        order_id=order_id,
        amount=Decimal("100.00"),
        status="completed",
        transaction_id="tx-789",
    )
    mock_order_repo.get_order = AsyncMock(
        return_value=None
    )  # Order not found
    mock_payment_repo.get_payment = AsyncMock(
        return_value=test_payment
    )  # Payment found

    # Use GetOrderUseCase for status checks
    use_case = GetOrderUseCase(mock_order_repo, mock_payment_repo)

    # Act
    result = await use_case.get_order_status(order_id)

    # Assert
    assert result.order_id == order_id
    assert result.status == "completed"
    assert result.payment_id == test_payment.payment_id
    assert result.transaction_id == test_payment.transaction_id
    assert (
        result.refund_id is None
    )  # Should not be populated from payment if not refunded
    assert result.refund_status is None
    mock_order_repo.get_order.assert_awaited_once_with(order_id)
    mock_payment_repo.get_payment.assert_awaited_once_with(f"pmt_{order_id}")


@pytest.mark.asyncio
async def test_get_order_status_from_payment_refunded():
    """Test get_order_status when payment is refunded via fallback."""
    # Arrange
    mock_order_repo = AsyncMock(spec=OrderRepository)
    mock_payment_repo = AsyncMock(spec=PaymentRepository)

    order_id = "test-order-refunded"
    test_payment = Payment(
        payment_id=f"pmt_{order_id}",
        order_id=order_id,
        amount=Decimal("100.00"),
        status="refunded",
        transaction_id="tx-refund",
    )
    mock_order_repo.get_order = AsyncMock(return_value=None)
    mock_payment_repo.get_payment = AsyncMock(return_value=test_payment)

    # Use GetOrderUseCase for status checks
    use_case = GetOrderUseCase(mock_order_repo, mock_payment_repo)

    # Act
    result = await use_case.get_order_status(order_id)

    # Assert
    assert result.order_id == order_id
    assert result.status == "refunded"  # Payment status is 'refunded'
    assert (
        result.refund_id == f"ref_{test_payment.payment_id}"
    )  # Derived refund_id
    assert result.refund_status == "completed"  # Mapped to 'completed'


@pytest.mark.asyncio
async def test_get_order_status_returns_processing_if_neither_found():
    """Test that get_order_status returns 'processing' if neither order nor
    payment found."""
    # Arrange
    mock_order_repo = AsyncMock(spec=OrderRepository)
    mock_payment_repo = AsyncMock(spec=PaymentRepository)

    order_id = "test-order-789"
    mock_order_repo.get_order = AsyncMock(return_value=None)
    mock_payment_repo.get_payment = AsyncMock(return_value=None)

    # Use GetOrderUseCase for status checks
    use_case = GetOrderUseCase(mock_order_repo, mock_payment_repo)

    # Act
    result = await use_case.get_order_status(order_id)

    # Assert
    assert result.order_id == order_id
    assert result.status == "processing"
    assert result.payment_id is None
    assert result.transaction_id is None
    assert result.reason is None
    assert result.current_step is None
    assert result.refund_id is None
    assert result.refund_status is None
    mock_order_repo.get_order.assert_awaited_once_with(order_id)
    mock_payment_repo.get_payment.assert_awaited_once_with(f"pmt_{order_id}")

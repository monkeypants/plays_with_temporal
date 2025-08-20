import pytest
from unittest.mock import AsyncMock, MagicMock
from decimal import Decimal

from sample.usecase import CancelOrderUseCase
from sample.repositories import (
    PaymentRepository,
    InventoryRepository,
    OrderRepository,
)
from sample.domain import (
    Order,
    Payment,
    InventoryItem,
    OrderItem,
    RefundPaymentArgs,
    RefundPaymentOutcome,
)


@pytest.mark.asyncio
async def test_cancel_order_successful_refund_and_release() -> None:
    """Test successful order cancellation with payment refund and inventory
    release."""
    # Arrange
    mock_order_repo = MagicMock(spec=OrderRepository)
    mock_payment_repo = MagicMock(spec=PaymentRepository)
    mock_inventory_repo = MagicMock(spec=InventoryRepository)

    order_id = "test-order-cancel-123"
    payment_id = f"pmt_{order_id}"
    test_order = Order(
        order_id=order_id,
        customer_id="cust123",
        items=[
            OrderItem(product_id="prod1", quantity=2, price=Decimal("50.00"))
        ],
        total_amount=Decimal("100.00"),
        status="completed",
    )
    test_payment = Payment(
        payment_id=payment_id,
        order_id=order_id,
        amount=Decimal("100.00"),
        status="completed",
        transaction_id="tx-123",
    )

    mock_order_repo.get_order = AsyncMock(return_value=test_order)

    # Use a side effect to capture the status of the order object at the
    # time of call
    saved_order_statuses = []

    async def save_order_side_effect(order_obj: Order) -> None:
        saved_order_statuses.append(order_obj.status)
        # The mock itself doesn't need to return anything for save_order
        pass

    mock_order_repo.save_order = AsyncMock(side_effect=save_order_side_effect)

    mock_order_repo.cancel_order = (
        AsyncMock()
    )  # This is now called by the use case

    mock_payment_repo.get_payment = AsyncMock(return_value=test_payment)
    mock_payment_repo.refund_payment = AsyncMock(
        return_value=RefundPaymentOutcome(
            status="refunded", refund_id=f"ref_{payment_id}"
        )
    )

    mock_inventory_repo.release_items = AsyncMock(
        return_value=[InventoryItem(product_id="prod1", quantity=2)]
    )

    use_case = CancelOrderUseCase(
        order_repo=mock_order_repo,
        payment_repo=mock_payment_repo,
        inventory_repo=mock_inventory_repo,
    )

    # Act
    result = await use_case.cancel_order(
        order_id, reason="Customer changed mind"
    )

    # Assert
    assert result.status == "CANCELLED"
    assert result.order_id == order_id
    assert result.reason == "Customer changed mind"
    assert result.refund_id == f"ref_{payment_id}"
    assert result.refund_status == "completed"

    mock_order_repo.get_order.assert_awaited_once_with(order_id)
    # Check that save_order was called twice
    assert mock_order_repo.save_order.call_count == 2
    # Now assert against the captured statuses
    assert saved_order_statuses[0] == "CANCELLING"
    assert saved_order_statuses[1] == "CANCELLED"

    mock_payment_repo.get_payment.assert_awaited_once_with(payment_id)
    mock_payment_repo.refund_payment.assert_awaited_once_with(
        RefundPaymentArgs(
            payment_id=payment_id,
            order_id=order_id,
            amount=Decimal("100.00"),
            reason="Customer changed mind",
        )
    )
    mock_inventory_repo.release_items.assert_awaited_once()


@pytest.mark.asyncio
async def test_cancel_order_not_found() -> None:
    """Test cancellation of a non-existent order."""
    # Arrange
    mock_order_repo = MagicMock(spec=OrderRepository)
    mock_payment_repo = MagicMock(spec=PaymentRepository)
    mock_inventory_repo = MagicMock(spec=InventoryRepository)

    order_id = "non-existent-order"
    mock_order_repo.get_order = AsyncMock(return_value=None)

    use_case = CancelOrderUseCase(
        order_repo=mock_order_repo,
        payment_repo=mock_payment_repo,
        inventory_repo=mock_inventory_repo,
    )

    # Act
    result = await use_case.cancel_order(order_id)

    # Assert
    assert result.status == "FAILED"
    assert result.reason == "Order not found."
    assert result.order_id == order_id

    mock_order_repo.get_order.assert_awaited_once_with(order_id)
    mock_order_repo.save_order.assert_not_awaited()
    mock_payment_repo.get_payment.assert_not_awaited()
    mock_inventory_repo.release_items.assert_not_awaited()


@pytest.mark.asyncio
async def test_cancel_order_already_cancelled() -> None:
    """Test cancellation of an order that is already cancelled."""
    # Arrange
    mock_order_repo = MagicMock(spec=OrderRepository)
    mock_payment_repo = MagicMock(spec=PaymentRepository)
    mock_inventory_repo = MagicMock(spec=InventoryRepository)

    order_id = "already-cancelled-order"
    test_order = Order(
        order_id=order_id,
        customer_id="cust123",
        items=[
            OrderItem(product_id="prod1", quantity=1, price=Decimal("10.00"))
        ],
        total_amount=Decimal("10.00"),
        status="CANCELLED",
        reason="Already cancelled",
    )

    mock_order_repo.get_order = AsyncMock(return_value=test_order)

    use_case = CancelOrderUseCase(
        order_repo=mock_order_repo,
        payment_repo=mock_payment_repo,
        inventory_repo=mock_inventory_repo,
    )

    # Act
    result = await use_case.cancel_order(order_id)

    # Assert
    assert result.status == "CANCELLED"
    assert result.reason == "Already cancelled"
    assert result.order_id == order_id

    mock_order_repo.get_order.assert_awaited_once_with(order_id)
    mock_order_repo.save_order.assert_not_awaited()  # Should not save again
    mock_payment_repo.get_payment.assert_not_awaited()
    mock_inventory_repo.release_items.assert_not_awaited()


@pytest.mark.asyncio
async def test_cancel_order_no_payment_to_refund() -> None:
    """Test cancellation when no payment was made (e.g., order failed
    early)."""
    # Arrange
    mock_order_repo = MagicMock(spec=OrderRepository)
    mock_payment_repo = MagicMock(spec=PaymentRepository)
    mock_inventory_repo = MagicMock(spec=InventoryRepository)

    order_id = "no-payment-order"
    test_order = Order(
        order_id=order_id,
        customer_id="cust123",
        items=[
            OrderItem(product_id="prod1", quantity=1, price=Decimal("10.00"))
        ],
        total_amount=Decimal("10.00"),
        status="pending",  # Or FAILED, PAYMENT_FAILED
    )

    mock_order_repo.get_order = AsyncMock(return_value=test_order)
    mock_order_repo.save_order = AsyncMock()
    mock_payment_repo.get_payment = AsyncMock(
        return_value=None
    )  # No payment found
    mock_inventory_repo.release_items = AsyncMock()

    use_case = CancelOrderUseCase(
        order_repo=mock_order_repo,
        payment_repo=mock_payment_repo,
        inventory_repo=mock_inventory_repo,
    )

    # Act
    result = await use_case.cancel_order(order_id)

    # Assert
    assert result.status == "CANCELLED"
    assert result.order_id == order_id
    assert result.refund_id is None
    assert result.refund_status == "not_applicable"

    mock_order_repo.get_order.assert_awaited_once_with(order_id)
    assert mock_order_repo.save_order.call_count == 2
    mock_payment_repo.get_payment.assert_awaited_once()
    # No refund attempted
    mock_payment_repo.refund_payment.assert_not_awaited()
    mock_inventory_repo.release_items.assert_awaited_once()


@pytest.mark.asyncio
async def test_cancel_order_refund_fails_but_continues() -> None:
    """Test that if refund fails, cancellation still proceeds (logs error)."""
    # Arrange
    mock_order_repo = MagicMock(spec=OrderRepository)
    mock_payment_repo = MagicMock(spec=PaymentRepository)
    mock_inventory_repo = MagicMock(spec=InventoryRepository)

    order_id = "refund-fail-order"
    payment_id = f"pmt_{order_id}"
    test_order = Order(
        order_id=order_id,
        customer_id="cust123",
        items=[
            OrderItem(product_id="prod1", quantity=1, price=Decimal("10.00"))
        ],
        total_amount=Decimal("10.00"),
        status="completed",
    )
    test_payment = Payment(
        payment_id=payment_id,
        order_id=order_id,
        amount=Decimal("10.00"),
        status="completed",
        transaction_id="tx-456",
    )

    mock_order_repo.get_order = AsyncMock(return_value=test_order)

    # Use a side effect to capture the status of the order object at the
    # time of call
    saved_order_statuses = []

    async def save_order_side_effect(order_obj: Order) -> None:
        saved_order_statuses.append(order_obj.status)
        pass

    mock_order_repo.save_order = AsyncMock(side_effect=save_order_side_effect)

    mock_payment_repo.get_payment = AsyncMock(return_value=test_payment)
    mock_payment_repo.refund_payment = AsyncMock(
        return_value=RefundPaymentOutcome(
            status="failed", reason="Payment gateway error"
        )
    )  # Simulate refund failure

    mock_inventory_repo.release_items = AsyncMock()

    use_case = CancelOrderUseCase(
        order_repo=mock_order_repo,
        payment_repo=mock_payment_repo,
        inventory_repo=mock_inventory_repo,
    )

    # Act
    result = await use_case.cancel_order(order_id)

    # Assert
    assert result.status == "CANCELLED"  # Order still cancelled
    assert result.order_id == order_id
    assert result.refund_id is None  # No refund ID if failed
    assert result.refund_status == "failed"  # Refund status is failed

    mock_order_repo.get_order.assert_awaited_once_with(order_id)
    assert mock_order_repo.save_order.call_count == 2
    assert saved_order_statuses[0] == "CANCELLING"
    assert saved_order_statuses[1] == "CANCELLED"
    mock_payment_repo.get_payment.assert_awaited_once_with(payment_id)
    mock_payment_repo.refund_payment.assert_awaited_once()
    # Inventory still released
    mock_inventory_repo.release_items.assert_awaited_once()


@pytest.mark.asyncio
async def test_cancel_order_unexpected_exception() -> None:
    """Test that an unexpected exception during cancellation is handled
    gracefully."""
    # Arrange
    mock_order_repo = MagicMock(spec=OrderRepository)
    mock_payment_repo = MagicMock(spec=PaymentRepository)
    mock_inventory_repo = MagicMock(spec=InventoryRepository)

    order_id = "exception-order"
    test_order = Order(
        order_id=order_id,
        customer_id="cust123",
        items=[
            OrderItem(product_id="prod1", quantity=1, price=Decimal("10.00"))
        ],
        total_amount=Decimal("10.00"),
        status="completed",
    )

    mock_order_repo.get_order = AsyncMock(return_value=test_order)

    # Use a side effect to capture the status of the order object at the
    # time of call
    saved_order_statuses = []

    async def save_order_side_effect(order_obj: Order) -> None:
        saved_order_statuses.append(order_obj.status)
        pass

    mock_order_repo.save_order = AsyncMock(side_effect=save_order_side_effect)

    # Simulate an unexpected error during payment refund attempt
    mock_payment_repo.get_payment = AsyncMock(
        side_effect=Exception("Database connection lost")
    )

    use_case = CancelOrderUseCase(
        order_repo=mock_order_repo,
        payment_repo=mock_payment_repo,
        inventory_repo=mock_inventory_repo,
    )

    # Act
    result = await use_case.cancel_order(order_id)

    # Assert
    assert result.status == "FAILED"
    assert result.reason is not None and "Database connection lost" in str(
        result.reason
    )
    assert result.order_id == order_id

    mock_order_repo.get_order.assert_awaited_once_with(order_id)
    # save_order should be called at least once for CANCELLING, and once
    # for FAILED_CANCELLATION
    assert mock_order_repo.save_order.call_count == 2
    assert saved_order_statuses[0] == "CANCELLING"
    assert saved_order_statuses[1] == "FAILED_CANCELLATION"
    mock_payment_repo.get_payment.assert_awaited_once()
    mock_payment_repo.refund_payment.assert_not_awaited()
    # Should not be called if earlier step failed unexpectedly
    mock_inventory_repo.release_items.assert_not_awaited()

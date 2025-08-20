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
    Payment,
    InventoryItem,
    PaymentOutcome,
    InventoryReservationOutcome,
    CreateOrderRequest,
    OrderItemRequest,
)  # Updated import path for CreateOrderRequest and OrderItemRequest


@pytest.mark.asyncio
async def test_payment_failure_releases_inventory():
    """Verify saga compensation: payment failure releases reserved
    inventory"""
    mock_payment_repo = MagicMock(spec=PaymentRepository)
    mock_inventory_repo = MagicMock(spec=InventoryRepository)
    mock_order_repo = MagicMock(spec=OrderRepository)  # New mock
    mock_order_request_repo = MagicMock(
        spec=OrderRequestRepository
    )  # New mock

    # Configure successful inventory reservation
    mock_inventory_repo.reserve_items = AsyncMock(
        return_value=InventoryReservationOutcome(
            status="reserved",
            reserved_items=[InventoryItem(product_id="prod1", quantity=2)],
        )
    )
    mock_inventory_repo.release_items = AsyncMock(
        return_value=[InventoryItem(product_id="prod1", quantity=2)]
    )

    # Configure payment failure
    mock_payment_repo.process_payment = AsyncMock(
        return_value=PaymentOutcome(
            status="failed", reason="Payment declined"
        )
    )
    # Configure new mocks for order ID generation and mapping storage
    mock_order_repo.generate_order_id = AsyncMock(return_value="order123")
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
    request_id = "req-123"  # Define a request_id

    result = await use_case.fulfill_order(
        request, request_id
    )  # Pass request_id

    # Verify saga compensation was executed
    mock_order_repo.generate_order_id.assert_awaited_once()
    mock_order_request_repo.store_bidirectional_mapping.assert_awaited_once_with(
        request_id, "order123"
    )
    mock_inventory_repo.reserve_items.assert_awaited_once()
    mock_payment_repo.process_payment.assert_awaited_once()
    mock_inventory_repo.release_items.assert_awaited_once()  # Compensation
    assert result.status == "PAYMENT_FAILED"
    assert result.reason is not None and "Payment declined" in result.reason
    assert result.order_id == "order123"


@pytest.mark.asyncio
async def test_inventory_failure_does_not_process_payment():
    """Verify saga pattern: inventory failure prevents payment processing"""
    mock_payment_repo = MagicMock(spec=PaymentRepository)
    mock_inventory_repo = MagicMock(spec=InventoryRepository)
    mock_order_repo = MagicMock(spec=OrderRepository)  # New mock
    mock_order_request_repo = MagicMock(
        spec=OrderRequestRepository
    )  # New mock

    # Configure inventory failure
    mock_inventory_repo.reserve_items = AsyncMock(
        return_value=InventoryReservationOutcome(
            status="failed", reason="Insufficient inventory"
        )
    )

    use_case = OrderFulfillmentUseCase(
        mock_payment_repo,
        mock_inventory_repo,
        mock_order_repo,  # Pass new mock
        mock_order_request_repo,  # Pass new mock
    )
    # Configure new mocks for order ID generation and mapping storage
    mock_order_repo.generate_order_id = AsyncMock(return_value="order123")
    mock_order_request_repo.store_bidirectional_mapping = AsyncMock(
        return_value=None
    )

    request = CreateOrderRequest(
        customer_id="cust123",
        items=[
            OrderItemRequest(
                product_id="prod1", quantity=2, price=Decimal("50.00")
            )
        ],
    )
    request_id = "req-123"  # Define a request_id

    result = await use_case.fulfill_order(
        request, request_id
    )  # Pass request_id

    # Verify payment was never attempted
    mock_order_repo.generate_order_id.assert_awaited_once()
    mock_order_request_repo.store_bidirectional_mapping.assert_awaited_once_with(
        request_id, "order123"
    )
    mock_payment_repo.process_payment.assert_not_awaited()
    mock_inventory_repo.reserve_items.assert_awaited_once()
    assert result.status == "INVENTORY_FAILED"
    assert (
        result.reason is not None
        and "Insufficient inventory" in result.reason
    )
    assert result.order_id == "order123"


@pytest.mark.asyncio
async def test_successful_saga_completes_all_steps():
    """Verify successful saga executes all forward actions without
    compensation"""
    mock_payment_repo = MagicMock(spec=PaymentRepository)
    mock_inventory_repo = MagicMock(spec=InventoryRepository)
    mock_order_repo = MagicMock(spec=OrderRepository)  # New mock
    mock_order_request_repo = MagicMock(
        spec=OrderRequestRepository
    )  # New mock

    # Configure successful operations
    mock_inventory_repo.reserve_items = AsyncMock(
        return_value=InventoryReservationOutcome(
            status="reserved",
            reserved_items=[InventoryItem(product_id="prod1", quantity=2)],
        )
    )
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
    # Configure new mocks for order ID generation and mapping storage
    mock_order_repo.generate_order_id = AsyncMock(return_value="order123")
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
    request_id = "req-123"  # Define a request_id

    result = await use_case.fulfill_order(
        request, request_id
    )  # Pass request_id

    # Verify all forward actions executed
    mock_order_repo.generate_order_id.assert_awaited_once()
    mock_order_request_repo.store_bidirectional_mapping.assert_awaited_once_with(
        request_id, "order123"
    )
    mock_inventory_repo.reserve_items.assert_awaited_once()
    mock_payment_repo.process_payment.assert_awaited_once()

    # Verify no compensation actions
    mock_inventory_repo.release_items.assert_not_awaited()

    assert result.status == "completed"  # Assert lowercase "completed"
    assert result.order_id == "order123"


@pytest.mark.asyncio
async def test_exception_during_payment_triggers_compensation():
    """Verify saga compensation: unexpected exception during payment
    releases inventory"""
    mock_payment_repo = MagicMock(spec=PaymentRepository)
    mock_inventory_repo = MagicMock(spec=InventoryRepository)
    mock_order_repo = MagicMock(spec=OrderRepository)  # New mock
    mock_order_request_repo = MagicMock(
        spec=OrderRequestRepository
    )  # New mock

    # Configure successful inventory reservation
    mock_inventory_repo.reserve_items = AsyncMock(
        return_value=InventoryReservationOutcome(
            status="reserved",
            reserved_items=[InventoryItem(product_id="prod1", quantity=1)],
        )
    )
    mock_inventory_repo.release_items = AsyncMock(
        return_value=[InventoryItem(product_id="prod1", quantity=1)]
    )

    # Configure payment to throw unexpected exception (not a business outcome)
    mock_payment_repo.process_payment = AsyncMock(
        side_effect=Exception("Payment service connection lost")
    )
    # Configure new mocks for order ID generation and mapping storage
    mock_order_repo.generate_order_id = AsyncMock(return_value="order123")
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
                product_id="prod1", quantity=1, price=Decimal("30.00")
            )
        ],
    )
    request_id = "req-123"  # Define a request_id

    result = await use_case.fulfill_order(
        request, request_id
    )  # Pass request_id

    # Verify compensation was executed
    mock_order_repo.generate_order_id.assert_awaited_once()
    mock_order_request_repo.store_bidirectional_mapping.assert_awaited_once_with(
        request_id, "order123"
    )
    mock_inventory_repo.reserve_items.assert_awaited_once()
    mock_payment_repo.process_payment.assert_awaited_once()
    mock_inventory_repo.release_items.assert_awaited_once()  # Compensation
    assert result.status == "FAILED"
    assert (
        result.reason is not None
        and "Payment service connection lost" in result.reason
    )
    assert result.order_id == "order123"


@pytest.mark.asyncio
async def test_compensation_failure_is_logged_but_not_propagated():
    """Verify saga compensation: compensation failures are logged but don't
    prevent error response"""
    mock_payment_repo = MagicMock(spec=PaymentRepository)
    mock_inventory_repo = MagicMock(spec=InventoryRepository)
    mock_order_repo = MagicMock(spec=OrderRepository)  # New mock
    mock_order_request_repo = MagicMock(
        spec=OrderRequestRepository
    )  # New mock

    # Configure successful inventory reservation
    mock_inventory_repo.reserve_items = AsyncMock(
        return_value=InventoryReservationOutcome(
            status="reserved",
            reserved_items=[InventoryItem(product_id="prod1", quantity=1)],
        )
    )
    # Configure compensation to fail
    mock_inventory_repo.release_items = AsyncMock(
        side_effect=Exception("Compensation failed")
    )

    # Configure payment to return a failed outcome
    mock_payment_repo.process_payment = AsyncMock(
        return_value=PaymentOutcome(
            status="failed", reason="Payment gateway error"
        )
    )
    # Configure new mocks for order ID generation and mapping storage
    mock_order_repo.generate_order_id = AsyncMock(return_value="order123")
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
                product_id="prod1", quantity=1, price=Decimal("30.00")
            )
        ],
    )
    request_id = "req-123"  # Define a request_id

    # Should not raise exception even though compensation fails
    result = await use_case.fulfill_order(
        request, request_id
    )  # Pass request_id

    # Verify all operations were attempted
    mock_order_repo.generate_order_id.assert_awaited_once()
    mock_order_request_repo.store_bidirectional_mapping.assert_awaited_once_with(
        request_id, "order123"
    )
    mock_inventory_repo.reserve_items.assert_awaited_once()
    mock_payment_repo.process_payment.assert_awaited_once()
    # Compensation attempted
    mock_inventory_repo.release_items.assert_awaited_once()

    # Should still return PAYMENT_FAILED status with original error
    assert result.status == "PAYMENT_FAILED"
    assert (
        result.reason is not None and "Payment gateway error" in result.reason
    )
    assert result.order_id == "order123"


@pytest.mark.asyncio
async def test_idempotent_compensation_safe_for_multiple_calls():
    """Verify saga compensation: release_items is safe to call multiple
    times"""
    mock_payment_repo = MagicMock(spec=PaymentRepository)
    mock_inventory_repo = MagicMock(spec=InventoryRepository)
    mock_order_repo = MagicMock(spec=OrderRepository)  # New mock
    mock_order_request_repo = MagicMock(
        spec=OrderRequestRepository
    )  # New mock

    # Configure successful inventory reservation
    mock_inventory_repo.reserve_items = AsyncMock(
        return_value=InventoryReservationOutcome(
            status="reserved",
            reserved_items=[InventoryItem(product_id="prod1", quantity=1)],
        )
    )
    # Configure idempotent release
    mock_inventory_repo.release_items = AsyncMock(
        return_value=[InventoryItem(product_id="prod1", quantity=1)]
    )

    # Configure payment failure
    mock_payment_repo.process_payment = AsyncMock(
        return_value=PaymentOutcome(
            status="failed", reason="Payment already processed"
        )
    )
    # Configure new mocks for order ID generation and mapping storage
    mock_order_repo.generate_order_id = AsyncMock(return_value="order123")
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
                product_id="prod1", quantity=1, price=Decimal("30.00")
            )
        ],
    )
    request_id = "req-123"  # Define a request_id

    # Run the same order fulfillment twice
    result1 = await use_case.fulfill_order(
        request, request_id
    )  # Pass request_id
    result2 = await use_case.fulfill_order(
        request, request_id
    )  # Pass request_id

    # Both should succeed with same result
    assert result1.status == "PAYMENT_FAILED"
    assert result2.status == "PAYMENT_FAILED"
    assert result1.order_id == result2.order_id

    # Verify operations were called for both attempts
    assert mock_order_repo.generate_order_id.call_count == 2
    assert mock_order_request_repo.store_bidirectional_mapping.call_count == 2
    assert mock_inventory_repo.reserve_items.call_count == 2
    assert mock_payment_repo.process_payment.call_count == 2
    assert mock_inventory_repo.release_items.call_count == 2


@pytest.mark.asyncio
async def test_saga_step_ordering_is_correct():
    """Verify saga pattern: steps execute in correct order (inventory
    first, then payment)"""
    mock_payment_repo = MagicMock(spec=PaymentRepository)
    mock_inventory_repo = MagicMock(spec=InventoryRepository)
    mock_order_repo = MagicMock(spec=OrderRepository)  # New mock
    mock_order_request_repo = MagicMock(
        spec=OrderRequestRepository
    )  # New mock

    call_order = []

    # Track call order
    async def track_reserve(*args, **kwargs):
        call_order.append("reserve_inventory")
        return InventoryReservationOutcome(
            status="reserved",
            reserved_items=[InventoryItem(product_id="prod1", quantity=1)],
        )

    async def track_payment(*args, **kwargs):
        call_order.append("process_payment")
        return PaymentOutcome(
            status="completed",
            payment=Payment(
                payment_id="payment123",
                order_id="order123",
                amount=Decimal("30.00"),
                status="completed",
            ),
        )

    mock_inventory_repo.reserve_items = AsyncMock(side_effect=track_reserve)
    mock_payment_repo.process_payment = AsyncMock(side_effect=track_payment)
    # Configure new mocks for order ID generation and mapping storage
    mock_order_repo.generate_order_id = AsyncMock(return_value="order123")
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
                product_id="prod1", quantity=1, price=Decimal("30.00")
            )
        ],
    )
    request_id = "req-123"  # Define a request_id

    result = await use_case.fulfill_order(
        request, request_id
    )  # Pass request_id

    # Verify correct order: order ID generation, mapping, inventory
    # reservation before payment
    assert call_order == [
        "reserve_inventory",
        "process_payment",
    ]  # Only tracks use case internal calls
    mock_order_repo.generate_order_id.assert_awaited_once()
    mock_order_request_repo.store_bidirectional_mapping.assert_awaited_once_with(
        request_id, "order123"
    )
    assert result.status == "completed"  # Assert lowercase "completed"
    assert result.order_id == "order123"

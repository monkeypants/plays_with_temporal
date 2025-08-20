"""
Security-focused tests for use case business logic.

These tests focus on critical error paths, compensation logic, and security
scenarios that are essential for financial operations but often missed in
basic testing.
"""

import pytest
from decimal import Decimal
from unittest.mock import AsyncMock

from sample.usecase import OrderFulfillmentUseCase, CancelOrderUseCase
from sample.domain import (
    Order,
    OrderItem,
    OrderItemRequest,
    InventoryItem,
    Payment,
    PaymentOutcome,
    InventoryReservationOutcome,
    RefundPaymentOutcome,
    CreateOrderRequest,
)
from sample.repositories import (
    PaymentRepository,
    InventoryRepository,
    OrderRepository,
    OrderRequestRepository,
)
from util.repositories import FileStorageRepository
from util.domain import FileMetadata


class TestOrderFulfillmentUseCaseSecurity:
    """Security-focused tests for OrderFulfillmentUseCase."""

    def setup_method(self) -> None:
        """Set up mocks and use case for each test."""
        self.mock_payment_repo = AsyncMock(spec=PaymentRepository)
        self.mock_inventory_repo = AsyncMock(spec=InventoryRepository)
        self.mock_order_repo = AsyncMock(spec=OrderRepository)
        self.mock_order_request_repo = AsyncMock(spec=OrderRequestRepository)
        self.mock_file_storage_repo = AsyncMock(spec=FileStorageRepository)

        # Default successful outcomes
        self.mock_order_repo.generate_order_id.return_value = "ord-123"
        self.mock_inventory_repo.reserve_items.return_value = (
            InventoryReservationOutcome(
                status="reserved",
                reserved_items=[
                    InventoryItem(product_id="prod-1", quantity=1, reserved=1)
                ],
            )
        )
        self.mock_payment_repo.process_payment.return_value = PaymentOutcome(
            status="completed",
            payment=Payment(
                payment_id="pmt-123",
                order_id="ord-123",
                amount=Decimal("100.00"),
                status="completed",
                transaction_id="txn-456",
            ),
        )

        self.use_case = OrderFulfillmentUseCase(
            payment_repo=self.mock_payment_repo,
            inventory_repo=self.mock_inventory_repo,
            order_repo=self.mock_order_repo,
            order_request_repo=self.mock_order_request_repo,
            file_storage_repo=self.mock_file_storage_repo,
        )

        self.sample_request = CreateOrderRequest(
            customer_id="cust-123",
            items=[
                OrderItemRequest(
                    product_id="prod-1", quantity=2, price=Decimal("50.00")
                )
            ],
        )

    @pytest.mark.asyncio
    async def test_fulfill_order_inventory_compensation_on_payment_failure(
        self,
    ) -> None:
        """Test that inventory is released when payment fails after
        reservation."""
        # Arrange: Inventory succeeds, payment fails
        self.mock_inventory_repo.reserve_items.return_value = (
            InventoryReservationOutcome(
                status="reserved",
                reserved_items=[
                    InventoryItem(product_id="prod-1", quantity=2, reserved=2)
                ],
            )
        )
        self.mock_payment_repo.process_payment.return_value = PaymentOutcome(
            status="failed", reason="Card declined"
        )

        # Act
        result = await self.use_case.fulfill_order(
            self.sample_request, "req-123"
        )

        # Assert: Compensation was called
        self.mock_inventory_repo.release_items.assert_called_once()
        assert result.status == "PAYMENT_FAILED"
        assert result.reason is not None and "Card declined" in result.reason

        # Verify order was saved with failed status
        save_calls = self.mock_order_repo.save_order.call_args_list
        final_order = save_calls[-1][0][0]
        assert final_order.status == "PAYMENT_FAILED"

    @pytest.mark.asyncio
    async def test_fulfill_order_compensation_failure_is_logged_not_raised(
        self,
    ) -> None:
        """Test that compensation failures are logged but don't prevent error
        response."""
        # Arrange: Payment fails, then compensation fails
        self.mock_payment_repo.process_payment.return_value = PaymentOutcome(
            status="failed", reason="Payment service unavailable"
        )
        self.mock_inventory_repo.release_items.side_effect = Exception(
            "Inventory service down"
        )

        # Act & Assert: Should not raise, should return controlled error
        result = await self.use_case.fulfill_order(
            self.sample_request, "req-123"
        )

        # Assert: Original error preserved, compensation attempted
        assert result.status == "PAYMENT_FAILED"
        assert (
            result.reason is not None
            and "Payment service unavailable" in result.reason
        )
        self.mock_inventory_repo.release_items.assert_called_once()

    @pytest.mark.asyncio
    async def test_fulfill_order_unexpected_exception_triggers_compensation(
        self,
    ) -> None:
        """Test that unexpected exceptions trigger inventory compensation."""
        # Arrange: Inventory reserved, then unexpected error
        self.mock_inventory_repo.reserve_items.return_value = (
            InventoryReservationOutcome(
                status="reserved",
                reserved_items=[
                    InventoryItem(product_id="prod-1", quantity=2, reserved=2)
                ],
            )
        )
        self.mock_payment_repo.process_payment.side_effect = RuntimeError(
            "Database connection lost"
        )

        # Act
        result = await self.use_case.fulfill_order(
            self.sample_request, "req-123"
        )

        # Assert: Compensation attempted, order marked failed
        self.mock_inventory_repo.release_items.assert_called_once()
        assert result.status == "FAILED"
        assert (
            result.reason is not None and "Unexpected error" in result.reason
        )
        assert (
            result.reason is not None
            and "Database connection lost" in result.reason
        )

    @pytest.mark.asyncio
    async def test_fulfill_order_double_failure_scenario(self) -> None:
        """Test behavior when both operation and compensation fail."""
        # Arrange: Payment fails, compensation also fails
        self.mock_payment_repo.process_payment.side_effect = Exception(
            "Payment service down"
        )
        self.mock_inventory_repo.release_items.side_effect = Exception(
            "Inventory service down"
        )

        # Act
        result = await self.use_case.fulfill_order(
            self.sample_request, "req-123"
        )

        # Assert: Should handle gracefully, not crash
        assert result.status == "FAILED"
        assert (
            result.reason is not None and "Unexpected error" in result.reason
        )
        # Should attempt compensation despite failure
        self.mock_inventory_repo.release_items.assert_called_once()

    @pytest.mark.asyncio
    async def test_fulfill_order_persists_state_at_each_step(self) -> None:
        """Test that order state is persisted at each critical step."""
        # Arrange: All operations succeed
        self.mock_inventory_repo.reserve_items.return_value = (
            InventoryReservationOutcome(
                status="reserved",
                reserved_items=[
                    InventoryItem(product_id="prod-1", quantity=2, reserved=2)
                ],
            )
        )
        self.mock_payment_repo.process_payment.return_value = PaymentOutcome(
            status="completed",
            payment=Payment(
                payment_id="pmt-123",
                order_id="ord-123",
                amount=Decimal("100.00"),
                status="completed",
                transaction_id="txn-456",
            ),
        )

        # Act
        await self.use_case.fulfill_order(self.sample_request, "req-123")

        # Assert: Order saved multiple times with correct status progression
        save_calls = self.mock_order_repo.save_order.call_args_list
        assert len(save_calls) >= 2  # Initial + final save

        # Check final order state
        final_order = save_calls[-1][0][0]
        assert final_order.status == "completed"
        assert final_order.order_id == "ord-123"

    @pytest.mark.asyncio
    async def test_fulfill_order_validates_domain_model_creation(
        self,
    ) -> None:
        """Test that invalid order data is caught during domain model
        creation."""
        # Arrange: Create a valid request but mock the order creation to fail
        # This simulates validation failure during Order domain model
        # creation
        valid_request = CreateOrderRequest(
            customer_id="cust-123",
            items=[
                OrderItemRequest(
                    product_id="prod-1", quantity=1, price=Decimal("50.00")
                )
            ],
        )

        # Mock the order repo to simulate validation failure during order
        # creation
        # This could happen if there are additional business rules in Order
        # creation that aren't in the CreateOrderRequest validation
        self.mock_order_repo.generate_order_id.return_value = "ord-123"

        # We'll test by patching the Order constructor to raise a validation
        # error. We need to patch it where it's imported in the usecase module
        import unittest.mock

        with unittest.mock.patch("sample.usecase.Order") as mock_order_class:
            mock_order_class.side_effect = ValueError(
                "Invalid order data: test validation error"
            )

            # Act & Assert: Should raise validation error
            with pytest.raises(ValueError, match="Invalid order data"):
                await self.use_case.fulfill_order(valid_request, "req-123")

            # Assert: No repository operations attempted after validation
            # failure
            self.mock_inventory_repo.reserve_items.assert_not_called()
            self.mock_payment_repo.process_payment.assert_not_called()

    @pytest.mark.asyncio
    async def test_upload_order_attachment_validates_order_ownership(
        self,
    ) -> None:
        """Test that file uploads are properly associated with orders."""
        # Arrange
        expected_metadata = FileMetadata(
            file_id="file-456",
            size_bytes=9,
            content_type="text/plain",
            metadata={"order_id": "ord-123", "type": "invoice"},
        )
        self.mock_file_storage_repo.upload_file.return_value = (
            expected_metadata
        )

        # Act
        result = await self.use_case.upload_order_attachment(
            order_id="ord-123",
            file_id="file-456",
            data=b"test data",
            metadata={"type": "invoice"},
        )

        # Assert: Metadata includes order_id for traceability
        upload_args = self.mock_file_storage_repo.upload_file.call_args[0][0]
        assert upload_args.metadata["order_id"] == "ord-123"
        assert upload_args.metadata["type"] == "invoice"
        assert upload_args.file_id == "file-456"
        assert upload_args.data == b"test data"
        assert result == expected_metadata

    @pytest.mark.asyncio
    async def test_get_order_attachment_metadata_prevents_cross_order_access(
        self,
    ) -> None:
        """Test that users can't access files from other orders."""
        # Arrange: File exists but belongs to different order
        self.mock_file_storage_repo.get_file_metadata.return_value = (
            FileMetadata(
                file_id="file-456",
                size_bytes=100,
                content_type="text/plain",
                metadata={"order_id": "ord-999"},  # Different order
            )
        )

        # Act
        result = await self.use_case.get_order_attachment_metadata(
            "ord-123", "file-456"
        )

        # Assert: Access denied
        assert result is None  # Should not return metadata for wrong order

    @pytest.mark.asyncio
    async def test_get_order_attachment_metadata_allows_correct_order_access(
        self,
    ) -> None:
        """Test that users can access files from their own orders."""
        # Arrange: File exists and belongs to correct order
        expected_metadata = FileMetadata(
            file_id="file-456",
            size_bytes=100,
            content_type="text/plain",
            metadata={"order_id": "ord-123"},  # Correct order
        )
        self.mock_file_storage_repo.get_file_metadata.return_value = (
            expected_metadata
        )

        # Act
        result = await self.use_case.get_order_attachment_metadata(
            "ord-123", "file-456"
        )

        # Assert: Access granted
        assert result == expected_metadata

    @pytest.mark.asyncio
    async def test_file_operations_fail_gracefully_without_storage_repo(
        self,
    ) -> None:
        """Test that file operations fail gracefully when storage repo not
        configured."""
        # Arrange: Use case without file storage repo
        use_case_no_storage = OrderFulfillmentUseCase(
            payment_repo=self.mock_payment_repo,
            inventory_repo=self.mock_inventory_repo,
            order_repo=self.mock_order_repo,
            order_request_repo=self.mock_order_request_repo,
            file_storage_repo=None,  # No file storage
        )

        # Act & Assert: Should raise clear error
        with pytest.raises(
            RuntimeError, match="File storage service is not available"
        ):
            await use_case_no_storage.upload_order_attachment(
                "ord-123", "file-456", b"data", {}
            )

        with pytest.raises(
            RuntimeError, match="File storage service is not available"
        ):
            await use_case_no_storage.download_order_attachment(
                "ord-123", "file-456"
            )

        with pytest.raises(
            RuntimeError, match="File storage service is not available"
        ):
            await use_case_no_storage.get_order_attachment_metadata(
                "ord-123", "file-456"
            )

    @pytest.mark.asyncio
    async def test_upload_order_attachment_repo_raises_exception(
        self,
    ) -> None:
        """Test that upload_order_attachment handles exceptions from repo."""
        # Arrange
        self.mock_file_storage_repo.upload_file.side_effect = RuntimeError(
            "Minio service unavailable"
        )

        # Act & Assert
        with pytest.raises(RuntimeError, match="Minio service unavailable"):
            await self.use_case.upload_order_attachment(
                order_id="ord-123",
                file_id="file-exception",
                data=b"some data",
                metadata={},
            )

        self.mock_file_storage_repo.upload_file.assert_called_once()

    @pytest.mark.asyncio
    async def test_download_order_attachment_repo_raises_exception(
        self,
    ) -> None:
        """Test that download_order_attachment handles exceptions from
        repo.
        """
        # Arrange
        self.mock_file_storage_repo.get_file_metadata.return_value = (
            FileMetadata(
                file_id="file-exception",
                filename="test.txt",
                content_type="text/plain",
                size_bytes=10,
                metadata={"order_id": "ord-123"},
            )
        )
        self.mock_file_storage_repo.download_file.side_effect = RuntimeError(
            "Network error during download"
        )

        # Act & Assert
        with pytest.raises(
            RuntimeError, match="Network error during download"
        ):
            await self.use_case.download_order_attachment(
                "ord-123", "file-exception"
            )

        self.mock_file_storage_repo.download_file.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_order_attachment_metadata_repo_raises_exception(
        self,
    ) -> None:
        """Test that get_order_attachment_metadata handles exceptions from
        repo.
        """
        # Arrange
        self.mock_file_storage_repo.get_file_metadata.side_effect = (
            RuntimeError("Metadata service timeout")
        )

        # Act & Assert
        with pytest.raises(RuntimeError, match="Metadata service timeout"):
            await self.use_case.get_order_attachment_metadata(
                "ord-123", "file-exception"
            )

        self.mock_file_storage_repo.get_file_metadata.assert_called_once()


class TestCancelOrderUseCaseSecurity:
    """Security-focused tests for CancelOrderUseCase."""

    def setup_method(self) -> None:
        """Set up mocks and use case for each test."""
        self.mock_order_repo = AsyncMock(spec=OrderRepository)
        self.mock_payment_repo = AsyncMock(spec=PaymentRepository)
        self.mock_inventory_repo = AsyncMock(spec=InventoryRepository)

        self.cancel_use_case = CancelOrderUseCase(
            order_repo=self.mock_order_repo,
            payment_repo=self.mock_payment_repo,
            inventory_repo=self.mock_inventory_repo,
        )

    @pytest.mark.asyncio
    async def test_cancel_order_refund_status_tracking(self) -> None:
        """Test that refund status is correctly tracked on order object."""
        # Arrange: Order with completed payment
        existing_order = Order(
            order_id="ord-123",
            customer_id="cust-123",
            items=[
                OrderItem(
                    product_id="prod-1", quantity=1, price=Decimal("100.00")
                )
            ],
            total_amount=Decimal("100.00"),
            status="completed",
        )
        self.mock_order_repo.get_order.return_value = existing_order

        completed_payment = Payment(
            payment_id="pmt-or-123",
            order_id="ord-123",
            amount=Decimal("100.00"),
            status="completed",
            transaction_id="txn-456",
        )
        self.mock_payment_repo.get_payment.return_value = completed_payment

        self.mock_payment_repo.refund_payment.return_value = (
            RefundPaymentOutcome(status="refunded", refund_id="ref-123")
        )

        # Act
        result = await self.cancel_use_case.cancel_order(
            "ord-123", "Customer request"
        )

        # Assert: Refund status correctly set on order
        save_calls = self.mock_order_repo.save_order.call_args_list
        saved_order = save_calls[-1][0][0]
        assert saved_order.refund_id == "ref-123"
        assert saved_order.refund_status == "completed"
        assert result.refund_status == "completed"
        assert result.refund_id == "ref-123"

    @pytest.mark.asyncio
    async def test_cancel_order_handles_refund_failure_gracefully(
        self,
    ) -> None:
        """Test that refund failures don't prevent order cancellation."""
        # Arrange: Order with completed payment, but refund fails
        existing_order = Order(
            order_id="ord-123",
            customer_id="cust-123",
            items=[
                OrderItem(
                    product_id="prod-1", quantity=1, price=Decimal("100.00")
                )
            ],
            total_amount=Decimal("100.00"),
            status="completed",
        )
        self.mock_order_repo.get_order.return_value = existing_order

        completed_payment = Payment(
            payment_id="pmt-ord-123",
            order_id="ord-123",
            amount=Decimal("100.00"),
            status="completed",
            transaction_id="txn-456",
        )
        self.mock_payment_repo.get_payment.return_value = completed_payment

        # Refund fails
        self.mock_payment_repo.refund_payment.return_value = (
            RefundPaymentOutcome(
                status="failed", reason="Payment processor unavailable"
            )
        )

        # Act
        result = await self.cancel_use_case.cancel_order(
            "ord-123", "Customer request"
        )

        # Assert: Order still cancelled, refund status tracked
        assert result.status == "CANCELLED"
        save_calls = self.mock_order_repo.save_order.call_args_list
        saved_order = save_calls[-1][0][0]
        assert saved_order.refund_status == "failed"
        assert saved_order.status == "CANCELLED"

    @pytest.mark.asyncio
    async def test_cancel_order_handles_no_payment_scenarios(self) -> None:
        """Test cancellation when no payment exists or payment failed."""
        # Arrange: Order exists but no payment
        existing_order = Order(
            order_id="ord-123",
            customer_id="cust-123",
            items=[
                OrderItem(
                    product_id="prod-1", quantity=1, price=Decimal("100.00")
                )
            ],
            total_amount=Decimal("100.00"),
            status="pending",
        )
        self.mock_order_repo.get_order.return_value = existing_order
        self.mock_payment_repo.get_payment.return_value = None  # No payment

        # Act
        result = await self.cancel_use_case.cancel_order(
            "ord-123", "Customer request"
        )

        # Assert: Order cancelled, refund not applicable
        assert result.status == "CANCELLED"
        save_calls = self.mock_order_repo.save_order.call_args_list
        saved_order = save_calls[-1][0][0]
        assert saved_order.refund_status == "not_applicable"
        assert saved_order.refund_id is None

    @pytest.mark.asyncio
    async def test_cancel_order_unexpected_exception_handling(self) -> None:
        """Test that unexpected exceptions during cancellation are handled
        properly."""
        # Arrange: Order exists
        existing_order = Order(
            order_id="ord-123",
            customer_id="cust-123",
            items=[
                OrderItem(
                    product_id="prod-1", quantity=1, price=Decimal("100.00")
                )
            ],
            total_amount=Decimal("100.00"),
            status="completed",
        )
        self.mock_order_repo.get_order.return_value = existing_order

        # Unexpected exception during inventory release
        self.mock_inventory_repo.release_items.side_effect = RuntimeError(
            "Inventory system crashed"
        )

        # Act
        result = await self.cancel_use_case.cancel_order(
            "ord-123", "Customer request"
        )

        # Assert: Controlled failure response
        assert result.status == "FAILED"
        assert (
            result.reason is not None
            and "Cancellation failed due to unexpected error" in result.reason
        )
        assert (
            result.reason is not None
            and "Inventory system crashed" in result.reason
        )

        # Order should be marked as failed cancellation
        save_calls = self.mock_order_repo.save_order.call_args_list
        saved_order = save_calls[-1][0][0]
        assert saved_order.status == "FAILED_CANCELLATION"

    @pytest.mark.asyncio
    async def test_cancel_order_prevents_double_cancellation(self) -> None:
        """Test that already cancelled orders return current status."""
        # Arrange: Order already cancelled
        cancelled_order = Order(
            order_id="ord-123",
            customer_id="cust-123",
            items=[
                OrderItem(
                    product_id="prod-1", quantity=1, price=Decimal("100.00")
                )
            ],
            total_amount=Decimal("100.00"),
            status="CANCELLED",
            reason="Previously cancelled",
            refund_id="ref-456",
            refund_status="completed",
        )
        self.mock_order_repo.get_order.return_value = cancelled_order

        # Act
        result = await self.cancel_use_case.cancel_order(
            "ord-123", "Duplicate request"
        )

        # Assert: Returns existing status, no additional processing
        assert result.status == "CANCELLED"
        assert result.reason == "Previously cancelled"
        assert result.refund_id == "ref-456"
        assert result.refund_status == "completed"

        # Should not attempt refund or inventory operations
        self.mock_payment_repo.refund_payment.assert_not_called()
        self.mock_inventory_repo.release_items.assert_not_called()

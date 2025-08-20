"""
End-to-end tests that validate repository implementations against their
contracts. These tests use real implementations with actual storage backends.
"""

import pytest
import pytest_asyncio
from decimal import Decimal

from sample.repos.minio.payment import MinioPaymentRepository
from sample.domain import Order, OrderItem


@pytest.mark.e2e
class TestMinioPaymentRepositoryContract:
    """Test MinioPaymentRepository against PaymentRepository protocol."""

    @pytest_asyncio.fixture
    async def payment_repo(self) -> MinioPaymentRepository:
        """Create a MinioPaymentRepository instance for testing."""
        # Use localhost:9000 as per docker-compose.test.yml
        return MinioPaymentRepository(endpoint="localhost:9000")

    @pytest.fixture
    def sample_order(self) -> Order:
        """Create a sample order for testing."""
        return Order(
            order_id="test-order-123",
            customer_id="customer-456",
            items=[
                OrderItem(
                    product_id="product-1", quantity=2, price=Decimal("10.00")
                )
            ],
            total_amount=Decimal("20.00"),
        )

    @pytest.mark.asyncio
    async def test_process_payment_success(
        self, payment_repo: MinioPaymentRepository, sample_order: Order
    ) -> None:
        """Test successful payment processing."""
        outcome = await payment_repo.process_payment(sample_order)

        assert outcome.status == "completed"
        assert outcome.payment is not None
        assert outcome.payment.order_id == sample_order.order_id
        assert outcome.payment.amount == sample_order.total_amount

    @pytest.mark.asyncio
    async def test_get_payment_existing(
        self, payment_repo: MinioPaymentRepository, sample_order: Order
    ) -> None:
        """Test retrieving an existing payment."""
        # First process a payment
        outcome = await payment_repo.process_payment(sample_order)
        assert outcome.payment is not None
        payment_id = outcome.payment.payment_id

        # Then retrieve it
        retrieved_payment = await payment_repo.get_payment(payment_id)

        assert retrieved_payment is not None
        assert retrieved_payment.payment_id == payment_id
        assert retrieved_payment.order_id == sample_order.order_id

    @pytest.mark.asyncio
    async def test_get_payment_nonexistent(
        self, payment_repo: MinioPaymentRepository
    ) -> None:
        """Test retrieving a non-existent payment."""
        payment = await payment_repo.get_payment("nonexistent-payment-id")
        assert payment is None

    @pytest.mark.asyncio
    async def test_payment_repository_idempotency(
        self, payment_repo: MinioPaymentRepository
    ) -> None:
        """Verify payment processing is idempotent"""
        order = Order(
            order_id="test-order-123",
            customer_id="cust123",
            items=[
                OrderItem(
                    product_id="prod1", quantity=1, price=Decimal("50.00")
                )
            ],
            total_amount=Decimal("50.00"),
        )

        # Process same order twice
        payment_outcome1 = await payment_repo.process_payment(order)
        payment_outcome2 = await payment_repo.process_payment(order)

        # Should return identical results
        assert payment_outcome1.status == "completed"
        assert payment_outcome2.status == "completed"
        assert payment_outcome1.payment is not None
        assert payment_outcome2.payment is not None
        assert (
            payment_outcome1.payment.payment_id
            == payment_outcome2.payment.payment_id
        )
        assert (
            payment_outcome1.payment.amount == payment_outcome2.payment.amount
        )
        assert (
            payment_outcome1.payment.order_id
            == payment_outcome2.payment.order_id
        )

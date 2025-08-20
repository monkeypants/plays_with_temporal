import pytest
from decimal import Decimal
from pydantic import ValidationError

from sample.domain import (
    Order,
    OrderItem,
    Payment,
    InventoryItem,
    RefundPaymentArgs,  # Added
    RefundPaymentOutcome,  # Added
)


def test_order_requires_positive_amount() -> None:
    """Business rule: Orders must have positive total amounts"""
    with pytest.raises(
        ValidationError, match="Total amount must be positive"
    ):
        Order(
            order_id="ord123",
            customer_id="cust123",
            items=[
                OrderItem(
                    product_id="prod1", quantity=1, price=Decimal("10.00")
                )
            ],
            total_amount=Decimal("-50.00"),  # Invalid
        )


def test_order_requires_items() -> None:
    """Business rule: Orders must contain at least one item"""
    with pytest.raises(
        ValidationError, match="Order must contain at least one item"
    ):
        Order(
            order_id="ord123",
            customer_id="cust123",
            items=[],  # Invalid - empty list
            total_amount=Decimal("100.00"),
        )


def test_payment_amount_must_be_positive() -> None:
    """Business rule: Payment amounts must be positive"""
    with pytest.raises(ValidationError, match="Amount must be positive"):
        Payment(
            payment_id="pay123",
            order_id="ord123",
            amount=Decimal("-10.00"),  # Invalid
            status="completed",
        )


def test_payment_status_validation() -> None:
    """Business rule: Payment status must be one of the allowed values"""
    # Valid statuses should work
    valid_statuses = [
        "completed",
        "failed",
        "pending",
        "cancelled",
        "refunded",
    ]
    for status in valid_statuses:
        payment = Payment(
            payment_id="pay123",
            order_id="ord123",
            amount=Decimal("100.00"),
            status=status,
        )
        assert payment.status == status

    # Invalid status should fail
    with pytest.raises(ValidationError):
        Payment(
            payment_id="pay123",
            order_id="ord123",
            amount=Decimal("100.00"),
            status="invalid_status",
        )


def test_refund_payment_args_amount_must_be_positive() -> None:
    """Business rule: RefundPaymentArgs amount must be positive."""
    with pytest.raises(ValidationError, match="Amount must be positive"):
        RefundPaymentArgs(
            payment_id="pay123",
            order_id="ord123",
            amount=Decimal("-10.00"),  # Invalid
            reason="test",
        )
    with pytest.raises(ValidationError, match="Amount must be positive"):
        RefundPaymentArgs(
            payment_id="pay123",
            order_id="ord123",
            amount=Decimal("0.00"),  # Invalid
            reason="test",
        )
    # Valid case
    args = RefundPaymentArgs(
        payment_id="pay123", order_id="ord123", amount=Decimal("10.00")
    )
    assert args.amount == Decimal("10.00")


def test_refund_payment_outcome_status_validation() -> None:
    """Business rule: RefundPaymentOutcome status must be one of the allowed
    values."""
    # Valid statuses should work
    valid_statuses = ["refunded", "failed"]
    for status in valid_statuses:
        outcome = RefundPaymentOutcome(status=status)
        assert outcome.status == status

    # Invalid status should fail
    with pytest.raises(ValidationError):
        RefundPaymentOutcome(status="in_progress")


def test_refund_payment_outcome_refund_id_present_if_refunded() -> None:
    """Business rule: refund_id must be present if status is 'refunded'."""
    with pytest.raises(
        ValidationError,
        match="Refund ID must be present if status is 'refunded'",
    ):
        RefundPaymentOutcome(status="refunded", refund_id=None)

    # Valid case
    outcome = RefundPaymentOutcome(status="refunded", refund_id="ref123")
    assert outcome.refund_id == "ref123"

    # Valid for 'failed' status without refund_id
    outcome = RefundPaymentOutcome(status="failed", refund_id=None)
    assert outcome.refund_id is None


def test_order_status_validation() -> None:
    """Business rule: Order status must be one of the allowed values,
    including new cancellation statuses."""
    valid_statuses = [
        "pending",
        "completed",
        "FAILED",
        "PAYMENT_FAILED",
        "CANCELLING",
        "CANCELLED",
        "FAILED_CANCELLATION",
    ]
    for status in valid_statuses:
        order = Order(
            order_id="ord123",
            customer_id="cust123",
            items=[
                OrderItem(
                    product_id="prod1", quantity=1, price=Decimal("10.00")
                )
            ],
            total_amount=Decimal("10.00"),
            status=status,
        )
        assert order.status == status

    with pytest.raises(ValidationError):
        Order(
            order_id="ord123",
            customer_id="cust123",
            items=[
                OrderItem(
                    product_id="prod1", quantity=1, price=Decimal("10.00")
                )
            ],
            total_amount=Decimal("10.00"),
            status="invalid_order_status",
        )


def test_order_refund_status_validation() -> None:
    """Business rule: Order refund_status must be one of the allowed
    values.
    """
    valid_refund_statuses = [
        "completed",
        "failed",
        "pending",
        "not_applicable",
    ]
    for status in valid_refund_statuses:
        order = Order(
            order_id="ord123",
            customer_id="cust123",
            items=[
                OrderItem(
                    product_id="prod1", quantity=1, price=Decimal("10.00")
                )
            ],
            total_amount=Decimal("10.00"),
            refund_status=status,
        )
        assert order.refund_status == status

    with pytest.raises(ValidationError):
        Order(
            order_id="ord123",
            customer_id="cust123",
            items=[
                OrderItem(
                    product_id="prod1", quantity=1, price=Decimal("10.00")
                )
            ],
            total_amount=Decimal("10.00"),
            refund_status="invalid_refund_status",
        )


def test_order_item_quantity_must_be_positive() -> None:
    """Business rule: Order item quantities must be positive"""
    with pytest.raises(ValidationError, match="Quantity must be positive"):
        OrderItem(
            product_id="prod1", quantity=0, price=Decimal("10.00")
        )  # Invalid

    with pytest.raises(ValidationError, match="Quantity must be positive"):
        OrderItem(
            product_id="prod1", quantity=-1, price=Decimal("10.00")
        )  # Invalid


def test_order_item_price_must_be_positive() -> None:
    """Business rule: Order item prices must be positive"""
    with pytest.raises(ValidationError, match="Price must be positive"):
        OrderItem(
            product_id="prod1", quantity=1, price=Decimal("0.00")
        )  # Invalid

    with pytest.raises(ValidationError, match="Price must be positive"):
        OrderItem(
            product_id="prod1", quantity=1, price=Decimal("-5.00")
        )  # Invalid


def test_inventory_item_quantities_must_be_non_negative() -> None:
    """Business rule: Inventory quantities must be non-negative"""
    # Valid non-negative quantities
    item = InventoryItem(product_id="prod1", quantity=0, reserved=0)
    assert item.quantity == 0
    assert item.reserved == 0

    # Invalid negative quantity
    with pytest.raises(
        ValidationError, match="Quantity must be non-negative"
    ):
        InventoryItem(product_id="prod1", quantity=-1, reserved=0)  # Invalid

    # Invalid negative reserved
    with pytest.raises(
        ValidationError, match="Reserved quantity must be non-negative"
    ):
        InventoryItem(product_id="prod1", quantity=10, reserved=-1)  # Invalid


def test_valid_domain_objects_pass_validation() -> None:
    """Verify that valid domain objects pass all validation"""
    # Valid OrderItem
    item = OrderItem(product_id="prod1", quantity=2, price=Decimal("25.50"))
    assert item.product_id == "prod1"
    assert item.quantity == 2
    assert item.price == Decimal("25.50")

    # Valid Order
    order = Order(
        order_id="ord123",
        customer_id="cust123",
        items=[item],
        total_amount=Decimal("51.00"),
    )
    assert order.order_id == "ord123"
    assert len(order.items) == 1
    assert order.total_amount == Decimal("51.00")

    # Valid Payment
    payment = Payment(
        payment_id="pay123",
        order_id="ord123",
        amount=Decimal("51.00"),
        status="completed",
    )
    assert payment.payment_id == "pay123"
    assert payment.status == "completed"

    # Valid InventoryItem
    inventory = InventoryItem(product_id="prod1", quantity=100, reserved=2)
    assert inventory.product_id == "prod1"
    assert inventory.quantity == 100
    assert inventory.reserved == 2

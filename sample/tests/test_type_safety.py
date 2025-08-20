from decimal import Decimal

from sample.domain import Payment, Order, OrderItem


def test_payment_domain_model_guarantees():
    """Verify Payment model enforces required attributes"""
    payment = Payment(
        payment_id="pay123",
        order_id="ord123",
        amount=Decimal("100.00"),
        status="completed",
    )
    # These should never fail if domain model is correct
    assert payment.status == "completed"
    assert payment.payment_id == "pay123"
    assert payment.order_id == "ord123"
    assert payment.amount == Decimal("100.00")
    # No defensive hasattr() checks needed


def test_payment_model_has_all_required_fields():
    """Verify Payment model has all expected fields accessible"""
    payment = Payment(
        payment_id="pay456",
        order_id="ord456",
        amount=Decimal("250.50"),
        status="failed",
        transaction_id="tx789",
    )

    # All fields should be directly accessible
    assert payment.payment_id == "pay456"
    assert payment.order_id == "ord456"
    assert payment.amount == Decimal("250.50")
    assert payment.status == "failed"
    assert payment.transaction_id == "tx789"


def test_order_domain_model_guarantees():
    """Verify Order model enforces required attributes"""
    order = Order(
        order_id="ord123",
        customer_id="cust123",
        items=[
            OrderItem(product_id="prod1", quantity=1, price=Decimal("10.00"))
        ],
        total_amount=Decimal("10.00"),
    )

    # These should never fail if domain model is correct
    assert order.order_id == "ord123"
    assert order.customer_id == "cust123"
    assert len(order.items) == 1
    assert order.total_amount == Decimal("10.00")
    # No defensive hasattr() checks needed


def test_order_item_domain_model_guarantees():
    """Verify OrderItem model enforces required attributes"""
    item = OrderItem(product_id="prod1", quantity=5, price=Decimal("25.99"))

    # These should never fail if domain model is correct
    assert item.product_id == "prod1"
    assert item.quantity == 5
    assert item.price == Decimal("25.99")
    # No defensive hasattr() checks needed


def test_payment_with_optional_transaction_id():
    """Verify Payment model handles optional transaction_id correctly"""
    # Without transaction_id
    payment1 = Payment(
        payment_id="pay123",
        order_id="ord123",
        amount=Decimal("100.00"),
        status="completed",
    )
    assert payment1.transaction_id is None

    # With transaction_id
    payment2 = Payment(
        payment_id="pay456",
        order_id="ord456",
        amount=Decimal("200.00"),
        status="completed",
        transaction_id="tx789",
    )
    assert payment2.transaction_id == "tx789"

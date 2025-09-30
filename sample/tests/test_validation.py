"""
Tests for runtime validation utilities.
"""

import pytest
import warnings
from unittest.mock import MagicMock, patch
from decimal import Decimal
from typing import Generator

from sample.validation import (
    validate_domain_model,
    validate_pydantic_response,
    create_validated_repository_factory,
    RepositoryValidationError,
    DomainValidationError,
    ensure_payment_repository,
)
from sample.repositories import PaymentRepository, InventoryRepository
from sample.repos.minio.inventory import MinioInventoryRepository
from sample.repos.minio.payment import MinioPaymentRepository
from util.temporal.decorators import temporal_activity_registration
from sample.domain import Order, Payment, OrderItem


@pytest.fixture
def temporal_payment_repo() -> Generator[PaymentRepository, None, None]:
    """Fixture that provides a mocked TemporalMinioPaymentRepository."""

    @temporal_activity_registration("sample.payment_repo.minio")
    class TestTemporalMinioPaymentRepository(MinioPaymentRepository):
        pass

    with patch("sample.repos.minio.payment.Minio") as mock_minio:
        mock_client = MagicMock()
        mock_minio.return_value = mock_client
        mock_client.bucket_exists.return_value = True
        yield TestTemporalMinioPaymentRepository("test-endpoint")


def test_ensure_repository_provides_type_safety(
    temporal_payment_repo: PaymentRepository,
) -> None:
    """Test that ensure_* functions provide proper typing"""
    repo = temporal_payment_repo

    # This should pass both runtime and static type checking
    validated_repo = ensure_payment_repository(repo)

    # Type checker knows this is a PaymentRepository
    assert hasattr(validated_repo, "process_payment")
    assert hasattr(validated_repo, "get_payment")


def test_validate_domain_model_success() -> None:
    """Test successful domain model validation"""
    data = {
        "order_id": "ord123",
        "customer_id": "cust123",
        "items": [{"product_id": "prod1", "quantity": 1, "price": "10.00"}],
        "total_amount": "10.00",
    }

    order = validate_domain_model(data, Order)

    assert isinstance(order, Order)
    assert order.order_id == "ord123"
    assert order.customer_id == "cust123"
    assert len(order.items) == 1


def test_validate_domain_model_validation_error() -> None:
    """Test domain model validation with invalid data"""
    data = {
        "order_id": "ord123",
        "customer_id": "cust123",
        "items": [],  # Invalid - empty items list
        "total_amount": "10.00",
    }

    with pytest.raises(
        DomainValidationError, match="Order must contain at least one item"
    ):
        validate_domain_model(data, Order)


def test_validate_domain_model_missing_required_field() -> None:
    """Test domain model validation with missing required field"""
    data = {
        "order_id": "ord123",
        # Missing customer_id
        "items": [{"product_id": "prod1", "quantity": 1, "price": "10.00"}],
        "total_amount": "10.00",
    }

    with pytest.raises(DomainValidationError, match="Field required"):
        validate_domain_model(data, Order)


def test_validate_pydantic_response_success() -> None:
    """Test successful Pydantic response validation"""
    payment = Payment(
        payment_id="pay123",
        order_id="ord123",
        amount=Decimal("100.00"),
        status="completed",
    )

    validated = validate_pydantic_response(payment, Payment)

    assert validated is payment
    assert isinstance(validated, Payment)


def test_validate_pydantic_response_wrong_type() -> None:
    """Test Pydantic response validation with wrong type"""
    wrong_object = "not_a_payment"

    with pytest.raises(
        DomainValidationError, match="Expected Payment, got str"
    ):
        validate_pydantic_response(wrong_object, Payment)


def test_validate_pydantic_response_invalid_state() -> None:
    """Test Pydantic response validation with invalid model state"""
    # Create a payment with valid initial data
    payment = Payment(
        payment_id="pay123",
        order_id="ord123",
        amount=Decimal("100.00"),
        status="completed",
    )

    # Manually corrupt the state (this is artificial but demonstrates the
    # concept)
    # In real scenarios, this might happen due to external state changes
    payment.__dict__["amount"] = "invalid_amount"

    # Suppress the expected Pydantic serialisation warning
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        with pytest.raises(DomainValidationError, match="has invalid state"):
            validate_pydantic_response(payment, Payment)


def test_ensure_payment_repository_success(
    temporal_payment_repo: PaymentRepository,
) -> None:
    """Test convenience function for payment repository validation"""
    repo = temporal_payment_repo

    # Should not raise any exception
    ensure_payment_repository(repo)


def test_ensure_payment_repository_failure() -> None:
    """Test convenience function with invalid payment repository"""
    # Create a mock that's definitely missing required methods
    invalid_repo = MagicMock(spec=[])

    with pytest.raises(RepositoryValidationError):
        ensure_payment_repository(invalid_repo)


def test_inventory_repository_validation() -> None:
    """Test that inventory repository validation works"""

    @temporal_activity_registration("sample.inventory_repo.minio")
    class TestTemporalMinioInventoryRepository(MinioInventoryRepository):
        pass

    with patch("sample.repos.minio.inventory.Minio") as mock_minio:
        mock_client = MagicMock()
        mock_minio.return_value = mock_client
        mock_client.bucket_exists.return_value = True

        repo = TestTemporalMinioInventoryRepository("test-endpoint")

        # Should not raise any exception - verify it's an InventoryRepository
        assert isinstance(repo, InventoryRepository)


def test_factory_function_metadata() -> None:
    """Test that factory function has proper metadata"""

    @temporal_activity_registration("sample.payment_repo.minio")
    class TestTemporalMinioPaymentRepository(MinioPaymentRepository):
        pass

    factory = create_validated_repository_factory(
        PaymentRepository,  # type: ignore[type-abstract]
        TestTemporalMinioPaymentRepository,
    )

    assert (
        factory.__name__
        == "create_validated_TestTemporalMinioPaymentRepository"
    )
    assert (
        factory.__doc__ is not None
        and "TestTemporalMinioPaymentRepository" in factory.__doc__
    )
    assert (
        factory.__doc__ is not None and "PaymentRepository" in factory.__doc__
    )


def test_validation_with_complex_domain_model() -> None:
    """Test validation with complex nested domain model"""
    data = {
        "order_id": "ord123",
        "customer_id": "cust123",
        "items": [
            {"product_id": "prod1", "quantity": 2, "price": "25.50"},
            {"product_id": "prod2", "quantity": 1, "price": "10.00"},
        ],
        "total_amount": "61.00",
    }

    order = validate_domain_model(data, Order)

    assert isinstance(order, Order)
    assert len(order.items) == 2
    assert all(isinstance(item, OrderItem) for item in order.items)
    assert order.items[0].quantity == 2
    assert order.items[1].price == Decimal("10.00")


def test_validation_preserves_pydantic_validation_errors() -> None:
    """Test that validation preserves detailed Pydantic validation errors"""
    data = {
        "order_id": "ord123",
        "customer_id": "cust123",
        "items": [
            {"product_id": "prod1", "quantity": -1, "price": "10.00"}
        ],  # Invalid quantity
        "total_amount": "10.00",
    }

    with pytest.raises(DomainValidationError) as exc_info:
        validate_domain_model(data, Order)

    # Should preserve the original Pydantic validation error details
    assert "Quantity must be positive" in str(exc_info.value)


def test_isinstance_works_with_runtime_checkable(
    temporal_payment_repo: PaymentRepository,
) -> None:
    """Test that isinstance() works directly with @runtime_checkable
    protocols"""
    repo = temporal_payment_repo

    # Direct isinstance check should work
    assert isinstance(repo, PaymentRepository)

    # Cross-protocol checks should fail
    assert not isinstance(repo, InventoryRepository)


def test_runtime_checkable_limitation_with_non_callable() -> None:
    """Test documenting the limitation of @runtime_checkable with
    non-callable attributes"""

    # Create a mock that has the required attributes but they're not callable
    fake_repo = type(
        "FakeRepo",
        (),
        {
            "process_payment": "not_callable",
            "get_payment": "also_not_callable",
            "refund_payment": "yet_another_non_callable",
        },
    )()

    # This passes because @runtime_checkable only checks attribute existence
    assert isinstance(fake_repo, PaymentRepository)

    # But validation still passes (this is the limitation)
    if not isinstance(fake_repo, PaymentRepository):
        raise RepositoryValidationError(
            "Repository does not implement PaymentRepository protocol"
        )

    # The real test would be at runtime when methods are called
    # This demonstrates why integration tests are important

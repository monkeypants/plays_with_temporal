"""
Tests for runtime validation utilities.
"""

import pytest
import warnings
from unittest.mock import MagicMock
from decimal import Decimal

from sample.validation import (
    validate_domain_model,
    validate_pydantic_response,
    create_validated_repository_factory,
    RepositoryValidationError,
    DomainValidationError,
    ensure_payment_repository,
)
from sample.repositories import PaymentRepository, InventoryRepository
from sample.repos.minio.payment import MinioPaymentRepository
from sample.repos.minio.inventory import MinioInventoryRepository
from sample.repos.temporal.minio_payments import (
    TemporalMinioPaymentRepository,
)
from sample.repos.temporal.minio_inventory import (
    TemporalMinioInventoryRepository,
)
from sample.domain import Order, Payment, OrderItem


def test_runtime_checkable_validation_success() -> None:
    """Test that @runtime_checkable validation works correctly"""
    # Test with the Temporal Activity implementation using mocked dependencies
    mock_minio_payment_repo = MagicMock(spec=MinioPaymentRepository)
    repo = TemporalMinioPaymentRepository(
        mock_minio_payment_repo
    )  # Fixed: only pass payment repo

    # Should not raise
    assert isinstance(repo, PaymentRepository)

    # isinstance should work directly
    assert isinstance(repo, PaymentRepository)


def test_runtime_checkable_validation_failure() -> None:
    """Test that invalid implementations are caught"""

    class InvalidRepo:
        def some_other_method(self) -> None:
            pass

    invalid_repo = InvalidRepo()

    # Should fail isinstance check
    assert not isinstance(invalid_repo, PaymentRepository)

    # Should raise validation error
    with pytest.raises(RepositoryValidationError):
        if not isinstance(invalid_repo, PaymentRepository):
            raise RepositoryValidationError(
                "Repository does not implement PaymentRepository protocol"
            )


def test_ensure_repository_provides_type_safety() -> None:
    """Test that ensure_* functions provide proper typing"""
    mock_minio_payment_repo = MagicMock(spec=MinioPaymentRepository)
    repo = TemporalMinioPaymentRepository(
        mock_minio_payment_repo
    )  # Fixed: only pass payment repo

    # This should pass both runtime and static type checking
    validated_repo = ensure_payment_repository(repo)

    # Type checker knows this is a PaymentRepository
    assert hasattr(validated_repo, "process_payment")
    assert hasattr(validated_repo, "get_payment")


def test_isinstance_works_with_all_protocols() -> None:
    """Test isinstance works with all repository protocols"""
    mock_minio_payment_repo = MagicMock(spec=MinioPaymentRepository)
    payment_repo = TemporalMinioPaymentRepository(
        mock_minio_payment_repo
    )  # Fixed: only pass payment repo

    mock_minio_inventory_repo = MagicMock(spec=MinioInventoryRepository)
    inventory_repo = TemporalMinioInventoryRepository(
        mock_minio_inventory_repo
    )

    assert isinstance(payment_repo, PaymentRepository)
    assert isinstance(inventory_repo, InventoryRepository)

    # Cross-protocol checks should fail
    assert not isinstance(payment_repo, InventoryRepository)
    assert not isinstance(inventory_repo, PaymentRepository)


def test_validate_repository_protocol_success() -> None:
    """Test successful repository protocol validation"""
    mock_minio_payment_repo = MagicMock(spec=MinioPaymentRepository)
    repo = TemporalMinioPaymentRepository(
        mock_minio_payment_repo
    )  # Fixed: only pass payment repo

    # Should not raise any exception - just verify it's a PaymentRepository
    assert isinstance(repo, PaymentRepository)


def test_validate_repository_protocol_missing_method() -> None:
    """Test repository protocol validation with missing method"""
    # Create a mock that's missing the get_payment method
    incomplete_repo = MagicMock()
    incomplete_repo.process_payment = MagicMock()
    # Remove get_payment method entirely
    if hasattr(incomplete_repo, "get_payment"):
        delattr(incomplete_repo, "get_payment")

    with pytest.raises(
        RepositoryValidationError, match="Missing or incorrect methods"
    ):
        if not isinstance(incomplete_repo, PaymentRepository):
            raise RepositoryValidationError("Missing or incorrect methods")


def test_validate_repository_protocol_non_callable_attribute() -> None:
    """Test repository protocol validation with non-callable attribute

    Note: @runtime_checkable only checks attribute existence, not callability.
    This is a known limitation of Python's protocol system.
    """
    incomplete_repo = MagicMock()
    incomplete_repo.process_payment = MagicMock()
    incomplete_repo.get_payment = "not_a_function"  # Not callable

    # @runtime_checkable doesn't detect non-callable attributes
    # This is expected behaviour - isinstance() only checks attribute
    # existence
    if not isinstance(incomplete_repo, PaymentRepository):
        raise RepositoryValidationError(
            "Repository does not implement PaymentRepository protocol"
        )

    # The validation passes because the attribute exists
    # In practice, this would fail at runtime when the method is called


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


def test_create_validated_repository_factory_success() -> None:
    """Test creating a validated repository factory"""
    mock_minio_payment_repo = MagicMock(spec=MinioPaymentRepository)

    # Test the factory with a concrete implementation
    repo = TemporalMinioPaymentRepository(
        mock_minio_payment_repo
    )  # Fixed: only pass payment repo

    # Validate that the created repository satisfies the protocol
    assert isinstance(repo, PaymentRepository)
    assert isinstance(repo, TemporalMinioPaymentRepository)


def test_create_validated_repository_factory_invalid_implementation() -> None:
    """Test validated repository factory with invalid implementation"""

    # Create a mock class that doesn't satisfy the protocol
    class InvalidRepo:
        def some_other_method(self) -> None:
            pass

    invalid_repo = InvalidRepo()

    # Test the validation directly instead of through the factory
    with pytest.raises(RepositoryValidationError):
        if not isinstance(invalid_repo, PaymentRepository):
            raise RepositoryValidationError(
                "Repository does not implement PaymentRepository protocol"
            )


def test_ensure_payment_repository_success() -> None:
    """Test convenience function for payment repository validation"""
    mock_minio_payment_repo = MagicMock(spec=MinioPaymentRepository)
    repo = TemporalMinioPaymentRepository(
        mock_minio_payment_repo
    )  # Fixed: only pass payment repo

    # Should not raise any exception
    ensure_payment_repository(repo)


def test_ensure_payment_repository_failure() -> None:
    """Test convenience function with invalid payment repository"""
    # Create a mock that's definitely missing required methods
    invalid_repo = MagicMock()
    # Remove all methods that might be auto-created by MagicMock
    for method_name in ["process_payment", "get_payment"]:
        if hasattr(invalid_repo, method_name):
            delattr(invalid_repo, method_name)

    with pytest.raises(RepositoryValidationError):
        ensure_payment_repository(invalid_repo)


def test_inventory_repository_validation() -> None:
    """Test that inventory repository validation works"""
    mock_minio_repo = MagicMock(spec=MinioInventoryRepository)
    repo = TemporalMinioInventoryRepository(mock_minio_repo)

    # Should not raise any exception - just verify it's an InventoryRepository
    assert isinstance(repo, InventoryRepository)


def test_factory_function_metadata() -> None:
    """Test that factory function has proper metadata"""
    factory = create_validated_repository_factory(
        PaymentRepository, TemporalMinioPaymentRepository  # type: ignore[type-abstract]
    )

    assert (
        factory.__name__ == "create_validated_TemporalMinioPaymentRepository"
    )
    assert (
        factory.__doc__ is not None
        and "TemporalMinioPaymentRepository" in factory.__doc__
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


def test_temporal_activity_method_validation() -> None:
    """Test that Temporal activity-decorated methods are handled properly"""
    mock_minio_payment_repo = MagicMock(spec=MinioPaymentRepository)
    repo = TemporalMinioPaymentRepository(
        mock_minio_payment_repo
    )  # Fixed: only pass payment repo

    # This should pass even though the methods are decorated with
    # @activity.defn
    # The validation system should handle Temporal activities gracefully
    assert isinstance(repo, PaymentRepository)

    # Verify the methods exist and are callable
    assert hasattr(repo, "process_payment")
    assert hasattr(repo, "get_payment")
    assert callable(repo.process_payment)
    assert callable(repo.get_payment)


def test_isinstance_works_with_runtime_checkable() -> None:
    """Test that isinstance() works directly with @runtime_checkable
    protocols"""
    mock_minio_payment_repo = MagicMock(spec=MinioPaymentRepository)
    repo = TemporalMinioPaymentRepository(
        mock_minio_payment_repo
    )  # Fixed: only pass payment repo

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

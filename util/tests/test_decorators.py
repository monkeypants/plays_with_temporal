"""
Tests for the temporal_repository decorator.

This module tests the decorator in isolation to ensure it properly wraps
async methods as Temporal activities without depending on the existing
repository implementations.
"""

from unittest.mock import patch
from typing import Any, Optional

from temporalio import activity

from util.repos.temporal.decorators import temporal_repository


class MockBaseRepository:
    """Mock base repository class for testing inheritance."""

    async def base_async_method(self, arg1: str) -> str:
        """Base async method that should be wrapped."""
        return f"base_result_{arg1}"

    def base_sync_method(self, arg1: str) -> str:
        """Base sync method that should NOT be wrapped."""
        return f"base_sync_{arg1}"

    async def _private_async_method(self, arg1: str) -> str:
        """Private async method that should NOT be wrapped."""
        return f"private_{arg1}"


class MockRepository(MockBaseRepository):
    """Mock repository class for testing the decorator."""

    async def process_payment(self, order_id: str, amount: float) -> dict:
        """Mock payment processing method."""
        return {"status": "success", "order_id": order_id, "amount": amount}

    async def get_payment(self, payment_id: str) -> Optional[dict]:
        """Mock get payment method."""
        if payment_id == "not_found":
            return None
        return {"payment_id": payment_id, "status": "completed"}

    async def refund_payment(self, payment_id: str) -> dict:
        """Mock refund payment method."""
        return {"status": "refunded", "payment_id": payment_id}

    def sync_method(self, value: str) -> str:
        """Sync method that should NOT be wrapped."""
        return f"sync_{value}"

    async def _private_method(self, value: str) -> str:
        """Private async method that should NOT be wrapped."""
        return f"private_{value}"


def test_decorator_wraps_public_async_methods() -> None:
    """Test decorator wraps all public async methods as activities."""

    @temporal_repository("test.repo")
    class DecoratedRepository(MockRepository):
        pass

    # Check that async methods are wrapped with activity decorator
    # Use dir() check since hasattr() doesn't work with Temporal activities
    assert "__temporal_activity_definition" in dir(
        DecoratedRepository.process_payment
    )
    assert "__temporal_activity_definition" in dir(
        DecoratedRepository.get_payment
    )
    assert "__temporal_activity_definition" in dir(
        DecoratedRepository.refund_payment
    )
    assert "__temporal_activity_definition" in dir(
        DecoratedRepository.base_async_method
    )

    # Check activity names by accessing the attribute directly
    process_payment_attrs = {
        attr: getattr(DecoratedRepository.process_payment, attr, None)
        for attr in dir(DecoratedRepository.process_payment)
        if attr == "__temporal_activity_definition"
    }
    get_payment_attrs = {
        attr: getattr(DecoratedRepository.get_payment, attr, None)
        for attr in dir(DecoratedRepository.get_payment)
        if attr == "__temporal_activity_definition"
    }
    refund_payment_attrs = {
        attr: getattr(DecoratedRepository.refund_payment, attr, None)
        for attr in dir(DecoratedRepository.refund_payment)
        if attr == "__temporal_activity_definition"
    }
    base_async_attrs = {
        attr: getattr(DecoratedRepository.base_async_method, attr, None)
        for attr in dir(DecoratedRepository.base_async_method)
        if attr == "__temporal_activity_definition"
    }

    # Verify the attributes exist and have the expected names
    assert process_payment_attrs
    assert get_payment_attrs
    assert refund_payment_attrs
    assert base_async_attrs


def test_decorator_does_not_wrap_sync_methods() -> None:
    """Test that sync methods are not wrapped as activities."""

    @temporal_repository("test.repo")
    class DecoratedRepository(MockRepository):
        pass

    # Check that sync methods are NOT wrapped
    assert "__temporal_activity_definition" not in dir(
        DecoratedRepository.sync_method
    )
    assert "__temporal_activity_definition" not in dir(
        DecoratedRepository.base_sync_method
    )


def test_decorator_does_not_wrap_private_methods() -> None:
    """Test that private async methods are not wrapped as activities."""

    @temporal_repository("test.repo")
    class DecoratedRepository(MockRepository):
        pass

    # Check that private async methods are NOT wrapped
    assert "__temporal_activity_definition" not in dir(
        DecoratedRepository._private_method
    )
    assert "__temporal_activity_definition" not in dir(
        DecoratedRepository._private_async_method
    )


def test_decorated_methods_preserve_functionality() -> None:
    """Test that decorated methods still work as expected."""

    @temporal_repository("test.repo")
    class DecoratedRepository(MockRepository):
        pass

    repo = DecoratedRepository()

    # Test sync method works normally
    result = repo.sync_method("test")
    assert result == "sync_test"

    # Test private method works normally
    async def test_private() -> None:
        result = await repo._private_method("test")
        assert result == "private_test"

    import asyncio

    asyncio.run(test_private())


def test_decorated_methods_preserve_metadata() -> None:
    """Test that decorated methods preserve original method metadata."""

    @temporal_repository("test.repo")
    class DecoratedRepository(MockRepository):
        pass

    repo = DecoratedRepository()

    # Check that method names are preserved
    assert repo.process_payment.__name__ == "process_payment"
    assert repo.get_payment.__name__ == "get_payment"
    assert repo.refund_payment.__name__ == "refund_payment"

    # Check that docstrings are preserved
    assert "Mock payment processing method" in (
        repo.process_payment.__doc__ or ""
    )
    assert "Mock get payment method" in (repo.get_payment.__doc__ or "")
    assert "Mock refund payment method" in (repo.refund_payment.__doc__ or "")


def test_activity_names_with_different_prefixes() -> None:
    """Test different prefixes generate different activity names."""

    captured_activity_names = []
    original_activity_defn = activity.defn

    def mock_activity_defn(name: Optional[str] = None, **kwargs: Any) -> Any:
        """Mock activity.defn to capture the activity names being created."""
        if name:
            captured_activity_names.append(name)
        return original_activity_defn(name=name, **kwargs)

    with patch(
        "util.repos.temporal.decorators.activity.defn",
        side_effect=mock_activity_defn,
    ):

        @temporal_repository("test.payment_service")
        class PaymentServiceRepo(MockRepository):
            pass

        @temporal_repository("test.inventory_service")
        class InventoryServiceRepo(MockRepository):
            pass

    # Verify that activity names were captured with the correct prefixes
    payment_activities = [
        name
        for name in captured_activity_names
        if name.startswith("test.payment_service")
    ]
    inventory_activities = [
        name
        for name in captured_activity_names
        if name.startswith("test.inventory_service")
    ]

    # Should have created activities for each async method
    expected_payment_activities = {
        "test.payment_service.process_payment",
        "test.payment_service.get_payment",
        "test.payment_service.refund_payment",
        "test.payment_service.base_async_method",
    }
    expected_inventory_activities = {
        "test.inventory_service.process_payment",
        "test.inventory_service.get_payment",
        "test.inventory_service.refund_payment",
        "test.inventory_service.base_async_method",
    }

    assert set(payment_activities) == expected_payment_activities
    assert set(inventory_activities) == expected_inventory_activities

    # Verify no activity names overlap between the two services
    assert not set(payment_activities).intersection(set(inventory_activities))


def test_decorator_handles_inheritance_correctly() -> None:
    """Test that the decorator properly handles method resolution order."""

    class ChildRepository(MockRepository):
        async def child_method(self, value: str) -> str:
            """Child-specific method."""
            return f"child_{value}"

        async def process_payment(self, order_id: str, amount: float) -> dict:
            """Override parent method."""
            return {
                "status": "child_success",
                "order_id": order_id,
                "amount": amount,
            }

    @temporal_repository("test.child")
    class DecoratedChildRepository(ChildRepository):
        pass

    # Check that all async methods are wrapped, including inherited ones
    assert "__temporal_activity_definition" in dir(
        DecoratedChildRepository.child_method
    )
    assert "__temporal_activity_definition" in dir(
        DecoratedChildRepository.process_payment
    )
    assert "__temporal_activity_definition" in dir(
        DecoratedChildRepository.base_async_method
    )


def test_decorator_logs_wrapped_methods() -> None:
    """Test that the decorator logs which methods it wraps."""

    with patch("util.repos.temporal.decorators.logger") as mock_logger:

        @temporal_repository("test.logging")
        class DecoratedRepository(MockRepository):
            pass

        # Check that debug logs were called for each method
        mock_logger.debug.assert_called()
        mock_logger.info.assert_called_once()

        # Check that the info log contains the expected information
        info_call = mock_logger.info.call_args
        assert "Temporal repository decorator applied" in info_call[0][0]
        assert "DecoratedRepository" in info_call[0][0]


def test_empty_class_decorator() -> None:
    """Test decorator behavior with a class that has no async methods."""

    class EmptyRepository:
        def sync_only(self, value: str) -> str:
            return f"sync_{value}"

    @temporal_repository("test.empty")
    class DecoratedEmptyRepository(EmptyRepository):
        pass

    # Should still work, just no methods wrapped
    assert "__temporal_activity_definition" not in dir(
        DecoratedEmptyRepository.sync_only
    )


def test_decorator_type_preservation() -> None:
    """Test decorator preserves class type for isinstance checks."""

    @temporal_repository("test.types")
    class DecoratedRepository(MockRepository):
        pass

    repo = DecoratedRepository()

    # Check that isinstance still works
    assert isinstance(repo, DecoratedRepository)
    assert isinstance(repo, MockRepository)
    assert isinstance(repo, MockBaseRepository)


def test_multiple_decorations() -> None:
    """Test repository can be decorated multiple times with prefixes."""

    @temporal_repository("test.first")
    class FirstDecoration(MockRepository):
        pass

    @temporal_repository("test.second")
    class SecondDecoration(MockRepository):
        pass

    # Check that each has different activity names
    assert "__temporal_activity_definition" in dir(
        FirstDecoration.process_payment
    )
    assert "__temporal_activity_definition" in dir(
        SecondDecoration.process_payment
    )

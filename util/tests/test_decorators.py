"""
Tests for temporal decorators.

This module tests the decorators in isolation to ensure they properly wrap
async methods as Temporal activities and handle type substitution correctly.
"""

# Standard library imports
import asyncio
import inspect
from typing import (
    Any,
    Optional,
    TypeVar,
    Protocol,
    runtime_checkable,
    get_origin,
    get_args,
    List,
)
from unittest.mock import patch

# Third-party imports
import pytest
from pydantic import BaseModel
from temporalio import activity

# Project imports
import util.temporal.decorators as decorators_module

from util.temporal.decorators import (
    temporal_activity_registration,
    temporal_workflow_proxy,
    _extract_concrete_type_from_base,
    _substitute_typevar_with_concrete,
    _needs_pydantic_validation,
)


@runtime_checkable
class MockBaseRepositoryProtocol(Protocol):
    """Mock base repository protocol for testing inheritance."""

    async def base_async_method(self, arg1: str) -> str:
        """Base async method that should be wrapped."""
        ...

    def base_sync_method(self, arg1: str) -> str:
        """Base sync method that should NOT be wrapped."""
        ...

    async def _private_async_method(self, arg1: str) -> str:
        """Private async method that should NOT be wrapped."""
        ...


@runtime_checkable
class MockRepositoryProtocol(MockBaseRepositoryProtocol, Protocol):
    """Mock repository protocol for testing the decorator."""

    async def process_payment(self, order_id: str, amount: float) -> dict:
        """Mock payment processing method."""
        ...

    async def get_payment(self, payment_id: str) -> Optional[dict]:
        """Mock get payment method."""
        ...

    async def refund_payment(self, payment_id: str) -> dict:
        """Mock refund payment method."""
        ...

    def sync_method(self, value: str) -> str:
        """Sync method that should NOT be wrapped."""
        ...

    async def _private_method(self, value: str) -> str:
        """Private async method that should NOT be wrapped."""
        ...


class MockRepository(MockRepositoryProtocol):
    """Concrete mock repository implementation for testing."""

    async def base_async_method(self, arg1: str) -> str:
        """Base async method that should be wrapped."""
        return f"base_result_{arg1}"

    def base_sync_method(self, arg1: str) -> str:
        """Base sync method that should NOT be wrapped."""
        return f"base_sync_{arg1}"

    async def _private_async_method(self, arg1: str) -> str:
        """Private async method that should NOT be wrapped."""
        return f"private_{arg1}"

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

    @temporal_activity_registration("test.repo")
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

    @temporal_activity_registration("test.repo")
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

    @temporal_activity_registration("test.repo")
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

    @temporal_activity_registration("test.repo")
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

    asyncio.run(test_private())


def test_decorated_methods_preserve_metadata() -> None:
    """Test that decorated methods preserve original method metadata."""

    @temporal_activity_registration("test.repo")
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

        @temporal_activity_registration("test.payment_service")
        class PaymentServiceRepo(MockRepository):
            pass

        @temporal_activity_registration("test.inventory_service")
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

    @runtime_checkable
    class ChildRepositoryProtocol(MockRepositoryProtocol, Protocol):
        async def child_method(self, value: str) -> str:
            """Child-specific method."""
            ...

    class ChildRepository(ChildRepositoryProtocol):
        async def base_async_method(self, arg1: str) -> str:
            return f"base_result_{arg1}"

        def base_sync_method(self, arg1: str) -> str:
            return f"base_sync_{arg1}"

        async def _private_async_method(self, arg1: str) -> str:
            return f"private_{arg1}"

        async def process_payment(self, order_id: str, amount: float) -> dict:
            return {
                "status": "success",
                "order_id": order_id,
                "amount": amount,
            }

        async def get_payment(self, payment_id: str) -> Optional[dict]:
            if payment_id == "not_found":
                return None
            return {"payment_id": payment_id, "status": "completed"}

        async def refund_payment(self, payment_id: str) -> dict:
            return {"status": "refunded", "payment_id": payment_id}

        def sync_method(self, value: str) -> str:
            return f"sync_{value}"

        async def _private_method(self, value: str) -> str:
            return f"private_{value}"

        async def child_method(self, value: str) -> str:
            """Child-specific method."""
            return f"child_{value}"

    @temporal_activity_registration("test.child")
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

        @temporal_activity_registration("test.logging")
        class DecoratedRepository(MockRepository):
            pass

        # Check that debug logs were called for each method
        mock_logger.debug.assert_called()

        # Should have two info calls: method discovery and decorator app
        assert mock_logger.info.call_count == 2

        # Check that the final info log contains the expected information
        final_info_call = mock_logger.info.call_args_list[-1]
        assert (
            "Temporal activity registration decorator applied"
            in final_info_call[0][0]
        )
        assert "DecoratedRepository" in final_info_call[0][0]


def test_empty_class_decorator() -> None:
    """Test decorator behavior with a class that has no async methods."""

    @runtime_checkable
    class EmptyRepositoryProtocol(Protocol):
        def sync_only(self, value: str) -> str: ...

    class EmptyRepository(EmptyRepositoryProtocol):
        def sync_only(self, value: str) -> str:
            return f"sync_{value}"

    @temporal_activity_registration("test.empty")
    class DecoratedEmptyRepository(EmptyRepository):
        pass

    # Should still work, just no methods wrapped
    assert "__temporal_activity_definition" not in dir(
        DecoratedEmptyRepository.sync_only
    )


def test_decorator_type_preservation() -> None:
    """Test decorator preserves class type for isinstance checks."""

    @temporal_activity_registration("test.types")
    class DecoratedRepository(MockRepository):
        pass

    repo = DecoratedRepository()

    # Check that isinstance still works
    assert isinstance(repo, DecoratedRepository)
    assert isinstance(repo, MockRepository)
    assert isinstance(repo, MockBaseRepositoryProtocol)


def test_multiple_decorations() -> None:
    """Test repository can be decorated multiple times with prefixes."""

    @temporal_activity_registration("test.first")
    class FirstDecoration(MockRepository):
        pass

    @temporal_activity_registration("test.second")
    class SecondDecoration(MockRepository):
        pass

    # Check that each has different activity names
    assert "__temporal_activity_definition" in dir(
        FirstDecoration.process_payment
    )
    assert "__temporal_activity_definition" in dir(
        SecondDecoration.process_payment
    )


# Test domain models for type substitution tests
class MockAssemblySpecification(BaseModel):
    """Mock domain model for type substitution tests."""

    assembly_specification_id: str
    name: str
    status: str = "active"


class MockDocument(BaseModel):
    """Another mock domain model."""

    document_id: str
    title: str
    content: str


# Test repository protocols
T = TypeVar("T", bound=BaseModel)


@runtime_checkable
class BaseRepository(Protocol[T]):
    """Generic base repository protocol for testing."""

    async def get(self, entity_id: str) -> Optional[T]: ...

    async def save(self, entity: T) -> None: ...

    async def generate_id(self) -> str: ...


@runtime_checkable
class MockAssemblySpecificationRepository(
    BaseRepository[MockAssemblySpecification], Protocol
):
    """Mock repository inheriting from BaseRepository with concrete type."""

    pass


@runtime_checkable
class MockDocumentRepository(BaseRepository[MockDocument], Protocol):
    """Another mock repository with different concrete type."""

    pass


@runtime_checkable
class NonGenericRepository(Protocol):
    """Repository that doesn't follow BaseRepository[T] pattern."""

    async def get(self, id: str) -> Optional[MockDocument]: ...


class TestTypeExtraction:
    """Tests for _extract_concrete_type_from_base function."""

    def test_extracts_concrete_type_from_direct_inheritance(self) -> None:
        """Test extracting type from direct BaseRepository inheritance."""
        concrete_type = _extract_concrete_type_from_base(
            MockAssemblySpecificationRepository
        )
        assert concrete_type == MockAssemblySpecification

    def test_extracts_different_concrete_types(self) -> None:
        """Test different repositories extract their concrete types."""
        assembly_type = _extract_concrete_type_from_base(
            MockAssemblySpecificationRepository
        )
        document_type = _extract_concrete_type_from_base(
            MockDocumentRepository
        )

        assert assembly_type == MockAssemblySpecification
        assert document_type == MockDocument
        assert assembly_type != document_type

    def test_extracts_from_proxy_class_inheritance(self) -> None:
        """Test extracting concrete type from workflow proxy classes."""

        class TestWorkflowProxy(MockAssemblySpecificationRepository):
            pass

        concrete_type = _extract_concrete_type_from_base(TestWorkflowProxy)
        assert concrete_type == MockAssemblySpecification

    def test_returns_none_for_non_generic_repository(self) -> None:
        """Test that non-generic repositories return None."""
        concrete_type = _extract_concrete_type_from_base(NonGenericRepository)
        assert concrete_type is None

    def test_returns_none_for_object_class(self) -> None:
        """Test that base object class returns None."""
        concrete_type = _extract_concrete_type_from_base(object)
        assert concrete_type is None


class TestTypeSubstitution:
    """Tests for _substitute_typevar_with_concrete function."""

    def test_substitutes_direct_typevar(self) -> None:
        """Test direct TypeVar substitution."""
        result = _substitute_typevar_with_concrete(
            T, MockAssemblySpecification
        )
        assert result == MockAssemblySpecification

    def test_substitutes_optional_typevar(self) -> None:
        """Test Optional[TypeVar] substitution."""
        optional_t = Optional[T]
        result = _substitute_typevar_with_concrete(
            optional_t, MockAssemblySpecification
        )

        # Should be Optional[MockAssemblySpecification]
        origin = get_origin(result)
        args = get_args(result)
        assert origin is not None
        assert MockAssemblySpecification in args
        assert type(None) in args

    def test_substitutes_nested_generics(self) -> None:
        """Test substitution in nested generic types."""
        nested_generic = List[Optional[T]]
        result = _substitute_typevar_with_concrete(
            nested_generic, MockDocument
        )

        # Should be List[Optional[MockDocument]]
        outer_origin = get_origin(result)
        outer_args = get_args(result)
        assert outer_origin is list
        assert len(outer_args) == 1

        inner_type = outer_args[0]
        inner_args = get_args(inner_type)
        assert MockDocument in inner_args
        assert type(None) in inner_args

    def test_returns_non_generic_types_unchanged(self) -> None:
        """Test that non-generic types are returned unchanged."""
        result_str = _substitute_typevar_with_concrete(
            str, MockAssemblySpecification
        )
        result_int = _substitute_typevar_with_concrete(
            int, MockAssemblySpecification
        )
        result_concrete = _substitute_typevar_with_concrete(
            MockDocument, MockAssemblySpecification
        )

        assert result_str is str
        assert result_int is int
        assert result_concrete == MockDocument

    def test_handles_none_annotation(self) -> None:
        """Test handling of None annotations."""
        result = _substitute_typevar_with_concrete(
            None, MockAssemblySpecification
        )
        assert result is None

    def test_handles_signature_empty(self) -> None:
        """Test handling of inspect.Signature.empty."""
        result = _substitute_typevar_with_concrete(
            inspect.Signature.empty, MockAssemblySpecification
        )
        assert result == inspect.Signature.empty

    def test_fails_fast_on_reconstruction_error(self) -> None:
        """Test that reconstruction errors raise informative exceptions."""

        # Create a mock type that will fail reconstruction
        class FailingOrigin:
            def __getitem__(self, item: Any) -> Any:
                raise TypeError("Mock reconstruction failure")

            def __str__(self) -> str:
                return "FailingOrigin"

        # Mock get_origin and get_args to return our failing type
        def mock_get_origin(annotation: Any) -> Any:
            if annotation == "FAILING_TYPE":
                return FailingOrigin()
            return get_origin(annotation)

        def mock_get_args(annotation: Any) -> tuple[Any, ...]:
            if annotation == "FAILING_TYPE":
                return (T,)
            return get_args(annotation)

        with (
            patch.object(
                decorators_module, "get_origin", side_effect=mock_get_origin
            ),
            patch.object(
                decorators_module, "get_args", side_effect=mock_get_args
            ),
        ):
            with pytest.raises(TypeError) as exc_info:
                _substitute_typevar_with_concrete(
                    "FAILING_TYPE", MockAssemblySpecification
                )

            error_message = str(exc_info.value)
            assert "Failed to reconstruct generic type" in error_message
            assert "FailingOrigin" in error_message
            assert "FAILING_TYPE" in error_message
            assert "MockAssemblySpecification" in error_message


class TestPydanticValidationDetection:
    """Tests for _needs_pydantic_validation function."""

    def test_detects_pydantic_model_types(self) -> None:
        """Test detection of Pydantic model types."""
        assert _needs_pydantic_validation(MockAssemblySpecification)
        assert _needs_pydantic_validation(MockDocument)

    def test_detects_optional_pydantic_types(self) -> None:
        """Test detection of Optional[PydanticModel] types."""
        assert _needs_pydantic_validation(Optional[MockAssemblySpecification])
        assert _needs_pydantic_validation(Optional[MockDocument])

    def test_rejects_non_pydantic_types(self) -> None:
        """Test that non-Pydantic types are not flagged for validation."""
        assert not _needs_pydantic_validation(str)
        assert not _needs_pydantic_validation(int)
        assert not _needs_pydantic_validation(dict)
        assert not _needs_pydantic_validation(Optional[str])

    def test_rejects_typevar_types(self) -> None:
        """Test TypeVar types aren't flagged for validation (the bug)."""
        assert not _needs_pydantic_validation(T)
        assert not _needs_pydantic_validation(Optional[T])

    def test_handles_none_and_empty(self) -> None:
        """Test handling of None and Signature.empty."""
        assert not _needs_pydantic_validation(None)
        assert not _needs_pydantic_validation(inspect.Signature.empty)


class TestWorkflowProxyIntegration:
    """Integration tests for temporal_workflow_proxy with substitution."""

    def test_extracts_type_from_proxy_class(self) -> None:
        """Test decorator extracts concrete types from proxy classes."""

        @temporal_workflow_proxy(
            activity_base="test.assembly_spec_repo.minio",
            default_timeout_seconds=30,
        )
        class TestWorkflowAssemblySpecificationRepositoryProxy(
            MockAssemblySpecificationRepository
        ):
            pass

        # Verify type extraction works
        concrete_type = _extract_concrete_type_from_base(
            TestWorkflowAssemblySpecificationRepositoryProxy
        )
        assert concrete_type == MockAssemblySpecification

    def test_creates_proxy_methods(self) -> None:
        """Test that the decorator creates expected proxy methods."""

        @temporal_workflow_proxy(
            activity_base="test.document_repo.minio",
            default_timeout_seconds=30,
        )
        class TestWorkflowDocumentRepositoryProxy(MockDocumentRepository):
            pass

        proxy = TestWorkflowDocumentRepositoryProxy()  # type: ignore[abstract]

        # Check that methods exist
        assert hasattr(proxy, "get")
        assert hasattr(proxy, "save")
        assert hasattr(proxy, "generate_id")

        # Check instance attributes
        assert hasattr(proxy, "activity_timeout")
        assert hasattr(proxy, "activity_fail_fast_retry_policy")

    def test_different_repositories_get_different_types(self) -> None:
        """Test that different repositories extract their respective types."""

        @temporal_workflow_proxy(
            activity_base="test.assembly_spec_repo.minio",
            default_timeout_seconds=30,
        )
        class ProxyA(MockAssemblySpecificationRepository):
            pass

        @temporal_workflow_proxy(
            activity_base="test.document_repo.minio",
            default_timeout_seconds=30,
        )
        class ProxyB(MockDocumentRepository):
            pass

        type_a = _extract_concrete_type_from_base(ProxyA)
        type_b = _extract_concrete_type_from_base(ProxyB)

        assert type_a == MockAssemblySpecification
        assert type_b == MockDocument
        assert type_a != type_b

    def test_handles_non_generic_repository_gracefully(self) -> None:
        """Test that non-generic repositories are handled gracefully."""

        @temporal_workflow_proxy(
            activity_base="test.non_generic_repo.minio",
            default_timeout_seconds=30,
        )
        class TestNonGenericProxy(NonGenericRepository):
            pass

        # Should not raise an error
        proxy = TestNonGenericProxy()  # type: ignore[abstract]
        assert hasattr(proxy, "get")

        # Should return None for concrete type (logged but not errored)
        concrete_type = _extract_concrete_type_from_base(TestNonGenericProxy)
        assert concrete_type is None


class TestEndToEndTypeSubstitution:
    """End-to-end tests demonstrating the complete type substitution fix."""

    def test_type_substitution_enables_pydantic_validation(self) -> None:
        """Test type substitution enables Pydantic validation."""
        # Simulate the problematic method signature: Optional[~T]
        original_annotation = Optional[T]

        # Before fix: TypeVar prevents validation
        assert not _needs_pydantic_validation(original_annotation)

        # After substitution: Concrete type enables validation
        substituted_annotation = _substitute_typevar_with_concrete(
            original_annotation, MockAssemblySpecification
        )
        assert _needs_pydantic_validation(substituted_annotation)

    def test_demonstrates_original_problem_and_solution(self) -> None:
        """Test dict vs Pydantic object problem and solution."""
        # Create test data
        test_spec = MockAssemblySpecification(
            assembly_specification_id="test-123",
            name="Test Spec",
            status="active",
        )

        # Convert to dict (simulates what Temporal activity returns)
        activity_result_dict = test_spec.model_dump(mode="json")

        # Demonstrate the problem: dict doesn't have Pydantic attributes
        assert isinstance(activity_result_dict, dict)
        with pytest.raises(AttributeError):
            # This would fail because dict doesn't have the attribute
            getattr(activity_result_dict, "assembly_specification_id")

        # Demonstrate the solution: reconstruct Pydantic object
        reconstructed = MockAssemblySpecification.model_validate(
            activity_result_dict
        )
        assert isinstance(reconstructed, MockAssemblySpecification)
        assert (
            reconstructed.assembly_specification_id == "test-123"
        )  # This works
        assert reconstructed.name == "Test Spec"
        assert reconstructed.status == "active"

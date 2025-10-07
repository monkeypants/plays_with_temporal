"""
Temporal decorators for automatically creating activities and workflow proxies

This module provides decorators that automatically:
1. Wrap protocol methods as Temporal activities
2. Generate workflow proxy classes that delegate to activities
Both reduce boilerplate and ensure consistent patterns.
"""

import inspect
import functools
import logging
from datetime import timedelta
from typing import (
    Any,
    Callable,
    Type,
    TypeVar,
    Optional,
    get_origin,
    get_args,
)

from temporalio import activity, workflow
from temporalio.common import RetryPolicy
from pydantic import BaseModel

from julee_example.domain.repositories.base import BaseRepository
from .activities import discover_protocol_methods

logger = logging.getLogger(__name__)

T = TypeVar("T")


def _extract_concrete_type_from_base(cls: type) -> Optional[type]:
    """
    Extract the concrete type argument from a generic base class.

    For example, if a class inherits from
    BaseRepository[AssemblySpecification], this function will return
    AssemblySpecification.

    Args:
        cls: Class to analyze for generic base types

    Returns:
        The concrete type if found, None otherwise
    """
    # Check the class hierarchy for generic base classes
    for base in cls.__mro__:
        # Check if this class has __orig_bases__ (generic type information)
        if hasattr(base, "__orig_bases__"):
            for orig_base in base.__orig_bases__:
                origin = get_origin(orig_base)
                if origin is not None:
                    args = get_args(orig_base)
                    # Look for BaseRepository[ConcreteType] pattern
                    if origin is BaseRepository and len(args) == 1:
                        concrete_type = args[0]
                        # Make sure it's a concrete type, not another TypeVar
                        if not isinstance(concrete_type, TypeVar):
                            logger.debug(
                                f"Extracted concrete type {concrete_type} "
                                f"from {orig_base}"
                            )
                            return concrete_type  # type: ignore[no-any-return]
    return None


def _substitute_typevar_with_concrete(
    annotation: Any, concrete_type: type
) -> Any:
    """
    Substitute TypeVar instances with concrete type in type annotations.

    Args:
        annotation: Type annotation that may contain TypeVars
        concrete_type: Concrete type to substitute for TypeVars

    Returns:
        Type annotation with TypeVars replaced by concrete type

    Raises:
        TypeError: If type reconstruction fails during substitution
    """
    if isinstance(annotation, TypeVar):
        return concrete_type

    origin = get_origin(annotation)
    if origin is not None:
        args = get_args(annotation)
        if args:
            # Recursively substitute in generic arguments
            new_args = tuple(
                _substitute_typevar_with_concrete(arg, concrete_type)
                for arg in args
            )
            # Reconstruct the generic type with substituted arguments
            try:
                return origin[new_args]  # type: ignore
            except TypeError as e:
                # Fail fast - type reconstruction should work if substituting
                raise TypeError(
                    f"Failed to reconstruct generic type {origin} with "
                    f"args {new_args}. "
                    f"Original annotation: {annotation}, "
                    f"concrete type: {concrete_type}. "
                    f"This indicates an issue with type substitution logic."
                ) from e

    # origin is None - normal for non-generic types like str, bool, etc.
    return annotation


def temporal_activity_registration(
    activity_prefix: str,
) -> Callable[[Type[T]], Type[T]]:
    """
    Class decorator that wraps async protocol methods as Temporal activities.

    This decorator inspects the class and wraps all async methods (coroutine
    functions) that don't start with underscore as Temporal activities. The
    activity names are generated using the provided prefix and the method
    name.

    Args:
        activity_prefix: Prefix for activity names (e.g.,
        "sample.payment_repo.minio") Method names will be appended to create
        full activity names like "sample.payment_repo.minio.process_payment"

    Returns:
        The decorated class with all async methods wrapped as Temporal
        activities

    Example:
        @temporal_activity_registration("sample.payment_repo.minio")
        class TemporalMinioPaymentRepository(MinioPaymentRepository):
            pass

        # This automatically creates activities for all protocol methods:
        # - process_payment ->
        #   "sample.payment_repo.minio.process_payment"
        # - get_payment ->
        #   "sample.payment_repo.minio.get_payment"
        # - refund_payment ->
        #   "sample.payment_repo.minio.refund_payment"
    """

    def decorator(cls: Type[T]) -> Type[T]:
        logger.debug(
            f"Applying temporal_activity_registration decorator to "
            f"{cls.__name__}"
        )

        # Track which methods we wrap for logging
        wrapped_methods = []

        # Use common method discovery - for activities, wrap protocol methods
        async_methods_to_wrap = discover_protocol_methods(cls.__mro__)

        # Now wrap all the async methods we found
        for name, method in async_methods_to_wrap.items():
            # Create activity name by combining prefix and method name
            activity_name = f"{activity_prefix}.{name}"

            logger.debug(
                f"Wrapping method {name} as activity {activity_name}"
            )

            # Create a new method that calls the original to avoid decorator
            # conflicts while preserving the exact signature for Pydantic
            def create_wrapper_method(
                original_method: Callable[..., Any], method_name: str
            ) -> Callable[..., Any]:
                # Create wrapper with preserved signature for proper type
                # conversion

                @functools.wraps(original_method)
                async def wrapper_method(*args: Any, **kwargs: Any) -> Any:
                    return await original_method(*args, **kwargs)

                # Preserve method metadata explicitly
                wrapper_method.__name__ = method_name
                wrapper_method.__qualname__ = f"{cls.__name__}.{method_name}"
                wrapper_method.__doc__ = original_method.__doc__
                wrapper_method.__annotations__ = getattr(
                    original_method, "__annotations__", {}
                )

                return wrapper_method

            # Create the wrapper and apply activity decorator
            wrapper_method = create_wrapper_method(method, name)
            wrapped_method = activity.defn(name=activity_name)(wrapper_method)

            # Replace the method on the class with the wrapped version
            setattr(cls, name, wrapped_method)

            wrapped_methods.append(name)

        logger.info(
            f"Temporal activity registration decorator applied to "
            f"{cls.__name__}",
            extra={
                "wrapped_methods": wrapped_methods,
                "activity_prefix": activity_prefix,
            },
        )

        return cls

    return decorator


def temporal_workflow_proxy(
    activity_base: str,
    default_timeout_seconds: int = 30,
    retry_methods: Optional[list[str]] = None,
) -> Callable[[Type[T]], Type[T]]:
    """
    Class decorator that automatically creates workflow proxy methods that
    delegate to Temporal activities.

    This decorator inspects the protocol/interface being implemented and
    generates methods that call workflow.execute_activity with the appropriate
    activity names, timeouts, and retry policies.

    Args:
        activity_base: Base activity name (e.g., "julee.document_repo.minio")
        default_timeout_seconds: Default timeout for activities in seconds
        retry_methods: List of method names that should use retry policies

    Returns:
        The decorated class with all protocol methods implemented as
        workflow activity calls

    Example:
        @temporal_workflow_proxy(
            "julee.document_repo.minio",
            default_timeout_seconds=30,
            retry_methods=["save", "generate_id"]
        )
        class WorkflowDocumentRepositoryProxy(DocumentRepository):
            pass

        # This automatically creates workflow methods for all methods:
        # - get() -> calls "julee.document_repo.minio.get" activity
        # - save() -> calls "julee.document_repo.minio.save" with retry
        # - generate_id() -> calls "julee.document_repo.minio.generate_id"
        #   with retry
    """

    def decorator(cls: Type[T]) -> Type[T]:
        logger.debug(
            f"Applying temporal_workflow_proxy decorator to {cls.__name__}"
        )

        retry_methods_set = set(retry_methods or [])

        # Create default retry policy for methods that need it
        fail_fast_retry_policy = RetryPolicy(
            initial_interval=timedelta(seconds=1),
            maximum_attempts=1,
            backoff_coefficient=1.0,
            maximum_interval=timedelta(seconds=1),
        )

        # Use method discovery - for workflow proxies, wrap protocol methods
        methods_to_implement = discover_protocol_methods(cls.__mro__)

        # Generate workflow proxy methods
        wrapped_methods = []

        for method_name, original_method in methods_to_implement.items():
            logger.debug(
                f"Creating workflow proxy method {method_name} -> "
                f"{activity_base}.{method_name}"
            )

            # Get method signature for type hints
            sig = inspect.signature(original_method)
            return_annotation = sig.return_annotation

            # Try to extract concrete type from class inheritance
            concrete_type = _extract_concrete_type_from_base(cls)

            # Substitute TypeVars with concrete type if found
            if concrete_type is not None:
                return_annotation = _substitute_typevar_with_concrete(
                    return_annotation, concrete_type
                )
                logger.debug(
                    f"Substituted TypeVar in {method_name} return type: "
                    f"{sig.return_annotation} -> {return_annotation}"
                )
            else:
                # Log when we couldn't extract concrete type - might indicate
                # a repository that doesn't follow BaseRepository[T] pattern
                logger.debug(
                    f"No concrete type for {cls.__name__}.{method_name}. "
                    f"Return annotation: {sig.return_annotation}. "
                    f"If Pydantic objects returned, ensure repo inherits "
                    f"from BaseRepository[ConcreteType]."
                )

            # Determine if return type needs Pydantic validation
            needs_validation = _needs_pydantic_validation(return_annotation)
            is_optional = _is_optional_type(return_annotation)
            inner_type = (
                _get_optional_inner_type(return_annotation)
                if is_optional
                else return_annotation
            )

            def create_workflow_method(
                method_name: str,
                needs_validation: bool,
                is_optional: bool,
                inner_type: Any,
                original_method: Any,
            ) -> Callable[..., Any]:
                @functools.wraps(original_method)
                async def workflow_method(
                    self: Any, *args: Any, **kwargs: Any
                ) -> Any:
                    # Create activity name
                    activity_name = f"{activity_base}.{method_name}"

                    # Set up activity options
                    activity_timeout = timedelta(
                        seconds=default_timeout_seconds
                    )
                    retry_policy = None

                    # Add retry policy if this method needs it
                    if method_name in retry_methods_set:
                        retry_policy = fail_fast_retry_policy

                    # Log the call
                    logger.debug(
                        f"Workflow: Calling {method_name} activity",
                        extra={
                            "activity_name": activity_name,
                            "args_count": len(args),
                            "kwargs_count": len(kwargs),
                        },
                    )

                    # Prepare arguments (exclude self)
                    activity_args = args if args else ()

                    # Handle kwargs - Temporal doesn't support kwargs directly
                    if kwargs:
                        raise ValueError(
                            f"Keyword arguments not supported in workflow "
                            f"proxy for {method_name}. Temporal activities "
                            f"only accept positional arguments. Please "
                            f"modify the calling code to use positional "
                            f"arguments instead of: {list(kwargs.keys())}"
                        )

                    # Execute the activity
                    if activity_args:
                        raw_result = await workflow.execute_activity(
                            activity_name,
                            args=activity_args,
                            start_to_close_timeout=activity_timeout,
                            retry_policy=retry_policy,
                        )
                    else:
                        raw_result = await workflow.execute_activity(
                            activity_name,
                            start_to_close_timeout=activity_timeout,
                            retry_policy=retry_policy,
                        )

                    # Handle return value validation
                    result = raw_result
                    if needs_validation and raw_result is not None:
                        if hasattr(inner_type, "model_validate"):
                            result = inner_type.model_validate(
                                raw_result,
                                context={"temporal_validation": True},
                            )
                        else:
                            # For other types, just return as-is
                            result = raw_result
                    elif (
                        is_optional
                        and raw_result is not None
                        and hasattr(inner_type, "model_validate")
                    ):
                        result = inner_type.model_validate(
                            raw_result, context={"temporal_validation": True}
                        )

                    # Log completion
                    logger.debug(
                        f"Workflow: {method_name} activity completed",
                        extra={
                            "activity_name": activity_name,
                            "result_type": type(result).__name__,
                        },
                    )

                    return result

                return workflow_method

            # Create and set the method on the class
            workflow_method = create_workflow_method(
                method_name,
                needs_validation,
                is_optional,
                inner_type,
                original_method,
            )
            setattr(cls, method_name, workflow_method)
            wrapped_methods.append(method_name)

        # Always generate __init__ that calls super() for consistent init
        def __init__(proxy_self: Any) -> None:
            # Call parent __init__ to preserve any existing init logic
            super(cls, proxy_self).__init__()
            # Set instance variables for consistency with manual pattern
            proxy_self.activity_timeout = timedelta(
                seconds=default_timeout_seconds
            )
            proxy_self.activity_fail_fast_retry_policy = (
                fail_fast_retry_policy
            )
            logger.debug(f"Initialized {cls.__name__}")

        setattr(cls, "__init__", __init__)

        logger.info(
            f"Temporal workflow proxy decorator applied to {cls.__name__}",
            extra={
                "wrapped_methods": wrapped_methods,
                "activity_base": activity_base,
                "default_timeout_seconds": default_timeout_seconds,
                "retry_methods": list(retry_methods_set),
            },
        )

        return cls

    return decorator


def _needs_pydantic_validation(annotation: Any) -> bool:
    """Check if a type annotation indicates a Pydantic model."""
    if annotation is None or annotation == inspect.Signature.empty:
        return False

    # Handle Optional types
    if _is_optional_type(annotation):
        inner_type = _get_optional_inner_type(annotation)
        return _is_pydantic_model(inner_type)

    return _is_pydantic_model(annotation)


def _is_pydantic_model(type_hint: Any) -> bool:
    """Check if a type is a Pydantic model."""
    if inspect.isclass(type_hint) and issubclass(type_hint, BaseModel):
        return True
    return False


def _is_optional_type(annotation: Any) -> bool:
    """Check if a type annotation is Optional[T]."""
    origin = get_origin(annotation)
    if origin is not None:
        args = get_args(annotation)
        # Optional[T] is Union[T, None]
        return (
            hasattr(origin, "__name__") and origin.__name__ == "UnionType"
        ) or (
            str(origin) == "typing.Union"
            and len(args) == 2
            and type(None) in args
        )
    return False


def _get_optional_inner_type(annotation: Any) -> Any:
    """Get the inner type from Optional[T]."""
    args = get_args(annotation)
    if len(args) == 2:
        return args[0] if args[1] is type(None) else args[1]
    return annotation

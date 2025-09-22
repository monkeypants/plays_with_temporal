"""
Temporal decorators for automatically creating activities and workflow proxies

This module provides decorators that automatically:
1. Wrap async protocol methods as Temporal activities
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

logger = logging.getLogger(__name__)

T = TypeVar("T")


def _discover_protocol_methods(
    cls_hierarchy: tuple[type, ...],
) -> dict[str, Any]:
    """
    Common function to discover protocol methods that should be wrapped.

    This function is used by both temporal_activity_registration and
    temporal_workflow_proxy to ensure they operate on the exact same
    set of methods by finding async methods defined in protocol interfaces.

    Args:
        cls_hierarchy: The class MRO (method resolution order)

    Returns:
        Dict mapping method names to method objects
    """
    methods_to_wrap = {}

    # Look for protocol interfaces (classes with runtime_checkable/Protocol)
    class_names = [cls.__name__ for cls in cls_hierarchy]
    logger.debug(f"Protocol discovery for class hierarchy: {class_names}")

    for base_class in cls_hierarchy:
        # Skip object base class
        if base_class is object:
            continue

        # Check if this is a protocol class
        has_protocol_attr = hasattr(base_class, "__protocol__")
        has_is_protocol = getattr(base_class, "_is_protocol", False)
        has_protocol_in_str = "Protocol" in str(base_class)

        is_protocol = (
            has_protocol_attr or has_is_protocol or has_protocol_in_str
        )

        logger.debug(
            f"Class {base_class.__name__}: __protocol__={has_protocol_attr}, "
            f"_is_protocol={has_is_protocol}, "
            f"Protocol_in_str={has_protocol_in_str}, "
            f"is_protocol={is_protocol}"
        )

        if is_protocol:
            logger.debug(f"Processing protocol class: {base_class.__name__}")
            # Get methods defined in this protocol
            for name in base_class.__dict__:
                if name in methods_to_wrap:
                    continue  # Already found this method

                method = getattr(base_class, name)
                is_coro = inspect.iscoroutinefunction(method)
                starts_underscore = name.startswith("_")

                logger.debug(
                    f"  Method {name}: is_coroutine={is_coro}, "
                    f"starts_underscore={starts_underscore}"
                )

                # Only wrap async methods that don't start with underscore
                if is_coro and not starts_underscore:
                    methods_to_wrap[name] = method
                    logger.debug(f"    -> Added {name} to protocol methods")

    # Enable protocol discovery with logging to debug E2E issue
    method_names = list(methods_to_wrap.keys())
    logger.debug(
        f"Protocol discovery found {len(methods_to_wrap)} methods: "
        f"{method_names}"
    )

    # If no protocol methods found, fall back to all async methods
    # (for backward compatibility with non-protocol base classes)
    if not methods_to_wrap:
        logger.debug(
            "No protocol methods found, using fallback method discovery"
        )
        for base_class in cls_hierarchy:
            if base_class is object:
                continue

            for name in base_class.__dict__:
                if name in methods_to_wrap:
                    continue

                method = getattr(base_class, name)
                if inspect.iscoroutinefunction(
                    method
                ) and not name.startswith("_"):
                    methods_to_wrap[name] = method

    final_method_names = list(methods_to_wrap.keys())
    logger.debug(
        f"Final method discovery found {len(methods_to_wrap)} methods: "
        f"{final_method_names}"
    )
    return methods_to_wrap


def temporal_activity_registration(
    activity_prefix: str,
) -> Callable[[Type[T]], Type[T]]:
    """
    Class decorator that automatically wraps all async methods as Temporal
    activities.

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

        # This automatically creates activities for all async methods:
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

        # Use common method discovery
        async_methods_to_wrap = _discover_protocol_methods(cls.__mro__)

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

        # Use the same method discovery as temporal_activity_registration
        methods_to_implement = _discover_protocol_methods(cls.__mro__)

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

                    # Note: kwargs not currently supported by this decorator
                    # Most repository methods use positional args only
                    if kwargs:
                        raise ValueError(
                            f"kwargs not supported in workflow proxy "
                            f"for {method_name}. Use positional args."
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
                            result = inner_type.model_validate(raw_result)
                        else:
                            # For other types, just return as-is
                            result = raw_result
                    elif (
                        is_optional
                        and raw_result is not None
                        and hasattr(inner_type, "model_validate")
                    ):
                        result = inner_type.model_validate(raw_result)

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

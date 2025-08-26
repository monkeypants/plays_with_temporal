"""
Temporal decorator for automatically wrapping repository methods as activities

This module provides a decorator that automatically wraps repository methods
as Temporal activities, reducing boilerplate and ensuring consistent patterns.
"""

import inspect
import functools
import logging
from typing import Any, Callable, Type, TypeVar

from temporalio import activity

logger = logging.getLogger(__name__)

T = TypeVar("T")


def temporal_repository(activity_prefix: str) -> Callable[[Type[T]], Type[T]]:
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
        @temporal_repository("sample.payment_repo.minio")
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
            f"Applying temporal_repository decorator to {cls.__name__}"
        )

        # Track which methods we wrap for logging
        wrapped_methods = []

        # Look at all classes in the MRO to find async methods to wrap
        async_methods_to_wrap = {}

        for base_class in cls.__mro__:
            # Skip object base class
            if base_class is object:
                continue

            # Get methods defined in this class (not inherited ones we've
            # already seen)
            for name in base_class.__dict__:
                if name in async_methods_to_wrap:
                    continue  # Already found this method in a subclass

                method = getattr(base_class, name)

                # Only wrap async methods that don't start with underscore
                if inspect.iscoroutinefunction(
                    method
                ) and not name.startswith("_"):
                    async_methods_to_wrap[name] = method

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
                # Create wrapper with preserved signature for proper type conversion

                @functools.wraps(original_method)
                async def wrapper_method(*args, **kwargs):
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
            f"Temporal repository decorator applied to {cls.__name__}",
            extra={
                "wrapped_methods": wrapped_methods,
                "activity_prefix": activity_prefix,
            },
        )

        return cls

    return decorator

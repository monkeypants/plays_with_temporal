"""
Temporal decorators for automatically wrapping repository methods as
activities.

This module provides decorators that can automatically wrap repository methods
as Temporal activities, reducing boilerplate and ensuring consistent patterns.
"""

import inspect
import logging
from typing import Any, Callable, Type, TypeVar

from temporalio import activity

logger = logging.getLogger(__name__)

T = TypeVar("T")


def temporal_repository(activity_prefix: str):
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
        @temporal_repository("sample.order_fulfillment.payment_repo")
        class OrderFulfillmentPaymentRepository(MinioPaymentRepository):
            pass

        # This automatically creates activities for all async methods: -
        # process_payment ->
        # "sample.order_fulfillment.payment_repo.process_payment" -
        #  get_payment
        # -> "sample.order_fulfillment.payment_repo.get_payment" -
        # refund_payment ->
        # "sample.order_fulfillment.payment_repo.refund_payment"
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
            # conflicts
            def create_wrapper_method(original_method, method_name):
                async def wrapper_method(self, *args, **kwargs):
                    return await original_method(self, *args, **kwargs)

                # Preserve method metadata
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


def temporal_activity(activity_name: str):
    """
    Method decorator that wraps a single method as a Temporal activity.

    This is useful when you need more granular control over individual methods
    or when the automatic class decorator doesn't meet your needs.

    Args:
        activity_name: Full activity name for this method

    Returns:
        The decorated method wrapped as a Temporal activity

    Example:
        class MyRepository:
            @temporal_activity("sample.custom.activity.name")
            async def my_method(self, arg: str) -> str:
                return f"processed {arg}"
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        logger.debug(
            f"Wrapping method {func.__name__} as activity {activity_name}"
        )
        return activity.defn(name=activity_name)(func)

    return decorator


def create_temporal_wrapper(
    base_class: Type[T], activity_prefix: str, wrapper_class_name: str = None
) -> Type[T]:
    """
    Factory function that creates a Temporal wrapper class dynamically.

    This is an alternative to the class decorator that creates a new class
    rather than modifying an existing one. Useful when you want to keep
    the original class unchanged.

    Args:
        base_class: The base repository class to wrap
        activity_prefix: Prefix for activity names
        wrapper_class_name: Name for the new class (defaults to
        Temporal{BaseName})

    Returns:
        A new class that inherits from base_class with methods wrapped as
        activities

    Example:
        from sample.repos.minio.payment import MinioPaymentRepository

        TemporalPaymentRepo = create_temporal_wrapper(
            MinioPaymentRepository,
            "sample.order_fulfillment.payment_repo",
            "OrderFulfillmentPaymentRepository"
        )

        # Use the dynamically created class
        repo = TemporalPaymentRepo("localhost:9000")
    """
    if wrapper_class_name is None:
        wrapper_class_name = f"Temporal{base_class.__name__}"

    logger.debug(
        f"Creating temporal wrapper {wrapper_class_name} "
        + "for {base_class.__name__}"
    )

    # Dictionary to hold the wrapped methods for the new class
    class_dict = {}
    wrapped_methods = []

    # Find all async methods in the base class to wrap
    for name, method in inspect.getmembers(base_class):
        if inspect.iscoroutinefunction(method) and not name.startswith("_"):
            activity_name = f"{activity_prefix}.{name}"

            # Create a wrapper function that calls the parent method
            def create_method_wrapper(method_name: str, activity_name: str):
                async def wrapper(self, *args, **kwargs):
                    # Get the method from the parent class and call it
                    parent_method = getattr(
                        super(wrapper_class, self), method_name
                    )
                    return await parent_method(*args, **kwargs)

                # Apply activity decorator and preserve metadata
                wrapper.__name__ = method_name
                wrapper.__qualname__ = f"{wrapper_class_name}.{method_name}"

                return activity.defn(name=activity_name)(wrapper)

            class_dict[name] = create_method_wrapper(name, activity_name)
            wrapped_methods.append(name)

    # Create the new class dynamically
    wrapper_class = type(wrapper_class_name, (base_class,), class_dict)

    logger.info(
        f"Created temporal wrapper class {wrapper_class_name}",
        extra={
            "base_class": base_class.__name__,
            "wrapped_methods": wrapped_methods,
            "activity_prefix": activity_prefix,
        },
    )

    return wrapper_class


def get_temporal_activity_info(cls: Type) -> dict[str, str]:
    """
    Helper function to inspect a class and return information about its
    Temporal activities.

    Args:
        cls: Class to inspect

    Returns:
        Dictionary mapping method names to their activity names

    Example:
        info = get_temporal_activity_info(OrderFulfillmentPaymentRepository)
        # Returns:
        # {
        # 'process_payment':
        # 'sample.order_fulfillment.payment_repo.process_payment',
        # 'get_payment': 'sample.order_fulfillment.payment_repo.get_payment',
        # 'refund_payment':
        # 'sample.order_fulfillment.payment_repo.refund_payment'
        # }
    """
    activity_info = {}

    for name, method in inspect.getmembers(cls):
        try:
            # Check if the method has a __dict__ and contains the activity
            # definition Note: The key is '__temporal_activity_definition'
            # (single trailing underscore)
            if (
                hasattr(method, "__dict__")
                and "__temporal_activity_definition" in method.__dict__
            ):
                activity_def = method.__dict__[
                    "__temporal_activity_definition"
                ]
                activity_info[name] = activity_def.name
        except (AttributeError, TypeError):
            # Skip methods that don't have activity definitions
            continue

    return activity_info

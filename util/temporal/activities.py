"""
Utilities for working with Temporal activities.

This module provides helper functions for automatically discovering and
collecting activity methods from decorated instances, eliminating the need
for manual activity registration boilerplate.
"""

import inspect
import logging
from typing import Any

logger = logging.getLogger(__name__)


def discover_protocol_methods(
    cls_hierarchy: tuple[type, ...],
) -> dict[str, Any]:
    """
    Discover protocol methods that should be wrapped as activities.

    This function finds async methods defined in protocol interfaces within
    a class hierarchy. It's used to automatically collect methods that should
    be registered as Temporal activities.

    Args:
        cls_hierarchy: The class MRO (method resolution order)

    Returns:
        Dict mapping method names to method objects from the concrete class
    """
    methods_to_wrap = {}
    concrete_class = cls_hierarchy[0]  # The actual class being decorated

    # Look for protocol interfaces (classes with runtime_checkable/Protocol)
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

        # Only process protocol classes for architectural compliance
        if is_protocol:
            # Get method names defined in this class, but get the actual
            # implementation from the concrete class
            for name in base_class.__dict__:
                if name in methods_to_wrap:
                    continue  # Already found this method

                base_method = getattr(base_class, name)
                # Only wrap async methods that don't start with underscore
                if inspect.iscoroutinefunction(
                    base_method
                ) and not name.startswith("_"):
                    # Get the concrete implementation from the actual class
                    if hasattr(concrete_class, name):
                        concrete_method = getattr(concrete_class, name)
                        methods_to_wrap[name] = concrete_method

    # Log final results
    final_method_names = list(methods_to_wrap.keys())
    logger.debug(
        f"Method discovery found {len(methods_to_wrap)}: {final_method_names}"
    )
    return methods_to_wrap


def collect_activities_from_instances(*instances: Any) -> list[Any]:
    """Automatically collect all activity methods from decorated instances.

    Uses protocol method discovery to find and collect all methods that have
    been wrapped as Temporal activities by the @temporal_activity_registration
    decorator. This ensures we don't miss any activities and eliminates
    boilerplate registration code.

    Args:
        *instances: Repository and service instances decorated with
                   @temporal_activity_registration

    Returns:
        List of activity methods ready for Worker registration

    Example:
        # Instead of manually listing all activities:
        activities = [
            repo.generate_id,
            repo.save,
            repo.get,
            # ... many more lines
        ]

        # Use automatic discovery:
        activities = collect_activities_from_instances(
            temporal_assembly_repo,
            temporal_document_repo,
            temporal_knowledge_service,
        )
    """
    activities = []

    for instance in instances:
        # Use the same discovery logic as the decorator
        methods_to_collect = discover_protocol_methods(
            instance.__class__.__mro__
        )

        # Get the actual bound methods from the instance
        for method_name in methods_to_collect:
            if hasattr(instance, method_name):
                bound_method = getattr(instance, method_name)
                activities.append(bound_method)
                logger.debug(
                    f"Collected activity method: "
                    f"{instance.__class__.__name__}.{method_name}"
                )

    logger.info(
        f"Collected {len(activities)} activities from "
        f"{len(instances)} instances"
    )

    return activities

"""
Temporal utilities package.

This package provides utility functions and classes for working with
Temporal workflows and activities.
"""

from .activities import (
    collect_activities_from_instances,
    discover_protocol_methods,
)
from .decorators import (
    temporal_activity_registration,
    temporal_workflow_proxy,
)

__all__ = [
    "collect_activities_from_instances",
    "discover_protocol_methods",
    "temporal_activity_registration",
    "temporal_workflow_proxy",
]

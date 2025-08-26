"""
Temporal repository utilities.

This module provides utilities for working with Temporal repositories,
including the temporal_repository decorator for automatically wrapping
repository methods as Temporal activities.
"""

from .decorators import temporal_repository

__all__ = ["temporal_repository"]

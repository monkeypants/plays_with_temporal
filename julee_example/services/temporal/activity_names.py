"""
Shared activity name constants for the julee_example knowledge service domain.

This module contains activity name base constants that are shared between
activities.py and proxies.py, avoiding the need for either module to import
from the other, which would create problematic transitive dependencies.

By isolating these constants in their own module, we maintain DRY principles
while preserving Temporal's workflow sandbox restrictions. The proxies module
can import these constants without transitively importing non-deterministic
backend code from activities.py.
"""

# Activity name bases - shared constants for consistency between
# activity registrations and workflow proxies
KNOWLEDGE_SERVICE_ACTIVITY_BASE = "julee.knowledge_service"


# Export all constants
__all__ = [
    "KNOWLEDGE_SERVICE_ACTIVITY_BASE",
]

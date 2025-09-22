"""
Shared activity name constants for the sample domain.

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
ORDER_ACTIVITY_BASE = "sample.order_repo.minio"
PAYMENT_ACTIVITY_BASE = "sample.payment_repo.minio"
INVENTORY_ACTIVITY_BASE = "sample.inventory_repo.minio"
ORDER_REQUEST_ACTIVITY_BASE = "sample.order_request_repo.minio"


# Export all constants
__all__ = [
    "ORDER_ACTIVITY_BASE",
    "PAYMENT_ACTIVITY_BASE",
    "INVENTORY_ACTIVITY_BASE",
    "ORDER_REQUEST_ACTIVITY_BASE",
]

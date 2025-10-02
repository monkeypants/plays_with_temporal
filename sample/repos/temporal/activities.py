"""
Temporal activity wrapper classes for the sample domain.

This module contains all @temporal_activity_registration decorated classes
that wrap pure backend repositories as Temporal activities. These classes are
imported by the worker to register activities with Temporal.

The classes follow the naming pattern documented in systemPatterns.org:
- Activity names: {domain}.{repo_name}.{method}
- Each repository type gets its own activity prefix
"""

from util.temporal.decorators import temporal_activity_registration
from sample.repos.minio.order import MinioOrderRepository
from sample.repos.minio.payment import MinioPaymentRepository
from sample.repos.minio.inventory import MinioInventoryRepository
from sample.repos.minio.order_request import MinioOrderRequestRepository

# Import activity name bases from shared module
from sample.repos.temporal.activity_names import (
    ORDER_ACTIVITY_BASE,
    PAYMENT_ACTIVITY_BASE,
    INVENTORY_ACTIVITY_BASE,
    ORDER_REQUEST_ACTIVITY_BASE,
)


@temporal_activity_registration(ORDER_ACTIVITY_BASE)
class TemporalMinioOrderRepository(MinioOrderRepository):
    """Temporal activity wrapper for MinioOrderRepository."""

    pass


@temporal_activity_registration(PAYMENT_ACTIVITY_BASE)
class TemporalMinioPaymentRepository(MinioPaymentRepository):
    """Temporal activity wrapper for MinioPaymentRepository."""

    pass


@temporal_activity_registration(INVENTORY_ACTIVITY_BASE)
class TemporalMinioInventoryRepository(MinioInventoryRepository):
    """Temporal activity wrapper for MinioInventoryRepository."""

    pass


@temporal_activity_registration(ORDER_REQUEST_ACTIVITY_BASE)
class TemporalMinioOrderRequestRepository(MinioOrderRequestRepository):
    """Temporal activity wrapper for MinioOrderRequestRepository."""

    pass


# Export the temporal repository classes for use in worker.py
__all__ = [
    "TemporalMinioOrderRepository",
    "TemporalMinioPaymentRepository",
    "TemporalMinioInventoryRepository",
    "TemporalMinioOrderRequestRepository",
    # Export constants for proxy consistency
    "ORDER_ACTIVITY_BASE",
    "PAYMENT_ACTIVITY_BASE",
    "INVENTORY_ACTIVITY_BASE",
    "ORDER_REQUEST_ACTIVITY_BASE",
]

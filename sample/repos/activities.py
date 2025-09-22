"""
Temporal activity wrapper classes for the sample domain.

This module contains the @temporal_activity_registration decorated classes
that wrap
pure backend repositories as Temporal activities. These classes are only
imported by the worker to avoid workflow sandbox violations.

The classes follow the naming pattern documented in systemPatterns.org:
- Activity names: {domain}.{usecase}.{constructor_param_name}.{method}
- Since these are shared across use cases, they use repo-specific prefixes
"""

from util.repos.temporal.decorators import temporal_activity_registration
from sample.repos.minio.order import MinioOrderRepository
from sample.repos.minio.payment import MinioPaymentRepository
from sample.repos.minio.inventory import MinioInventoryRepository
from sample.repos.minio.order_request import MinioOrderRequestRepository


@temporal_activity_registration("sample.order_repo.minio")
class TemporalMinioOrderRepository(MinioOrderRepository):
    """Temporal activity wrapper for MinioOrderRepository."""

    pass


@temporal_activity_registration("sample.payment_repo.minio")
class TemporalMinioPaymentRepository(MinioPaymentRepository):
    """Temporal activity wrapper for MinioPaymentRepository."""

    pass


@temporal_activity_registration("sample.inventory_repo.minio")
class TemporalMinioInventoryRepository(MinioInventoryRepository):
    """Temporal activity wrapper for MinioInventoryRepository."""

    pass


@temporal_activity_registration("sample.order_request_repo.minio")
class TemporalMinioOrderRequestRepository(MinioOrderRequestRepository):
    """Temporal activity wrapper for MinioOrderRequestRepository."""

    pass


# Export the temporal repository classes for use in worker.py
__all__ = [
    "TemporalMinioOrderRepository",
    "TemporalMinioPaymentRepository",
    "TemporalMinioInventoryRepository",
    "TemporalMinioOrderRequestRepository",
]

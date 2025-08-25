"""
Temporal activity implementations using the @temporal_repository decorator.

This module creates the temporal activity wrapper classes for all repository
types used in the sample domain. These classes are created using the
@temporal_repository decorator which automatically wraps all async methods
as Temporal activities.

The classes created here follow the naming pattern documented in
systemPatterns.org:
- Activity names: {domain}.{usecase}.{constructor_param_name}.{method}
- Since these are shared across use cases, they use repo-specific prefixes
"""

from util.repos.temporal.decorators import temporal_repository
from sample.repos.minio.order import MinioOrderRepository
from sample.repos.minio.payment import MinioPaymentRepository
from sample.repos.minio.inventory import MinioInventoryRepository
from sample.repos.minio.order_request import MinioOrderRequestRepository

# Create temporal repository classes using the decorator
# These will be imported and instantiated in worker.py


@temporal_repository("sample.order_repo.minio")
class TemporalMinioOrderRepository(MinioOrderRepository):
    """Temporal activity wrapper for MinioOrderRepository."""

    pass


@temporal_repository("sample.payment_repo.minio")
class TemporalMinioPaymentRepository(MinioPaymentRepository):
    """Temporal activity wrapper for MinioPaymentRepository."""

    pass


@temporal_repository("sample.inventory_repo.minio")
class TemporalMinioInventoryRepository(MinioInventoryRepository):
    """Temporal activity wrapper for MinioInventoryRepository."""

    pass


@temporal_repository("sample.order_request_repo.minio")
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

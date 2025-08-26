"""
Dependency injection for FastAPI endpoints.
"""

import os
import logging
from typing import Any, Dict

from fastapi import Depends
from temporalio.client import Client
from temporalio.contrib.pydantic import pydantic_data_converter

from sample.repositories import (
    OrderRequestRepository,
)
from util.repositories import FileStorageRepository  # Updated import path

from sample.repos.minio.order_request import MinioOrderRequestRepository
from sample.repos.minio.order import MinioOrderRepository
from sample.repos.minio.payment import MinioPaymentRepository
from sample.usecase import (
    GetOrderUseCase,
)
from sample.validation import (
    ensure_order_repository,
    ensure_payment_repository,
)  # New import for validation

logger = logging.getLogger(__name__)


class DependencyContainer:
    """
    Dependency injection container with singleton lifecycle management.
    Always creates real clients; mocks are provided by test overrides.
    """

    def __init__(self) -> None:
        self._instances: Dict[str, Any] = {}

    async def get_or_create(self, key: str, factory: Any) -> Any:
        """Get or create a singleton instance."""
        if key not in self._instances:
            self._instances[key] = await factory()
        return self._instances[key]

    async def get_temporal_client(self) -> Client:
        """Get or create Temporal client."""
        client = await self.get_or_create(
            "temporal_client", self._create_temporal_client
        )
        return client  # type: ignore[no-any-return]

    async def _create_temporal_client(self) -> Client:
        """Create Temporal client with proper configuration."""
        temporal_endpoint = os.environ.get(
            "TEMPORAL_ENDPOINT", "temporal:7233"
        )
        logger.debug(
            "Creating Temporal client",
            extra={"endpoint": temporal_endpoint, "namespace": "default"},
        )

        client = await Client.connect(
            temporal_endpoint,
            namespace="default",
            data_converter=pydantic_data_converter,
        )

        logger.debug(
            "Temporal client created",
            extra={
                "endpoint": temporal_endpoint,
                "data_converter_type": type(client.data_converter).__name__,
            },
        )
        return client


# Global container instance
_container = DependencyContainer()


async def get_temporal_client() -> Client:
    """FastAPI dependency for Temporal client."""
    return await _container.get_temporal_client()


async def get_minio_order_request_repository() -> OrderRequestRepository:
    """FastAPI dependency for direct Minio OrderRequestRepository."""
    return MinioOrderRequestRepository()


async def get_temporal_file_storage_repository() -> FileStorageRepository:
    """FastAPI dependency for FileStorageRepository."""
    from util.repos.minio.file_storage import MinioFileStorageRepository
    from util.repos.temporal.minio_file_storage import (
        TemporalMinioFileStorageRepository,
    )

    minio_repo = MinioFileStorageRepository()
    return TemporalMinioFileStorageRepository(minio_repo)


def _get_minio_endpoint() -> str:
    """Helper to get Minio endpoint with a default for host-side tests."""
    return os.environ.get("MINIO_ENDPOINT", "localhost:9000")


async def get_minio_order_repository() -> MinioOrderRepository:
    """FastAPI dependency for direct Minio OrderRepository."""
    # Instantiated directly, bypassing Temporal proxies
    return MinioOrderRepository(endpoint=_get_minio_endpoint())


async def get_minio_payment_repository() -> MinioPaymentRepository:
    """FastAPI dependency for direct Minio PaymentRepository."""
    # Instantiated directly, bypassing Temporal proxies
    return MinioPaymentRepository(endpoint=_get_minio_endpoint())


async def get_get_order_use_case(
    order_repo: MinioOrderRepository = Depends(get_minio_order_repository),
    payment_repo: MinioPaymentRepository = Depends(
        get_minio_payment_repository
    ),
) -> GetOrderUseCase:
    """FastAPI dependency for GetOrderUseCase."""
    return GetOrderUseCase(
        order_repo=ensure_order_repository(order_repo),
        payment_repo=ensure_payment_repository(payment_repo),
    )


async def get_minio_file_storage_repository() -> FileStorageRepository:
    """FastAPI dependency for direct Minio FileStorageRepository."""
    from util.repos.minio.file_storage import MinioFileStorageRepository

    return MinioFileStorageRepository()


# Note: OrderFulfillmentUseCase and CancelOrderUseCase are used within
# workflows, not directly in the API. The API dispatches workflows using the
# Temporal client. The workflow dependencies are handled by workflow proxies,
# not client-side repositories. For simple CRUD operations like file
# upload/download, use direct repositories.

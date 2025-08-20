"""
Dependency injection for FastAPI endpoints.
"""

import os
import logging

from fastapi import Depends
from temporalio.client import Client
from temporalio.contrib.pydantic import pydantic_data_converter

from sample.repositories import (
    PaymentRepository,
    InventoryRepository,
    OrderRepository,
    OrderRequestRepository,
)
from util.repositories import FileStorageRepository  # Updated import path
from sample.repos.temporal.client_proxies.payment import (
    TemporalPaymentRepository,
)
from sample.repos.temporal.client_proxies.inventory import (
    TemporalInventoryRepository,
)
from sample.repos.temporal.client_proxies.order import TemporalOrderRepository
from sample.repos.temporal.client_proxies.order_request import (
    TemporalOrderRequestRepository,
)
from sample.repos.minio.order_request import MinioOrderRequestRepository
from sample.repos.minio.order import MinioOrderRepository
from sample.repos.minio.payment import MinioPaymentRepository
from util.repos.temporal.minio_file_storage import (
    TemporalMinioFileStorageRepository,
)
from sample.usecase import (
    OrderFulfillmentUseCase,
    GetOrderUseCase,
    CancelOrderUseCase,
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

    def __init__(self):
        self._instances = {}

    async def get_or_create(self, key: str, factory):
        """Get or create a singleton instance."""
        if key not in self._instances:
            self._instances[key] = await factory()
        return self._instances[key]

    async def get_temporal_client(self) -> Client:
        """Get or create Temporal client."""
        return await self.get_or_create(
            "temporal_client", self._create_temporal_client
        )

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


async def get_temporal_payment_repository() -> PaymentRepository:
    """FastAPI dependency for PaymentRepository."""
    client = await get_temporal_client()
    return TemporalPaymentRepository(client)


async def get_temporal_inventory_repository() -> InventoryRepository:
    """FastAPI dependency for InventoryRepository."""
    client = await get_temporal_client()
    return TemporalInventoryRepository(client)


async def get_temporal_order_repository() -> OrderRepository:
    """FastAPI dependency for OrderRepository."""
    client = await get_temporal_client()
    return TemporalOrderRepository(client)


async def get_temporal_order_request_repository() -> OrderRequestRepository:
    """FastAPI dependency for OrderRequestRepository."""
    client = await get_temporal_client()
    return TemporalOrderRequestRepository(client)


async def get_minio_order_request_repository() -> OrderRequestRepository:
    """FastAPI dependency for direct Minio OrderRequestRepository."""
    return MinioOrderRequestRepository()


async def get_temporal_file_storage_repository() -> FileStorageRepository:
    """FastAPI dependency for FileStorageRepository."""
    client = await get_temporal_client()
    return TemporalMinioFileStorageRepository(client)


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


async def get_order_fulfillment_use_case() -> OrderFulfillmentUseCase:
    """FastAPI dependency for OrderFulfillmentUseCase."""
    payment_repo = await get_temporal_payment_repository()
    inventory_repo = await get_temporal_inventory_repository()
    order_repo = (
        await get_temporal_order_repository()
    )  # This remains the Temporal proxy for fulfillment
    order_request_repo = await get_temporal_order_request_repository()
    file_storage_repo = await get_temporal_file_storage_repository()

    return OrderFulfillmentUseCase(
        payment_repo=payment_repo,
        inventory_repo=inventory_repo,
        order_repo=order_repo,
        order_request_repo=order_request_repo,
        file_storage_repo=file_storage_repo,
    )


async def get_cancel_order_use_case() -> CancelOrderUseCase:
    """FastAPI dependency for CancelOrderUseCase."""
    order_repo = await get_temporal_order_repository()
    payment_repo = await get_temporal_payment_repository()

    return CancelOrderUseCase(
        order_repo=order_repo,
        payment_repo=payment_repo,
    )

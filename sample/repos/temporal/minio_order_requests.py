"""
Temporal Activity implementation of OrderRequestRepository.
Wraps MinioOrderRequestRepository and exposes its methods as Temporal
activities.
"""

import logging
from typing import Optional
from temporalio import activity

from sample.repositories import OrderRequestRepository
from sample.repos.minio.order_request import MinioOrderRequestRepository

logger = logging.getLogger(__name__)


class TemporalMinioOrderRequestRepository(OrderRequestRepository):
    """
    Temporal Activity implementation of OrderRequestRepository.
    Delegates calls to a concrete MinioOrderRequestRepository instance.
    """

    def __init__(self, minio_order_request_repo: MinioOrderRequestRepository):
        self._minio_order_request_repo = minio_order_request_repo
        logger.debug("Initialized TemporalMinioOrderRequestRepository")

    @activity.defn(
        name="sample.order_fulfillment.order_request_repo.minio.store_bidirectional_mapping"
    )
    async def store_bidirectional_mapping(
        self, request_id: str, order_id: str
    ) -> None:
        """Store bidirectional mapping via the underlying Minio repository."""
        logger.info(
            "Activity: store_bidirectional_mapping called",
            extra={"request_id": request_id, "order_id": order_id},
        )
        await self._minio_order_request_repo.store_bidirectional_mapping(
            request_id, order_id
        )

    @activity.defn(
        name="sample.order_fulfillment.order_request_repo.minio.get_order_id_for_request"
    )
    async def get_order_id_for_request(
        self, request_id: str
    ) -> Optional[str]:
        """Get order ID for a given request ID via the underlying Minio
        repository.
        """
        logger.info(
            "Activity: get_order_id_for_request called",
            extra={"request_id": request_id},
        )
        return await self._minio_order_request_repo.get_order_id_for_request(
            request_id
        )

    @activity.defn(
        name="sample.order_fulfillment.order_request_repo.minio.get_request_id_for_order"
    )
    async def get_request_id_for_order(self, order_id: str) -> Optional[str]:
        """Get request ID for a given order ID via the underlying Minio
        repository.
        """
        logger.info(
            "Activity: get_request_id_for_order called",
            extra={"order_id": order_id},
        )
        return await self._minio_order_request_repo.get_request_id_for_order(
            order_id
        )

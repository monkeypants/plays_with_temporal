"""
Temporal Activity implementation of OrderRepository.
Wraps MinioOrderRepository and exposes its methods as Temporal activities.
"""

import logging
from typing import Optional

from temporalio import activity

from sample.domain import Order
from sample.repositories import OrderRepository
from sample.repos.minio.order import MinioOrderRepository

logger = logging.getLogger(__name__)


class TemporalMinioOrderRepository(OrderRepository):
    """
    Temporal Activity implementation of OrderRepository.
    Delegates calls to a concrete MinioOrderRepository instance.
    """

    def __init__(self, minio_order_repo: MinioOrderRepository):
        self._minio_order_repo = minio_order_repo
        logger.debug("Initialized TemporalMinioOrderRepository")

    @activity.defn(
        name="sample.order_fulfillment.order_repo.minio.generate_order_id"
    )
    async def generate_order_id(self) -> str:
        """Generate a unique order ID via the underlying Minio repository."""
        logger.info("Activity: generate_order_id called")
        return await self._minio_order_repo.generate_order_id()

    @activity.defn(
        name="sample.order_fulfillment.order_repo.minio.save_order"
    )
    async def save_order(self, order: Order) -> None:
        """Save an order via the underlying Minio repository."""
        logger.info(
            "Activity: save_order called",
            extra={"order_id": order.order_id, "status": order.status},
        )
        await self._minio_order_repo.save_order(order)

    @activity.defn(name="sample.order_fulfillment.order_repo.minio.get_order")
    async def get_order(self, order_id: str) -> Optional[Order]:
        """Get an order via the underlying Minio repository."""
        logger.info(
            "Activity: get_order called", extra={"order_id": order_id}
        )
        return await self._minio_order_repo.get_order(order_id)

    @activity.defn(name="sample.cancel_order.order_repo.minio.cancel_order")
    async def cancel_order(
        self, order_id: str, reason: Optional[str] = None
    ) -> None:
        """Cancel an order via the underlying Minio repository."""
        logger.info(
            "Activity: cancel_order called",
            extra={"order_id": order_id, "reason": reason},
        )
        await self._minio_order_repo.cancel_order(order_id, reason)

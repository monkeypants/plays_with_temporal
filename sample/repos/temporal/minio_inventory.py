"""
Temporal Activity implementation of InventoryRepository.
Wraps MinioInventoryRepository and exposes its methods as Temporal activities.
"""

import logging
from typing import List

from temporalio import activity

from sample.domain import Order, InventoryItem, InventoryReservationOutcome
from sample.repositories import InventoryRepository
from sample.repos.minio.inventory import MinioInventoryRepository

logger = logging.getLogger(__name__)


class TemporalMinioInventoryRepository(InventoryRepository):
    """
    Temporal Activity implementation of InventoryRepository.
    Delegates calls to a concrete MinioInventoryRepository instance.
    """

    def __init__(self, minio_inventory_repo: MinioInventoryRepository):
        self._minio_inventory_repo = minio_inventory_repo
        logger.debug("Initialized TemporalMinioInventoryRepository")

    @activity.defn(
        name="sample.order_fulfillment.inventory_repo.minio.reserve_items"
    )
    async def reserve_items(
        self, order: Order
    ) -> InventoryReservationOutcome:
        """Reserve inventory items via the underlying Minio repository."""
        logger.info(
            "Activity: reserve_items called",
            extra={
                "order_id": order.order_id,
                "item_count": len(order.items),
            },
        )
        return await self._minio_inventory_repo.reserve_items(order)

    @activity.defn(
        name="sample.cancel_order.inventory_repo.minio.release_items"
    )
    async def release_items(self, order: Order) -> List[InventoryItem]:
        """Release inventory items via the underlying Minio repository."""
        logger.info(
            "Activity: release_items called",
            extra={
                "order_id": order.order_id,
                "item_count": len(order.items),
            },
        )
        return await self._minio_inventory_repo.release_items(order)

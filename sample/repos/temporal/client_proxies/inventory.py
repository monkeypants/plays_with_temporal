"""
Client-side proxy for InventoryRepository that dispatches Temporal workflows.
"""

import logging
from typing import List, Optional

from temporalio.client import Client

from sample.domain import Order, InventoryReservationOutcome, InventoryItem
from sample.repositories import InventoryRepository

logger = logging.getLogger(__name__)


class TemporalInventoryRepository(InventoryRepository):
    """
    Client-side proxy for InventoryRepository that dispatches Temporal
    workflows.
    """

    def __init__(
        self,
        client: Client,
        concrete_repo: Optional[InventoryRepository] = None,
    ):
        self.client = client
        self.workflow_timeout_seconds = 60

    async def reserve_items(
        self, order: Order
    ) -> InventoryReservationOutcome:
        """Reserve items via Temporal workflow dispatch."""
        logger.debug(
            "Dispatching reserve_items workflow",
            extra={
                "order_id": order.order_id,
                "item_count": len(order.items),
            },
        )

        try:
            # This would typically be part of the OrderFulfillmentWorkflow
            # For standalone inventory operations, we'd dispatch a dedicated
            # workflow

            # For now, return a mock outcome to show the pattern
            reserved_items = [
                InventoryItem(
                    product_id=item.product_id,
                    quantity=item.quantity,
                    reserved=item.quantity,
                )
                for item in order.items
            ]

            outcome = InventoryReservationOutcome(
                status="reserved",
                reserved_items=reserved_items,
            )

            logger.info(
                "Items reserved via workflow",
                extra={
                    "order_id": order.order_id,
                    "reserved_count": len(reserved_items),
                },
            )

            return outcome
        except Exception as e:
            logger.error(
                "Failed to reserve items via workflow",
                extra={"order_id": order.order_id, "error": str(e)},
            )
            raise

    async def release_items(self, order: Order) -> List[InventoryItem]:
        """Release items via Temporal workflow dispatch."""
        logger.debug(
            "Dispatching release_items workflow",
            extra={
                "order_id": order.order_id,
                "item_count": len(order.items),
            },
        )

        try:
            # This would typically be part of compensation workflows
            # For standalone inventory operations, we'd dispatch a dedicated
            # workflow

            # For now, return mock items to show the pattern
            released_items = [
                InventoryItem(
                    product_id=item.product_id,
                    quantity=item.quantity,
                    reserved=0,
                )
                for item in order.items
            ]

            logger.info(
                "Items released via workflow",
                extra={
                    "order_id": order.order_id,
                    "released_count": len(released_items),
                },
            )

            return released_items
        except Exception as e:
            logger.error(
                "Failed to release items via workflow",
                extra={"order_id": order.order_id, "error": str(e)},
            )
            raise

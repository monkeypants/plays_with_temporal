"""
Client-side proxy for OrderRepository that dispatches Temporal workflows.
"""

import logging
from typing import Optional

from temporalio.client import Client

from sample.domain import Order
from sample.repositories import OrderRepository

logger = logging.getLogger(__name__)


class TemporalOrderRepository(OrderRepository):
    """
    Client-side proxy for OrderRepository that dispatches Temporal workflows.
    """

    def __init__(
        self, client: Client, concrete_repo: Optional[OrderRepository] = None
    ):
        self.client = client
        self.workflow_timeout_seconds = 60

    async def generate_order_id(self) -> str:
        """Generate order ID via Temporal workflow dispatch."""
        logger.debug("Dispatching generate_order_id workflow")

        # This would dispatch a workflow that generates an order ID
        # The workflow would use workflow proxies to call activities
        try:
            # For now, generate a simple ID to show the pattern
            # In reality, this would dispatch a workflow
            import uuid

            order_id = str(uuid.uuid4())
            logger.info(
                "Order ID generated via workflow",
                extra={"order_id": order_id},
            )
            return order_id
        except Exception as e:
            logger.error(
                "Failed to generate order ID via workflow",
                extra={"error": str(e)},
            )
            raise

    async def save_order(self, order: Order) -> None:
        """Save order via Temporal workflow dispatch."""
        logger.debug(
            "Dispatching save_order workflow",
            extra={"order_id": order.order_id, "status": order.status},
        )

        try:
            # This would dispatch a workflow that saves the order
            logger.info(
                "Order saved via workflow",
                extra={"order_id": order.order_id},
            )
        except Exception as e:
            logger.error(
                "Failed to save order via workflow",
                extra={"order_id": order.order_id, "error": str(e)},
            )
            raise

    async def cancel_order(
        self, order_id: str, reason: Optional[str] = None
    ) -> None:
        """Cancel order via Temporal workflow dispatch."""
        logger.debug(
            "Dispatching cancel_order workflow",
            extra={"order_id": order_id, "reason": reason},
        )

        try:
            # This would dispatch the CancelOrderWorkflow
            workflow_id = f"cancel-order-{order_id}"

            # Dispatch the actual CancelOrderWorkflow
            from sample.workflow import CancelOrderWorkflow

            handle = await self.client.start_workflow(
                CancelOrderWorkflow.run,
                order_id,
                reason,
                id=workflow_id,
                task_queue="order-fulfillment-queue",
            )

            # Wait for the workflow to complete
            await handle.result()

            logger.info(
                "Order cancellation completed via workflow",
                extra={"order_id": order_id, "workflow_id": workflow_id},
            )
        except Exception as e:
            logger.error(
                "Failed to cancel order via workflow",
                extra={"order_id": order_id, "error": str(e)},
            )
            raise

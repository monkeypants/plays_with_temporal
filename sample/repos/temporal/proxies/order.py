"""
Workflow-specific proxy for OrderRepository.
This class is used *inside* Temporal workflows to call activities.
It ensures workflow determinism by delegating all non-deterministic
operations to activities.
"""

import logging
from typing import Optional

from temporalio import workflow

from sample.domain import Order
from sample.repositories import OrderRepository

logger = logging.getLogger(__name__)


class WorkflowOrderRepositoryProxy(OrderRepository):
    """
    Workflow implementation of OrderRepository that calls activities.
    This proxy ensures that all interactions with the OrderRepository are
    performed via Temporal activities, maintaining workflow determinism.
    """

    def __init__(self):
        self.activity_timeout = workflow.timedelta(seconds=10)
        logger.debug("Initialized WorkflowOrderRepositoryProxy")

    async def generate_order_id(self) -> str:
        """Generate a unique order ID by executing an activity."""
        logger.debug("Workflow: Calling generate_order_id activity")

        result = await workflow.execute_activity(
            "sample.order_fulfillment.order_repo.minio.generate_order_id",
            start_to_close_timeout=self.activity_timeout,
        )

        logger.debug(
            "Workflow: generate_order_id activity completed",
            extra={"order_id": result},
        )
        return result  # type: ignore[no-any-return]

    async def save_order(self, order: Order) -> None:
        """Persist the state of an order by executing an activity."""
        logger.debug(
            "Workflow: Calling save_order activity",
            extra={"order_id": order.order_id, "status": order.status},
        )
        await workflow.execute_activity(
            "sample.order_fulfillment.order_repo.minio.save_order",
            order,
            start_to_close_timeout=self.activity_timeout,
        )
        logger.debug(
            "Workflow: save_order activity completed",
            extra={"order_id": order.order_id},
        )

    async def get_order(self, order_id: str) -> Optional[Order]:
        """Retrieve an order by its ID by executing an activity."""
        logger.debug(
            "Workflow: Calling get_order activity",
            extra={"order_id": order_id},
        )

        # The activity returns an Optional[Order] Pydantic model, but
        # Temporal's data converter might deserialize it as a dict or None
        # in the workflow context.
        # Explicitly re-validate if not None.
        raw_result = await workflow.execute_activity(
            "sample.order_fulfillment.order_repo.minio.get_order",
            order_id,
            start_to_close_timeout=self.activity_timeout,
        )

        result = None
        if raw_result is not None:
            result = Order.model_validate(raw_result)

        logger.debug(
            "Workflow: get_order activity completed",
            extra={
                "order_id": order_id,
                "found": result is not None,
                "result_type": type(result).__name__ if result else None,
            },
        )
        return result

    async def cancel_order(
        self, order_id: str, reason: Optional[str] = None
    ) -> None:
        """Cancel an order by executing an activity."""
        logger.debug(
            "Workflow: Calling cancel_order activity",
            extra={"order_id": order_id, "reason": reason},
        )
        await workflow.execute_activity(
            "sample.cancel_order.order_repo.minio.cancel_order",
            {
                "order_id": order_id,
                "reason": reason,
            },  # Pass as dict for activity args
            start_to_close_timeout=self.activity_timeout,
        )
        logger.debug(
            "Workflow: cancel_order activity completed",
            extra={"order_id": order_id},
        )

"""
Workflow-specific proxy for InventoryRepository.
This class is used *inside* Temporal workflows to call activities.
It ensures workflow determinism by delegating all non-deterministic
operations to activities.
"""

import logging
from typing import List

from temporalio import workflow
from temporalio.common import RetryPolicy

from sample.domain import Order, InventoryItem, InventoryReservationOutcome
from sample.repositories import InventoryRepository

logger = logging.getLogger(__name__)


class WorkflowInventoryRepositoryProxy(InventoryRepository):
    """
    Workflow implementation of InventoryRepository that calls activities.
    This proxy ensures that all interactions with the InventoryRepository are
    performed via Temporal activities, maintaining workflow determinism.
    """

    def __init__(self):
        self.activity_timeout = workflow.timedelta(seconds=10)
        self.activity_fail_fast_retry_policy = RetryPolicy(
            initial_interval=workflow.timedelta(seconds=1),
            maximum_attempts=1,
            backoff_coefficient=1.0,
            maximum_interval=workflow.timedelta(seconds=1),
        )
        logger.debug("Initialized WorkflowInventoryRepositoryProxy")

    async def reserve_items(
        self, order: Order
    ) -> InventoryReservationOutcome:
        """Reserve inventory items by executing an activity."""
        logger.debug(
            "Workflow: Calling reserve_items activity",
            extra={
                "order_id": order.order_id,
                "item_count": len(order.items),
            },
        )

        # The activity returns a Pydantic model, but Temporal's data converter
        # might deserialize it as a dict in the workflow context.
        # Explicitly re-validate to ensure it's a Pydantic model.
        raw_result = await workflow.execute_activity(
            "sample.order_fulfillment.inventory_repo.minio.reserve_items",
            order,
            start_to_close_timeout=self.activity_timeout,
            retry_policy=self.activity_fail_fast_retry_policy,
        )
        result = InventoryReservationOutcome.model_validate(raw_result)

        logger.debug(
            "Workflow: reserve_items activity completed",
            extra={
                "order_id": order.order_id,
                "result_type": type(result).__name__,
                "result_count": (
                    len(result.reserved_items) if result.reserved_items else 0
                ),
            },
        )

        return result

    async def release_items(self, order: Order) -> List[InventoryItem]:
        """Release previously reserved inventory items by executing an
        activity.
        """
        logger.debug(
            "Workflow: Calling release_items activity",
            extra={
                "order_id": order.order_id,
                "item_count": len(order.items),
            },
        )

        # The activity returns a list of Pydantic models, but Temporal's
        # data converter might deserialize it as a list of dicts in the
        # workflow context. Explicitly re-validate each item to ensure
        # they are Pydantic models.
        raw_results = await workflow.execute_activity(
            "sample.cancel_order.inventory_repo.minio.release_items",
            order,
            start_to_close_timeout=self.activity_timeout,
        )
        # Convert each dict in the list back to an InventoryItem Pydantic
        # model
        results = [
            InventoryItem.model_validate(item_data)
            for item_data in raw_results
        ]

        logger.debug(
            "Workflow: release_items activity completed",
            extra={
                "order_id": order.order_id,
                "result_type": type(results).__name__,
                "result_count": (
                    len(results) if isinstance(results, list) else 0
                ),
            },
        )

        return results

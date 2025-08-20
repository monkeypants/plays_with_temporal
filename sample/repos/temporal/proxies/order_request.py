"""
Workflow-specific proxy for OrderRequestRepository.
This class is used *inside* Temporal workflows to call activities.
It ensures workflow determinism by delegating all non-deterministic
operations to activities.
"""

import logging
from typing import Optional

from temporalio import workflow

from sample.repositories import OrderRequestRepository

logger = logging.getLogger(__name__)


class WorkflowOrderRequestRepositoryProxy(OrderRequestRepository):
    """
    Workflow implementation of OrderRequestRepository that calls activities.
    This proxy ensures that all interactions with the
    OrderRequestRepository are performed via Temporal activities,
    maintaining workflow determinism.
    """

    def __init__(self) -> None:
        self.activity_timeout = workflow.timedelta(seconds=10)
        logger.debug("Initialized WorkflowOrderRequestRepositoryProxy")

    async def store_bidirectional_mapping(
        self, request_id: str, order_id: str
    ) -> None:
        """Store bidirectional mapping by executing an activity."""
        logger.debug(
            "Workflow: Calling store_bidirectional_mapping activity",
            extra={"request_id": request_id, "order_id": order_id},
        )

        await workflow.execute_activity(
            "sample.order_fulfillment.order_request_repo.minio.store_bidirectional_mapping",
            args=[request_id, order_id],
            start_to_close_timeout=self.activity_timeout,
        )

        logger.info(
            "Workflow: Bidirectional mapping stored",
            extra={"request_id": request_id, "order_id": order_id},
        )

    async def get_order_id_for_request(
        self, request_id: str
    ) -> Optional[str]:
        """Get order ID for a given request ID by executing an activity."""
        logger.debug(
            "Workflow: Calling get_order_id_for_request activity",
            extra={"request_id": request_id},
        )

        result = await workflow.execute_activity(
            "sample.order_fulfillment.order_request_repo.minio.get_order_id_for_request",
            args=[request_id],
            start_to_close_timeout=self.activity_timeout,
        )

        logger.debug(
            "Workflow: get_order_id_for_request activity completed",
            extra={"request_id": request_id, "order_id": result},
        )
        return result  # type: ignore[no-any-return]

    async def get_request_id_for_order(self, order_id: str) -> Optional[str]:
        """Get request ID for a given order ID by executing an activity."""
        logger.debug(
            "Workflow: Calling get_request_id_for_order activity",
            extra={"order_id": order_id},
        )

        result = await workflow.execute_activity(
            "sample.order_fulfillment.order_request_repo.minio.get_request_id_for_order",
            args=[order_id],
            start_to_close_timeout=self.activity_timeout,
        )

        logger.debug(
            "Workflow: get_request_id_for_order activity completed",
            extra={"order_id": order_id, "request_id": result},
        )
        return result  # type: ignore[no-any-return]

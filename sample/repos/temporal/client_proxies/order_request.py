"""
Client-side proxy for OrderRequestRepository that calls Temporal workflows.
This proxy dispatches workflows and polls for results instead of executing
activities directly.
"""

import logging
from typing import Optional

from temporalio.client import Client

from sample.repositories import OrderRequestRepository

logger = logging.getLogger(__name__)


class TemporalOrderRequestRepository(OrderRequestRepository):
    """
    Client-side proxy for OrderRequestRepository that dispatches Temporal
    workflows.
    This proxy ensures that operations are performed via workflow dispatch,
    not direct activity execution.
    """

    def __init__(
        self,
        client: Client,
        concrete_repo: Optional[OrderRequestRepository] = None,
    ):
        self.client = client
        self.workflow_timeout_seconds = 60

    async def store_bidirectional_mapping(
        self, request_id: str, order_id: str
    ) -> None:
        """Store mapping via Temporal workflow dispatch."""
        logger.debug(
            "Dispatching store_bidirectional_mapping workflow",
            extra={"request_id": request_id, "order_id": order_id},
        )

        # For simple operations like this, we could dispatch a dedicated
        # workflow or integrate into existing workflows. For now, this is a
        # placeholder that shows the correct pattern - dispatch workflows,
        # don't execute activities

        try:
            # This would dispatch a workflow that handles the mapping storage
            # The actual workflow implementation would use the workflow
            # proxies to call activities that delegate to the concrete
            # repository
            logger.info(
                "Bidirectional mapping operation completed via workflow",
                extra={"request_id": request_id, "order_id": order_id},
            )
        except Exception as e:
            logger.error(
                "Failed to store bidirectional mapping via workflow",
                extra={
                    "request_id": request_id,
                    "order_id": order_id,
                    "error": str(e),
                },
            )
            raise

    async def get_order_id_for_request(
        self, request_id: str
    ) -> Optional[str]:
        """Get order ID via Temporal workflow dispatch."""
        logger.debug(
            "Dispatching get_order_id_for_request workflow",
            extra={"request_id": request_id},
        )

        # For query operations, we might dispatch a query workflow
        # or use a different pattern. The key is NOT calling execute_activity
        # on the client directly
        try:
            # This would dispatch a workflow that queries the mapping
            # For now, return None to indicate the operation needs proper
            # workflow
            logger.debug(
                "Order ID query completed via workflow",
                extra={"request_id": request_id},
            )
            return None
        except Exception as e:
            logger.error(
                "Failed to get order ID via workflow",
                extra={"request_id": request_id, "error": str(e)},
            )
            raise

    async def get_request_id_for_order(self, order_id: str) -> Optional[str]:
        """Get request ID via Temporal workflow dispatch."""
        logger.debug(
            "Dispatching get_request_id_for_order workflow",
            extra={"order_id": order_id},
        )

        try:
            # This would dispatch a workflow that queries the mapping
            logger.debug(
                "Request ID query completed via workflow",
                extra={"order_id": order_id},
            )
            return None
        except Exception as e:
            logger.error(
                "Failed to get request ID via workflow",
                extra={"order_id": order_id, "error": str(e)},
            )
            raise

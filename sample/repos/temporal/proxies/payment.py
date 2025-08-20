"""
Workflow-specific proxy for PaymentRepository.
This class is used *inside* Temporal workflows to call activities.
It ensures workflow determinism by delegating all non-deterministic
operations to activities.
"""

import logging
from typing import Optional

from temporalio import workflow
from temporalio.common import RetryPolicy

from sample.domain import (
    Order,
    Payment,
    PaymentOutcome,
    RefundPaymentArgs,
    RefundPaymentOutcome,
)  # Added RefundPaymentArgs, RefundPaymentOutcome
from sample.repositories import PaymentRepository

logger = logging.getLogger(__name__)


class WorkflowPaymentRepositoryProxy(PaymentRepository):
    """
    Workflow implementation of PaymentRepository that calls activities.
    This proxy ensures that all interactions with the PaymentRepository are
    performed via Temporal activities, maintaining workflow determinism.
    """

    def __init__(self) -> None:
        self.activity_timeout = workflow.timedelta(seconds=10)
        self.activity_fail_fast_retry_policy = RetryPolicy(
            initial_interval=workflow.timedelta(seconds=1),
            maximum_attempts=1,
            backoff_coefficient=1.0,
            maximum_interval=workflow.timedelta(seconds=1),
        )
        logger.debug("Initialized WorkflowPaymentRepositoryProxy")

    async def process_payment(self, order: Order) -> PaymentOutcome:
        """Process payment by executing an activity."""
        logger.debug(
            "Workflow: Calling process_payment activity",
            extra={
                "order_id": order.order_id,
                "amount": str(order.total_amount),
            },
        )

        # The activity returns a Pydantic model, but Temporal's data converter
        # might deserialize it as a dict in the workflow context.
        # Explicitly re-validate to ensure it's a Pydantic model.
        raw_result = await workflow.execute_activity(
            "sample.order_fulfillment.payment_repo.minio.process_payment",
            order,
            start_to_close_timeout=self.activity_timeout,
            retry_policy=self.activity_fail_fast_retry_policy,
        )
        result = PaymentOutcome.model_validate(raw_result)

        logger.debug(
            "Workflow: process_payment activity completed",
            extra={
                "order_id": order.order_id,
                "result_type": type(result).__name__,
            },
        )

        return result

    async def get_payment(self, payment_id: str) -> Optional[Payment]:
        """Get payment by ID by executing an activity."""
        logger.debug(
            "Workflow: Calling get_payment activity",
            extra={"payment_id": payment_id},
        )

        # The activity returns an Optional[Payment] Pydantic model, but
        # Temporal's data converter might deserialize it as a dict or None
        # in the workflow context. Explicitly re-validate if not None.
        raw_result = await workflow.execute_activity(
            "sample.order_fulfillment.payment_repo.minio.get_payment",
            payment_id,
            start_to_close_timeout=self.activity_timeout,
        )

        result = None
        if raw_result is not None:
            result = Payment.model_validate(raw_result)

        logger.debug(
            "Workflow: get_payment activity completed",
            extra={
                "payment_id": payment_id,
                "found": result is not None,
                "result_type": type(result).__name__ if result else None,
            },
        )

        return result

    async def refund_payment(
        self, args: RefundPaymentArgs
    ) -> RefundPaymentOutcome:
        """Refund a previously processed payment by executing an activity."""
        logger.debug(
            "Workflow: Calling refund_payment activity",
            extra={"payment_id": args.payment_id, "amount": str(args.amount)},
        )
        raw_result = await workflow.execute_activity(
            "sample.cancel_order.payment_repo.minio.refund_payment",
            args,
            start_to_close_timeout=self.activity_timeout,
            retry_policy=self.activity_fail_fast_retry_policy,
        )
        result = RefundPaymentOutcome.model_validate(raw_result)
        logger.debug(
            "Workflow: refund_payment activity completed",
            extra={
                "payment_id": args.payment_id,
                "result_status": result.status,
            },
        )
        return result

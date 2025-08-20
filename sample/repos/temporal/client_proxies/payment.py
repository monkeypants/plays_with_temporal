"""
Client-side proxy for PaymentRepository that dispatches Temporal workflows.
"""

import logging
from typing import Optional

from temporalio.client import Client

from sample.domain import (
    Order,
    Payment,
    PaymentOutcome,
    RefundPaymentArgs,
    RefundPaymentOutcome,
)
from sample.repositories import PaymentRepository

logger = logging.getLogger(__name__)


class TemporalPaymentRepository(PaymentRepository):
    """
    Client-side proxy for PaymentRepository that dispatches Temporal
    workflows.
    """

    def __init__(
        self,
        client: Client,
        concrete_repo: Optional[PaymentRepository] = None,
    ):
        self.client = client
        self.workflow_timeout_seconds = 60

    async def process_payment(self, order: Order) -> PaymentOutcome:
        """Process payment via Temporal workflow dispatch."""
        logger.debug(
            "Dispatching process_payment workflow",
            extra={
                "order_id": order.order_id,
                "amount": str(order.total_amount),
            },
        )

        try:
            # This would typically be part of the OrderFulfillmentWorkflow
            # For standalone payment processing, we'd dispatch a dedicated
            # workflow

            # For now, return a mock outcome to show the pattern
            # In reality, this would dispatch a workflow and wait for results
            payment = Payment(
                payment_id=f"pmt_{order.order_id}",
                order_id=order.order_id,
                amount=order.total_amount,
                status="completed",
                transaction_id=f"tx_{order.order_id}",
            )

            outcome = PaymentOutcome(
                status="completed",
                payment=payment,
            )

            logger.info(
                "Payment processed via workflow",
                extra={
                    "order_id": order.order_id,
                    "payment_id": payment.payment_id,
                },
            )

            return outcome
        except Exception as e:
            logger.error(
                "Failed to process payment via workflow",
                extra={"order_id": order.order_id, "error": str(e)},
            )
            raise

    async def get_payment(self, payment_id: str) -> Optional[Payment]:
        """Get payment via Temporal workflow dispatch."""
        logger.debug(
            "Dispatching get_payment workflow",
            extra={"payment_id": payment_id},
        )

        try:
            # This would dispatch a workflow that queries payment data
            logger.debug(
                "Payment query completed via workflow",
                extra={"payment_id": payment_id},
            )
            return None
        except Exception as e:
            logger.error(
                "Failed to get payment via workflow",
                extra={"payment_id": payment_id, "error": str(e)},
            )
            raise

    async def refund_payment(
        self, args: RefundPaymentArgs
    ) -> RefundPaymentOutcome:
        """Refund payment via Temporal workflow dispatch."""
        logger.debug(
            "Dispatching refund_payment workflow",
            extra={"payment_id": args.payment_id, "amount": str(args.amount)},
        )

        try:
            # This would typically be part of the CancelOrderWorkflow
            # For standalone refunds, we'd dispatch a dedicated workflow

            # For now, return a mock outcome to show the pattern
            outcome = RefundPaymentOutcome(
                status="refunded",
                refund_id=f"ref_{args.payment_id}",
            )

            logger.info(
                "Payment refunded via workflow",
                extra={
                    "payment_id": args.payment_id,
                    "refund_id": outcome.refund_id,
                },
            )

            return outcome
        except Exception as e:
            logger.error(
                "Failed to refund payment via workflow",
                extra={"payment_id": args.payment_id, "error": str(e)},
            )
            raise

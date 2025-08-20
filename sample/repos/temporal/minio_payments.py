"""
Temporal Activity implementation of PaymentRepository.
Wraps MinioPaymentRepository and exposes its methods as Temporal activities.
"""

import logging
from typing import Optional

from temporalio import activity

from sample.domain import (
    Order,
    Payment,
    PaymentOutcome,
    RefundPaymentArgs,
    RefundPaymentOutcome,
)
from sample.repositories import PaymentRepository
from sample.repos.minio.payment import MinioPaymentRepository

logger = logging.getLogger(__name__)


class TemporalMinioPaymentRepository(PaymentRepository):
    """
    Temporal Activity implementation of PaymentRepository.
    Delegates calls to a concrete MinioPaymentRepository instance.
    """

    def __init__(
        self,
        minio_payment_repo: MinioPaymentRepository,
    ):
        self._minio_payment_repo = minio_payment_repo
        logger.debug("Initialized TemporalMinioPaymentRepository")

    @activity.defn(
        name="sample.order_fulfillment.payment_repo.minio.process_payment"
    )
    async def process_payment(self, order: Order) -> PaymentOutcome:
        """Process payment via the underlying Minio repository."""
        logger.info(
            "Activity: process_payment called",
            extra={
                "order_id": order.order_id,
                "amount": str(order.total_amount),
            },
        )
        return await self._minio_payment_repo.process_payment(order)

    @activity.defn(
        name="sample.order_fulfillment.payment_repo.minio.get_payment"
    )
    async def get_payment(self, payment_id: str) -> Optional[Payment]:
        """Get payment via the underlying Minio repository."""
        logger.info(
            "Activity: get_payment called", extra={"payment_id": payment_id}
        )
        return await self._minio_payment_repo.get_payment(payment_id)

    @activity.defn(
        name="sample.cancel_order.payment_repo.minio.refund_payment"
    )
    async def refund_payment(
        self, args: RefundPaymentArgs
    ) -> RefundPaymentOutcome:
        """Refund payment via the underlying Minio repository."""
        logger.info(
            "Activity: refund_payment called",
            extra={"payment_id": args.payment_id, "amount": str(args.amount)},
        )
        return await self._minio_payment_repo.refund_payment(args)

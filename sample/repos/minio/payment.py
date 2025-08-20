"""
Minio implementation of PaymentRepository.
"""

import io
import logging
from datetime import datetime
from typing import Optional
from minio import Minio  # type: ignore[import-untyped]
from minio.error import S3Error  # type: ignore[import-untyped]

from typing import Literal
from sample.domain import (
    Order,
    Payment,
    PaymentOutcome,
    RefundPaymentArgs,
    RefundPaymentOutcome,
)  # Added RefundPaymentArgs, RefundPaymentOutcome
from sample.repositories import PaymentRepository

logger = logging.getLogger(__name__)


class MinioPaymentRepository(PaymentRepository):
    """
    Minio implementation of PaymentRepository that uses Minio for persistence.
    """

    def __init__(self, endpoint: str):
        minio_endpoint = endpoint
        logger.debug(
            "Initializing MinioPaymentRepository",
            extra={"minio_endpoint": minio_endpoint},
        )

        self.client = Minio(
            minio_endpoint,
            access_key="minioadmin",
            secret_key="minioadmin",
            secure=False,
        )
        self.bucket_name = "payments"
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self) -> None:
        try:
            if not self.client.bucket_exists(self.bucket_name):
                logger.info(
                    "Creating payments bucket",
                    extra={"bucket_name": self.bucket_name},
                )
                self.client.make_bucket(self.bucket_name)
            else:
                logger.debug(
                    "Payments bucket already exists",
                    extra={"bucket_name": self.bucket_name},
                )
        except S3Error as e:
            logger.error(
                "Failed to create payments bucket",
                extra={"bucket_name": self.bucket_name, "error": str(e)},
            )
            raise

    async def process_payment(self, order: Order) -> PaymentOutcome:
        """Process payment and persist the result to Minio."""
        logger.info(
            "Processing payment via MinioPaymentRepository",
            extra={
                "order_id": order.order_id,
                "customer_id": order.customer_id,
                "amount": str(order.total_amount),
            },
        )

        payment_status: Literal["completed", "failed", "pending", "cancelled", "refunded"] = "completed"
        payment_reason = None

        # Create the payment object with the determined status
        payment = Payment(
            payment_id=f"pmt_{order.order_id}",
            order_id=order.order_id,
            amount=order.total_amount,
            status=payment_status,
            transaction_id=(
                f"tx_{order.order_id}"
                if payment_status == "completed"
                else None
            ),
        )

        logger.debug(
            "Payment object created",
            extra={
                "payment_id": payment.payment_id,
                "order_id": payment.order_id,
                "status": payment.status,
            },
        )

        # Persist the payment object to Minio using Pydantic serialization
        try:
            payment_json = payment.model_dump_json().encode("utf-8")
            data_stream = io.BytesIO(payment_json)
            self.client.put_object(
                bucket_name=self.bucket_name,
                object_name=payment.payment_id,
                data=data_stream,
                length=len(payment_json),
                metadata={"order_id": payment.order_id},
            )
            logger.info(
                "Payment persisted to Minio storage",
                extra={
                    "payment_id": payment.payment_id,
                    "order_id": payment.order_id,
                    "bucket": self.bucket_name,
                    "persisted_status": payment.status,
                },
            )
        except S3Error as e:
            logger.error(
                "Failed to persist payment to Minio",
                extra={
                    "payment_id": payment.payment_id,
                    "order_id": payment.order_id,
                    "error": str(e),
                },
            )
            raise

        # Create the payment object with the determined status
        payment = Payment(
            payment_id=f"pmt_{order.order_id}",
            order_id=order.order_id,
            amount=order.total_amount,
            status=payment_status,
            transaction_id=(
                f"tx_{order.order_id}"
                if payment_status == "completed"
                else None
            ),
        )

        logger.debug(
            "MinioPaymentRepository: Payment object created for persistence",
            extra={
                "payment_id": payment.payment_id,
                "order_id": payment.order_id,
                "status": payment.status,
                "amount": str(payment.amount),
            },
        )

        # Persist the payment object to Minio using Pydantic serialization
        object_name = payment.payment_id
        payment_json = payment.model_dump_json().encode("utf-8")
        data_stream = io.BytesIO(payment_json)
        try:
            # Check if object exists and if content is same (idempotency)
            try:
                existing_response = self.client.get_object(
                    bucket_name=self.bucket_name, object_name=object_name
                )
                existing_data = existing_response.read()
                existing_response.close()
                existing_response.release_conn()

                if existing_data == payment_json:
                    logger.debug(
                        "MinioPaymentRepository: Payment object already "
                        "exists with correct content, skipping put "
                        "(idempotent)",
                        extra={
                            "payment_id": payment.payment_id,
                            "object_name": object_name,
                        },
                    )
                    return PaymentOutcome(
                        status=payment_status,
                        payment=(
                            payment if payment_status == "completed" else None
                        ),
                        reason=payment_reason,
                    )
                else:
                    logger.warning(
                        "MinioPaymentRepository: Payment object exists with "
                        "different content, overwriting",
                        extra={
                            "payment_id": payment.payment_id,
                            "object_name": object_name,
                        },
                    )

            except S3Error as e:
                if getattr(e, "code", None) == "NoSuchKey":
                    logger.debug(
                        "MinioPaymentRepository: Payment object not found, "
                        "creating new",
                        extra={
                            "payment_id": payment.payment_id,
                            "object_name": object_name,
                        },
                    )
                else:
                    raise  # Re-raise if it's another S3 error

            self.client.put_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                data=data_stream,
                length=len(payment_json),
                metadata={
                    "order_id": payment.order_id,
                    "status": payment.status,
                    "processed_at": datetime.utcnow().isoformat(),
                },
            )
            logger.info(
                "MinioPaymentRepository: Payment persisted to Minio storage "
                "successfully",
                extra={
                    "payment_id": payment.payment_id,
                    "order_id": payment.order_id,
                    "bucket": self.bucket_name,
                    "persisted_status": payment.status,
                    "object_name": object_name,
                },
            )
        except S3Error as e:
            logger.error(
                "MinioPaymentRepository: Failed to persist payment to Minio",
                extra={
                    "payment_id": payment.payment_id,
                    "order_id": payment.order_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                exc_info=True,
            )
            raise
        except Exception as e:
            logger.error(
                "MinioPaymentRepository: Unexpected error during payment "
                "persistence",
                extra={
                    "payment_id": payment.payment_id,
                    "order_id": payment.order_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                exc_info=True,
            )
            raise

        outcome_status: Literal["completed", "failed", "refunded"]
        if payment_status == "completed":
            outcome_status = "completed"
        else:
            outcome_status = "failed"
        return PaymentOutcome(
            status=outcome_status,
            payment=payment if outcome_status == "completed" else None,
            reason=payment_reason,
        )

    async def get_payment(self, payment_id: str) -> Optional[Payment]:
        """Get payment by ID from Minio."""
        logger.debug(
            "MinioPaymentRepository: Attempting to retrieve payment from "
            "Minio",
            extra={
                "payment_id": payment_id,
                "source_bucket": self.bucket_name,
            },
        )
        try:
            response = self.client.get_object(
                bucket_name=self.bucket_name, object_name=payment_id
            )
            data = response.read()
            response.close()
            response.release_conn()

            payment_json = data.decode("utf-8")
            payment = Payment.model_validate_json(payment_json)

            logger.info(
                "MinioPaymentRepository: Payment retrieved successfully from "
                "Minio",
                extra={
                    "payment_id": payment_id,
                    "order_id": payment.order_id,
                    "status": payment.status,
                    "amount": str(payment.amount),
                    "retrieved_at": datetime.utcnow().isoformat(),
                    "payload_size_bytes": len(data),
                },
            )

            return payment
        except S3Error as e:
            if getattr(e, "code", None) == "NoSuchKey":
                logger.debug(
                    "MinioPaymentRepository: Payment not found in Minio "
                    "storage (NoSuchKey)",
                    extra={
                        "payment_id": payment_id,
                        "error_code": "NoSuchKey",
                    },
                )
            else:
                logger.error(
                    "MinioPaymentRepository: Error retrieving payment object "
                    "from Minio",
                    extra={
                        "payment_id": payment_id,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                    exc_info=True,
                )
            return None
        except Exception as e:
            logger.error(
                "MinioPaymentRepository: Unexpected error during payment "
                "retrieval",
                extra={
                    "payment_id": payment_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                exc_info=True,
            )
            return None

    async def refund_payment(
        self, args: RefundPaymentArgs
    ) -> RefundPaymentOutcome:
        """Refund a previously processed payment and persist the result to
        Minio.
        """
        logger.info(
            "MinioPaymentRepository: Attempting to refund payment",
            extra={
                "payment_id": args.payment_id,
                "order_id": args.order_id,
                "amount": str(args.amount),
                "reason": args.reason,
            },
        )

        # First, try to retrieve the original payment
        existing_payment = await self.get_payment(args.payment_id)

        if not existing_payment:
            logger.warning(
                "MinioPaymentRepository: Refund failed: Original payment not "
                "found",
                extra={
                    "payment_id": args.payment_id,
                    "order_id": args.order_id,
                },
            )
            return RefundPaymentOutcome(
                status="failed", reason="Original payment not found."
            )

        if existing_payment.status == "refunded":
            logger.info(
                "MinioPaymentRepository: Refund already processed for this "
                "payment",
                extra={
                    "payment_id": args.payment_id,
                    "order_id": args.order_id,
                    "current_status": existing_payment.status,
                },
            )
            return RefundPaymentOutcome(
                status="refunded", refund_id=f"ref_{args.payment_id}"
            )

        if existing_payment.status != "completed":
            logger.warning(
                "MinioPaymentRepository: Refund failed: Payment is not in "
                "'completed' status",
                extra={
                    "payment_id": args.payment_id,
                    "order_id": args.order_id,
                    "current_status": existing_payment.status,
                },
            )
            return RefundPaymentOutcome(
                status="failed",
                reason=(
                    f"Payment status is '{existing_payment.status}', "
                    "cannot refund."
                ),
            )

        # Proceed with refund logic
        refund_id = f"ref_{args.payment_id}"
        original_payment_status = existing_payment.status

        # Update the existing payment object's status to "refunded"
        existing_payment.status = "refunded"

        # Persist the updated payment object
        object_name = existing_payment.payment_id
        payment_json = existing_payment.model_dump_json().encode("utf-8")
        data_stream = io.BytesIO(payment_json)
        try:
            self.client.put_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                data=data_stream,
                length=len(payment_json),
                metadata={
                    "order_id": existing_payment.order_id,
                    "refund_id": refund_id,
                    "original_status": original_payment_status,
                    "refunded_at": datetime.utcnow().isoformat(),
                },
            )
            logger.info(
                "MinioPaymentRepository: Payment successfully marked as "
                "refunded and persisted to Minio",
                extra={
                    "payment_id": existing_payment.payment_id,
                    "order_id": existing_payment.order_id,
                    "refund_id": refund_id,
                    "bucket": self.bucket_name,
                    "object_name": object_name,
                },
            )
            return RefundPaymentOutcome(
                status="refunded", refund_id=refund_id
            )
        except S3Error as e:
            logger.error(
                "MinioPaymentRepository: Failed to persist refunded payment "
                "to Minio",
                extra={
                    "payment_id": existing_payment.payment_id,
                    "order_id": existing_payment.order_id,
                    "refund_id": refund_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                exc_info=True,
            )
            return RefundPaymentOutcome(
                status="failed",
                reason=f"Failed to persist refund status: {str(e)}",
            )
        except Exception as e:
            logger.error(
                "MinioPaymentRepository: Unexpected error during refund "
                "persistence",
                extra={
                    "payment_id": existing_payment.payment_id,
                    "order_id": existing_payment.order_id,
                    "refund_id": refund_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                exc_info=True,
            )
            return RefundPaymentOutcome(
                status="failed",
                reason=f"Unexpected error during refund: {str(e)}",
            )

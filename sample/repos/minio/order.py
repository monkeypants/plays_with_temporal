"""
Minio implementation of OrderRepository.
"""

import io
import uuid
import logging
from datetime import datetime
from typing import Optional
from minio import Minio
from minio.error import S3Error

from sample.domain import Order
from sample.repositories import OrderRepository

logger = logging.getLogger(__name__)


class MinioOrderRepository(OrderRepository):
    """
    Minio implementation of OrderRepository.
    Uses Minio for persistence of Order objects.
    """

    def __init__(self, endpoint: str):
        minio_endpoint = endpoint
        logger.debug(
            "Initializing MinioOrderRepository",
            extra={"minio_endpoint": minio_endpoint},
        )

        self.client = Minio(
            minio_endpoint,
            access_key="minioadmin",
            secret_key="minioadmin",
            secure=False,
        )
        self.bucket_name = "orders"
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self):
        try:
            if not self.client.bucket_exists(self.bucket_name):
                logger.info(
                    "Creating orders bucket",
                    extra={"bucket_name": self.bucket_name},
                )
                self.client.make_bucket(self.bucket_name)
            else:
                logger.debug(
                    "Orders bucket already exists",
                    extra={"bucket_name": self.bucket_name},
                )
        except S3Error as e:
            logger.error(
                "Failed to create orders bucket",
                extra={"bucket_name": self.bucket_name, "error": str(e)},
            )
            raise

    async def generate_order_id(self) -> str:
        """Generate a unique order ID using uuid4"""
        order_id = str(uuid.uuid4())
        logger.info(
            "MinioOrderRepository: Generated order ID",
            extra={
                "order_id": order_id,
            },
        )
        return order_id

    async def save_order(self, order: Order) -> None:
        """Persist the state of an order to Minio."""
        object_name = order.order_id
        order_json = order.model_dump_json().encode("utf-8")
        data_stream = io.BytesIO(order_json)

        logger.debug(
            "MinioOrderRepository: Attempting to save order state to Minio",
            extra={
                "order_id": order.order_id,
                "status": order.status,
                "refund_id": order.refund_id,
                "refund_status": order.refund_status,
                "target_bucket": self.bucket_name,
                "object_name": object_name,
                "payload_size_bytes": len(order_json),
            },
        )
        try:
            # Check if object exists and if content is same (idempotency)
            try:
                existing_response = self.client.get_object(
                    bucket_name=self.bucket_name, object_name=object_name
                )
                existing_data = existing_response.read()
                existing_response.close()
                existing_response.release_conn()

                if existing_data == order_json:
                    logger.info(
                        "MinioOrderRepository: Order state already matches, "
                        "skipping save (idempotent)",
                        extra={
                            "order_id": order.order_id,
                            "status": order.status,
                        },
                    )
                    return  # No need to save if already identical
                else:
                    logger.warning(
                        "MinioOrderRepository: Order object exists with "
                        "different content, overwriting",
                        extra={
                            "order_id": order.order_id,
                            "status": order.status,
                            "object_name": object_name,
                        },
                    )

            except S3Error as e:
                if getattr(e, "code", None) == "NoSuchKey":
                    logger.debug(
                        "MinioOrderRepository: Order object not found, "
                        "creating new",
                        extra={
                            "order_id": order.order_id,
                            "object_name": object_name,
                        },
                    )
                else:
                    raise  # Re-raise if it's another S3 error

            self.client.put_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                data=data_stream,
                length=len(order_json),
                metadata={
                    "customer_id": order.customer_id,
                    "status": order.status,
                    "saved_at": datetime.utcnow().isoformat(),
                },
            )
            logger.info(
                "MinioOrderRepository: Order state persisted to Minio "
                "successfully",
                extra={
                    "order_id": order.order_id,
                    "status": order.status,
                    "bucket": self.bucket_name,
                    "object_name": object_name,
                },
            )
        except S3Error as e:
            logger.error(
                "MinioOrderRepository: Failed to persist order state to "
                "Minio",
                extra={
                    "order_id": order.order_id,
                    "status": order.status,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                exc_info=True,
            )
            raise
        except Exception as e:
            logger.error(
                "MinioOrderRepository: Unexpected error during order save",
                extra={
                    "order_id": order.order_id,
                    "status": order.status,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                exc_info=True,
            )
            raise

    async def get_order(self, order_id: str) -> Optional[Order]:
        """Retrieve an order by its ID from Minio."""
        logger.debug(
            "MinioOrderRepository: Attempting to retrieve order from Minio",
            extra={"order_id": order_id, "source_bucket": self.bucket_name},
        )
        try:
            response = self.client.get_object(
                bucket_name=self.bucket_name, object_name=order_id
            )
            data = response.read()
            response.close()
            response.release_conn()

            order_json = data.decode("utf-8")
            order = Order.model_validate_json(order_json)

            logger.info(
                "MinioOrderRepository: Order retrieved successfully from "
                "Minio",
                extra={
                    "order_id": order_id,
                    "status": order.status,
                    "refund_id": order.refund_id,
                    "refund_status": order.refund_status,
                    "retrieved_at": datetime.utcnow().isoformat(),
                    "payload_size_bytes": len(data),
                },
            )
            return order
        except S3Error as e:
            if getattr(e, "code", None) == "NoSuchKey":
                logger.debug(
                    "MinioOrderRepository: Order not found in Minio storage "
                    "(NoSuchKey)",
                    extra={"order_id": order_id, "error_code": "NoSuchKey"},
                )
            else:
                logger.error(
                    "MinioOrderRepository: Error retrieving order object from"
                    " Minio",
                    extra={
                        "order_id": order_id,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                    exc_info=True,
                )
            return None
        except Exception as e:
            logger.error(
                "MinioOrderRepository: Unexpected error during order "
                "retrieval",
                extra={
                    "order_id": order_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                exc_info=True,
            )
            return None

    async def cancel_order(
        self, order_id: str, reason: Optional[str] = None
    ) -> None:
        """Cancel an order by updating its status to 'CANCELLED' in Minio."""
        logger.info(
            "MinioOrderRepository: Attempting to cancel order",
            extra={"order_id": order_id, "reason": reason},
        )

        order = await self.get_order(order_id)
        if not order:
            logger.warning(
                "MinioOrderRepository: Cannot cancel order: Order not found",
                extra={"order_id": order_id},
            )
            return  # Idempotent: if not found, nothing to do

        if order.status == "CANCELLED":
            logger.info(
                "MinioOrderRepository: Order already cancelled, no action "
                "needed",
                extra={"order_id": order_id},
            )
            return  # Idempotent: already cancelled

        # Update order status and reason
        original_status = order.status
        order.status = "CANCELLED"
        order.reason = reason if reason else "Cancelled by user request"

        await self.save_order(order)  # Persist the updated order
        logger.info(
            "MinioOrderRepository: Order successfully cancelled and persisted"
            " to Minio",
            extra={
                "order_id": order_id,
                "original_status": original_status,
                "new_status": order.status,
            },
        )

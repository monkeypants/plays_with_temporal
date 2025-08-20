"""
Minio implementation of InventoryRepository.
"""

import io
import logging
from typing import List
from minio import Minio  # type: ignore[import-untyped]
from minio.error import S3Error  # type: ignore[import-untyped]

from sample.domain import Order, InventoryItem, InventoryReservationOutcome
from sample.repositories import InventoryRepository

logger = logging.getLogger(__name__)


class MinioInventoryRepository(InventoryRepository):
    """
    Minio implementation of InventoryRepository that uses Minio for
    persistence.
    """

    def __init__(self, endpoint: str):
        minio_endpoint = endpoint
        logger.debug(
            "Initializing MinioInventoryRepository",
            extra={"minio_endpoint": minio_endpoint},
        )

        self.client = Minio(
            minio_endpoint,
            access_key="minioadmin",
            secret_key="minioadmin",
            secure=False,
        )
        self.bucket_name = "inventory"
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self) -> None:
        try:
            if not self.client.bucket_exists(self.bucket_name):
                logger.info(
                    "MinioInventoryRepository: Creating inventory bucket",
                    extra={"bucket_name": self.bucket_name},
                )
                self.client.make_bucket(self.bucket_name)
            else:
                logger.debug(
                    "MinioInventoryRepository: Inventory bucket already "
                    "exists",
                    extra={"bucket_name": self.bucket_name},
                )
        except S3Error as e:
            logger.error(
                "MinioInventoryRepository: Failed to create inventory bucket",
                extra={"bucket_name": self.bucket_name, "error": str(e)},
            )
            raise

    async def _persist_inventory_state(
        self, order: Order, reserved: bool
    ) -> List[InventoryItem]:
        """Helper to persist the state of inventory items to Minio."""
        action = "reserving" if reserved else "releasing"
        log_prefix = f"MinioInventoryRepository: {action.capitalize()} items"
        logger.debug(
            f"{log_prefix} - Started",
            extra={
                "order_id": order.order_id,
                "item_count": len(order.items),
                "reserved_flag": reserved,
            },
        )

        items_to_return = []
        for order_item in order.items:
            item = InventoryItem(
                product_id=order_item.product_id,
                quantity=order_item.quantity,
                # If reserved, all quantity is reserved. If releasing,
                # reserved=0
                reserved=order_item.quantity if reserved else 0,
            )
            items_to_return.append(item)

            object_name = f"{order.order_id}_{item.product_id}"
            item_json = item.model_dump_json().encode("utf-8")
            data_stream = io.BytesIO(item_json)

            try:
                # Check if object exists and if content is same (idempotency)
                try:
                    existing_response = self.client.get_object(
                        bucket_name=self.bucket_name, object_name=object_name
                    )
                    existing_data = existing_response.read()
                    existing_response.close()
                    existing_response.release_conn()

                    if existing_data == item_json:
                        logger.debug(
                            f"{log_prefix} - Item already in correct state",
                            extra={
                                "order_id": order.order_id,
                                "product_id": item.product_id,
                                "object_name": object_name,
                            },
                        )
                        continue  # Skip put_object if state is correct
                    else:
                        logger.warning(
                            f"{log_prefix} - Item exists with different "
                            "content, overwriting",
                            extra={
                                "order_id": order.order_id,
                                "product_id": item.product_id,
                                "object_name": object_name,
                            },
                        )

                except S3Error as e:
                    if getattr(e, "code", None) == "NoSuchKey":
                        logger.debug(
                            f"{log_prefix} - Item object not found, "
                            "creating new",
                            extra={
                                "order_id": order.order_id,
                                "product_id": item.product_id,
                                "object_name": object_name,
                            },
                        )
                    else:
                        raise  # Re-raise if it's another S3 error

                # Perform put_object
                self.client.put_object(
                    bucket_name=self.bucket_name,
                    object_name=object_name,
                    data=data_stream,
                    length=len(item_json),
                    metadata={"order_id": order.order_id, "action": action},
                )
                logger.debug(
                    f"{log_prefix} - Item persisted to Minio",
                    extra={
                        "order_id": order.order_id,
                        "product_id": item.product_id,
                        "object_name": object_name,
                        "action": action,
                    },
                )
            except S3Error as e:
                logger.error(
                    f"{log_prefix} - Failed to persist inventory item to "
                    "Minio",
                    extra={
                        "order_id": order.order_id,
                        "product_id": item.product_id,
                        "object_name": object_name,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                )
                raise
            except Exception as e:
                logger.error(
                    f"{log_prefix} - Unexpected error during inventory item "
                    "persistence",
                    extra={
                        "order_id": order.order_id,
                        "product_id": item.product_id,
                        "object_name": object_name,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                    exc_info=True,
                )
                raise

        logger.info(
            f"MinioInventoryRepository: {action.capitalize()} completed "
            "successfully",
            extra={
                "order_id": order.order_id,
                "processed_items": len(items_to_return),
                "action": action,
            },
        )
        return items_to_return

    async def reserve_items(
        self, order: Order
    ) -> InventoryReservationOutcome:
        """Reserve inventory items and persist the state to Minio."""
        logger.debug(
            "MinioInventoryRepository: Calling reserve_items",
            extra={"order_id": order.order_id},
        )
        reserved_items = await self._persist_inventory_state(
            order, reserved=True
        )
        logger.info(
            "MinioInventoryRepository: reserve_items completed",
            extra={
                "order_id": order.order_id,
                "status": "reserved",
                "reserved_count": len(reserved_items),
            },
        )
        return InventoryReservationOutcome(
            status="reserved", reserved_items=reserved_items
        )

    async def release_items(self, order: Order) -> List[InventoryItem]:
        """Release previously reserved inventory items and persist the state
        to Minio.
        """
        logger.debug(
            "MinioInventoryRepository: Calling release_items",
            extra={"order_id": order.order_id},
        )
        released_items = await self._persist_inventory_state(
            order, reserved=False
        )
        logger.info(
            "MinioInventoryRepository: release_items completed",
            extra={
                "order_id": order.order_id,
                "status": "released",
                "released_count": len(released_items),
            },
        )
        return released_items

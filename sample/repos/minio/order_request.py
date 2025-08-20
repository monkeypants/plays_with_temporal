"""
Minio implementation of OrderRequestRepository.
"""

import os
import io
import logging
from typing import Optional
from minio import Minio
from minio.error import S3Error

from sample.domain import RequestOrderMapping
from sample.repositories import OrderRequestRepository

logger = logging.getLogger(__name__)


class MinioOrderRequestRepository(OrderRequestRepository):
    """
    Minio implementation of OrderRequestRepository that uses Minio for
    persistence. Uses dual S3 objects for O(1) bidirectional lookups.
    """

    def __init__(self):
        minio_endpoint = os.environ.get("MINIO_ENDPOINT", "minio:9000")
        logger.debug(
            "Initializing MinioOrderRequestRepository",
            extra={"minio_endpoint": minio_endpoint},
        )

        self.client = Minio(
            minio_endpoint,
            access_key="minioadmin",
            secret_key="minioadmin",
            secure=False,
        )
        self.bucket_name = "request-mappings"
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self):
        try:
            if not self.client.bucket_exists(self.bucket_name):
                logger.info(
                    "Creating request mappings bucket",
                    extra={"bucket_name": self.bucket_name},
                )
                self.client.make_bucket(self.bucket_name)
            else:
                logger.debug(
                    "Request mappings bucket already exists",
                    extra={"bucket_name": self.bucket_name},
                )
        except S3Error as e:
            logger.error(
                "Failed to create request mappings bucket",
                extra={"bucket_name": self.bucket_name, "error": str(e)},
            )
            raise

    async def store_bidirectional_mapping(
        self, request_id: str, order_id: str
    ) -> None:
        """Store bidirectional mapping idempotently using dual S3 objects."""
        logger.debug(
            "MinioOrderRequestRepository: Starting "
            "store_bidirectional_mapping",
            extra={"request_id": request_id, "order_id": order_id},
        )

        # Create the mapping object (same data for both indices)
        mapping = RequestOrderMapping(
            request_id=request_id, order_id=order_id
        )
        mapping_json = mapping.model_dump_json().encode("utf-8")

        # Define both object names
        request_object_name = f"request-{request_id}.json"
        order_object_name = f"order-{order_id}.json"

        # Store both objects idempotently
        success_count = 0
        errors = []

        # Store request index
        try:
            await self._store_mapping_object(
                request_object_name,
                mapping_json,
                {
                    "request_id": request_id,
                    "order_id": order_id,
                    "index_type": "request",
                },
            )
            success_count += 1
            logger.debug(
                "MinioOrderRequestRepository: Request index storage attempt "
                "completed",
                extra={
                    "request_id": request_id,
                    "object_name": request_object_name,
                    "status": "success",
                },
            )
        except Exception as e:
            error_msg = f"Failed to store request index: {str(e)}"
            errors.append(error_msg)
            logger.error(
                "MinioOrderRequestRepository: Request index storage failed",
                extra={
                    "request_id": request_id,
                    "object_name": request_object_name,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                exc_info=True,
            )

        # Store order index
        try:
            await self._store_mapping_object(
                order_object_name,
                mapping_json,
                {
                    "request_id": request_id,
                    "order_id": order_id,
                    "index_type": "order",
                },
            )
            success_count += 1
            logger.debug(
                "MinioOrderRequestRepository: Order index storage attempt "
                "completed",
                extra={
                    "order_id": order_id,
                    "object_name": order_object_name,
                    "status": "success",
                },
            )
        except Exception as e:
            error_msg = f"Failed to store order index: {str(e)}"
            errors.append(error_msg)
            logger.error(
                "MinioOrderRequestRepository: Order index storage failed",
                extra={
                    "order_id": order_id,
                    "object_name": order_object_name,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                exc_info=True,
            )

        # Evaluate results
        if success_count == 2:
            logger.info(
                "MinioOrderRequestRepository: Bidirectional mapping stored "
                "successfully",
                extra={
                    "request_id": request_id,
                    "order_id": order_id,
                    "request_object": request_object_name,
                    "order_object": order_object_name,
                },
            )
        elif success_count == 1:
            logger.warning(
                "MinioOrderRequestRepository: Partial mapping storage - will "
                "retry on next call",
                extra={
                    "request_id": request_id,
                    "order_id": order_id,
                    "success_count": success_count,
                    "errors": errors,
                },
            )
        else:
            logger.error(
                "MinioOrderRequestRepository: Complete mapping storage "
                "failure",
                extra={
                    "request_id": request_id,
                    "order_id": order_id,
                    "errors": errors,
                },
                exc_info=True,
            )
            raise Exception(
                f"Failed to store bidirectional mapping: {'; '.join(errors)}"
            )

    async def _store_mapping_object(
        self, object_name: str, mapping_json: bytes, metadata: dict
    ) -> None:
        """Store a single mapping object idempotently."""
        logger.debug(
            "MinioOrderRequestRepository: _store_mapping_object - checking "
            "existence",
            extra={"object_name": object_name},
        )
        try:
            # Check if object already exists with correct content
            try:
                existing_response = self.client.get_object(
                    bucket_name=self.bucket_name, object_name=object_name
                )
                existing_data = existing_response.read()
                existing_response.close()
                existing_response.release_conn()

                if existing_data == mapping_json:
                    logger.debug(
                        "MinioOrderRequestRepository: Mapping object already "
                        "exists with correct content, skipping put",
                        extra={"object_name": object_name},
                    )
                    return
                else:
                    logger.warning(
                        "MinioOrderRequestRepository: Mapping object exists "
                        "with different content, overwriting",
                        extra={"object_name": object_name},
                    )

            except S3Error as e:
                if getattr(e, "code", None) == "NoSuchKey":
                    logger.debug(
                        "MinioOrderRequestRepository: Mapping object doesn't "
                        "exist (NoSuchKey), creating new",
                        extra={"object_name": object_name},
                    )
                else:
                    logger.error(
                        "MinioOrderRequestRepository: S3Error checking "
                        "existence of mapping object",
                        extra={
                            "object_name": object_name,
                            "error": str(e),
                            "error_code": getattr(e, "code", "N/A"),
                        },
                        exc_info=True,
                    )
                    raise  # Re-raise if it's another S3 error

            data_stream = io.BytesIO(mapping_json)
            self.client.put_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                data=data_stream,
                length=len(mapping_json),
                metadata=metadata,
            )
            logger.debug(
                "MinioOrderRequestRepository: Mapping object put "
                "successfully",
                extra={
                    "object_name": object_name,
                    "size_bytes": len(mapping_json),
                },
            )

        except S3Error as e:
            logger.error(
                "MinioOrderRequestRepository: S3 error storing mapping "
                "object",
                extra={
                    "object_name": object_name,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                exc_info=True,
            )
            raise Exception(f"S3 error storing {object_name}: {str(e)}")
        except Exception as e:
            logger.error(
                "MinioOrderRequestRepository: Unexpected error storing "
                "mapping object",
                extra={
                    "object_name": object_name,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                exc_info=True,
            )
            raise Exception(
                f"Unexpected error storing {object_name}: {str(e)}"
            )

    async def get_order_id_for_request(
        self, request_id: str
    ) -> Optional[str]:
        """Get order ID for a given request ID - O(1) lookup."""
        object_name = f"request-{request_id}.json"
        logger.debug(
            "MinioOrderRequestRepository: get_order_id_for_request - "
            "attempting lookup",
            extra={"request_id": request_id, "object_name": object_name},
        )
        mapping = await self._get_mapping_from_object(object_name)

        if mapping:
            logger.info(
                "MinioOrderRequestRepository: Found order ID for request",
                extra={
                    "request_id": request_id,
                    "order_id": mapping.order_id,
                },
            )
            return mapping.order_id

        logger.info(
            "MinioOrderRequestRepository: No order ID found for request",
            extra={"request_id": request_id},
        )
        return None

    async def get_request_id_for_order(self, order_id: str) -> Optional[str]:
        """Get request ID for a given order ID - O(1) lookup."""
        object_name = f"order-{order_id}.json"
        logger.debug(
            "MinioOrderRequestRepository: get_request_id_for_order - "
            "attempting lookup",
            extra={"order_id": order_id, "object_name": object_name},
        )
        mapping = await self._get_mapping_from_object(object_name)

        if mapping:
            logger.info(
                "MinioOrderRequestRepository: Found request ID for order",
                extra={
                    "order_id": order_id,
                    "request_id": mapping.request_id,
                },
            )
            return mapping.request_id

        logger.info(
            "MinioOrderRequestRepository: No request ID found for order",
            extra={"order_id": order_id},
        )
        return None

    async def _get_mapping_from_object(
        self, object_name: str
    ) -> Optional[RequestOrderMapping]:
        """Helper to get mapping from a specific S3 object."""

        logger.debug(
            "MinioOrderRequestRepository: _get_mapping_from_object - "
            "Retrieving object",
            extra={"object_name": object_name, "bucket": self.bucket_name},
        )

        try:
            response = self.client.get_object(
                bucket_name=self.bucket_name, object_name=object_name
            )
            data = response.read()
            response.close()
            response.release_conn()

            mapping_json = data.decode("utf-8")
            mapping = RequestOrderMapping.model_validate_json(mapping_json)

            logger.debug(
                "MinioOrderRequestRepository: Mapping retrieved successfully",
                extra={
                    "object_name": object_name,
                    "request_id": mapping.request_id,
                    "order_id": mapping.order_id,
                    "payload_size_bytes": len(data),
                },
            )

            return mapping

        except S3Error as e:
            if getattr(e, "code", None) == "NoSuchKey":
                logger.debug(
                    "MinioOrderRequestRepository: Mapping object not found "
                    "(NoSuchKey)",
                    extra={
                        "object_name": object_name,
                        "error_code": "NoSuchKey",
                    },
                )
            else:
                logger.error(
                    "MinioOrderRequestRepository: Error retrieving mapping "
                    "object from Minio",
                    extra={
                        "object_name": object_name,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                    exc_info=True,
                )
            return None
        except Exception as e:
            logger.error(
                "MinioOrderRequestRepository: Unexpected error during mapping"
                " retrieval",
                extra={
                    "object_name": object_name,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                exc_info=True,
            )
            return None

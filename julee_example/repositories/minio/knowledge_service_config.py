"""
Minio implementation of KnowledgeServiceConfigRepository.

This module provides a Minio-based implementation of the KnowledgeServiceConfigRepository
protocol that follows the Clean Architecture patterns defined in the
Fun-Police Framework. It handles knowledge service configuration storage
as JSON objects in Minio, ensuring idempotency and proper error handling.

The implementation stores knowledge service configurations as JSON objects
in Minio, following the large payload handling pattern from the architectural
guidelines. Each configuration is stored with its knowledge_service_id as the key.
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from minio.error import S3Error  # type: ignore[import-untyped]

from julee_example.domain import KnowledgeServiceConfig
from julee_example.repositories.knowledge_service_config import KnowledgeServiceConfigRepository
from .client import MinioClient

logger = logging.getLogger(__name__)


class MinioKnowledgeServiceConfigRepository(KnowledgeServiceConfigRepository):
    """
    Minio implementation of KnowledgeServiceConfigRepository using Minio for persistence.

    This implementation stores knowledge service configurations as JSON objects:
    - Knowledge Service Configs: JSON objects in the "knowledge-service-configs" bucket

    Each configuration is stored with its knowledge_service_id as the object name
    for efficient retrieval and updates.
    """

    def __init__(self, client: MinioClient) -> None:
        """Initialize repository with Minio client.

        Args:
            client: MinioClient protocol implementation (real or fake)
        """
        logger.debug("Initializing MinioKnowledgeServiceConfigRepository")

        self.client = client
        self.bucket_name = "knowledge-service-configs"
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self) -> None:
        """Ensure the knowledge service config bucket exists."""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                logger.info(
                    "Creating knowledge service config bucket",
                    extra={"bucket_name": self.bucket_name},
                )
                self.client.make_bucket(self.bucket_name)
            else:
                logger.debug(
                    "Knowledge service config bucket already exists",
                    extra={"bucket_name": self.bucket_name},
                )
        except S3Error as e:
            logger.error(
                "Failed to create knowledge service config bucket",
                extra={"bucket_name": self.bucket_name, "error": str(e)},
            )
            raise

    async def get(
        self, knowledge_service_id: str
    ) -> Optional[KnowledgeServiceConfig]:
        """Retrieve a knowledge service configuration by ID.

        Args:
            knowledge_service_id: Unique knowledge service identifier

        Returns:
            KnowledgeServiceConfig object if found, None otherwise
        """
        logger.debug(
            "MinioKnowledgeServiceConfigRepository: Attempting to retrieve knowledge service config",
            extra={
                "knowledge_service_id": knowledge_service_id,
                "bucket_name": self.bucket_name,
            },
        )

        try:
            # Get the knowledge service config from Minio
            response = self.client.get_object(
                bucket_name=self.bucket_name,
                object_name=knowledge_service_id
            )
            config_data = response.read()
            response.close()
            response.release_conn()

            config_json = config_data.decode("utf-8")
            config_dict = json.loads(config_json)

            logger.info(
                "MinioKnowledgeServiceConfigRepository: Knowledge service config retrieved successfully",
                extra={
                    "knowledge_service_id": knowledge_service_id,
                    "name": config_dict.get("name"),
                    "service_api": config_dict.get("service_api"),
                    "retrieved_at": datetime.now(timezone.utc).isoformat(),
                },
            )

            return KnowledgeServiceConfig(**config_dict)

        except S3Error as e:
            if getattr(e, "code", None) == "NoSuchKey":
                logger.debug(
                    "MinioKnowledgeServiceConfigRepository: Knowledge service config not found",
                    extra={"knowledge_service_id": knowledge_service_id},
                )
                return None
            else:
                logger.error(
                    "MinioKnowledgeServiceConfigRepository: Error retrieving knowledge service config",
                    extra={"knowledge_service_id": knowledge_service_id, "error": str(e)},
                )
                raise

    async def save(self, knowledge_service: KnowledgeServiceConfig) -> None:
        """Save a knowledge service configuration.

        Args:
            knowledge_service: Complete KnowledgeServiceConfig to save
        """
        logger.debug(
            "MinioKnowledgeServiceConfigRepository: Saving knowledge service config",
            extra={
                "knowledge_service_id": knowledge_service.knowledge_service_id,
                "name": knowledge_service.name,
                "service_api": knowledge_service.service_api.value,
            },
        )

        try:
            # Update timestamp
            knowledge_service.updated_at = datetime.now(timezone.utc)

            # Ensure created_at is set for new configs
            if knowledge_service.created_at is None:
                knowledge_service.created_at = datetime.now(timezone.utc)

            # Use Pydantic's JSON serialization for proper datetime handling
            config_json = knowledge_service.model_dump_json()

            self.client.put_object(
                bucket_name=self.bucket_name,
                object_name=knowledge_service.knowledge_service_id,
                data=config_json.encode("utf-8"),
                length=len(config_json.encode("utf-8")),
                content_type="application/json",
            )

            logger.info(
                "MinioKnowledgeServiceConfigRepository: Knowledge service config saved successfully",
                extra={
                    "knowledge_service_id": knowledge_service.knowledge_service_id,
                    "name": knowledge_service.name,
                    "service_api": knowledge_service.service_api.value,
                    "updated_at": knowledge_service.updated_at.isoformat(),
                },
            )

        except S3Error as e:
            logger.error(
                "MinioKnowledgeServiceConfigRepository: Error saving knowledge service config",
                extra={
                    "knowledge_service_id": knowledge_service.knowledge_service_id,
                    "error": str(e),
                },
            )
            raise

    async def generate_id(self) -> str:
        """Generate a unique knowledge service identifier.

        Returns:
            Unique knowledge service ID string
        """
        knowledge_service_id = f"ks-{uuid.uuid4()}"

        logger.debug(
            "MinioKnowledgeServiceConfigRepository: Generated knowledge service ID",
            extra={"knowledge_service_id": knowledge_service_id},
        )

        return knowledge_service_id

"""
Minio implementation of KnowledgeServiceConfigRepository.

This module provides a Minio-based implementation of the
KnowledgeServiceConfigRepository
protocol that follows the Clean Architecture patterns defined in the
Fun-Police Framework. It handles knowledge service configuration storage
as JSON objects in Minio, ensuring idempotency and proper error handling.

The implementation stores knowledge service configurations as JSON objects
in Minio, following the large payload handling pattern from the architectural
guidelines. Each configuration is stored with its knowledge_service_id as the
key.
"""

import logging
from typing import Optional, List, Dict

from julee_example.domain.models.knowledge_service_config import (
    KnowledgeServiceConfig,
)
from julee_example.domain.repositories.knowledge_service_config import (
    KnowledgeServiceConfigRepository,
)
from .client import MinioClient, MinioRepositoryMixin


class MinioKnowledgeServiceConfigRepository(
    KnowledgeServiceConfigRepository, MinioRepositoryMixin
):
    """
    Minio implementation of KnowledgeServiceConfigRepository using Minio for
    persistence.

    This implementation stores knowledge service configurations as JSON
    objects:
    - Knowledge Service Configs: JSON objects in the
      "knowledge-service-configs" bucket

    Each configuration is stored with its knowledge_service_id as the object
    name
    for efficient retrieval and updates.
    """

    def __init__(self, client: MinioClient) -> None:
        """Initialize repository with Minio client.

        Args:
            client: MinioClient protocol implementation (real or fake)
        """
        self.client = client
        self.logger = logging.getLogger(
            "MinioKnowledgeServiceConfigRepository"
        )
        self.bucket_name = "knowledge-service-configs"
        self.ensure_buckets_exist(self.bucket_name)

    async def get(
        self, knowledge_service_id: str
    ) -> Optional[KnowledgeServiceConfig]:
        """Retrieve a knowledge service configuration by ID.

        Args:
            knowledge_service_id: Unique knowledge service identifier

        Returns:
            KnowledgeServiceConfig object if found, None otherwise
        """
        object_name = f"config/{knowledge_service_id}"

        return self.get_json_object(
            bucket_name=self.bucket_name,
            object_name=object_name,
            model_class=KnowledgeServiceConfig,
            not_found_log_message="Knowledge service config not found",
            error_log_message="Error retrieving knowledge service config",
            extra_log_data={"knowledge_service_id": knowledge_service_id},
        )

    async def save(self, knowledge_service: KnowledgeServiceConfig) -> None:
        """Save a knowledge service configuration.

        Args:
            knowledge_service: Complete KnowledgeServiceConfig to save
        """
        # Update timestamps
        self.update_timestamps(knowledge_service)

        object_name = f"config/{knowledge_service.knowledge_service_id}"

        self.put_json_object(
            bucket_name=self.bucket_name,
            object_name=object_name,
            model=knowledge_service,
            success_log_message="Knowledge service config saved successfully",
            error_log_message="Error saving knowledge service config",
            extra_log_data={
                "knowledge_service_id": (
                    knowledge_service.knowledge_service_id
                ),
                "service_name": knowledge_service.name,
                "service_api": knowledge_service.service_api.value,
            },
        )

    async def get_many(
        self, knowledge_service_ids: List[str]
    ) -> Dict[str, Optional[KnowledgeServiceConfig]]:
        """Retrieve multiple knowledge service configs by ID.

        Args:
            knowledge_service_ids: List of unique knowledge service
            identifiers

        Returns:
            Dict mapping knowledge_service_id to KnowledgeServiceConfig (or
            None if not found)
        """
        # Convert knowledge service IDs to object names
        object_names = [
            f"config/{service_id}" for service_id in knowledge_service_ids
        ]

        # Get objects from Minio using batch method
        object_results = self.get_many_json_objects(
            bucket_name=self.bucket_name,
            object_names=object_names,
            model_class=KnowledgeServiceConfig,
            not_found_log_message="Knowledge service config not found",
            error_log_message="Error retrieving knowledge service config",
            extra_log_data={"knowledge_service_ids": knowledge_service_ids},
        )

        # Convert object names back to knowledge service IDs for the result
        result: Dict[str, Optional[KnowledgeServiceConfig]] = {}
        for i, service_id in enumerate(knowledge_service_ids):
            object_name = object_names[i]
            result[service_id] = object_results[object_name]

        return result

    async def generate_id(self) -> str:
        """Generate a unique knowledge service identifier.

        Returns:
            Unique knowledge service ID string
        """
        return self.generate_id_with_prefix("ks")

    async def list_all(self) -> List[KnowledgeServiceConfig]:
        """List all knowledge service configurations.

        Returns:
            List of all knowledge service configurations, sorted by
            knowledge_service_id
        """
        try:
            # Extract knowledge service IDs from objects with config/ prefix
            service_ids = self.list_objects_with_prefix_extract_ids(
                bucket_name=self.bucket_name,
                prefix="config/",
                entity_type_name="configs",
            )

            if not service_ids:
                return []

            # Get all configurations using the existing get_many method
            config_results = await self.get_many(service_ids)

            # Filter out None results and sort by knowledge_service_id
            configs = [
                config
                for config in config_results.values()
                if config is not None
            ]
            configs.sort(key=lambda x: x.knowledge_service_id)

            self.logger.debug(
                "Retrieved configs",
                extra={"count": len(configs)},
            )

            return configs

        except Exception as e:
            self.logger.error(
                "Error listing configs",
                exc_info=True,
                extra={
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "bucket": self.bucket_name,
                },
            )
            # Return empty list on error to avoid breaking the API
            return []

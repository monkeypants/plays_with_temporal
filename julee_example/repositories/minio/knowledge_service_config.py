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

from typing import Optional

from julee_example.domain import KnowledgeServiceConfig
from julee_example.repositories.knowledge_service_config import KnowledgeServiceConfigRepository
from .client import MinioClient, MinioRepositoryClient


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
        self.repo_client = MinioRepositoryClient(client, "MinioKnowledgeServiceConfigRepository")
        self.bucket_name = "knowledge-service-configs"
        self.repo_client.ensure_buckets_exist(self.bucket_name)

    async def get(
        self, knowledge_service_id: str
    ) -> Optional[KnowledgeServiceConfig]:
        """Retrieve a knowledge service configuration by ID.

        Args:
            knowledge_service_id: Unique knowledge service identifier

        Returns:
            KnowledgeServiceConfig object if found, None otherwise
        """
        return self.repo_client.get_json_object(
            bucket_name=self.bucket_name,
            object_name=knowledge_service_id,
            model_class=KnowledgeServiceConfig,
            not_found_log_message="Knowledge service config not found",
            error_log_message="Error retrieving knowledge service config",
            extra_log_data={"knowledge_service_id": knowledge_service_id}
        )

    async def save(self, knowledge_service: KnowledgeServiceConfig) -> None:
        """Save a knowledge service configuration.

        Args:
            knowledge_service: Complete KnowledgeServiceConfig to save
        """
        # Update timestamps
        self.repo_client.update_timestamps(knowledge_service)

        self.repo_client.put_json_object(
            bucket_name=self.bucket_name,
            object_name=knowledge_service.knowledge_service_id,
            model=knowledge_service,
            success_log_message="Knowledge service config saved successfully",
            error_log_message="Error saving knowledge service config",
            extra_log_data={
                "knowledge_service_id": knowledge_service.knowledge_service_id,
                "name": knowledge_service.name,
                "service_api": knowledge_service.service_api.value,
            }
        )

    async def generate_id(self) -> str:
        """Generate a unique knowledge service identifier.

        Returns:
            Unique knowledge service ID string
        """
        return self.repo_client.generate_id_with_prefix("ks")

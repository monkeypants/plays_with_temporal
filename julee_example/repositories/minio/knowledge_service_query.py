"""
Minio implementation of KnowledgeServiceQueryRepository.

This module provides a Minio-based implementation of the
KnowledgeServiceQueryRepository protocol that follows the Clean Architecture
patterns defined in the Fun-Police Framework. It handles knowledge service
query storage as JSON objects in Minio, ensuring idempotency and proper
error handling.

The implementation stores knowledge service queries as JSON objects in Minio,
following the large payload handling pattern from the architectural
guidelines.
Each query is stored as a separate object with the query ID as the key.
"""

import logging
import uuid

from typing import Optional


from julee_example.domain.assembly_specification import KnowledgeServiceQuery
from .client import MinioClient, MinioRepositoryMixin
from julee_example.repositories.knowledge_service_query import (
    KnowledgeServiceQueryRepository,
)

logger = logging.getLogger(__name__)


class MinioKnowledgeServiceQueryRepository(
    KnowledgeServiceQueryRepository, MinioRepositoryMixin
):
    """
    Minio implementation of KnowledgeServiceQueryRepository.

    This implementation stores knowledge service queries as JSON objects in
    Minio buckets, following the established patterns for Minio repositories
    in this system. Each query is stored as a separate object with
    deterministic naming.
    """

    def __init__(self, client: MinioClient) -> None:
        """Initialize repository with Minio client.

        Args:
            client: MinioClient protocol implementation (real or fake)
        """
        self.client = client
        self.logger = logging.getLogger(
            "MinioKnowledgeServiceQueryRepository"
        )
        self.bucket_name = "knowledge-service-queries"
        self.ensure_buckets_exist(self.bucket_name)

    async def get(self, query_id: str) -> Optional[KnowledgeServiceQuery]:
        """Retrieve a knowledge service query by ID.

        Args:
            query_id: Unique query identifier

        Returns:
            KnowledgeServiceQuery object if found, None otherwise
        """
        logger.debug(
            "MinioKnowledgeServiceQueryRepository: Attempting to retrieve "
            "query",
            extra={"query_id": query_id, "bucket": self.bucket_name},
        )

        object_name = f"query/{query_id}.json"

        # Get object from Minio
        query_data = self.get_json_object(
            bucket_name=self.bucket_name,
            object_name=object_name,
            model_class=KnowledgeServiceQuery,
            not_found_log_message="Knowledge service query not found",
            error_log_message="Error retrieving knowledge service query",
            extra_log_data={"query_id": query_id},
        )

        return query_data

    async def save(self, query: KnowledgeServiceQuery) -> None:
        """Store or update a knowledge service query.

        Args:
            query: KnowledgeServiceQuery object to store
        """
        logger.debug(
            "MinioKnowledgeServiceQueryRepository: Saving query",
            extra={"query_id": query.query_id, "bucket": self.bucket_name},
        )

        # Update the updated_at timestamp
        self.update_timestamps(query)

        object_name = f"query/{query.query_id}.json"

        # Store in Minio
        self.put_json_object(
            bucket_name=self.bucket_name,
            object_name=object_name,
            model=query,
            success_log_message="Knowledge service query saved successfully",
            error_log_message="Failed to save knowledge service query",
            extra_log_data={"query_id": query.query_id},
        )

    async def generate_id(self) -> str:
        """Generate a unique query identifier.

        Returns:
            Unique string identifier for a new query
        """
        query_id = f"query-{uuid.uuid4().hex[:12]}"

        logger.debug(
            "MinioKnowledgeServiceQueryRepository: Generated query ID",
            extra={"query_id": query_id},
        )

        return query_id

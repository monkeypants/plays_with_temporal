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

from typing import Optional, List, Dict


from julee_example.domain.models.assembly_specification import (
    KnowledgeServiceQuery,
)
from .client import MinioClient, MinioRepositoryMixin
from julee_example.domain.repositories.knowledge_service_query import (
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

        object_name = f"query/{query_id}"

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

        object_name = f"query/{query.query_id}"

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

    async def get_many(
        self, query_ids: List[str]
    ) -> Dict[str, Optional[KnowledgeServiceQuery]]:
        """Retrieve multiple knowledge service queries by ID.

        Args:
            query_ids: List of unique query identifiers

        Returns:
            Dict mapping query_id to KnowledgeServiceQuery (or None if not
            found)
        """
        logger.debug(
            "MinioKnowledgeServiceQueryRepository: Attempting to retrieve "
            "multiple queries",
            extra={
                "query_ids": query_ids,
                "count": len(query_ids),
                "bucket": self.bucket_name,
            },
        )

        # Convert query IDs to object names
        object_names = [f"query/{query_id}" for query_id in query_ids]

        # Get objects from Minio using batch method
        object_results = self.get_many_json_objects(
            bucket_name=self.bucket_name,
            object_names=object_names,
            model_class=KnowledgeServiceQuery,
            not_found_log_message="Knowledge service query not found",
            error_log_message="Error retrieving knowledge service query",
            extra_log_data={"query_ids": query_ids},
        )

        # Convert object names back to query IDs for the result
        result: Dict[str, Optional[KnowledgeServiceQuery]] = {}
        for i, query_id in enumerate(query_ids):
            object_name = object_names[i]
            result[query_id] = object_results[object_name]

        return result

    async def list_all(self) -> List[KnowledgeServiceQuery]:
        """List all knowledge service queries.

        Returns:
            List of all knowledge service queries, sorted by query_id
        """
        try:
            # Extract query IDs from objects with the query/ prefix
            query_ids = self.list_objects_with_prefix_extract_ids(
                bucket_name=self.bucket_name,
                prefix="query/",
                entity_type_name="queries",
            )

            if not query_ids:
                return []

            # Get all queries using the existing get_many method
            query_results = await self.get_many(query_ids)

            # Filter out None results and sort by query_id
            queries = [
                query for query in query_results.values() if query is not None
            ]
            queries.sort(key=lambda x: x.query_id)

            logger.debug(
                "Retrieved queries",
                extra={"count": len(queries)},
            )

            return queries

        except Exception as e:
            logger.error(
                "Error listing queries",
                exc_info=True,
                extra={
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "bucket": self.bucket_name,
                },
            )
            # Return empty list on error to avoid breaking the API
            return []

"""
Memory implementation of KnowledgeServiceQueryRepository.

This module provides an in-memory implementation of the
KnowledgeServiceQueryRepository protocol that follows the Clean Architecture
patterns defined in the Fun-Police Framework. It handles knowledge service
query storage in memory dictionaries, ensuring idempotency and proper error
handling.

The implementation uses Python dictionaries to store knowledge service query
data, making it ideal for testing scenarios where external dependencies
should be avoided.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, Optional

from julee_example.domain.assembly_specification import KnowledgeServiceQuery
from julee_example.repositories.knowledge_service_query import (
    KnowledgeServiceQueryRepository,
)

logger = logging.getLogger(__name__)


class MemoryKnowledgeServiceQueryRepository(KnowledgeServiceQueryRepository):
    """
    Memory implementation of KnowledgeServiceQueryRepository using Python
    dictionaries.

    This implementation stores knowledge service queries in memory:
    - Queries: Dictionary keyed by query_id containing KnowledgeServiceQuery
      objects

    This provides a lightweight, dependency-free option for testing while
    maintaining the same interface as other implementations.
    """

    def __init__(self) -> None:
        """Initialize repository with empty in-memory storage."""
        logger.debug("Initializing MemoryKnowledgeServiceQueryRepository")

        # Storage dictionary
        self._queries: Dict[str, KnowledgeServiceQuery] = {}

    async def get(self, query_id: str) -> Optional[KnowledgeServiceQuery]:
        """Retrieve a knowledge service query by ID.

        Args:
            query_id: Unique query identifier

        Returns:
            KnowledgeServiceQuery object if found, None otherwise
        """
        logger.debug(
            "MemoryKnowledgeServiceQueryRepository: Attempting to retrieve "
            "query",
            extra={"query_id": query_id},
        )

        query = self._queries.get(query_id)
        if not query:
            logger.debug(
                "MemoryKnowledgeServiceQueryRepository: Query not found",
                extra={"query_id": query_id},
            )
            return None

        logger.info(
            "MemoryKnowledgeServiceQueryRepository: Query retrieved "
            "successfully",
            extra={
                "query_id": query_id,
                "query_name": query.name,
                "knowledge_service_id": query.knowledge_service_id,
            },
        )

        return query

    async def save(self, query: KnowledgeServiceQuery) -> None:
        """Store or update a knowledge service query.

        Args:
            query: KnowledgeServiceQuery object to store
        """
        logger.debug(
            "MemoryKnowledgeServiceQueryRepository: Saving query",
            extra={"query_id": query.query_id},
        )

        # Update the updated_at timestamp using proper Pydantic pattern
        updated_query = query.model_copy(
            update={"updated_at": datetime.now(timezone.utc)}
        )

        # Store in memory
        self._queries[query.query_id] = updated_query

        logger.info(
            "MemoryKnowledgeServiceQueryRepository: Query saved successfully",
            extra={
                "query_id": query.query_id,
                "query_name": query.name,
                "knowledge_service_id": query.knowledge_service_id,
            },
        )

    async def generate_id(self) -> str:
        """Generate a unique query identifier.

        Returns:
            Unique string identifier for a new query
        """
        query_id = f"query-{uuid.uuid4().hex[:12]}"

        logger.debug(
            "MemoryKnowledgeServiceQueryRepository: Generated query ID",
            extra={"query_id": query_id},
        )

        return query_id

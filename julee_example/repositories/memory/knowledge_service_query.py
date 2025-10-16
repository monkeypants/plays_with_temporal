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
from typing import Dict, Optional, Any, List

from julee_example.domain.models.assembly_specification import (
    KnowledgeServiceQuery,
)
from julee_example.domain.repositories.knowledge_service_query import (
    KnowledgeServiceQueryRepository,
)
from .base import MemoryRepositoryMixin

logger = logging.getLogger(__name__)


class MemoryKnowledgeServiceQueryRepository(
    KnowledgeServiceQueryRepository,
    MemoryRepositoryMixin[KnowledgeServiceQuery],
):
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
        self.logger = logger
        self.entity_name = "KnowledgeServiceQuery"
        self.storage_dict: Dict[str, KnowledgeServiceQuery] = {}

        logger.debug("Initializing MemoryKnowledgeServiceQueryRepository")

    async def get(self, query_id: str) -> Optional[KnowledgeServiceQuery]:
        """Retrieve a knowledge service query by ID.

        Args:
            query_id: Unique query identifier

        Returns:
            KnowledgeServiceQuery object if found, None otherwise
        """
        return self.get_entity(query_id)

    async def save(self, query: KnowledgeServiceQuery) -> None:
        """Store or update a knowledge service query.

        Args:
            query: KnowledgeServiceQuery object to store
        """
        self.save_entity(query, "query_id")

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
        return self.get_many_entities(query_ids)

    async def generate_id(self) -> str:
        """Generate a unique query identifier.

        Returns:
            Unique string identifier for a new query
        """
        return self.generate_entity_id("query")

    async def list_all(self) -> List[KnowledgeServiceQuery]:
        """List all knowledge service queries.

        Returns:
            List of all knowledge service queries, sorted by query_id
        """
        self.logger.debug(
            "MemoryKnowledgeServiceQueryRepository: Listing all queries"
        )

        # Get all entities and sort by query_id
        entities = list(self.storage_dict.values())
        entities.sort(key=lambda x: x.query_id)

        self.logger.info(
            "MemoryKnowledgeServiceQueryRepository: Retrieved "
            f"{len(entities)} queries",
            extra={"count": len(entities)},
        )

        return entities

    def _add_entity_specific_log_data(
        self, entity: KnowledgeServiceQuery, log_data: Dict[str, Any]
    ) -> None:
        """Add knowledge service query-specific data to log entries."""
        super()._add_entity_specific_log_data(entity, log_data)
        log_data["query_name"] = entity.name
        log_data["knowledge_service_id"] = entity.knowledge_service_id

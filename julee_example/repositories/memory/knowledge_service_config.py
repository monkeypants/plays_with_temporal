"""
Memory implementation of KnowledgeServiceConfigRepository.

This module provides an in-memory implementation of the KnowledgeServiceConfigRepository
protocol that follows the Clean Architecture patterns defined in the
Fun-Police Framework. It handles knowledge service configuration storage
in memory dictionaries, ensuring idempotency and proper error handling.

The implementation uses Python dictionaries to store knowledge service
configuration data, making it ideal for testing scenarios where external
dependencies should be avoided. All operations are still async to maintain
interface compatibility.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict

from julee_example.domain import KnowledgeServiceConfig
from julee_example.repositories.knowledge_service_config import KnowledgeServiceConfigRepository

logger = logging.getLogger(__name__)


class MemoryKnowledgeServiceConfigRepository(KnowledgeServiceConfigRepository):
    """
    Memory implementation of KnowledgeServiceConfigRepository using Python dictionaries.

    This implementation stores knowledge service configurations in memory:
    - Knowledge Services: Dictionary keyed by knowledge_service_id containing KnowledgeServiceConfig objects

    This provides a lightweight, dependency-free option for testing while
    maintaining the same interface as other implementations.
    """

    def __init__(self) -> None:
        """Initialize repository with empty in-memory storage."""
        logger.debug("Initializing MemoryKnowledgeServiceConfigRepository")

        # Storage dictionary
        self._knowledge_services: Dict[str, KnowledgeServiceConfig] = {}

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
            "MemoryKnowledgeServiceConfigRepository: Attempting to retrieve knowledge service",
            extra={"knowledge_service_id": knowledge_service_id},
        )

        knowledge_service = self._knowledge_services.get(knowledge_service_id)
        if knowledge_service is None:
            logger.debug(
                "MemoryKnowledgeServiceConfigRepository: Knowledge service not found",
                extra={"knowledge_service_id": knowledge_service_id},
            )
            return None

        logger.info(
            "MemoryKnowledgeServiceConfigRepository: Knowledge service retrieved successfully",
            extra={
                "knowledge_service_id": knowledge_service_id,
                "name": knowledge_service.name,
                "service_api": knowledge_service.service_api.value,
            },
        )

        return knowledge_service

    async def save(self, knowledge_service: KnowledgeServiceConfig) -> None:
        """Save a knowledge service configuration.

        Args:
            knowledge_service: Complete KnowledgeServiceConfig to save
        """
        logger.debug(
            "MemoryKnowledgeServiceConfigRepository: Saving knowledge service",
            extra={"knowledge_service_id": knowledge_service.knowledge_service_id},
        )

        # Update timestamp
        knowledge_service.updated_at = datetime.now(timezone.utc)

        # Ensure created_at is set for new services
        if knowledge_service.created_at is None:
            knowledge_service.created_at = datetime.now(timezone.utc)

        # Store the knowledge service (idempotent - will overwrite if exists)
        self._knowledge_services[knowledge_service.knowledge_service_id] = knowledge_service

        logger.info(
            "MemoryKnowledgeServiceConfigRepository: Knowledge service saved successfully",
            extra={
                "knowledge_service_id": knowledge_service.knowledge_service_id,
                "name": knowledge_service.name,
                "service_api": knowledge_service.service_api.value,
            },
        )

    async def generate_id(self) -> str:
        """Generate a unique knowledge service identifier.

        Returns:
            Unique knowledge service ID string
        """
        knowledge_service_id = f"ks-{uuid.uuid4()}"

        logger.debug(
            "MemoryKnowledgeServiceConfigRepository: Generated knowledge service ID",
            extra={"knowledge_service_id": knowledge_service_id},
        )

        return knowledge_service_id

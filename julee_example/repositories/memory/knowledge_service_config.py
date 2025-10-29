"""
Memory implementation of KnowledgeServiceConfigRepository.

This module provides an in-memory implementation of the
KnowledgeServiceConfigRepository
protocol that follows the Clean Architecture patterns defined in the
Fun-Police Framework. It handles knowledge service configuration storage
in memory dictionaries, ensuring idempotency and proper error handling.

The implementation uses Python dictionaries to store knowledge service
configuration data, making it ideal for testing scenarios where external
dependencies should be avoided. All operations are still async to maintain
interface compatibility.
"""

import logging
from typing import Optional, Dict, Any, List

from julee_example.domain.models.knowledge_service_config import (
    KnowledgeServiceConfig,
)
from julee_example.domain.repositories.knowledge_service_config import (
    KnowledgeServiceConfigRepository,
)
from .base import MemoryRepositoryMixin

logger = logging.getLogger(__name__)


class MemoryKnowledgeServiceConfigRepository(
    KnowledgeServiceConfigRepository,
    MemoryRepositoryMixin[KnowledgeServiceConfig],
):
    """
    Memory implementation of KnowledgeServiceConfigRepository using Python
    dictionaries.

    This implementation stores knowledge service configurations in memory:
    - Knowledge Services: Dictionary keyed by knowledge_service_id containing
      KnowledgeServiceConfig objects

    This provides a lightweight, dependency-free option for testing while
    maintaining the same interface as other implementations.
    """

    def __init__(self) -> None:
        """Initialize repository with empty in-memory storage."""
        self.logger = logger
        self.entity_name = "KnowledgeServiceConfig"
        self.storage_dict: Dict[str, KnowledgeServiceConfig] = {}

        logger.debug("Initializing MemoryKnowledgeServiceConfigRepository")

    async def get(
        self, knowledge_service_id: str
    ) -> Optional[KnowledgeServiceConfig]:
        """Retrieve a knowledge service configuration by ID.

        Args:
            knowledge_service_id: Unique knowledge service identifier

        Returns:
            KnowledgeServiceConfig object if found, None otherwise
        """
        return self.get_entity(knowledge_service_id)

    async def save(self, knowledge_service: KnowledgeServiceConfig) -> None:
        """Save a knowledge service configuration.

        Args:
            knowledge_service: Complete KnowledgeServiceConfig to save
        """
        self.save_entity(knowledge_service, "knowledge_service_id")

    async def generate_id(self) -> str:
        """Generate a unique knowledge service identifier.

        Returns:
            Unique knowledge service ID string
        """
        return self.generate_entity_id("ks")

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
        return self.get_many_entities(knowledge_service_ids)

    async def list_all(self) -> List[KnowledgeServiceConfig]:
        """List all knowledge service configurations.

        Returns:
            List of all KnowledgeServiceConfig entities in the repository
        """
        self.logger.debug(
            f"Memory{self.entity_name}Repository: Listing all "
            f"{self.entity_name.lower()}s"
        )

        configs = list(self.storage_dict.values())

        self.logger.info(
            f"Memory{self.entity_name}Repository: Listed all "
            f"{self.entity_name.lower()}s",
            extra={"count": len(configs)},
        )

        return configs

    def _add_entity_specific_log_data(
        self, entity: KnowledgeServiceConfig, log_data: Dict[str, Any]
    ) -> None:
        """Add knowledge service config-specific data to log entries."""
        super()._add_entity_specific_log_data(entity, log_data)
        log_data["service_name"] = entity.name
        log_data["service_api"] = entity.service_api.value

"""
Memory implementation of AssemblyRepository.

This module provides an in-memory implementation of the AssemblyRepository
protocol that follows the Clean Architecture patterns defined in the
Fun-Police Framework. It handles assembly storage in memory dictionaries,
ensuring idempotency and proper error handling.

The implementation uses Python dictionaries to store assembly data, making it
ideal for testing scenarios where external dependencies should be avoided.
All operations are still async to maintain interface compatibility.
"""

import logging
from typing import Optional, Dict, Any, List

from julee_example.domain.models.assembly import Assembly
from julee_example.domain.repositories.assembly import AssemblyRepository
from .base import MemoryRepositoryMixin

logger = logging.getLogger(__name__)


class MemoryAssemblyRepository(
    AssemblyRepository, MemoryRepositoryMixin[Assembly]
):
    """
    Memory implementation of AssemblyRepository using Python dictionaries.

    This implementation stores assembly data in memory using a dictionary
    keyed by assembly_id. This provides a lightweight, dependency-free
    option for testing.
    """

    def __init__(self) -> None:
        """Initialize repository with empty in-memory storage."""
        self.logger = logger
        self.entity_name = "Assembly"
        self.storage_dict: Dict[str, Assembly] = {}

        logger.debug("Initializing MemoryAssemblyRepository")

    async def get(self, assembly_id: str) -> Optional[Assembly]:
        """Retrieve an assembly by ID.

        Args:
            assembly_id: Unique assembly identifier

        Returns:
            Assembly if found, None otherwise
        """
        return self.get_entity(assembly_id)

    async def save(self, assembly: Assembly) -> None:
        """Save assembly metadata (status, updated_at, etc.).

        Args:
            assembly: Assembly entity
        """
        self.save_entity(assembly, "assembly_id")

    async def generate_id(self) -> str:
        """Generate a unique assembly identifier.

        Returns:
            Unique assembly ID string
        """
        return self.generate_entity_id("assembly")

    async def get_many(
        self, assembly_ids: List[str]
    ) -> Dict[str, Optional[Assembly]]:
        """Retrieve multiple assemblies by ID.

        Args:
            assembly_ids: List of unique assembly identifiers

        Returns:
            Dict mapping assembly_id to Assembly (or None if not found)
        """
        return self.get_many_entities(assembly_ids)

    def _add_entity_specific_log_data(
        self, entity: Assembly, log_data: Dict[str, Any]
    ) -> None:
        """Add assembly-specific data to log entries."""
        super()._add_entity_specific_log_data(entity, log_data)
        log_data["assembled_document_id"] = entity.assembled_document_id

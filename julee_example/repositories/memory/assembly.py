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
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict

from julee_example.domain import Assembly
from julee_example.repositories.assembly import AssemblyRepository

logger = logging.getLogger(__name__)


class MemoryAssemblyRepository(AssemblyRepository):
    """
    Memory implementation of AssemblyRepository using Python dictionaries.

    This implementation stores assembly data in memory using a dictionary
    keyed by assembly_id. This provides a lightweight, dependency-free
    option for testing.
    """

    def __init__(self) -> None:
        """Initialize repository with empty in-memory storage."""
        logger.debug("Initializing MemoryAssemblyRepository")

        # Storage dictionary
        self._assemblies: Dict[str, Assembly] = {}

    async def get(self, assembly_id: str) -> Optional[Assembly]:
        """Retrieve an assembly by ID.

        Args:
            assembly_id: Unique assembly identifier

        Returns:
            Assembly if found, None otherwise
        """
        logger.debug(
            "MemoryAssemblyRepository: Attempting to retrieve assembly",
            extra={
                "assembly_id": assembly_id,
            },
        )

        assembly = self._assemblies.get(assembly_id)
        if assembly is None:
            logger.debug(
                "MemoryAssemblyRepository: Assembly not found",
                extra={"assembly_id": assembly_id},
            )
            return None

        logger.info(
            "MemoryAssemblyRepository: Assembly retrieved successfully",
            extra={
                "assembly_id": assembly_id,
                "assembled_document_id": assembly.assembled_document_id,
            },
        )

        return assembly

    async def save(self, assembly: Assembly) -> None:
        """Save assembly metadata (status, updated_at, etc.).

        Args:
            assembly: Assembly entity
        """
        logger.debug(
            "MemoryAssemblyRepository: Saving assembly",
            extra={
                "assembly_id": assembly.assembly_id,
                "status": assembly.status.value,
            },
        )

        # Update timestamp
        assembly_dict = assembly.model_dump()
        assembly_dict["updated_at"] = datetime.now(timezone.utc)

        updated_assembly = Assembly(**assembly_dict)
        self._assemblies[assembly.assembly_id] = updated_assembly

        logger.info(
            "MemoryAssemblyRepository: Assembly saved successfully",
            extra={
                "assembly_id": assembly.assembly_id,
                "status": assembly.status.value,
                "assembled_document_id": assembly.assembled_document_id,
            },
        )

    async def generate_id(self) -> str:
        """Generate a unique assembly identifier.

        Returns:
            Unique assembly ID string
        """
        assembly_id = f"assembly-{uuid.uuid4()}"

        logger.debug(
            "MemoryAssemblyRepository: Generated assembly ID",
            extra={"assembly_id": assembly_id},
        )

        return assembly_id

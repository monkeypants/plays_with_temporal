"""
Memory implementation of AssemblySpecificationRepository.

This module provides an in-memory implementation of the
AssemblySpecificationRepository protocol that follows the Clean Architecture
patterns defined in the Fun-Police Framework. It handles assembly
specification storage with JSON schemas and knowledge service query
configurations in memory dictionaries, ensuring idempotency and proper
error handling.

The implementation uses Python dictionaries to store specification data,
making it ideal for testing scenarios where external dependencies should be
avoided. All operations are still async to maintain interface compatibility.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict

from julee_example.domain import AssemblySpecification
from julee_example.repositories.assembly_specification import (
    AssemblySpecificationRepository,
)

logger = logging.getLogger(__name__)


class MemoryAssemblySpecificationRepository(AssemblySpecificationRepository):
    """
    Memory implementation of AssemblySpecificationRepository using Python
    dictionaries.

    This implementation stores assembly specifications in memory:
    - Specifications: Dictionary keyed by assembly_specification_id containing
      AssemblySpecification objects

    This provides a lightweight, dependency-free option for testing while
    maintaining the same interface as other implementations.
    """

    def __init__(self) -> None:
        """Initialize repository with empty in-memory storage."""
        logger.debug("Initializing MemoryAssemblySpecificationRepository")

        # Storage dictionary
        self._specifications: Dict[str, AssemblySpecification] = {}

    async def get(
        self, assembly_specification_id: str
    ) -> Optional[AssemblySpecification]:
        """Retrieve an assembly specification by ID.

        Args:
            assembly_specification_id: Unique specification identifier

        Returns:
            AssemblySpecification if found, None otherwise
        """
        logger.debug(
            "MemoryAssemblySpecificationRepository: Attempting to retrieve "
            "specification",
            extra={
                "assembly_specification_id": assembly_specification_id,
            },
        )

        specification = self._specifications.get(assembly_specification_id)
        if specification is None:
            logger.debug(
                "MemoryAssemblySpecificationRepository: Specification not "
                "found",
                extra={
                    "assembly_specification_id": assembly_specification_id
                },
            )
            return None

        logger.info(
            "MemoryAssemblySpecificationRepository: Specification "
            "retrieved successfully",
            extra={
                "assembly_specification_id": assembly_specification_id,
                "spec_name": specification.name,
                "status": specification.status.value,
                "version": specification.version,
            },
        )

        return specification

    async def save(
        self, assembly_specification: AssemblySpecification
    ) -> None:
        """Save an assembly specification.

        Args:
            assembly_specification: Complete AssemblySpecification to save
        """
        logger.debug(
            "MemoryAssemblySpecificationRepository: Saving specification",
            extra={
                "assembly_specification_id": (
                    assembly_specification.assembly_specification_id
                ),
                "spec_name": assembly_specification.name,
                "status": assembly_specification.status.value,
            },
        )

        # Update timestamp
        assembly_specification.updated_at = datetime.now(timezone.utc)

        # Store the specification (idempotent - will overwrite if exists)
        self._specifications[
            assembly_specification.assembly_specification_id
        ] = assembly_specification

        logger.info(
            "MemoryAssemblySpecificationRepository: Specification saved "
            "successfully",
            extra={
                "assembly_specification_id": (
                    assembly_specification.assembly_specification_id
                ),
                "spec_name": assembly_specification.name,
                "status": assembly_specification.status.value,
                "version": assembly_specification.version,
                "updated_at": (assembly_specification.updated_at.isoformat()),
            },
        )

    async def generate_id(self) -> str:
        """Generate a unique assembly specification identifier.

        Returns:
            Unique assembly specification ID string
        """
        specification_id = f"spec-{uuid.uuid4()}"

        logger.debug(
            "MemoryAssemblySpecificationRepository: Generated specification "
            "ID",
            extra={"assembly_specification_id": specification_id},
        )

        return specification_id

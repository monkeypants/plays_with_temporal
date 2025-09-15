"""
Memory implementation of AssemblyRepository.

This module provides an in-memory implementation of the AssemblyRepository
protocol that follows the Clean Architecture patterns defined in the
Fun-Police Framework. It handles assembly storage with both assembly metadata
and iteration data in memory dictionaries, ensuring idempotency and proper
error handling.

The implementation uses Python dictionaries to store assembly data, making it
ideal for testing scenarios where external dependencies should be avoided.
All operations are still async to maintain interface compatibility.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict

from julee_example.domain import Assembly, AssemblyIteration
from julee_example.repositories.assembly import AssemblyRepository

logger = logging.getLogger(__name__)


class MemoryAssemblyRepository(AssemblyRepository):
    """
    Memory implementation of AssemblyRepository using Python dictionaries.

    This implementation stores assembly metadata and iterations in memory:
    - Assembly metadata: Dictionary keyed by assembly_id
    - Iterations: Dictionary keyed by assembly_id containing lists of
      iterations

    This separation maintains the same logical structure as other
    implementations
    while providing a lightweight, dependency-free option for testing.
    """

    def __init__(self) -> None:
        """Initialize repository with empty in-memory storage."""
        logger.debug("Initializing MemoryAssemblyRepository")

        # Storage dictionaries
        self._assemblies: Dict[str, Assembly] = {}
        self._iterations: Dict[str, list[AssemblyIteration]] = {}

    async def get(self, assembly_id: str) -> Optional[Assembly]:
        """Retrieve an assembly with all its iterations.

        Args:
            assembly_id: Unique assembly identifier

        Returns:
            Assembly aggregate with all iterations if found, None otherwise
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

        # Get iterations for this assembly
        iterations = self._iterations.get(assembly_id, [])

        # Create a copy with current iterations
        assembly_dict = assembly.model_dump()
        assembly_dict["iterations"] = iterations
        result = Assembly(**assembly_dict)

        logger.info(
            "MemoryAssemblyRepository: Assembly retrieved successfully",
            extra={
                "assembly_id": assembly_id,
                "iteration_count": len(iterations),
            },
        )

        return result

    async def add_iteration(
        self, assembly_id: str, assembly_iteration: AssemblyIteration
    ) -> Assembly:
        """Add a new iteration to an assembly and persist it immediately.

        Args:
            assembly_id: ID of the assembly to add iteration to
            assembly_iteration: Complete AssemblyIteration object to add

        Returns:
            Updated Assembly aggregate with the new iteration included
        """
        logger.debug(
            "MemoryAssemblyRepository: Adding iteration to assembly",
            extra={
                "assembly_id": assembly_id,
                "document_id": assembly_iteration.document_id,
            },
        )

        assembly = self._assemblies.get(assembly_id)
        if assembly is None:
            raise ValueError(f"Assembly not found: {assembly_id}")

        # Get existing iterations
        iterations = self._iterations.get(assembly_id, [])

        # Check for idempotency - if document_id already exists in iterations
        for existing_iteration in iterations:
            if (
                existing_iteration.document_id
                == assembly_iteration.document_id
            ):
                logger.debug(
                    "MemoryAssemblyRepository: Iteration with document_id "
                    "already exists, returning unchanged",
                    extra={
                        "assembly_id": assembly_id,
                        "document_id": assembly_iteration.document_id,
                    },
                )
                # Return assembly with current iterations
                assembly_dict = assembly.model_dump()
                assembly_dict["iterations"] = iterations
                return Assembly(**assembly_dict)

        # Use provided iteration but set sequential ID and update timestamps
        iteration_id = len(iterations) + 1
        new_iteration = AssemblyIteration(
            iteration_id=iteration_id,
            document_id=assembly_iteration.document_id,
            scorecard_results=assembly_iteration.scorecard_results,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        # Add iteration to storage
        iterations.append(new_iteration)
        self._iterations[assembly_id] = iterations

        # Update assembly timestamp
        assembly_dict = assembly.model_dump()
        assembly_dict["updated_at"] = datetime.now(timezone.utc)
        assembly_dict["iterations"] = iterations
        updated_assembly = Assembly(**assembly_dict)

        # Store updated assembly
        self._assemblies[assembly_id] = updated_assembly

        logger.info(
            "MemoryAssemblyRepository: Iteration added successfully",
            extra={
                "assembly_id": assembly_id,
                "iteration_id": new_iteration.iteration_id,
                "document_id": assembly_iteration.document_id,
                "scorecard_results_count": len(
                    new_iteration.scorecard_results
                ),
            },
        )

        return updated_assembly

    async def save(self, assembly: Assembly) -> None:
        """Save assembly metadata (status, updated_at, etc.).

        Args:
            assembly: Assembly aggregate
        """
        logger.debug(
            "MemoryAssemblyRepository: Saving assembly metadata",
            extra={
                "assembly_id": assembly.assembly_id,
                "status": assembly.status.value,
            },
        )

        # Update timestamp
        assembly_dict = assembly.model_dump()
        assembly_dict["updated_at"] = datetime.now(timezone.utc)

        # Don't overwrite iterations from the assembly object - they're
        # managed
        # separately via add_iteration
        existing_iterations = self._iterations.get(assembly.assembly_id, [])
        assembly_dict["iterations"] = existing_iterations

        updated_assembly = Assembly(**assembly_dict)
        self._assemblies[assembly.assembly_id] = updated_assembly

        logger.info(
            "MemoryAssemblyRepository: Assembly metadata saved successfully",
            extra={
                "assembly_id": assembly.assembly_id,
                "status": assembly.status.value,
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

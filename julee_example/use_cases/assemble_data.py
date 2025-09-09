"""
Use case logic for data assembly within the Capture, Extract, Assemble,
Publish workflow.

This module contains use case classes that orchestrate business logic while
remaining framework-agnostic. Dependencies are injected via repository
instances following the Clean Architecture principles.
"""

import logging
from datetime import datetime, timezone

from julee_example.domain import Assembly, AssemblyStatus
from julee_example.repositories import (
    DocumentRepository,
    AssemblyRepository,
    AssemblySpecificationRepository,
)
from sample.validation import ensure_repository_protocol
from .decorators import try_use_case_step

logger = logging.getLogger(__name__)


class AssembleDataUseCase:
    """
    Use case for assembling documents according to specifications.

    This class orchestrates the business logic for the "Assemble" phase
    of the Capture, Extract, Assemble, Publish workflow while remaining
    framework-agnostic. It depends only on repository protocols, not
    concrete implementations.

    In workflow contexts, this use case is called from workflow code with
    repository stubs that delegate to Temporal activities for durability.
    The use case remains completely unaware of whether it's running in a
    workflow context or a simple async context - it just calls repository
    methods and expects them to work correctly.

    Architectural Notes:
    - This class contains pure business logic with no framework dependencies
    - Repository dependencies are injected via constructor
      (dependency inversion)
    - All error handling and compensation logic is contained here
    - The use case works with domain objects exclusively
    - Deterministic execution is guaranteed by avoiding
      non-deterministic operations
    """

    def __init__(
        self,
        document_repo: DocumentRepository,
        assembly_repo: AssemblyRepository,
        assembly_specification_repo: AssemblySpecificationRepository,
    ) -> None:
        """Initialize data assembly use case.

        Args:
            document_repo: Repository for document operations
            assembly_repo: Repository for assembly operations
            assembly_specification_repo: Repository for assembly
                specification operations

        Note:
            The repositories passed here may be concrete implementations
            (for testing or direct execution) or workflow stubs (for
            Temporal workflow execution). The use case doesn't know or care
            which - it just calls the methods defined in the protocols.

            Repositories are validated at construction time to catch
            configuration errors early in the application lifecycle.
        """
        # Validate at construction time for early error detection
        self.document_repo = ensure_repository_protocol(
            document_repo, DocumentRepository  # type: ignore[type-abstract]
        )
        self.assembly_repo = ensure_repository_protocol(
            assembly_repo, AssemblyRepository  # type: ignore[type-abstract]
        )
        self.assembly_specification_repo = ensure_repository_protocol(
            assembly_specification_repo, AssemblySpecificationRepository  # type: ignore[type-abstract]
        )

    async def assemble_data(
        self,
        document_id: str,
        assembly_specification_id: str,
    ) -> Assembly:
        """
        Assemble a document according to its specification and create a new
        assembly.

        This method orchestrates the core assembly workflow:
        1. Generates a unique assembly ID
        2. Retrieves the assembly specification
        3. Retrieves the source document
        4. Processes the document according to the specification
        5. Creates and returns the new assembly

        Args:
            document_id: ID of the document to assemble
            assembly_specification_id: ID of the specification to use

        Returns:
            New Assembly with the assembled document iteration

        Raises:
            ValueError: If required entities are not found or invalid
            RuntimeError: If assembly processing fails
        """
        logger.debug(
            "Starting data assembly use case",
            extra={
                "document_id": document_id,
                "assembly_specification_id": assembly_specification_id,
            },
        )

        # Step 1: Generate unique assembly ID
        assembly_id = await self._generate_assembly_id(
            document_id, assembly_specification_id
        )

        # TODO: Implement the assembly logic following the saga pattern
        # This should:
        # 1. Validate all required entities exist
        # 2. Process the document according to the specification
        # 3. Add the iteration to the assembly
        # 4. Handle any compensation if needed

        # For now, return an empty Assembly with the generated ID
        assembly = Assembly(
            assembly_id=assembly_id,
            assembly_specification_id=assembly_specification_id,
            input_document_id=document_id,
            status=AssemblyStatus.PENDING,
            iterations=[],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        return assembly

    @try_use_case_step("assembly_id_generation")
    async def _generate_assembly_id(
        self, document_id: str, assembly_specification_id: str
    ) -> str:
        """Generate a unique assembly ID with consistent error handling."""
        return await self.assembly_repo.generate_id()

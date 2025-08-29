"""
Assembly specification repository interface defined as Protocol for the
Capture, Extract, Assemble, Publish workflow.

This module defines the repository protocol for handling assembly
specifications and template management. All repository operations follow the
same principles as the sample repositories:

- **Idempotency**: All methods are designed to be idempotent and safe for
  retry. Multiple calls with the same parameters will produce the same
  result without unintended side effects.

- **Workflow Safety**: All operations are safe to call from deterministic
  workflow contexts. Non-deterministic operations (like ID generation) are
  explicitly delegated to activities.

- **Domain Objects**: Methods accept and return domain objects or primitives,
  never framework-specific types.

In Temporal workflow contexts, these protocols are implemented by workflow
stubs that delegate to activities for durability and proper error handling.
"""

from typing import Protocol, List, Optional, runtime_checkable
from julee_example.domain import AssemblySpec


@runtime_checkable
class AssemblySpecRepository(Protocol):
    """Handles assembly specifications and template management.

    This repository manages the templates and specifications that define
    how documents are assembled into final outputs.
    """

    async def get_assembly_spec(
        self, assembly_id: str
    ) -> Optional[AssemblySpec]:
        """Retrieve specification for an assembly type.

        Args:
            assembly_id: Assembly type identifier

        Returns:
            AssemblySpec if found, None otherwise

        Implementation Notes:
        - Must be idempotent: multiple calls return same result
        - Should include template path and required extractors
        - May be cached for performance
        - Critical for determining extraction requirements
        - Used in workflow planning phase
        """
        ...

    async def get_required_extractors(
        self, assembly_ids: List[str]
    ) -> List[str]:
        """Get all extractors required for given assembly types.

        Args:
            assembly_ids: List of assembly type identifiers

        Returns:
            Deduplicated list of required extractor names

        Implementation Notes:
        - Must be idempotent and deterministic
        - Should handle overlapping extractor requirements
        - Could inspect Jinja2 templates for context variables
        - Alternative to parsing templates at runtime
        - Used for workflow fan-out planning
        """
        ...

    async def get_template_content(self, template_path: str) -> Optional[str]:
        """Retrieve template content for rendering.

        Args:
            template_path: Path to the template file

        Returns:
            Template content as string, None if not found

        Implementation Notes:
        - Must be idempotent: multiple calls return same result
        - Templates typically Jinja2 format
        - Used during assembly rendering phase
        - May be cached for performance
        - Should handle template versioning if needed
        """
        ...

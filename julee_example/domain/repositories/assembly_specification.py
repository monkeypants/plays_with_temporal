"""
AssemblySpecification repository interface defined as Protocol for the
Capture, Extract, Assemble, Publish workflow.

This module defines the core assembly specification storage and retrieval
repository protocol. The repository works with AssemblySpecification domain
objects that define how to assemble documents of specific types.

All repository operations follow the same principles as the sample
repositories:

- **Idempotency**: All methods are designed to be idempotent and safe for
  retry. Multiple calls with the same parameters will produce the same
  result without unintended side effects.

- **Workflow Safety**: All operations are safe to call from deterministic
  workflow contexts. Non-deterministic operations (like ID generation) are
  explicitly delegated to activities.

- **Domain Objects**: Methods accept and return domain objects or primitives,
  never framework-specific types. AssemblySpecification contains its JSON
  schema and knowledge service query configurations.

- **Specification Management**: Repository handles complete
  AssemblySpecification entities including their JSON schemas and knowledge
  service query mappings for document assembly workflows.

In Temporal workflow contexts, these protocols are implemented by workflow
stubs that delegate to activities for durability and proper error handling.
"""

from typing import Protocol, runtime_checkable
from julee_example.domain.models.assembly_specification import (
    AssemblySpecification,
)
from .base import BaseRepository


@runtime_checkable
class AssemblySpecificationRepository(
    BaseRepository[AssemblySpecification], Protocol
):
    """Handles assembly specification storage and retrieval operations.

    This repository manages AssemblySpecification entities within the Capture,
    Extract, Assemble, Publish workflow. Specifications define how to assemble
    documents of specific types, including JSON schemas and knowledge service
    query configurations.

    Inherits common CRUD operations (get, save, generate_id) from
    BaseRepository.
    """

    pass

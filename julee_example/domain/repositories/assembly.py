"""
Assembly repository interface defined as Protocol for the Capture, Extract,
Assemble, Publish workflow.

This module defines the core assembly storage and retrieval repository
protocol. The repository works with Assembly domain objects that produce
a single assembled document.

All repository operations follow the same principles as the sample
repositories:

- **Idempotency**: All methods are designed to be idempotent and safe for
  retry. Multiple calls with the same parameters will produce the same
  result without unintended side effects.

- **Workflow Safety**: All operations are safe to call from deterministic
  workflow contexts. Non-deterministic operations (like ID generation) are
  explicitly delegated to activities.

- **Domain Objects**: Methods accept and return domain objects or primitives,
  never framework-specific types. Assembly contains its assembled document ID.

- **Aggregate Boundary**: Repository handles Assembly entities with their
  assembled document references.

In Temporal workflow contexts, these protocols are implemented by workflow
stubs that delegate to activities for durability and proper error handling.
"""

from typing import runtime_checkable, Protocol
from julee_example.domain.models import Assembly
from .base import BaseRepository


@runtime_checkable
class AssemblyRepository(BaseRepository[Assembly], Protocol):
    """Handles assembly storage and retrieval operations.

    This repository manages Assembly entities within the Capture, Extract,
    Assemble, Publish workflow. Each Assembly produces a single assembled
    document.

    Inherits common CRUD operations (get, save, generate_id) from
    BaseRepository.
    """

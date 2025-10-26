"""
Policy repository interface defined as Protocol for the Capture, Extract,
Assemble, Publish workflow.

This module defines the core policy storage and retrieval repository
protocol. The repository works with Policy domain objects that define
validation criteria and optional transformations for documents.

All repository operations follow the same principles as the sample
repositories:

- **Idempotency**: All methods are designed to be idempotent and safe for
  retry. Multiple calls with the same parameters will produce the same
  result without unintended side effects.

- **Workflow Safety**: All operations are safe to call from deterministic
  workflow contexts. Non-deterministic operations (like ID generation) are
  explicitly delegated to activities.

- **Domain Objects**: Methods accept and return domain objects or primitives,
  never framework-specific types. Policy contains validation scores and
  optional transformation queries.

- **Policy Management**: Repository handles Policy entities with their
  validation criteria, transformation queries, and status management for
  the quality assurance workflow.

In Temporal workflow contexts, these protocols are implemented by workflow
stubs that delegate to activities for durability and proper error handling.
"""

from typing import runtime_checkable, Protocol
from julee_example.domain.models import Policy
from .base import BaseRepository


@runtime_checkable
class PolicyRepository(BaseRepository[Policy], Protocol):
    """Handles policy storage and retrieval operations.

    This repository manages Policy entities within the Capture, Extract,
    Assemble, Publish workflow. Policies define validation criteria and
    optional transformations for documents in the quality assurance process.

    Inherits common CRUD operations (get, save, generate_id) from
    BaseRepository.
    """

    pass

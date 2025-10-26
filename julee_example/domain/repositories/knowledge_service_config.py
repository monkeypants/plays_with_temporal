"""
KnowledgeServiceConfig repository interface defined as Protocol for the
Capture, Extract, Assemble, Publish workflow.

This module defines the knowledge service configuration repository protocol.
The repository works with KnowledgeService domain objects for metadata
persistence only. External service operations are handled by the service
layer.

All repository operations follow the same principles as the sample
repositories:

- **Idempotency**: All methods are designed to be idempotent and safe for
  retry. Multiple calls with the same parameters will produce the same
  result without unintended side effects.

- **Workflow Safety**: All operations are safe to call from deterministic
  workflow contexts. Non-deterministic operations (like ID generation) are
  explicitly delegated to activities.

- **Domain Objects**: Methods accept and return domain objects or primitives,
  never framework-specific types. Results are returned as structured domain
  objects.

- **External Service Integration**: Repository implementations handle the
  complexities of integrating with external knowledge services while
  maintaining a clean, consistent interface.

In Temporal workflow contexts, these protocols are implemented by workflow
stubs that delegate to activities for durability and proper error handling.
"""

from typing import Protocol, runtime_checkable
from julee_example.domain.models.knowledge_service_config import (
    KnowledgeServiceConfig,
)
from .base import BaseRepository


@runtime_checkable
class KnowledgeServiceConfigRepository(
    BaseRepository[KnowledgeServiceConfig], Protocol
):
    """Handles knowledge service configuration persistence.

    This repository manages knowledge service metadata and configuration
    storage within the Capture, Extract, Assemble, Publish workflow.
    External service operations are handled separately by the service layer.

    Inherits common CRUD operations (get, save, generate_id) from
    BaseRepository.
    """

    pass

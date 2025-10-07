"""
Document repository interface defined as Protocol for the Capture, Extract,
Assemble, Publish workflow.

This module defines the core document storage and retrieval repository
protocol. The repository works with Document domain objects that use BinaryIO
streams for efficient content handling.

All repository operations follow the same principles as the sample
repositories:

- **Idempotency**: All methods are designed to be idempotent and safe for
  retry. Multiple calls with the same parameters will produce the same
  result without unintended side effects.

- **Workflow Safety**: All operations are safe to call from deterministic
  workflow contexts. Non-deterministic operations (like ID generation) are
  explicitly delegated to activities.

- **Domain Objects**: Methods accept and return domain objects or primitives,
  never framework-specific types. Content streams are handled through the
  BinaryIO interface.

- **Content Streaming**: Repository implementations should support both
  small content (via BytesIO) and large content (via file streams) through
  the unified ContentStream interface wrapping io.IOBase.

In Temporal workflow contexts, these protocols are implemented by workflow
stubs that delegate to activities for durability and proper error handling.
"""

from typing import runtime_checkable, Protocol
from julee_example.domain.models import Document
from .base import BaseRepository


@runtime_checkable
class DocumentRepository(BaseRepository[Document], Protocol):
    """Handles document storage and retrieval operations.

    This repository manages the core document storage and metadata
    operations within the Capture, Extract, Assemble, Publish workflow.

    Inherits common CRUD operations (get, save, generate_id) from
    BaseRepository. The save method handles both content and metadata
    storage atomically.
    """

    pass

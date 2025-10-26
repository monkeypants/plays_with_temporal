"""
KnowledgeServiceQuery repository interface defined as Protocol for the
Capture, Extract, Assemble, Publish workflow.

This module defines the knowledge service query repository protocol.
The repository works with KnowledgeServiceQuery domain objects for
storing and retrieving query configurations that define how to extract
data using external knowledge services.

All repository operations follow the same principles as the sample
repositories:
- Protocol-based design for Clean Architecture
- Type safety with runtime validation
- Idempotent operations
- Proper error handling
- Framework independence

The repository handles the persistence of query definitions including
prompts, assistant prompts, metadata, and service configurations
that are used during the assembly process.
"""

from typing import Protocol, runtime_checkable

from julee_example.domain.models.assembly_specification import (
    KnowledgeServiceQuery,
)
from .base import BaseRepository


@runtime_checkable
class KnowledgeServiceQueryRepository(
    BaseRepository[KnowledgeServiceQuery], Protocol
):
    """Handles knowledge service query persistence and retrieval.

    This repository manages the storage and retrieval of
    KnowledgeServiceQuery domain objects within the Capture, Extract,
    Assemble, Publish workflow. These queries define how to extract
    specific data using external knowledge services during assembly.

    Inherits common CRUD operations (get, save, generate_id) from
    BaseRepository.
    """

    pass

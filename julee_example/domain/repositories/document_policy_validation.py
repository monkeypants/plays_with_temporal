"""
DocumentPolicyValidation repository interface defined as Protocol for the
Capture, Extract, Assemble, Publish workflow.

This module defines the core document policy validation storage and retrieval
repository protocol. The repository works with DocumentPolicyValidation
domain objects that track the validation of documents against policies.

All repository operations follow the same principles as the sample
repositories:

- **Idempotency**: All methods are designed to be idempotent and safe for
  retry. Multiple calls with the same parameters will produce the same
  result without unintended side effects.

- **Workflow Safety**: All operations are safe to call from deterministic
  workflow contexts. Non-deterministic operations (like ID generation) are
  explicitly delegated to activities.

- **Domain Objects**: Methods accept and return domain objects or primitives,
  never framework-specific types. DocumentPolicyValidation contains
  validation results, scores, and transformation tracking.

- **Validation Management**: Repository handles DocumentPolicyValidation
  entities with their status tracking, score recording, and transformation
  results for the quality assurance workflow.

In Temporal workflow contexts, these protocols are implemented by workflow
stubs that delegate to activities for durability and proper error handling.
"""

from typing import runtime_checkable, Protocol
from julee_example.domain.models.policy import DocumentPolicyValidation
from .base import BaseRepository


@runtime_checkable
class DocumentPolicyValidationRepository(
    BaseRepository[DocumentPolicyValidation], Protocol
):
    """Handles document policy validation storage and retrieval operations.

    This repository manages DocumentPolicyValidation entities within the
    Capture, Extract, Assemble, Publish workflow. These entities track the
    complete lifecycle of validating documents against policies, including
    initial validation scores, transformation results, and final outcomes.

    Inherits common CRUD operations (get, save, generate_id) from
    BaseRepository.
    """

    pass

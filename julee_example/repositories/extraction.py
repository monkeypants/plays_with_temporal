"""
Extraction repository interface defined as Protocol for the Capture, Extract,
Assemble, Publish workflow.

This module defines the repository protocol for handling extraction operations
and results storage. All repository operations follow the same principles as
the sample repositories:

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
from julee_example.domain import ExtractionResult


@runtime_checkable
class ExtractionRepository(Protocol):
    """Handles extraction operations and results storage.

    This repository manages the extraction of structured data from documents
    using various extractor implementations.
    """

    async def run_extraction(
        self, extractor_name: str, knowledge_service_id: str, document_id: str
    ) -> ExtractionResult:
        """Run a specific extractor on a document.

        Args:
            extractor_name: Name of the extractor to run
            knowledge_service_id: Document ID in knowledge service
            document_id: Internal document identifier

        Returns:
            ExtractionResult containing extracted data and status

        Implementation Notes:
        - May be non-deterministic (LLM-based extraction)
        - Should be idempotent: same inputs return same result
        - Must handle extractor failures gracefully
        - Suitable for parallel execution in workflow
        - Core operation in the "Extract" phase of Capture, Extract, Assemble,
          Publish
        """
        ...

    async def get_extraction_results(
        self, document_id: str, extractor_names: Optional[List[str]] = None
    ) -> List[ExtractionResult]:
        """Retrieve extraction results for a document.

        Args:
            document_id: Internal document identifier
            extractor_names: Specific extractors to retrieve, or None for all

        Returns:
            List of ExtractionResult objects

        Implementation Notes:
        - Must be idempotent: multiple calls return same results
        - Should handle missing or failed extractions
        - Used to gather context variables for template rendering
        - Critical for assembly phase workflow decisions
        """
        ...

    async def store_extraction_result(
        self, document_id: str, result: ExtractionResult
    ) -> None:
        """Store an extraction result.

        Args:
            document_id: Internal document identifier
            result: ExtractionResult to store

        Implementation Notes:
        - Must be idempotent: storing same result is safe
        - Should handle updates to existing extraction results
        - Used to persist extraction outputs for assembly
        - May need to handle large extracted data efficiently
        """
        ...

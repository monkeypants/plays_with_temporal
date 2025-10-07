"""
Memory implementation of DocumentPolicyValidationRepository.

This module provides an in-memory implementation of the
DocumentPolicyValidationRepository protocol that follows the Clean
Architecture patterns defined in the Fun-Police Framework. It handles
document policy validation storage in memory dictionaries, ensuring
idempotency and proper error handling.

The implementation uses Python dictionaries to store validation data, making
it ideal for testing scenarios where external dependencies should be avoided.
All operations are still async to maintain interface compatibility.
"""

import logging
from typing import Optional, Dict, Any, List

from julee_example.domain.models.policy import DocumentPolicyValidation
from julee_example.domain.repositories.document_policy_validation import (
    DocumentPolicyValidationRepository,
)
from .base import MemoryRepositoryMixin

logger = logging.getLogger(__name__)


class MemoryDocumentPolicyValidationRepository(
    DocumentPolicyValidationRepository,
    MemoryRepositoryMixin[DocumentPolicyValidation],
):
    """
    Memory implementation of DocumentPolicyValidationRepository using Python
    dictionaries.

    This implementation stores document policy validation data in memory using
    a dictionary keyed by validation_id. This provides a lightweight,
    dependency-free option for testing.
    """

    def __init__(self) -> None:
        """Initialize repository with empty in-memory storage."""
        self.logger = logger
        self.entity_name = "DocumentPolicyValidation"
        self.storage_dict: Dict[str, DocumentPolicyValidation] = {}

        logger.debug("Initializing MemoryDocumentPolicyValidationRepository")

    async def get(
        self, validation_id: str
    ) -> Optional[DocumentPolicyValidation]:
        """Retrieve a document policy validation by ID.

        Args:
            validation_id: Unique validation identifier

        Returns:
            DocumentPolicyValidation if found, None otherwise
        """
        return self.get_entity(validation_id)

    async def save(self, validation: DocumentPolicyValidation) -> None:
        """Save a document policy validation.

        Args:
            validation: Complete DocumentPolicyValidation to save
        """
        self.save_entity(validation, "validation_id")

    async def generate_id(self) -> str:
        """Generate a unique validation identifier.

        Returns:
            Unique validation ID string
        """
        return self.generate_entity_id("validation")

    async def get_many(
        self, validation_ids: List[str]
    ) -> Dict[str, Optional[DocumentPolicyValidation]]:
        """Retrieve multiple document policy validations by ID.

        Args:
            validation_ids: List of unique validation identifiers

        Returns:
            Dict mapping validation_id to DocumentPolicyValidation (or None if
            not found)
        """
        return self.get_many_entities(validation_ids)

    def _add_entity_specific_log_data(
        self, entity: DocumentPolicyValidation, log_data: Dict[str, Any]
    ) -> None:
        """Add validation-specific data to log entries."""
        super()._add_entity_specific_log_data(entity, log_data)
        log_data["input_document_id"] = entity.input_document_id
        log_data["policy_id"] = entity.policy_id
        log_data["validation_scores_count"] = len(entity.validation_scores)
        log_data["has_transformations"] = (
            entity.transformed_document_id is not None
            or entity.post_transform_validation_scores is not None
        )
        if entity.passed is not None:
            log_data["passed"] = entity.passed
        if entity.error_message:
            log_data["has_error"] = True

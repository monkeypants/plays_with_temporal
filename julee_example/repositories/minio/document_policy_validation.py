"""
Minio implementation of DocumentPolicyValidationRepository.

This module provides a Minio-based implementation of the
DocumentPolicyValidationRepository protocol that follows the Clean
Architecture patterns defined in the Fun-Police Framework. It handles
document policy validation storage as JSON objects in Minio, ensuring
idempotency and proper error handling.

The implementation stores document policy validations as JSON objects in
Minio, following the large payload handling pattern from the architectural
guidelines. Each validation is stored as a complete JSON document with its
status, scores, transformation results, and metadata.
"""

import logging
from typing import Optional, List, Dict

from julee_example.domain.models.policy import DocumentPolicyValidation
from julee_example.domain.repositories.document_policy_validation import (
    DocumentPolicyValidationRepository,
)
from .client import MinioClient, MinioRepositoryMixin


class MinioDocumentPolicyValidationRepository(
    DocumentPolicyValidationRepository, MinioRepositoryMixin
):
    """
    Minio implementation of DocumentPolicyValidationRepository using Minio for
    persistence.

    This implementation stores document policy validations as JSON objects in
    the "document-policy-validations" bucket. Each validation includes its
    complete status tracking, validation scores, transformation results, and
    metadata.
    """

    def __init__(self, client: MinioClient) -> None:
        """Initialize repository with Minio client.

        Args:
            client: MinioClient protocol implementation (real or fake)
        """
        self.client = client
        self.logger = logging.getLogger(
            "MinioDocumentPolicyValidationRepository"
        )
        self.validations_bucket = "document-policy-validations"
        self.ensure_buckets_exist(self.validations_bucket)

    async def get(
        self, validation_id: str
    ) -> Optional[DocumentPolicyValidation]:
        """Retrieve a document policy validation by ID."""
        return self.get_json_object(
            bucket_name=self.validations_bucket,
            object_name=validation_id,
            model_class=DocumentPolicyValidation,
            not_found_log_message="Document policy validation not found",
            error_log_message="Error retrieving document policy validation",
            extra_log_data={"validation_id": validation_id},
        )

    async def save(self, validation: DocumentPolicyValidation) -> None:
        """Save a document policy validation to Minio."""
        # Update timestamps
        self.update_timestamps(validation)

        self.put_json_object(
            bucket_name=self.validations_bucket,
            object_name=validation.validation_id,
            model=validation,
            success_log_message="Document policy validation saved "
            "successfully",
            error_log_message="Error saving document policy validation",
            extra_log_data={
                "validation_id": validation.validation_id,
                "input_document_id": validation.input_document_id,
                "policy_id": validation.policy_id,
                "status": validation.status.value,
                "validation_scores_count": len(validation.validation_scores),
                "has_transformations": (
                    validation.transformed_document_id is not None
                    or validation.post_transform_validation_scores is not None
                ),
                "passed": validation.passed,
            },
        )

    async def generate_id(self) -> str:
        """Generate a unique validation identifier."""
        return self.generate_id_with_prefix("validation")

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
        # Convert validation IDs to object names (direct mapping)
        object_names = validation_ids

        # Get objects from Minio using batch method
        object_results = self.get_many_json_objects(
            bucket_name=self.validations_bucket,
            object_names=object_names,
            model_class=DocumentPolicyValidation,
            not_found_log_message="Document policy validation not found",
            error_log_message="Error retrieving document policy validation",
            extra_log_data={"validation_ids": validation_ids},
        )

        # Convert object names back to validation IDs for the result
        result: Dict[str, Optional[DocumentPolicyValidation]] = {}
        for validation_id in validation_ids:
            result[validation_id] = object_results[validation_id]

        return result

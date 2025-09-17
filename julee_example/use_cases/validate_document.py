"""
Use case logic for document validation within the Capture, Extract, Assemble,
Publish workflow.

This module contains use case classes that orchestrate business logic while
remaining framework-agnostic. Dependencies are injected via repository
instances following the Clean Architecture principles.
"""

import logging
from datetime import datetime, timezone

from julee_example.domain import Document
from julee_example.domain.policy import (
    DocumentPolicyValidation,
    DocumentPolicyValidationStatus,
    Policy,
)
from julee_example.repositories import (
    DocumentRepository,
    KnowledgeServiceQueryRepository,
    KnowledgeServiceConfigRepository,
)
from julee_example.repositories import (
    PolicyRepository,
    DocumentPolicyValidationRepository,
)
from sample.validation import ensure_repository_protocol

logger = logging.getLogger(__name__)


class ValidateDocumentUseCase:
    """
    Use case for validating documents against policies.

    This class orchestrates the business logic for document validation within
    the Capture, Extract, Assemble, Publish workflow while remaining
    framework-agnostic. It depends only on repository protocols, not
    concrete implementations.

    In workflow contexts, this use case is called from workflow code with
    repository stubs that delegate to Temporal activities for durability.
    The use case remains completely unaware of whether it's running in a
    workflow context or a simple async context - it just calls repository
    methods and expects them to work correctly.

    Architectural Notes:
    - This class contains pure business logic with no framework dependencies
    - Repository dependencies are injected via constructor
      (dependency inversion)
    - All error handling and compensation logic is contained here
    - The use case works with domain objects exclusively
    - Deterministic execution is guaranteed by avoiding
      non-deterministic operations
    """

    def __init__(
        self,
        document_repo: DocumentRepository,
        knowledge_service_query_repo: KnowledgeServiceQueryRepository,
        knowledge_service_config_repo: KnowledgeServiceConfigRepository,
        policy_repo: PolicyRepository,
        document_policy_validation_repo: DocumentPolicyValidationRepository,
    ) -> None:
        """Initialize validate document use case.

        Args:
            document_repo: Repository for document operations
            knowledge_service_query_repo: Repository for knowledge service
                query operations
            knowledge_service_config_repo: Repository for knowledge service
                configuration operations
            policy_repo: Repository for policy operations
            document_policy_validation_repo: Repository for document policy
                validation operations

        Note:
            The repositories passed here may be concrete implementations
            (for testing or direct execution) or workflow stubs (for
            Temporal workflow execution). The use case doesn't know or care
            which - it just calls the methods defined in the protocols.

            Repositories are validated at construction time to catch
            configuration errors early in the application lifecycle.
        """
        # Validate at construction time for early error detection
        self.document_repo = ensure_repository_protocol(
            document_repo, DocumentRepository  # type: ignore[type-abstract]
        )
        self.knowledge_service_query_repo = ensure_repository_protocol(
            knowledge_service_query_repo, KnowledgeServiceQueryRepository  # type: ignore[type-abstract]
        )
        self.knowledge_service_config_repo = ensure_repository_protocol(
            knowledge_service_config_repo, KnowledgeServiceConfigRepository  # type: ignore[type-abstract]
        )
        self.policy_repo = ensure_repository_protocol(
            policy_repo, PolicyRepository  # type: ignore[type-abstract]
        )
        self.document_policy_validation_repo = ensure_repository_protocol(
            document_policy_validation_repo,
            DocumentPolicyValidationRepository,  # type: ignore[type-abstract]
        )

    async def validate_document(
        self, document_id: str, policy_id: str
    ) -> DocumentPolicyValidation:
        """
        Validate a document against a policy and return the validation result.

        This method orchestrates the core validation workflow:
        1. Generates a unique validation ID
        2. Retrieves the document and policy
        3. Creates and stores the initial validation record
        4. Performs the validation process (to be implemented)
        5. Updates and returns the completed validation

        Args:
            document_id: ID of the document to validate
            policy_id: ID of the policy to validate against

        Returns:
            DocumentPolicyValidation with validation results

        Raises:
            ValueError: If required entities are not found or invalid
            RuntimeError: If validation processing fails
        """
        logger.debug(
            "Starting document validation use case",
            extra={
                "document_id": document_id,
                "policy_id": policy_id,
            },
        )

        # Step 1: Generate unique validation ID
        validation_id = (
            await self.document_policy_validation_repo.generate_id()
        )

        # Step 2: Retrieve document and policy (validate they exist)
        await self._retrieve_document(document_id)
        await self._retrieve_policy(policy_id)

        # Step 3: Create and store initial validation record
        validation = DocumentPolicyValidation(
            validation_id=validation_id,
            input_document_id=document_id,
            policy_id=policy_id,
            status=DocumentPolicyValidationStatus.PENDING,
            validation_scores=[],
            started_at=datetime.now(timezone.utc),
        )

        await self.document_policy_validation_repo.save(validation)

        logger.debug(
            "Initial validation record created",
            extra={
                "validation_id": validation_id,
                "document_id": document_id,
                "policy_id": policy_id,
                "status": validation.status.value,
            },
        )

        # TODO: Implement actual validation logic here
        # This is where we would:
        # 1. Execute validation queries against the document
        # 2. Calculate validation scores
        # 3. Determine if transformations are needed
        # 4. Apply transformations if required
        # 5. Re-validate after transformations
        # 6. Determine final pass/fail result

        logger.info(
            "Document validation completed (stubbed)",
            extra={
                "validation_id": validation_id,
                "document_id": document_id,
                "policy_id": policy_id,
            },
        )

        return validation

    async def _retrieve_document(self, document_id: str) -> Document:
        """Retrieve document with error handling."""
        document = await self.document_repo.get(document_id)
        if not document:
            raise ValueError(f"Document not found: {document_id}")
        return document

    async def _retrieve_policy(self, policy_id: str) -> Policy:
        """Retrieve policy with error handling."""
        policy = await self.policy_repo.get(policy_id)
        if not policy:
            raise ValueError(f"Policy not found: {policy_id}")
        return policy

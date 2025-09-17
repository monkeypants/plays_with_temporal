"""
Use case logic for document validation within the Capture, Extract, Assemble,
Publish workflow.

This module contains use case classes that orchestrate business logic while
remaining framework-agnostic. Dependencies are injected via repository
instances following the Clean Architecture principles.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Tuple

from julee_example.domain import Document, KnowledgeServiceQuery
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
from julee_example.services import knowledge_service_factory, KnowledgeService
from sample.validation import ensure_repository_protocol
from .decorators import try_use_case_step

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
        4. Retrieves all validation queries needed for the policy
        5. Retrieves all knowledge services needed for validation
        6. Registers the document with knowledge services
        7. Executes validation queries and calculates scores
        8. Determines pass/fail and updates validation record

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
        document = await self._retrieve_document(document_id)
        policy = await self._retrieve_policy(policy_id)

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

        try:
            # Step 4: Update status to in progress
            validation.status = DocumentPolicyValidationStatus.IN_PROGRESS
            await self.document_policy_validation_repo.save(validation)

            # Step 5: Retrieve all validation queries needed for this policy
            queries = await self._retrieve_validation_queries(policy)

            # Step 6: Retrieve all knowledge services needed for validation
            knowledge_services = await self._retrieve_all_knowledge_services(
                queries
            )

            # Step 7: Register the document with knowledge services
            document_registrations = (
                await self._register_document_with_services(
                    document, queries, knowledge_services
                )
            )

            # Step 8: Execute validation queries and calculate scores
            validation_scores = await self._execute_validation_queries(
                document,
                policy,
                document_registrations,
                queries,
                knowledge_services,
            )

            # Step 9: Update validation with scores and determine pass/fail
            passed = self._determine_validation_result(
                validation_scores, policy.validation_scores
            )

            final_status = (
                DocumentPolicyValidationStatus.PASSED
                if passed
                else DocumentPolicyValidationStatus.FAILED
            )

            # Create new validation instance with updated scores
            validation = DocumentPolicyValidation(
                validation_id=validation.validation_id,
                input_document_id=validation.input_document_id,
                policy_id=validation.policy_id,
                validation_scores=validation_scores,  # Triggers validation
                transformed_document_id=validation.transformed_document_id,
                post_transform_validation_scores=validation.post_transform_validation_scores,
                started_at=validation.started_at,
                completed_at=datetime.now(timezone.utc),
                error_message=validation.error_message,
                status=final_status,
                passed=passed,
            )

            await self.document_policy_validation_repo.save(validation)

            logger.info(
                "Document validation completed",
                extra={
                    "validation_id": validation_id,
                    "document_id": document_id,
                    "policy_id": policy_id,
                    "passed": passed,
                    "validation_scores": validation_scores,
                },
            )

            return validation

        except Exception as e:
            # Mark validation as failed due to error
            validation.status = DocumentPolicyValidationStatus.ERROR
            validation.error_message = str(e)
            validation.passed = False
            validation.completed_at = datetime.now(timezone.utc)
            await self.document_policy_validation_repo.save(validation)

            logger.error(
                "Document validation failed",
                extra={
                    "validation_id": validation_id,
                    "document_id": document_id,
                    "policy_id": policy_id,
                    "error": str(e),
                },
                exc_info=True,
            )
            raise

    @try_use_case_step("document_retrieval")
    async def _retrieve_document(self, document_id: str) -> Document:
        """Retrieve document with error handling."""
        document = await self.document_repo.get(document_id)
        if not document:
            raise ValueError(f"Document not found: {document_id}")
        return document

    @try_use_case_step("policy_retrieval")
    async def _retrieve_policy(self, policy_id: str) -> Policy:
        """Retrieve policy with error handling."""
        policy = await self.policy_repo.get(policy_id)
        if not policy:
            raise ValueError(f"Policy not found: {policy_id}")
        return policy

    @try_use_case_step("validation_queries_retrieval")
    async def _retrieve_validation_queries(
        self, policy: Policy
    ) -> Dict[str, KnowledgeServiceQuery]:
        """Retrieve all knowledge service queries needed for validation."""
        queries = {}
        for query_id, required_score in policy.validation_scores:
            query = await self.knowledge_service_query_repo.get(query_id)
            if not query:
                raise ValueError(
                    f"Knowledge service query not found: {query_id}"
                )
            queries[query_id] = query
        return queries

    @try_use_case_step("knowledge_services_retrieval")
    async def _retrieve_all_knowledge_services(
        self, queries: Dict[str, KnowledgeServiceQuery]
    ) -> Dict[str, KnowledgeService]:
        """Retrieve all unique knowledge services needed for validation."""
        knowledge_services = {}
        unique_service_ids = {
            query.knowledge_service_id for query in queries.values()
        }

        for service_id in unique_service_ids:
            knowledge_service = await self._get_knowledge_service(service_id)
            knowledge_services[service_id] = knowledge_service

        return knowledge_services

    @try_use_case_step("document_registration")
    async def _register_document_with_services(
        self,
        document: Document,
        queries: Dict[str, KnowledgeServiceQuery],
        knowledge_services: Dict[str, KnowledgeService],
    ) -> Dict[str, str]:
        """
        Register the document with all knowledge services needed for
        validation.

        Args:
            document: The document to register
            queries: Dict of query_id to KnowledgeServiceQuery objects
            knowledge_services: Dict of service_id to KnowledgeService
                instances

        Returns:
            Dict mapping knowledge_service_id to service_file_id
        """
        registrations = {}
        required_service_ids = {
            query.knowledge_service_id for query in queries.values()
        }

        for knowledge_service_id in required_service_ids:
            knowledge_service = knowledge_services[knowledge_service_id]
            registration_result = await knowledge_service.register_file(
                document
            )
            registrations[knowledge_service_id] = (
                registration_result.knowledge_service_file_id
            )

        return registrations

    @try_use_case_step("validation_execution")
    async def _execute_validation_queries(
        self,
        document: Document,
        policy: Policy,
        document_registrations: Dict[str, str],
        queries: Dict[str, KnowledgeServiceQuery],
        knowledge_services: Dict[str, KnowledgeService],
    ) -> List[Tuple[str, int]]:
        """
        Execute all validation queries and return the actual scores achieved.

        Args:
            document: The document being validated
            policy: The policy being applied
            document_registrations: Mapping of service_id to service_file_id
            queries: Dict of query_id to KnowledgeServiceQuery objects
            knowledge_services: Dict of service_id to KnowledgeService
                instances

        Returns:
            List of (query_id, actual_score) tuples
        """
        validation_scores = []

        # Execute each validation query defined in the policy
        for query_id, required_score in policy.validation_scores:
            # Get the query configuration
            query = queries[query_id]

            # Get the knowledge service
            knowledge_service = knowledge_services[query.knowledge_service_id]

            # Get the service file ID from our registrations
            service_file_id = document_registrations.get(
                query.knowledge_service_id
            )
            if not service_file_id:
                raise ValueError(
                    f"Document not registered with service "
                    f"{query.knowledge_service_id}"
                )

            # Execute the validation query
            query_result = await knowledge_service.execute_query(
                query_text=query.prompt,
                service_file_ids=[service_file_id],
                query_metadata=query.query_metadata,
                assistant_prompt=query.assistant_prompt,
            )

            # Extract the score from the query result
            actual_score = self._extract_score_from_result(
                query_result.result_data
            )
            validation_scores.append((query_id, actual_score))

            logger.debug(
                "Validation query executed",
                extra={
                    "query_id": query_id,
                    "required_score": required_score,
                    "actual_score": actual_score,
                    "passed": actual_score >= required_score,
                },
            )

        return validation_scores

    @try_use_case_step("knowledge_service_creation")
    async def _get_knowledge_service(
        self, knowledge_service_id: str
    ) -> KnowledgeService:
        """Get knowledge service instance with error handling."""
        config = await self.knowledge_service_config_repo.get(
            knowledge_service_id
        )
        if not config:
            raise ValueError(
                f"Knowledge service config not found: {knowledge_service_id}"
            )
        return knowledge_service_factory(config)

    def _extract_score_from_result(self, result_data: Dict) -> int:
        """
        Extract a numeric score from the knowledge service query result.

        Similar to _parse_query_result, but expects a numeric response.
        Returns the actual score without range validation to preserve data
        integrity.
        """
        response_text = result_data.get("response", "")
        if not response_text:
            raise ValueError("Empty response from knowledge service")

        # Try to parse response as integer directly
        try:
            score = int(response_text.strip())
            return score
        except ValueError as e:
            raise ValueError(
                f"Failed to parse numeric score from response: "
                f"{response_text}"
            ) from e

    def _determine_validation_result(
        self,
        actual_scores: List[Tuple[str, int]],
        required_scores: List[Tuple[str, int]],
    ) -> bool:
        """
        Determine if validation passed based on actual vs required scores.

        Args:
            actual_scores: List of (query_id, actual_score) tuples
            required_scores: List of (query_id, required_score) tuples from
                policy

        Returns:
            True if all required scores were met or exceeded, False otherwise
        """
        # Convert to dictionaries for easier lookup
        actual_scores_dict = dict(actual_scores)
        required_scores_dict = dict(required_scores)

        # Check if all required scores were met
        for query_id, required_score in required_scores_dict.items():
            actual_score = actual_scores_dict.get(query_id, 0)
            if actual_score < required_score:
                logger.debug(
                    "Validation failed for query",
                    extra={
                        "query_id": query_id,
                        "required_score": required_score,
                        "actual_score": actual_score,
                    },
                )
                return False

        return True

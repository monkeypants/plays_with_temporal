"""
Use case logic for document validation within the Capture, Extract, Assemble,
Publish workflow.

This module contains use case classes that orchestrate business logic while
remaining framework-agnostic. Dependencies are injected via repository
instances following the Clean Architecture principles.
"""

import hashlib
import io
import json
import logging
import multihash
from datetime import datetime
from typing import Callable, Dict, List, Tuple

from julee_example.domain.models import (
    Document,
    DocumentStatus,
    ContentStream,
    KnowledgeServiceQuery,
    DocumentPolicyValidation,
    Policy,
)
from julee_example.domain.models.policy import (
    DocumentPolicyValidationStatus,
)
from julee_example.domain.repositories import (
    DocumentRepository,
    DocumentPolicyValidationRepository,
    KnowledgeServiceConfigRepository,
    KnowledgeServiceQueryRepository,
    PolicyRepository,
)
from julee_example.services import KnowledgeService
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
        knowledge_service: KnowledgeService,
        now_fn: Callable[[], datetime],
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
            knowledge_service: Knowledge service instance for external
                operations
            now_fn: Function to get current time (e.g., workflow.now for
                Temporal workflows)

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
            document_repo,
            DocumentRepository,  # type: ignore[type-abstract]
        )
        self.knowledge_service = knowledge_service
        self.knowledge_service_query_repo = ensure_repository_protocol(
            knowledge_service_query_repo,
            KnowledgeServiceQueryRepository,  # type: ignore[type-abstract]
        )
        self.knowledge_service_config_repo = ensure_repository_protocol(
            knowledge_service_config_repo,
            KnowledgeServiceConfigRepository,  # type: ignore[type-abstract]
        )
        self.policy_repo = ensure_repository_protocol(
            policy_repo,
            PolicyRepository,  # type: ignore[type-abstract]
        )
        self.document_policy_validation_repo = ensure_repository_protocol(
            document_policy_validation_repo,
            DocumentPolicyValidationRepository,  # type: ignore[type-abstract]
        )
        self.now_fn = now_fn

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
            started_at=self.now_fn(),
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

            # Step 5: Retrieve all queries needed for this policy
            all_queries = await self._retrieve_all_queries(policy)

            # Step 6: Register the document with knowledge services
            document_registrations = (
                await self._register_document_with_services(
                    document, all_queries
                )
            )

            # Step 7: Execute validation queries and calculate scores
            validation_scores = await self._execute_validation_queries(
                document,
                policy,
                document_registrations,
                all_queries,
            )

            # Step 9: Update validation with scores
            validation.validation_scores = validation_scores
            validation.status = (
                DocumentPolicyValidationStatus.VALIDATION_COMPLETE
            )
            await self.document_policy_validation_repo.save(validation)

            # Step 10: Check if transformations are needed
            initial_passed = self._determine_validation_result(
                validation_scores, policy.validation_scores
            )

            if initial_passed or not policy.has_transformations:
                # No transformations needed - either passed or no
                # transformations available
                final_status = (
                    DocumentPolicyValidationStatus.PASSED
                    if initial_passed
                    else DocumentPolicyValidationStatus.FAILED
                )

                validation = DocumentPolicyValidation(
                    validation_id=validation.validation_id,
                    input_document_id=validation.input_document_id,
                    policy_id=validation.policy_id,
                    validation_scores=validation_scores,
                    transformed_document_id=validation.transformed_document_id,
                    post_transform_validation_scores=validation.post_transform_validation_scores,
                    started_at=validation.started_at,
                    completed_at=self.now_fn(),
                    error_message=validation.error_message,
                    status=final_status,
                    passed=initial_passed,
                )

                await self.document_policy_validation_repo.save(validation)

                logger.info(
                    "Document validation completed without transformations",
                    extra={
                        "validation_id": validation_id,
                        "document_id": document_id,
                        "policy_id": policy_id,
                        "passed": initial_passed,
                        "validation_scores": validation_scores,
                    },
                )

                return validation

            # Step 11: Initial validation failed and transformations are
            # available
            validation.status = (
                DocumentPolicyValidationStatus.TRANSFORMATION_REQUIRED
            )
            await self.document_policy_validation_repo.save(validation)

            logger.info(
                "Initial validation failed, applying transformations",
                extra={
                    "validation_id": validation_id,
                    "document_id": document_id,
                    "policy_id": policy_id,
                    "initial_scores": validation_scores,
                },
            )

            # Step 12: Apply transformations
            validation.status = (
                DocumentPolicyValidationStatus.TRANSFORMATION_IN_PROGRESS
            )
            await self.document_policy_validation_repo.save(validation)

            transformed_document = await self._apply_transformations(
                document,
                policy,
                all_queries,
                document_registrations,
            )

            validation.transformed_document_id = (
                transformed_document.document_id
            )
            validation.status = (
                DocumentPolicyValidationStatus.TRANSFORMATION_COMPLETE
            )
            await self.document_policy_validation_repo.save(validation)

            # Step 13: Register transformed document with knowledge services
            transformed_document_registrations = (
                await self._register_document_with_services(
                    transformed_document, all_queries
                )
            )

            # Step 14: Re-run validation queries on transformed document
            validation.status = DocumentPolicyValidationStatus.IN_PROGRESS
            await self.document_policy_validation_repo.save(validation)

            post_transform_validation_scores = (
                await self._execute_validation_queries(
                    transformed_document,
                    policy,
                    transformed_document_registrations,
                    all_queries,
                )
            )

            # Step 15: Determine final result based on post-transformation
            # scores
            final_passed = self._determine_validation_result(
                post_transform_validation_scores, policy.validation_scores
            )

            final_status = (
                DocumentPolicyValidationStatus.PASSED
                if final_passed
                else DocumentPolicyValidationStatus.FAILED
            )

            validation = DocumentPolicyValidation(
                validation_id=validation.validation_id,
                input_document_id=validation.input_document_id,
                policy_id=validation.policy_id,
                validation_scores=validation_scores,
                transformed_document_id=transformed_document.document_id,
                post_transform_validation_scores=post_transform_validation_scores,
                started_at=validation.started_at,
                completed_at=self.now_fn(),
                error_message=validation.error_message,
                status=final_status,
                passed=final_passed,
            )

            await self.document_policy_validation_repo.save(validation)

            logger.info(
                "Document validation completed with transformations",
                extra={
                    "validation_id": validation_id,
                    "document_id": document_id,
                    "policy_id": policy_id,
                    "passed": final_passed,
                    "initial_scores": validation_scores,
                    "final_scores": post_transform_validation_scores,
                    "transformed_document_id": (
                        transformed_document.document_id
                    ),
                },
            )

            return validation

        except Exception as e:
            # Mark validation as failed due to error
            validation.status = DocumentPolicyValidationStatus.ERROR
            validation.error_message = str(e)
            validation.passed = False
            validation.completed_at = self.now_fn()
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

    @try_use_case_step("all_queries_retrieval")
    async def _retrieve_all_queries(
        self, policy: Policy
    ) -> Dict[str, KnowledgeServiceQuery]:
        """Retrieve all knowledge service queries needed for validation and
        transformation."""
        all_queries = {}

        # Get validation queries
        for query_id, required_score in policy.validation_scores:
            query = await self.knowledge_service_query_repo.get(query_id)
            if not query:
                raise ValueError(f"Validation query not found: {query_id}")
            all_queries[query_id] = query

        # Get transformation queries
        if policy.transformation_queries:
            for query_id in policy.transformation_queries:
                query = await self.knowledge_service_query_repo.get(query_id)
                if not query:
                    raise ValueError(
                        f"Transformation query not found: {query_id}"
                    )
                all_queries[query_id] = query

        return all_queries

    @try_use_case_step("document_registration")
    async def _register_document_with_services(
        self,
        document: Document,
        queries: Dict[str, KnowledgeServiceQuery],
    ) -> Dict[str, str]:
        """
        Register the document with all knowledge services needed for
        validation.

        Args:
            document: The document to register
            queries: Dict of query_id to KnowledgeServiceQuery objects

        Returns:
            Dict mapping knowledge_service_id to service_file_id
        """
        registrations = {}
        required_service_ids = {
            query.knowledge_service_id for query in queries.values()
        }

        for knowledge_service_id in required_service_ids:
            # Get the config for this service
            config = await self.knowledge_service_config_repo.get(
                knowledge_service_id
            )
            if not config:
                raise ValueError(
                    f"Knowledge service config not found: "
                    f"{knowledge_service_id}"
                )

            registration_result = await self.knowledge_service.register_file(
                config, document
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
    ) -> List[Tuple[str, int]]:
        """
        Execute all validation queries and return the actual scores achieved.

        Args:
            document: The document being validated
            policy: The policy being applied
            document_registrations: Mapping of service_id to service_file_id
            queries: Dict of query_id to KnowledgeServiceQuery objects

        Returns:
            List of (query_id, actual_score) tuples
        """
        validation_scores = []

        # Execute each validation query defined in the policy
        for query_id, required_score in policy.validation_scores:
            # Get the query configuration
            query = queries[query_id]

            # Get the config for this service
            config = await self.knowledge_service_config_repo.get(
                query.knowledge_service_id
            )
            if not config:
                raise ValueError(
                    f"Knowledge service config not found: "
                    f"{query.knowledge_service_id}"
                )

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
            query_result = await self.knowledge_service.execute_query(
                config,
                query.prompt,
                [service_file_id],
                query.query_metadata,
                query.assistant_prompt,
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

    @try_use_case_step("document_transformation")
    async def _apply_transformations(
        self,
        document: Document,
        policy: Policy,
        all_queries: Dict[str, KnowledgeServiceQuery],
        document_registrations: Dict[str, str],
    ) -> Document:
        """
        Apply transformation queries to a document and return the
        transformed document.

        Args:
            document: The original document to transform
            policy: The policy containing transformation query IDs
            all_queries: Dict of all queries (validation and transformation)
            document_registrations: Mapping of service_id to service_file_id

        Returns:
            New Document object with transformed content

        Raises:
            ValueError: If transformation queries are not found or fail
            RuntimeError: If document transformation fails
        """
        if not policy.transformation_queries:
            raise ValueError("No transformation queries provided")

        logger.debug(
            "Applying transformations to document",
            extra={
                "document_id": document.document_id,
                "transformation_query_ids": policy.transformation_queries,
            },
        )

        # Apply transformations sequentially
        current_content = document.content
        if current_content is None:
            raise ValueError(
                "Document content stream is required for transformation"
            )
        current_content.seek(0)
        transformed_content = current_content.read().decode("utf-8")
        current_content.seek(0)

        for query_id in policy.transformation_queries:
            query = all_queries[query_id]

            # Get the config for this service
            config = await self.knowledge_service_config_repo.get(
                query.knowledge_service_id
            )
            if not config:
                raise ValueError(
                    f"Knowledge service config not found: "
                    f"{query.knowledge_service_id}"
                )

            # Get the service file ID from our registrations
            service_file_id = document_registrations.get(
                query.knowledge_service_id
            )
            if not service_file_id:
                raise ValueError(
                    f"Document not registered with service "
                    f"{query.knowledge_service_id}"
                )

            # Execute the transformation query
            transformation_result = (
                await self.knowledge_service.execute_query(
                    config,
                    query.prompt,
                    [service_file_id],
                    query.query_metadata,
                    query.assistant_prompt,
                )
            )

            # Extract transformed content from result
            transformed_content = self._extract_transformed_content(
                transformation_result.result_data
            )

            logger.debug(
                "Transformation query applied",
                extra={
                    "query_id": query_id,
                    "original_length": document.size_bytes,
                    "transformed_length": len(transformed_content),
                },
            )

        # Create new document with transformed content
        transformed_document_id = await self.document_repo.generate_id()

        # Create content stream from transformed text
        transformed_bytes = transformed_content.encode("utf-8")
        transformed_stream = io.BytesIO(transformed_bytes)

        # Calculate multihash for transformed content
        sha256_hasher = hashlib.sha256()
        sha256_hasher.update(transformed_bytes)
        sha256_hash = sha256_hasher.digest()
        mhash = multihash.encode(sha256_hash, multihash.SHA2_256)
        proper_multihash = str(mhash.hex())

        transformed_document = Document(
            document_id=transformed_document_id,
            original_filename=f"transformed_{document.original_filename}",
            content_type=document.content_type,
            size_bytes=len(transformed_bytes),
            content_multihash=proper_multihash,
            status=DocumentStatus.CAPTURED,
            content=ContentStream(transformed_stream),
            created_at=self.now_fn(),
            updated_at=self.now_fn(),
        )

        # Save the transformed document
        await self.document_repo.save(transformed_document)

        logger.info(
            "Document transformation completed",
            extra={
                "original_document_id": document.document_id,
                "transformed_document_id": transformed_document.document_id,
                "original_size": document.size_bytes,
                "transformed_size": transformed_document.size_bytes,
            },
        )

        return transformed_document

    def _extract_transformed_content(self, result_data: Dict) -> str:
        """
        Extract transformed document content from knowledge service result.

        Args:
            result_data: Result data from knowledge service transformation
                query

        Returns:
            Transformed document content as valid JSON string

        Raises:
            ValueError: If no valid JSON content can be extracted from result
        """
        response_text = result_data.get("response", "")
        if not response_text:
            raise ValueError("Empty response from transformation query")

        # The response must be valid JSON
        stripped_response: str = response_text.strip()
        try:
            # Parse to validate JSON structure
            json.loads(stripped_response)
            # Return the original response text (preserving formatting)
            return stripped_response
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Transformation result must be valid JSON, got: "
                f"{response_text[:100]}... Parse error: {e}"
            )

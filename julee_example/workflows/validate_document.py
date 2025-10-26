"""
Temporal workflow for document validation operations.

This workflow orchestrates the ValidateDocumentUseCase with Temporal's
durability guarantees, providing retry logic, state management, and
compensation for the document validation process.
"""

import logging
from temporalio import workflow
from temporalio.common import RetryPolicy
from datetime import timedelta

from julee_example.domain.models.policy import DocumentPolicyValidation
from julee_example.domain.use_cases import ValidateDocumentUseCase
from julee_example.repositories.temporal.proxies import (
    WorkflowDocumentRepositoryProxy,
    WorkflowKnowledgeServiceConfigRepositoryProxy,
    WorkflowKnowledgeServiceQueryRepositoryProxy,
)
from julee_example.services.temporal.proxies import (
    WorkflowKnowledgeServiceProxy,
)

logger = logging.getLogger(__name__)


@workflow.defn
class ValidateDocumentWorkflow:
    """
    Temporal workflow for document validation operations.

    This workflow:
    1. Receives document_id and policy_id
    2. Orchestrates the ValidateDocumentUseCase with workflow-safe proxies
    3. Provides durability and retry logic for validation processing
    4. Returns the completed DocumentPolicyValidation object

    The workflow remains framework-agnostic by delegating all business logic
    to the use case, while providing Temporal-specific orchestration concerns
    like retry policies, timeouts, and state management.
    """

    def __init__(self) -> None:
        self.current_step = "initialized"
        self.validation_id: str | None = None

    @workflow.query
    def get_current_step(self) -> str:
        """Query method to get the current workflow step"""
        return self.current_step

    @workflow.query
    def get_validation_id(self) -> str | None:
        """Query method to get the validation ID once created"""
        return self.validation_id

    @workflow.run
    async def run(
        self, document_id: str, policy_id: str
    ) -> DocumentPolicyValidation:
        """
        Execute the document validation workflow.

        Args:
            document_id: ID of the document to validate
            policy_id: ID of the policy to validate against

        Returns:
            Completed DocumentPolicyValidation object with validation results

        Raises:
            ValueError: If required entities are not found
            RuntimeError: If validation processing fails after retries
        """
        workflow.logger.info(
            "Starting document validation workflow",
            extra={
                "document_id": document_id,
                "policy_id": policy_id,
                "workflow_id": workflow.info().workflow_id,
                "run_id": workflow.info().run_id,
            },
        )

        self.current_step = "initializing_repositories"

        try:
            # Create workflow-safe repository proxies
            # These proxy all calls through Temporal activities for durability
            document_repo = WorkflowDocumentRepositoryProxy()  # type: ignore[abstract]
            knowledge_service_query_repo = (
                WorkflowKnowledgeServiceQueryRepositoryProxy()  # type: ignore[abstract]
            )
            knowledge_service_config_repo = (
                WorkflowKnowledgeServiceConfigRepositoryProxy()  # type: ignore[abstract]
            )

            workflow.logger.debug(
                "Repository proxies created",
                extra={
                    "document_id": document_id,
                    "policy_id": policy_id,
                },
            )

            self.current_step = "creating_use_case"

            # Create workflow-safe knowledge service proxy
            knowledge_service = WorkflowKnowledgeServiceProxy()  # type: ignore[abstract]

            # Import policy repository proxy (assuming it exists)
            try:
                from julee_example.repositories.temporal.proxies import (
                    WorkflowPolicyRepositoryProxy,
                    WorkflowDocumentPolicyValidationRepositoryProxy,
                )

                policy_repo = WorkflowPolicyRepositoryProxy()  # type: ignore[abstract]
                document_policy_validation_repo = (
                    WorkflowDocumentPolicyValidationRepositoryProxy()  # type: ignore[abstract]
                )
            except ImportError:
                # Fallback if proxies don't exist yet
                workflow.logger.warning(
                    "Policy repository proxies not found, workflow may fail"
                )
                raise ValueError(
                    "Policy repository proxies required for validation "
                    "workflow"
                )

            # Create the use case with workflow-safe repositories
            # The use case remains completely unaware it's running in workflow
            use_case = ValidateDocumentUseCase(
                document_repo=document_repo,
                knowledge_service_query_repo=knowledge_service_query_repo,
                knowledge_service_config_repo=knowledge_service_config_repo,
                policy_repo=policy_repo,
                document_policy_validation_repo=document_policy_validation_repo,
                knowledge_service=knowledge_service,
                now_fn=workflow.now,
            )

            workflow.logger.debug(
                "Use case created successfully",
                extra={
                    "document_id": document_id,
                    "policy_id": policy_id,
                },
            )

            self.current_step = "executing_validation"

            # Execute the validation process with workflow durability
            # All repository calls inside the use case will be executed as
            # Temporal activities with automatic retry and state persistence
            validation = await use_case.validate_document(
                document_id=document_id,
                policy_id=policy_id,
            )

            # Store the validation ID for queries
            self.validation_id = validation.validation_id

            self.current_step = "completed"

            workflow.logger.info(
                "Document validation workflow completed successfully",
                extra={
                    "document_id": document_id,
                    "policy_id": policy_id,
                    "validation_id": validation.validation_id,
                    "status": validation.status.value,
                    "passed": validation.passed,
                },
            )

            return validation

        except Exception as e:
            self.current_step = "failed"

            workflow.logger.error(
                "Document validation workflow failed",
                extra={
                    "document_id": document_id,
                    "policy_id": policy_id,
                    "validation_id": self.validation_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                exc_info=True,
            )

            # Re-raise to let Temporal handle retry logic
            raise

    @workflow.signal
    async def cancel_validation(self, reason: str) -> None:
        """
        Signal handler to cancel the validation process.

        Args:
            reason: Reason for cancellation

        Note:
            This is a placeholder for future cancellation logic.
            Currently, we rely on Temporal's built-in workflow cancellation.
        """
        workflow.logger.info(
            "Validation cancellation requested",
            extra={
                "validation_id": self.validation_id,
                "reason": reason,
                "current_step": self.current_step,
            },
        )

        # Future: Implement graceful cancellation logic here
        # For now, let the workflow be cancelled naturally by Temporal


# Workflow configuration with retry policies optimized for document validation
VALIDATE_DOCUMENT_RETRY_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=1),
    backoff_coefficient=2.0,
    maximum_interval=timedelta(minutes=5),
    maximum_attempts=3,
    non_retryable_error_types=["ValueError"],  # Don't retry validation errors
)

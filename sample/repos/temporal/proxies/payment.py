"""
Workflow-specific proxy for PaymentRepository.
This class is used *inside* Temporal workflows to call activities.
It ensures workflow determinism by delegating all non-deterministic
operations to activities.
"""

from util.repos.temporal.decorators import temporal_workflow_proxy
from sample.repositories import PaymentRepository


@temporal_workflow_proxy(
    "sample.payment_repo.minio",
    default_timeout_seconds=10,
    retry_methods=["process_payment", "refund_payment"],
)
class WorkflowPaymentRepositoryProxy(PaymentRepository):
    """
    Workflow implementation of PaymentRepository that calls activities.
    This proxy ensures that all interactions with the PaymentRepository are
    performed via Temporal activities, maintaining workflow determinism.
    """

    pass

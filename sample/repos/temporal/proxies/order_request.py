"""
Workflow-specific proxy for OrderRequestRepository.
This class is used *inside* Temporal workflows to call activities.
It ensures workflow determinism by delegating all non-deterministic
operations to activities.
"""

from util.repos.temporal.decorators import temporal_workflow_proxy
from sample.repositories import OrderRequestRepository


@temporal_workflow_proxy(
    "sample.order_request_repo.minio", default_timeout_seconds=10
)
class WorkflowOrderRequestRepositoryProxy(OrderRequestRepository):
    """
    Workflow implementation of OrderRequestRepository that calls activities.
    This proxy ensures that all interactions with the
    OrderRequestRepository are performed via Temporal activities,
    maintaining workflow determinism.
    """

    pass

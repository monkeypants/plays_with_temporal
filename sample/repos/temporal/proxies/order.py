"""
Workflow-specific proxy for OrderRepository.
This class is used *inside* Temporal workflows to call activities.
It ensures workflow determinism by delegating all non-deterministic
operations to activities.
"""

from util.repos.temporal.decorators import temporal_workflow_proxy
from sample.repositories import OrderRepository


@temporal_workflow_proxy(
    "sample.order_repo.minio", default_timeout_seconds=10
)
class WorkflowOrderRepositoryProxy(OrderRepository):
    """
    Workflow implementation of OrderRepository that calls activities.
    This proxy ensures that all interactions with the OrderRepository are
    performed via Temporal activities, maintaining workflow determinism.
    """

    pass

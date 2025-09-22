"""
Workflow-specific proxy for InventoryRepository.
This class is used *inside* Temporal workflows to call activities.
It ensures workflow determinism by delegating all non-deterministic
operations to activities.
"""

from util.repos.temporal.decorators import temporal_workflow_proxy
from sample.repositories import InventoryRepository


@temporal_workflow_proxy(
    "sample.inventory_repo.minio",
    default_timeout_seconds=10,
    retry_methods=["reserve_items"],
)
class WorkflowInventoryRepositoryProxy(InventoryRepository):
    """
    Workflow implementation of InventoryRepository that calls activities.
    This proxy ensures that all interactions with the InventoryRepository are
    performed via Temporal activities, maintaining workflow determinism.
    """

    pass

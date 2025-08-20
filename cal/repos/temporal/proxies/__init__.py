"""Workflow-safe proxies for calendar repositories."""

from .schedule import WorkflowScheduleRepositoryProxy
from .postgresql_schedule import WorkflowPostgreSQLScheduleRepositoryProxy

__all__ = [
    "WorkflowScheduleRepositoryProxy",
    "WorkflowPostgreSQLScheduleRepositoryProxy",
]

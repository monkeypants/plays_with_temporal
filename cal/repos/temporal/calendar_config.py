"""
Temporal Activity implementation of CalendarConfigurationRepository.
Delegates calls to a concrete LocalCalendarConfigurationRepository instance.
"""

import logging
from typing import List, Optional

from temporalio import activity

from cal.domain import CalendarCollection
from cal.repositories import CalendarConfigurationRepository
from cal.repos.local.calendar_config import (
    LocalCalendarConfigurationRepository,
)

logger = logging.getLogger(__name__)


class TemporalLocalCalendarConfigurationRepository(
    CalendarConfigurationRepository
):
    """
    Temporal Activity implementation of CalendarConfigurationRepository.
    Delegates calls to a concrete LocalCalendarConfigurationRepository
    instance.

    This follows the three-layer repository pattern:
    1. Pure Backend (LocalCalendarConfigurationRepository)
    2. Temporal Activity (TemporalLocalCalendarConfigurationRepository)
       - this class
    3. Workflow Proxy (WorkflowCalendarConfigurationRepositoryProxy)
    """

    def __init__(self, repository: LocalCalendarConfigurationRepository):
        """
        Initialize with a concrete LocalCalendarConfigurationRepository
        implementation.

        Args:
            repository: The concrete repository to delegate calls to
        """
        self._repository = repository
        logger.info(
            "TemporalLocalCalendarConfigurationRepository initialized "
            "with %s",
            repository.__class__.__name__,
        )

    @activity.defn(
        name="cal.create_schedule.config_repo.local.get_collection"
    )
    async def get_collection(
        self, collection_id: str
    ) -> Optional[CalendarCollection]:
        """Activity wrapper for get_collection."""
        return await self._repository.get_collection(collection_id)

    @activity.defn(
        name="cal.create_schedule.config_repo.local.list_collections"
    )
    async def list_collections(self) -> List[CalendarCollection]:
        """Activity wrapper for list_collections."""
        return await self._repository.list_collections()

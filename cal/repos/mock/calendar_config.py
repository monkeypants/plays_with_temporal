"""
Mock implementation of CalendarConfigurationRepository for development and
testing.
"""

import logging
from typing import List, Optional

from cal.domain import CalendarCollection, CalendarSource
from cal.repositories import CalendarConfigurationRepository

logger = logging.getLogger(__name__)


class MockCalendarConfigurationRepository(CalendarConfigurationRepository):
    """
    Mock implementation of CalendarConfigurationRepository with hardcoded
    collections for development and testing purposes.
    """

    def __init__(self):
        """Initialize with predefined mock collections."""
        self.collections = [
            CalendarCollection(
                collection_id="work",
                display_name="Work Calendars",
                default_calendar_id="primary",
                calendar_sources=[
                    CalendarSource(
                        calendar_id="primary",
                        display_name="Primary Work Calendar",
                        source_type="google",
                        enabled=True,
                        sync_priority=1,
                    ),
                    CalendarSource(
                        calendar_id="team@company.com",
                        display_name="Team Calendar",
                        source_type="google",
                        enabled=True,
                        sync_priority=2,
                        metadata={
                            "color": "blue",
                            "description": "Shared team events and meetings",
                        },
                    ),
                ],
            ),
            CalendarCollection(
                collection_id="personal",
                display_name="Personal Calendars",
                default_calendar_id="personal@gmail.com",
                calendar_sources=[
                    CalendarSource(
                        calendar_id="personal@gmail.com",
                        display_name="Personal Calendar",
                        source_type="google",
                        enabled=True,
                        sync_priority=1,
                    ),
                    CalendarSource(
                        calendar_id="family@gmail.com",
                        display_name="Family Calendar",
                        source_type="google",
                        enabled=True,
                        sync_priority=2,
                    ),
                ],
            ),
            CalendarCollection(
                collection_id="all",
                display_name="All Calendars",
                default_calendar_id="primary",
                calendar_sources=[
                    CalendarSource(
                        calendar_id="primary",
                        display_name="Primary Work Calendar",
                        source_type="google",
                        enabled=True,
                        sync_priority=1,
                    ),
                    CalendarSource(
                        calendar_id="team@company.com",
                        display_name="Team Calendar",
                        source_type="google",
                        enabled=True,
                        sync_priority=2,
                    ),
                    CalendarSource(
                        calendar_id="personal@gmail.com",
                        display_name="Personal Calendar",
                        source_type="google",
                        enabled=True,
                        sync_priority=3,
                    ),
                    CalendarSource(
                        calendar_id="family@gmail.com",
                        display_name="Family Calendar",
                        source_type="google",
                        enabled=False,
                        sync_priority=4,
                    ),
                ],
            ),
        ]
        logger.debug(
            f"Initialized MockCalendarConfigurationRepository with "
            f"{len(self.collections)} collections"
        )

    async def get_collection(
        self, collection_id: str
    ) -> Optional[CalendarCollection]:
        """Retrieve a calendar collection by its ID."""
        for collection in self.collections:
            if collection.collection_id == collection_id:
                logger.debug(f"Found mock collection: {collection_id}")
                return collection

        logger.debug(f"Mock collection not found: {collection_id}")
        return None

    async def list_collections(self) -> List[CalendarCollection]:
        """List all available calendar collections."""
        logger.debug(f"Returning {len(self.collections)} mock collections")
        return self.collections.copy()

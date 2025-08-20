"""
Defines the use cases for calendar operations.
"""

import json
import logging
from datetime import datetime
from typing import List, Optional

from .domain import (
    CalendarEvent,
    CalendarCollection,
    Schedule,
    TimeBlock,
    TimeBlockDecision,
    ScheduleStatus,
)
from .repositories import (
    CalendarRepository,
    ScheduleRepository,
    TimeBlockClassifierRepository,
    CalendarConfigurationRepository,
)
from util.repositories import FileStorageRepository

logger = logging.getLogger(__name__)


class CalendarSyncUseCase:
    """
    Orchestrates the synchronization of events from a source calendar to a
    sink calendar.

    This use case follows the Clean Architecture pattern, depending on
    repository abstractions rather than concrete implementations. It contains
    the business logic for calculating the delta between two calendars and
    applying the necessary changes.
    """

    def __init__(
        self,
        source_repo: CalendarRepository,
        sink_repo: CalendarRepository,
        file_storage_repo: FileStorageRepository,
    ):
        self.source_repo = source_repo
        self.sink_repo = sink_repo
        self.file_storage_repo = file_storage_repo

    async def execute(
        self,
        source_calendar_id: str,
        sink_calendar_id: str,
        full_sync: bool = False,
    ) -> None:
        """
        Executes the calendar synchronization process.

        1. Retrieves the last sync state from the sink.
        2. Fetches changes from the source since that state.
        3. Calculates the delta (creates, updates, deletes).
        4. Applies the delta to the sink.
        5. Stores the new sync state in the sink.
        """
        logger.info(
            "Starting calendar sync",
            extra={"source": source_calendar_id, "sink": sink_calendar_id},
        )

        # 1. Get last sync state from the sink repository (unless full sync)
        last_sync_state = None
        if not full_sync:
            last_sync_state = await self.sink_repo.get_sync_state(
                for_calendar_id=source_calendar_id
            )

        # 2. Fetch changes from the source repository
        changes = await self.source_repo.get_changes(
            calendar_id=source_calendar_id, sync_state=last_sync_state
        )

        # 2.1. Retrieve events from file storage if needed
        upserted_events = changes.upserted_events
        if changes.upserted_events_file_id:
            logger.info(
                "Downloading events from file storage",
                extra={
                    "file_id": changes.upserted_events_file_id,
                    "source_calendar_id": source_calendar_id,
                },
            )

            # Download events from file storage
            events_data = await self.file_storage_repo.download_file(
                changes.upserted_events_file_id
            )

            if events_data:
                # Deserialize events from JSON
                events_json = events_data.decode("utf-8")
                events_dicts = json.loads(events_json)
                upserted_events = [
                    CalendarEvent(**event_dict) for event_dict in events_dicts
                ]

                logger.info(
                    "Successfully downloaded and deserialized events",
                    extra={
                        "file_id": changes.upserted_events_file_id,
                        "event_count": len(upserted_events),
                    },
                )
            else:
                logger.warning(
                    "Failed to download events from file storage",
                    extra={"file_id": changes.upserted_events_file_id},
                )
                upserted_events = []

        # 3. Calculate the delta
        (
            events_to_create,
            events_to_update,
            event_ids_to_delete,
        ) = await self._calculate_delta(
            sink_calendar_id=sink_calendar_id,
            upserted_source_events=upserted_events,
            deleted_source_event_ids=changes.deleted_event_ids,
        )

        # 4. Apply changes to the sink repository
        if events_to_create or events_to_update or event_ids_to_delete:
            logger.info(
                "Applying changes to sink calendar",
                extra={
                    "create_count": len(events_to_create),
                    "update_count": len(events_to_update),
                    "delete_count": len(event_ids_to_delete),
                },
            )
            await self.sink_repo.apply_changes(
                calendar_id=sink_calendar_id,
                events_to_create=events_to_create,
                events_to_update=events_to_update,
                event_ids_to_delete=event_ids_to_delete,
            )
        else:
            logger.info("No changes to apply to sink calendar.")

        # 5. Store the new sync state in the sink repository
        await self.sink_repo.store_sync_state(
            for_calendar_id=source_calendar_id,
            sync_state=changes.new_sync_state,
        )

        logger.info(
            "Calendar sync completed successfully",
            extra={"source": source_calendar_id, "sink": sink_calendar_id},
        )

    async def _calculate_delta(
        self,
        sink_calendar_id: str,
        upserted_source_events: List[CalendarEvent],
        deleted_source_event_ids: List[str],
    ) -> tuple[List[CalendarEvent], List[CalendarEvent], List[str]]:
        """
        Determines which events need to be created, updated, or deleted
        in the sink.
        """
        # We need to check both upserted and deleted events against the sink
        source_event_ids = [
            e.event_id for e in upserted_source_events
        ] + deleted_source_event_ids
        if not source_event_ids:
            return [], [], []

        # Get the current state of these events from the sink
        sink_events = await self.sink_repo.get_events_by_ids(
            calendar_id=sink_calendar_id, event_ids=source_event_ids
        )
        sink_events_map = {e.event_id: e for e in sink_events}

        events_to_create: List[CalendarEvent] = []
        events_to_update: List[CalendarEvent] = []

        for source_event in upserted_source_events:
            sink_event = sink_events_map.get(source_event.event_id)
            if not sink_event:
                # Event exists in source but not in sink -> CREATE
                events_to_create.append(source_event)
            elif sink_event.last_modified < source_event.last_modified:
                # Event exists in both, but source is newer -> UPDATE
                events_to_update.append(source_event)

        # Deleted events are those in the deleted list that actually exist in
        # the sink
        event_ids_to_delete = [
            event_id
            for event_id in deleted_source_event_ids
            if event_id in sink_events_map
        ]

        return events_to_create, events_to_update, event_ids_to_delete


class CreateScheduleUseCase:
    """
    Creates a Schedule from calendar events for a specified time period.

    This use case follows Clean Architecture principles, depending only on
    repository abstractions. It contains the business logic for converting
    calendar events into time blocks and creating a cohesive schedule.
    """

    def __init__(
        self,
        calendar_repo: CalendarRepository,
        schedule_repo: ScheduleRepository,
        time_block_classifier_repo: TimeBlockClassifierRepository,
        config_repo: CalendarConfigurationRepository,
    ):
        self.calendar_repo = calendar_repo
        self.schedule_repo = schedule_repo
        self.time_block_classifier_repo = time_block_classifier_repo
        self.config_repo = config_repo

    async def execute(
        self,
        calendar_id: Optional[str] = None,
        calendar_collection: Optional[CalendarCollection] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Schedule:
        """
        Creates and persists a schedule from calendar events.

        Args:
            calendar_id: Single calendar to create a schedule from (legacy
                support)
            calendar_collection: Collection of calendars to create a schedule
                from
            start_date: Start of the schedule period (defaults to today)
            end_date: End of the schedule period (defaults to end of
                start_date day)

        Returns:
            The created Schedule object
        """
        # Validate arguments
        if not calendar_id and not calendar_collection:
            raise ValueError(
                "Either calendar_id or calendar_collection must be provided"
            )
        if calendar_id and calendar_collection:
            raise ValueError(
                "Cannot specify both calendar_id and calendar_collection"
            )
        # Default to today if no dates provided
        if start_date is None:
            from datetime import timezone

            start_date = datetime.now(tz=timezone.utc).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
        if end_date is None:
            end_date = start_date.replace(
                hour=23, minute=59, second=59, microsecond=999999
            )

        # Determine which calendars to query
        if calendar_collection:
            # Filter enabled calendars and sort by priority
            enabled_sources = [
                source
                for source in calendar_collection.calendar_sources
                if source.enabled
            ]
            enabled_sources.sort(key=lambda s: s.sync_priority)

            calendar_ids = [source.calendar_id for source in enabled_sources]
            collection_name: str = calendar_collection.display_name

            logger.info(
                "Using calendar collection",
                extra={
                    "collection_id": calendar_collection.collection_id,
                    "collection_name": collection_name,
                    "enabled_calendars": len(calendar_ids),
                    "total_calendars": len(
                        calendar_collection.calendar_sources
                    ),
                    "calendar_priorities": [
                        s.sync_priority for s in enabled_sources
                    ],
                },
            )
        else:
            calendar_ids = [calendar_id] if calendar_id else []
            collection_name = calendar_id or "unknown"

        logger.info(
            "Creating schedule from calendar events",
            extra={
                "calendar_ids": calendar_ids,
                "calendar_count": len(calendar_ids),
                "collection_name": collection_name,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "date_range_hours": (end_date - start_date).total_seconds()
                / 3600,
            },
        )

        # 1. Fetch events within the specified date range
        if len(calendar_ids) == 1:
            # Use single-calendar method for backward compatibility
            filtered_events = (
                await self.calendar_repo.get_events_by_date_range(
                    calendar_id=calendar_ids[0],
                    start_date=start_date,
                    end_date=end_date,
                )
            )
        else:
            # Use multi-calendar method with performance optimization
            filtered_events = await self.calendar_repo.get_events_by_date_range_multi_calendar(  # noqa: E501
                calendar_ids=calendar_ids,
                start_date=start_date,
                end_date=end_date,
            )

        logger.info(
            f"Retrieved {len(filtered_events)} events from "
            f"{len(calendar_ids)} calendar(s) in date range",
            extra={
                "calendar_ids": calendar_ids,
                "calendar_count": len(calendar_ids),
                "collection_name": collection_name,
                "event_count": len(filtered_events),
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "events_per_calendar": (
                    len(filtered_events) / len(calendar_ids)
                    if calendar_ids
                    else 0
                ),
            },
        )

        # 2. Convert calendar events to time blocks
        time_blocks = []

        for event in filtered_events:
            # Classify the event using the classifier repository
            classifier_repo = self.time_block_classifier_repo
            block_type = await classifier_repo.classify_block_type(event)
            await classifier_repo.classify_responsibility_area(event)

            # Perform event triage to get decision and reasoning
            suggested_decision, decision_reason = (
                await classifier_repo.triage_event(event)
            )

            time_block = TimeBlock(
                time_block_id="",  # Will be generated by repository
                title=event.title,
                start_time=event.start_time,
                end_time=event.end_time,
                type=block_type,
                suggested_decision=suggested_decision,
                decision_reason=decision_reason,
                decision=TimeBlockDecision.PENDING_REVIEW,
                decision_notes=None,
                delegated_to=None,
                source_calendar_event_id=event.event_id,
                meeting_id=None,
                metadata={
                    # Calendar event details
                    "description": event.description,
                    "location": event.location,
                    "organizer": event.organizer,
                    "attendee_count": len(event.attendees),
                    "attendee_emails": (
                        [a.email for a in event.attendees]
                        if event.attendees
                        else []
                    ),
                    "status": event.status.value,
                    "last_modified": event.last_modified.isoformat(),
                    "all_day": event.all_day,
                    # Source calendar information
                    "calendar_id": event.calendar_id,
                    "etag": event.etag,
                    # Calendar collection context (if applicable)
                    "collection_id": (
                        calendar_collection.collection_id
                        if calendar_collection
                        else None
                    ),
                    "collection_name": collection_name,
                    # Attendee details (if any)
                    "attendees": (
                        [
                            {
                                "email": a.email,
                                "display_name": a.display_name,
                                "response_status": a.response_status.value,
                            }
                            for a in event.attendees
                        ]
                        if event.attendees
                        else []
                    ),
                },
            )
            time_blocks.append(time_block)

        # 3. Create the schedule
        schedule = Schedule(
            schedule_id="",  # Will be generated by repository
            start_date=start_date,
            end_date=end_date,
            time_blocks=time_blocks,
            status=ScheduleStatus.DRAFT,
        )

        # 4. Persist the schedule
        await self.schedule_repo.save_schedule(schedule)

        logger.info(
            "Successfully created schedule",
            extra={
                "schedule_id": schedule.schedule_id,
                "time_block_count": len(time_blocks),
                "event_count": len(filtered_events),
                "conversion_rate": (
                    len(time_blocks) / len(filtered_events)
                    if filtered_events
                    else 0
                ),
                "schedule_duration_hours": (
                    end_date - start_date
                ).total_seconds()
                / 3600,
                "avg_event_duration_minutes": (
                    sum(
                        (block.end_time - block.start_time).total_seconds()
                        for block in time_blocks
                    )
                    / 60
                    / len(time_blocks)
                    if time_blocks
                    else 0
                ),
            },
        )

        return schedule

    async def execute_for_collection(
        self,
        collection_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Schedule:
        """
        Creates and persists a schedule from a calendar collection.

        Args:
            collection_id: ID of the calendar collection to create schedule
                from
            start_date: Start of the schedule period (defaults to today)
            end_date: End of the schedule period (defaults to end of
                start_date day)

        Returns:
            The created Schedule object
        """
        # Load collection configuration via repository
        collection = await self.config_repo.get_collection(collection_id)
        if not collection:
            raise ValueError(
                f"Calendar collection '{collection_id}' not found"
            )

        # Delegate to existing execute method with collection
        return await self.execute(
            calendar_collection=collection,
            start_date=start_date,
            end_date=end_date,
        )

"""
Google Calendar implementation of the CalendarRepository protocol.
"""

import logging
import os.path
from datetime import datetime
from typing import Any, Dict, List, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build, Resource

from cal.domain import (
    Attendee,
    AttendeeResponseStatus,
    CalendarEvent,
    CalendarEventStatus,
)
from cal.repositories import CalendarChanges, CalendarRepository, SyncState

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]


def get_google_calendar_service() -> Resource:
    """
    Shows basic usage of the Google Calendar API.
    Prints the start and name of the next 10 events on the user's calendar.

    Handles the OAuth2 flow. The 'token.json' file stores the user's access
    and refresh tokens, and is created automatically when the authorization
    flow completes for the first time. A valid 'credentials.json' from a
    Google Cloud project with the Calendar API enabled is required.
    """
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    return build("calendar", "v3", credentials=creds)


def _google_event_to_domain_event(
    item: Dict[str, Any], calendar_id: str
) -> CalendarEvent:
    """Converts a Google Calendar API event resource to a CalendarEvent."""

    # Debug logging for event status
    event_title = item.get("summary", "No Title")
    event_status = item.get("status", "unknown")
    logger.info(
        f"Processing event: '{event_title}' with status: '{event_status}'"
    )

    def _parse_datetime(time_data: Dict[str, str]) -> datetime:
        """Parses Google's datetime format."""
        dt_str = time_data.get("dateTime", time_data.get("date"))
        if dt_str is None:
            raise ValueError("No datetime or date found in time_data")

        # Parse the datetime string directly - Google Calendar API returns
        # ISO format
        try:
            if "T" in dt_str:
                # Full datetime with time - handle Z suffix for UTC
                if dt_str.endswith("Z"):
                    dt_str = dt_str[:-1] + "+00:00"
                return datetime.fromisoformat(dt_str)
            else:
                # Date only - treat as all-day event at midnight UTC
                return datetime.fromisoformat(dt_str + "T00:00:00+00:00")
        except ValueError as e:
            raise ValueError(
                f"Failed to parse datetime string '{dt_str}': {e}"
            )

    start_time = _parse_datetime(item["start"])
    end_time = _parse_datetime(item["end"])
    all_day = "date" in item["start"]

    attendees = [
        Attendee(
            email=a["email"],
            display_name=a.get("displayName"),
            response_status=AttendeeResponseStatus(a["responseStatus"]),
        )
        for a in item.get("attendees", [])
    ]

    return CalendarEvent(
        event_id=item["id"],
        calendar_id=calendar_id,
        title=item.get("summary", "No Title"),
        description=item.get("description"),
        start_time=start_time,
        end_time=end_time,
        all_day=all_day,
        location=item.get("location"),
        status=CalendarEventStatus(item["status"]),
        attendees=attendees,
        organizer=item.get("organizer", {}).get("email"),
        last_modified=datetime.fromisoformat(
            item["updated"].replace("Z", "+00:00")
        ),
        etag=item.get("etag"),
    )


class GoogleCalendarRepository(CalendarRepository):
    """
    A source repository for fetching events from the Google Calendar API.
    """

    def __init__(self, service: Resource):
        self._service = service

    async def get_changes(
        self, calendar_id: str, sync_state: Optional[SyncState]
    ) -> CalendarChanges:
        """
        Fetches changes from the Google Calendar API.
        If sync_state is None, performs a full sync. Otherwise, performs an
        incremental sync using the provided sync token.
        """
        upserted_events: List[CalendarEvent] = []
        deleted_event_ids: List[str] = []
        page_token = None

        while True:
            events_resource = self._service.events()
            request = events_resource.list(
                calendarId=calendar_id,
                pageToken=page_token,
                syncToken=sync_state.sync_token if sync_state else None,
            )
            events_result = await self._execute_request(request)

            for item in events_result.get("items", []):
                if item["status"] == "cancelled":
                    deleted_event_ids.append(item["id"])
                else:
                    try:
                        event = _google_event_to_domain_event(
                            item, calendar_id
                        )
                        upserted_events.append(event)
                        # Debug logging for event status
                        logger.debug(
                            f"Processed event: '{event.title}' with status: "
                            f"'{event.status.value}'"
                        )
                    except Exception as e:
                        logger.warning(
                            f"Skipping invalid calendar event "
                            f"{item.get('id', 'unknown')}: {str(e)}"
                        )
                        # Continue processing other events
                        continue

            page_token = events_result.get("nextPageToken")
            if not page_token:
                break

        new_sync_token = events_result.get("nextSyncToken")
        if not new_sync_token:
            raise ValueError(
                "Google Calendar API did not return a new sync token."
            )

        return CalendarChanges(
            upserted_events=upserted_events,
            upserted_events_file_id=None,
            deleted_event_ids=deleted_event_ids,
            new_sync_state=SyncState(sync_token=new_sync_token),
        )

    async def get_events_by_ids(
        self, calendar_id: str, event_ids: List[str]
    ) -> List[CalendarEvent]:
        """Not typically used for a source repo, required for completeness."""
        events = []
        for event_id in event_ids:
            try:
                events_resource = self._service.events()
                request = events_resource.get(
                    calendarId=calendar_id, eventId=event_id
                )
                event_item = await self._execute_request(request)
                if event_item and event_item.get("status") != "cancelled":
                    try:
                        events.append(
                            _google_event_to_domain_event(
                                event_item, calendar_id
                            )
                        )
                    except Exception as e:
                        logger.warning(
                            f"Skipping invalid calendar event {event_id}: "
                            f"{str(e)}"
                        )
                        # Continue processing other events
                        continue
            except Exception:
                logger.warning(
                    f"Could not retrieve event {event_id}", exc_info=True
                )
        return events

    async def get_events_by_date_range(
        self, calendar_id: str, start_date: datetime, end_date: datetime
    ) -> List[CalendarEvent]:
        """Fetch events within a specific date range."""
        events_resource = self._service.events()
        request = events_resource.list(
            calendarId=calendar_id,
            timeMin=start_date.isoformat(),
            timeMax=end_date.isoformat(),
            singleEvents=True,
            orderBy="startTime",
        )
        events_result = await self._execute_request(request)

        events = []
        for item in events_result.get("items", []):
            if item["status"] != "cancelled":
                try:
                    event = _google_event_to_domain_event(item, calendar_id)
                    events.append(event)
                except Exception as e:
                    logger.warning(
                        f"Skipping invalid event {item.get('id')}: {e}"
                    )

        return events

    async def get_events_by_date_range_multi_calendar(
        self,
        calendar_ids: List[str],
        start_date: datetime,
        end_date: datetime,
    ) -> List[CalendarEvent]:
        """Get events from multiple calendars within a specific date range."""
        all_events = []
        for calendar_id in calendar_ids:
            try:
                events = await self.get_events_by_date_range(
                    calendar_id, start_date, end_date
                )
                all_events.extend(events)
            except Exception as e:
                logger.warning(
                    f"Failed to fetch events from calendar {calendar_id}: {e}"
                )
                # Continue with other calendars even if one fails
                continue

        # Sort by start time for consistent ordering across calendars
        all_events.sort(key=lambda e: e.start_time)
        return all_events

    async def get_all_events(self, calendar_id: str) -> List[CalendarEvent]:
        raise NotImplementedError(
            "GoogleCalendarRepository is a source repository and does not "
            "support fetching all events directly. Use get_changes for "
            "synchronization."
        )

    async def _execute_request(self, request: Any) -> Any:
        """Asynchronously execute a Google API client request."""
        # The google-api-python-client is not natively async.
        # In a real async app, this would be run in a thread pool.
        # For this implementation, we execute it directly.
        try:
            return request.execute()
        except Exception as e:
            # Enhanced error logging for evaluation debugging
            error_type = type(e).__name__
            logger.error(
                f"Google API request failed: {error_type}: {str(e)}",
                extra={
                    "error_type": error_type,
                    "request_uri": getattr(request, "uri", "unknown"),
                    "request_method": getattr(request, "method", "unknown"),
                },
                exc_info=True,
            )
            raise

    async def apply_changes(
        self,
        calendar_id: str,
        events_to_create: List[CalendarEvent],
        events_to_update: List[CalendarEvent],
        event_ids_to_delete: List[str],
    ) -> None:
        raise NotImplementedError(
            "GoogleCalendarRepository is a source repository."
        )

    async def get_sync_state(
        self, for_calendar_id: str
    ) -> Optional[SyncState]:
        raise NotImplementedError(
            "GoogleCalendarRepository is a source repository."
        )

    async def store_sync_state(
        self, for_calendar_id: str, sync_state: SyncState
    ) -> None:
        raise NotImplementedError(
            "GoogleCalendarRepository is a source repository."
        )

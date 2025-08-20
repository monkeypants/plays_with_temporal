#!/usr/bin/env python3
"""
CLI for Google Calendar Integration Demo

This script demonstrates the complete calendar triage workflow using real
Google Calendar data:
1. Fetches calendar events from Google Calendar API
2. Applies AI triage analysis using the classifier
3. Creates a schedule with time blocks
4. Outputs the results in org-mode format

Prerequisites:
- Google Calendar API credentials (credentials.json)
- OAuth token will be generated on first run (token.json)

This validates the complete CalendarEvent → TimeBlock → Schedule flow
with real calendar data and shows the AI triage decisions in action.
"""

import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import click

# Add the project root to the path so we can import cal modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from cal.domain import TimeBlock
from cal.org import generate_org_content
from cal.repos.google.calendar import (
    get_google_calendar_service,
    GoogleCalendarRepository,
)
from cal.repos.local.calendar import LocalCalendarRepository
from cal.repos.local.time_block_classifier import (
    LocalTimeBlockClassifierRepository,
)
from cal.repositories import CalendarConfigurationRepository
from cal.usecase import CreateScheduleUseCase

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Suppress noisy Google API cache warnings
logging.getLogger("googleapiclient.discovery_cache").setLevel(logging.ERROR)


def create_google_calendar_use_case(
    calendar_id: str,
    config_repo: CalendarConfigurationRepository,
) -> CreateScheduleUseCase:
    """Factory function to create a configured use case for Google
    Calendar."""
    # Use actual Google Calendar repository
    service = get_google_calendar_service()
    google_calendar_repo = GoogleCalendarRepository(service)

    local_schedule_repo = LocalCalendarRepository(
        base_path="google_demo_data"
    )
    classifier_repo = LocalTimeBlockClassifierRepository()

    return CreateScheduleUseCase(
        calendar_repo=google_calendar_repo,
        schedule_repo=local_schedule_repo,
        time_block_classifier_repo=classifier_repo,
        config_repo=config_repo,
    )


async def _main(
    output_path: str,
    calendar_id: str,
    calendar_collection: Optional[str],
    timezone: Optional[str],
    start_date: Optional[str],
    end_date: Optional[str],
) -> None:
    """Async main function to run the Google Calendar demo."""
    click.echo("Google Calendar Triage Demo")
    click.echo("=" * 50)
    click.echo()

    # Initialize variables that may be used later
    collection = None
    enabled_calendars = []

    # Determine timezone
    import zoneinfo

    if timezone:
        tz = zoneinfo.ZoneInfo(timezone)
        click.echo(f"Using specified timezone: {timezone}")
    else:
        system_tz = datetime.now().astimezone().tzinfo
        if system_tz is None:
            tz = zoneinfo.ZoneInfo("UTC")
            click.echo("Using default timezone: UTC")
        else:
            # Get the timezone name from the system timezone
            # This handles the case where str(system_tz) returns abbreviations
            # like 'AEST'
            try:
                # Try to get the zone name from the tzinfo object
                if hasattr(system_tz, "zone"):
                    tz = zoneinfo.ZoneInfo(system_tz.zone)
                    click.echo(f"Using system timezone: {system_tz.zone}")
                elif hasattr(system_tz, "key"):
                    tz = zoneinfo.ZoneInfo(system_tz.key)
                    click.echo(f"Using system timezone: {system_tz.key}")
                else:
                    # Fallback: use the system timezone directly if it's
                    # already a ZoneInfo
                    if isinstance(system_tz, zoneinfo.ZoneInfo):
                        tz = system_tz
                        click.echo(f"Using system timezone: {system_tz}")
                    else:
                        # Last resort: use UTC
                        tz = zoneinfo.ZoneInfo("UTC")
                        click.echo(
                            f"Could not determine system timezone "
                            f"({system_tz}), using UTC"
                        )
            except Exception as e:
                # If all else fails, use UTC
                tz = zoneinfo.ZoneInfo("UTC")
                click.echo(f"Timezone error ({e}), using UTC")

    # Check for credentials file
    from pathlib import Path

    credentials_path = Path("credentials.json")
    if not credentials_path.exists():
        click.echo("Error: credentials.json not found!", err=True)
        click.echo(err=True)
        click.echo(
            "Please follow the setup instructions in README-google-setup.md",
            err=True,
        )
        click.echo("to obtain Google Calendar API credentials.", err=True)
        sys.exit(1)

    try:
        click.echo("Authenticating with Google Calendar API...")

        # Create configuration repository
        from cal.repos.local.calendar_config import (
            LocalCalendarConfigurationRepository,
        )

        config_repo = LocalCalendarConfigurationRepository()

        if calendar_collection:
            try:
                collection = await config_repo.get_collection(
                    calendar_collection
                )
                if not collection:
                    click.echo(
                        f"Error: Calendar collection '{calendar_collection}' "
                        f"not found in configuration",
                        err=True,
                    )
                    sys.exit(1)

                # Validate collection has enabled calendars
                enabled_calendars = [
                    source
                    for source in collection.calendar_sources
                    if source.enabled
                ]
                if not enabled_calendars:
                    click.echo(
                        "Error: No enabled calendars in collection", err=True
                    )
                    sys.exit(1)

                # Sort by priority for consistent processing
                enabled_calendars.sort(key=lambda s: s.sync_priority)

                # For demo purposes, use the first enabled calendar for
                # authentication. In a full implementation, we'd need to
                # handle multiple calendar authentication
                demo_calendar_id = enabled_calendars[0].calendar_id
                use_case = create_google_calendar_use_case(
                    demo_calendar_id, config_repo
                )

                click.echo(
                    f"Using calendar collection: {collection.display_name}"
                )
                click.echo(f"Collection ID: {collection.collection_id}")
                click.echo(
                    f"Total calendars: {len(collection.calendar_sources)}"
                )
                click.echo(f"Enabled calendars: {len(enabled_calendars)}")

                for i, source in enumerate(enabled_calendars, 1):
                    priority_info = f" (Priority: {source.sync_priority})"
                    click.echo(f"  {i}. {source.display_name}{priority_info}")

                disabled_count = len(collection.calendar_sources) - len(
                    enabled_calendars
                )
                if disabled_count > 0:
                    click.echo(f"Disabled calendars: {disabled_count}")

            except Exception as e:
                click.echo(
                    f"Error loading calendar configuration: {e}", err=True
                )
                sys.exit(1)
        else:
            use_case = create_google_calendar_use_case(
                calendar_id, config_repo
            )

        # Parse date range BEFORE creating use case
        click.echo(
            f"DEBUG: start_date_param='{start_date}', "
            f"end_date_param='{end_date}'"
        )

        if start_date:
            parsed_start_date = datetime.strptime(
                start_date, "%Y-%m-%d"
            ).replace(tzinfo=tz)
            parsed_start_date = parsed_start_date.replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            click.echo(f"DEBUG: Parsed start_date: {parsed_start_date}")
        else:
            # Default to today
            now = datetime.now(tz=tz)
            parsed_start_date = now.replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            click.echo(
                f"DEBUG: Using default start_date: {parsed_start_date}"
            )

        if end_date:
            parsed_end_date = datetime.strptime(end_date, "%Y-%m-%d").replace(
                tzinfo=tz
            )
            parsed_end_date = parsed_end_date.replace(
                hour=23, minute=59, second=59, microsecond=999999
            )
            click.echo(f"DEBUG: Parsed end_date: {parsed_end_date}")
        else:
            parsed_end_date = parsed_start_date.replace(
                hour=23, minute=59, second=59, microsecond=999999
            )
            click.echo(f"DEBUG: Using default end_date: {parsed_end_date}")

        click.echo(
            f"Using date range: "
            f"{parsed_start_date.strftime('%Y-%m-%d %H:%M %Z')} to "
            f"{parsed_end_date.strftime('%Y-%m-%d %H:%M %Z')}"
        )

        if calendar_collection:
            click.echo(
                f"Fetching events from {len(enabled_calendars)} calendars "
                f"and creating schedule with AI triage analysis..."
            )
            schedule = await use_case.execute(
                calendar_collection=collection,
                start_date=parsed_start_date,
                end_date=parsed_end_date,
            )
            click.echo(
                f"Created schedule with {len(schedule.time_blocks)} time "
                f"blocks from {len(enabled_calendars)} Google Calendars"
            )
        else:
            click.echo(
                "Fetching Google Calendar events and creating schedule with "
                "AI triage analysis..."
            )
            schedule = await use_case.execute(
                calendar_id=calendar_id,
                start_date=parsed_start_date,
                end_date=parsed_end_date,
            )
            click.echo(
                f"Created schedule with {len(schedule.time_blocks)} time "
                f"blocks from Google Calendar"
            )
        click.echo()

        if not schedule.time_blocks:
            click.echo(
                "No calendar events found in the specified time range."
            )
            click.echo(
                "Try scheduling some events in your Google Calendar and "
                "run the demo again."
            )
            return

        if calendar_collection and collection:
            click.echo(
                f"Triage Analysis Results from {collection.display_name}:"
            )
        else:
            click.echo("Triage Analysis Results from Google Calendar:")
        click.echo("-" * 50)

        # Group events by calendar if using collection
        if calendar_collection and collection and len(enabled_calendars) > 1:
            # Group time blocks by calendar_id for better organization
            calendar_blocks: Dict[str, List[TimeBlock]] = {}
            for block in schedule.time_blocks:
                cal_id = block.metadata.get("calendar_id", "unknown")
                if cal_id not in calendar_blocks:
                    calendar_blocks[cal_id] = []
                calendar_blocks[cal_id].append(block)

            # Display results grouped by calendar
            for cal_id, blocks in calendar_blocks.items():
                # Find calendar display name
                cal_name = cal_id
                if collection:
                    for source in enabled_calendars:
                        if source.calendar_id == cal_id:
                            cal_name = source.display_name
                            break

                click.echo(f"\n=== {cal_name} ({len(blocks)} events) ===")
                for i, block in enumerate(blocks, 1):
                    click.echo(f"{i}. {block.title}")
                    time_str = (
                        f"   Time: "
                        f"{block.start_time.strftime('%Y-%m-%d %H:%M')}"
                        f" - {block.end_time.strftime('%H:%M')}"
                    )
                    click.echo(time_str)
                    decision_text = (
                        block.suggested_decision.value.upper()
                        if block.suggested_decision
                        else "NONE"
                    )
                    decision_str = f"   Decision: {decision_text}"
                    click.echo(decision_str)
                    click.echo(f"   Reason: {block.decision_reason}")
                    if block.source_calendar_event_id:
                        event_id_str = (
                            f"   Google Event ID: "
                            f"{block.source_calendar_event_id}"
                        )
                        click.echo(event_id_str)
                    click.echo()
        else:
            # Single calendar or collection with one calendar - simple display
            for i, block in enumerate(schedule.time_blocks, 1):
                click.echo(f"{i}. {block.title}")
                time_str = (
                    f"   Time: {block.start_time.strftime('%Y-%m-%d %H:%M')}"
                    f" - {block.end_time.strftime('%H:%M')}"
                )
                click.echo(time_str)
                decision_text = (
                    block.suggested_decision.value.upper()
                    if block.suggested_decision
                    else "NONE"
                )
                click.echo(f"   Decision: {decision_text}")
                click.echo(f"   Reason: {block.decision_reason}")
                if block.source_calendar_event_id:
                    event_id_str = (
                        f"   Google Event ID: "
                        f"{block.source_calendar_event_id}"
                    )
                    click.echo(event_id_str)
                # Show calendar source if using collection
                if calendar_collection and collection:
                    cal_id = block.metadata.get("calendar_id", "unknown")
                    for source in enabled_calendars:
                        if source.calendar_id == cal_id:
                            click.echo(f"   Calendar: {source.display_name}")
                            break
                click.echo()

        output_file = Path(output_path)
        if calendar_collection and collection is not None:
            title = f"Calendar Triage: {collection.display_name}"
            section_title = f"Triage Decisions from {collection.display_name}"
        else:
            title = "Google Calendar Triage Demo Output"
            section_title = "Triage Decisions from Google Calendar"
        org_content = generate_org_content(schedule, title, section_title)

        with open(str(output_file), "w") as f:
            f.write(org_content)

        click.echo(f"Org-mode output written to: {output_file.absolute()}")
        click.echo()
        click.echo("Google Calendar demo completed successfully!")
        click.echo()
        click.echo("To view the results:")
        click.echo(f"   cat {output_file}")
        click.echo("   # or open in Emacs for full org-mode experience")

    except Exception as e:
        logger.error(f"Demo failed: {str(e)}", exc_info=True)
        click.echo(f"Demo failed: {str(e)}", err=True)
        click.echo(err=True)
        click.echo("Common issues:", err=True)
        click.echo("- Check internet connection", err=True)
        click.echo("- Missing or invalid credentials.json", err=True)
        click.echo("- Google Calendar API not enabled", err=True)
        click.echo("- Verify credentials.json is valid", err=True)
        click.echo("- Network connectivity issues", err=True)
        click.echo(
            "- OAuth token expired (delete token.json and try again)",
            err=True,
        )
        click.echo("- Try re-authenticating with Google", err=True)
        sys.exit(1)


@click.command()
@click.option(
    "--output-path",
    default="google_demo_output.org",
    help="Path to write the org-mode output file.",
    type=click.Path(),
)
@click.option(
    "--calendar-id",
    default="primary",
    help="ID of the Google Calendar to use.",
)
@click.option(
    "--calendar-collection",
    default=None,
    help="Name of calendar collection to use (from config/calendars.yaml)",
)
@click.option(
    "--timezone",
    default=None,
    help="Timezone override (defaults to system timezone)",
)
@click.option(
    "--start-date",
    default=None,
    help="Start date (YYYY-MM-DD format, defaults to today)",
)
@click.option(
    "--end-date",
    default=None,
    help="End date (YYYY-MM-DD format, defaults to end of start date)",
)
def main(
    output_path: str,
    calendar_id: str,
    calendar_collection: Optional[str],
    timezone: Optional[str],
    start_date: Optional[str],
    end_date: Optional[str],
) -> None:
    """Run the Google Calendar triage demo."""
    if calendar_id != "primary" and calendar_collection:
        click.echo(
            "Error: Cannot specify both --calendar-id and "
            "--calendar-collection",
            err=True,
        )
        sys.exit(1)

    # DEBUG: Log what Click is passing to main
    print(
        f"DEBUG main(): output_path='{output_path}', "
        f"calendar_id='{calendar_id}', "
        f"calendar_collection='{calendar_collection}', "
        f"timezone='{timezone}', start_date='{start_date}', "
        f"end_date='{end_date}'"
    )
    asyncio.run(
        _main(
            output_path,
            calendar_id,
            calendar_collection,
            timezone,
            start_date,
            end_date,
        )
    )


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
CLI for managing calendar sync scheduling via Temporal.

This script provides commands to manage scheduled calendar synchronization
using Temporal's native scheduling capabilities instead of a separate daemon.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

import click
from temporalio.client import (
    Client,
    ScheduleActionStartWorkflow,
    ScheduleSpec,
    ScheduleIntervalSpec,
)
from datetime import timedelta

# Add the project root to the path so we can import cal modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from cal.workflows import CalendarSyncWorkflow

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def _create_schedule(
    collection_id: str,
    interval_minutes: int,
    temporal_address: str,
) -> None:
    """Create a Temporal schedule for periodic calendar sync."""
    click.echo("Creating Calendar Sync Schedule")
    click.echo("=" * 35)
    click.echo()

    try:
        # Connect to Temporal
        click.echo(f"Connecting to Temporal at {temporal_address}...")
        client = await Client.connect(temporal_address)

        schedule_id = f"calendar-sync-{collection_id}"

        click.echo(f"Creating schedule: {schedule_id}")
        click.echo(f"Collection: {collection_id}")
        click.echo(f"Interval: {interval_minutes} minutes")
        click.echo()

        # Create the schedule using dedicated scheduled workflow
        from temporalio.client import Schedule

        schedule = Schedule(
            action=ScheduleActionStartWorkflow(
                CalendarSyncWorkflow.run,
                args=[
                    "primary",  # source_calendar_id
                    "postgresql",  # sink_calendar_id
                    False,  # full_sync
                ],
                id=f"sync-{collection_id}-{{.ScheduledTime.Unix}}",
                task_queue="calendar-task-queue",
            ),
            spec=ScheduleSpec(
                intervals=[
                    ScheduleIntervalSpec(
                        every=timedelta(minutes=interval_minutes)
                    )
                ]
            ),
        )

        await client.create_schedule(schedule_id, schedule)

        click.echo("Schedule created successfully!")
        click.echo(f"Schedule ID: {schedule_id}")
        click.echo(f"Sync will run every {interval_minutes} minutes")

    except Exception as e:
        logger.error(f"Schedule creation failed: {str(e)}", exc_info=True)
        click.echo(f"Schedule creation failed: {str(e)}", err=True)
        sys.exit(1)


async def _delete_schedule(
    collection_id: str,
    temporal_address: str,
) -> None:
    """Delete a Temporal schedule for calendar sync."""
    click.echo("Deleting Calendar Sync Schedule")
    click.echo("=" * 35)
    click.echo()

    try:
        # Connect to Temporal
        click.echo(f"Connecting to Temporal at {temporal_address}...")
        client = await Client.connect(temporal_address)

        schedule_id = f"calendar-sync-{collection_id}"

        click.echo(f"Deleting schedule: {schedule_id}")

        # Get and delete the schedule
        schedule_handle = client.get_schedule_handle(schedule_id)
        await schedule_handle.delete()

        click.echo("Schedule deleted successfully!")

    except Exception as e:
        logger.error(f"Schedule deletion failed: {str(e)}", exc_info=True)
        click.echo(f"Schedule deletion failed: {str(e)}", err=True)
        sys.exit(1)


async def _list_schedules(temporal_address: str) -> None:
    """List all calendar sync schedules."""
    click.echo("Calendar Sync Schedules")
    click.echo("=" * 25)
    click.echo()

    try:
        # Connect to Temporal
        client = await Client.connect(temporal_address)

        # List schedules with calendar-sync prefix
        schedules = []
        schedule_list = await client.list_schedules()
        async for schedule in schedule_list:
            if schedule.id.startswith("calendar-sync-"):
                schedules.append(schedule)

        if not schedules:
            click.echo("No calendar sync schedules found.")
            return

        for schedule in schedules:
            click.echo(f"Schedule ID: {schedule.id}")
            # Additional schedule details could be shown here
            click.echo()

    except Exception as e:
        logger.error(f"Schedule listing failed: {str(e)}", exc_info=True)
        click.echo(f"Schedule listing failed: {str(e)}", err=True)
        sys.exit(1)


@click.group()
def cli():
    """Manage calendar sync scheduling via Temporal."""
    pass


@cli.command()
@click.option(
    "--collection-id",
    default="work",
    help="Calendar collection ID to sync",
)
@click.option(
    "--interval-minutes",
    default=15,
    type=int,
    help="Sync interval in minutes",
)
@click.option(
    "--temporal-address",
    default=None,
    help="Temporal server address (defaults to TEMPORAL_ADDRESS env var "
    "or localhost:7233)",
)
def start(
    collection_id: str, interval_minutes: int, temporal_address: str | None
) -> None:
    """Create a scheduled sync for a calendar collection."""
    if temporal_address is None:
        temporal_address = os.environ.get(
            "TEMPORAL_ADDRESS", "localhost:7233"
        )

    asyncio.run(
        _create_schedule(collection_id, interval_minutes, temporal_address)
    )


@cli.command()
@click.option(
    "--collection-id",
    default="work",
    help="Calendar collection ID to stop syncing",
)
@click.option(
    "--temporal-address",
    default=None,
    help="Temporal server address (defaults to TEMPORAL_ADDRESS env var "
    "or localhost:7233)",
)
def stop(collection_id: str, temporal_address: str | None) -> None:
    """Delete a scheduled sync for a calendar collection."""
    if temporal_address is None:
        temporal_address = os.environ.get(
            "TEMPORAL_ADDRESS", "localhost:7233"
        )

    asyncio.run(_delete_schedule(collection_id, temporal_address))


@cli.command()
@click.option(
    "--temporal-address",
    default=None,
    help="Temporal server address (defaults to TEMPORAL_ADDRESS env var "
    "or localhost:7233)",
)
def status(temporal_address: str | None) -> None:
    """List all calendar sync schedules."""
    if temporal_address is None:
        temporal_address = os.environ.get(
            "TEMPORAL_ADDRESS", "localhost:7233"
        )

    asyncio.run(_list_schedules(temporal_address))


if __name__ == "__main__":
    cli()

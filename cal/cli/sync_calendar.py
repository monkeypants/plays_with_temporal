#!/usr/bin/env python3
"""
CLI for triggering calendar sync workflows.

This script provides commands to manually trigger calendar synchronization
between Google Calendar and PostgreSQL storage.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Optional

import click
from temporalio.client import Client

# Add the project root to the path so we can import cal modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from cal.workflows import CalendarSyncWorkflow

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def _trigger_sync(
    source_calendar_id: str,
    sink_calendar_id: str,
    full_sync: bool,
    temporal_address: str,
) -> None:
    """Async function to trigger calendar sync workflow."""
    click.echo("Calendar Sync Trigger")
    click.echo("=" * 30)
    click.echo()

    try:
        # Connect to Temporal
        click.echo(f"Connecting to Temporal at {temporal_address}...")
        client = await Client.connect(temporal_address)

        # Generate workflow ID
        workflow_id = f"calendar-sync-{source_calendar_id}-{sink_calendar_id}"
        if full_sync:
            workflow_id += "-full"

        click.echo(f"Starting sync workflow: {workflow_id}")
        click.echo(f"Source calendar: {source_calendar_id}")
        click.echo(f"Sink calendar: {sink_calendar_id}")
        click.echo(f"Full sync: {full_sync}")
        click.echo()

        # Start the workflow
        handle = await client.start_workflow(
            CalendarSyncWorkflow.run,
            args=[source_calendar_id, sink_calendar_id, full_sync],
            id=workflow_id,
            task_queue="calendar-task-queue",
        )

        click.echo("Workflow started successfully!")
        click.echo(f"Workflow ID: {handle.id}")
        click.echo(f"Run ID: {handle.result_run_id}")
        click.echo()

        # Wait for completion
        click.echo("⏳ Waiting for workflow completion...")
        result = await handle.result()

        if result:
            click.echo("Calendar sync completed successfully!")
        else:
            click.echo("Calendar sync failed!")
            sys.exit(1)

    except Exception as e:
        logger.error(f"Sync trigger failed: {str(e)}", exc_info=True)
        click.echo(f"Sync trigger failed: {str(e)}", err=True)
        sys.exit(1)


@click.command()
@click.option(
    "--source-calendar-id",
    default="primary",
    help="ID of the source calendar (e.g., Google Calendar)",
)
@click.option(
    "--sink-calendar-id",
    default="postgresql",
    help="ID of the sink calendar (PostgreSQL storage)",
)
@click.option(
    "--calendar-collection",
    default=None,
    help="Name of calendar collection to sync (from config/calendars.yaml)",
)
@click.option(
    "--full-sync",
    is_flag=True,
    help="Perform full sync (ignore sync tokens)",
)
@click.option(
    "--temporal-address",
    default=None,
    help="Temporal server address (defaults to TEMPORAL_ADDRESS env var "
    "or localhost:7233)",
)
def main(
    source_calendar_id: str,
    sink_calendar_id: str,
    calendar_collection: Optional[str],
    full_sync: bool,
    temporal_address: Optional[str],
) -> None:
    """Trigger calendar sync workflow."""
    if temporal_address is None:
        temporal_address = os.environ.get(
            "TEMPORAL_ADDRESS", "localhost:7233"
        )

    # Create configuration repository
    from cal.repos.local.calendar_config import (
        LocalCalendarConfigurationRepository,
    )

    config_repo = LocalCalendarConfigurationRepository()

    if calendar_collection:
        try:
            collection = asyncio.run(
                config_repo.get_collection(calendar_collection)
            )
            if not collection:
                click.echo(
                    f"Error: Calendar collection '{calendar_collection}' "
                    f"not found in configuration",
                    err=True,
                )
                sys.exit(1)

            # Display collection information
            click.echo(f"Collection: {collection.display_name}")
            enabled_sources = [
                s for s in collection.calendar_sources if s.enabled
            ]
            disabled_sources = [
                s for s in collection.calendar_sources if not s.enabled
            ]

            click.echo(f"Enabled calendars: {len(enabled_sources)}")
            click.echo(f"Disabled calendars: {len(disabled_sources)}")
            click.echo()

            # Sort by sync priority for consistent ordering
            enabled_sources.sort(key=lambda s: s.sync_priority)

            # Sync each enabled calendar in the collection
            for i, source in enumerate(enabled_sources, 1):
                sync_msg = (
                    f"[{i}/{len(enabled_sources)}] Syncing: "
                    f"{source.display_name} ({source.calendar_id}) "
                    f"[Priority: {source.sync_priority}]"
                )
                click.echo(sync_msg)
                try:
                    asyncio.run(
                        _trigger_sync(
                            source.calendar_id,
                            sink_calendar_id,
                            full_sync,
                            temporal_address,
                        )
                    )
                    click.echo(f"✓ Successfully synced {source.display_name}")
                except Exception as e:
                    click.echo(
                        f"✗ Failed to sync {source.display_name}: {e}",
                        err=True,
                    )
                    # Continue with other calendars rather than failing
                    # completely
                    continue
                click.echo()

            click.echo(
                f"Collection sync completed: {collection.display_name}"
            )

        except Exception as e:
            click.echo(f"Error loading calendar configuration: {e}", err=True)
            sys.exit(1)
    else:
        # Single calendar sync (legacy mode)
        asyncio.run(
            _trigger_sync(
                source_calendar_id,
                sink_calendar_id,
                full_sync,
                temporal_address,
            )
        )


if __name__ == "__main__":
    main()

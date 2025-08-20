#!/usr/bin/env python3
"""
CLI for Calendar.org Output Demo (Mock Data)

This script demonstrates the complete calendar triage workflow:
1. Fetches calendar events from a mock repository
2. Applies AI triage analysis using the classifier
3. Creates a schedule with time blocks
4. Outputs the results in org-mode format

This validates the complete CalendarEvent → TimeBlock → Schedule flow
and shows the AI triage decisions in action.
"""

import asyncio
import logging
import sys
from pathlib import Path

import click

# Add the project root to the path so we can import cal modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from cal.org import generate_org_content
from cal.repos.local.calendar import LocalCalendarRepository
from cal.repos.local.time_block_classifier import (
    LocalTimeBlockClassifierRepository,
)
from cal.repos.mock.calendar import MockCalendarRepository
from cal.repos.mock.calendar_config import MockCalendarConfigurationRepository
from cal.usecase import CreateScheduleUseCase

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def _main(output_path: str) -> None:
    """Async main function to run the demo."""
    click.echo("Calendar Triage Demo (Mock Data)")
    click.echo("=" * 50)
    click.echo()

    # 1. Set up repositories
    click.echo("Setting up repositories...")
    mock_calendar_repo = MockCalendarRepository()
    local_schedule_repo = LocalCalendarRepository(base_path="demo_data")
    classifier_repo = LocalTimeBlockClassifierRepository()
    config_repo = MockCalendarConfigurationRepository()

    # 2. Create the use case
    use_case = CreateScheduleUseCase(
        calendar_repo=mock_calendar_repo,
        schedule_repo=local_schedule_repo,
        time_block_classifier_repo=classifier_repo,
        config_repo=config_repo,
    )

    # 3. Execute the use case to create a schedule
    click.echo("Creating schedule with AI triage analysis...")
    schedule = await use_case.execute(calendar_id="demo-calendar")

    click.echo(
        f"Created schedule with {len(schedule.time_blocks)} time blocks"
    )
    click.echo()

    # 4. Display the results
    click.echo("Triage Analysis Results:")
    click.echo("-" * 30)
    for i, block in enumerate(schedule.time_blocks, 1):
        click.echo(f"{i}. {block.title}")
        click.echo(
            f"   Time: {block.start_time.strftime('%H:%M')} - "
            f"{block.end_time.strftime('%H:%M')}"
        )
        decision_text = (
            block.suggested_decision.value.upper()
            if block.suggested_decision
            else "NONE"
        )
        click.echo(f"   Decision: {decision_text}")
        click.echo(f"   Reason: {block.decision_reason}")
        click.echo()

    # 5. Write to file using the centralized org generator
    output_file = Path(output_path)
    title = "Calendar Triage Demo Output (Mock)"
    section_title = "Triage Decisions"
    org_content = generate_org_content(schedule, title, section_title)

    with open(str(output_file), "w") as f:
        f.write(org_content)

    click.echo(f"Org-mode output written to: {output_file.absolute()}")
    click.echo()
    click.echo("Demo completed successfully!")
    click.echo()
    click.echo("To view the results:")
    click.echo(f"   cat {output_file}")
    click.echo("   # or open in Emacs for full org-mode experience")


@click.command()
@click.option(
    "--output-path",
    default="demo_output.org",
    help="Path to write the org-mode output file.",
    type=click.Path(),
)
def main(output_path: str) -> None:
    """Run the calendar triage demo using mock data."""
    asyncio.run(_main(output_path))


if __name__ == "__main__":
    main()

"""
Tests for CLI programs.

These tests focus on CLI-specific concerns like argument parsing, error
handling, user feedback, and file operations. They mock use cases following
the testing pyramid principles from systemPatterns.org.
"""

from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, patch, mock_open

from click.testing import CliRunner

from cal.cli.mock_calendar import main as mock_main
from cal.cli.google_calendar import main as google_main
from cal.tests.factories import minimal_schedule, minimal_time_block
from cal.domain import ExecutiveDecision


class TestMockCalendarCLI:
    """Tests for the mock calendar CLI program."""

    def test_successful_execution_default_output(self) -> None:
        """Test CLI argument parsing, output formatting, and file
        operations."""
        runner = CliRunner()

        # Create simple test data - CLI doesn't care about business logic
        # details
        mock_schedule = minimal_schedule(
            schedule_id="test-schedule-123",
            time_blocks=[
                minimal_time_block(
                    time_block_id="block-1",
                    title="Test Meeting",
                    suggested_decision=ExecutiveDecision.ATTEND,
                    decision_reason="Important meeting",
                )
            ],
        )

        # Mock the use case as a black box - CLI shouldn't know about
        # repositories
        with patch(
            "cal.cli.mock_calendar.CreateScheduleUseCase"
        ) as mock_use_case_class:
            mock_use_case = AsyncMock()
            mock_use_case.execute.return_value = mock_schedule
            mock_use_case_class.return_value = mock_use_case

            # Mock file operations - this is CLI responsibility
            with patch("builtins.open", mock_open()) as mock_file:
                # Mock template rendering - this is presentation layer
                # responsibility
                with patch(
                    "cal.cli.mock_calendar.generate_org_content"
                ) as mock_generate:
                    mock_generate.return_value = "* Mock Org Content\n"

                    result = runner.invoke(mock_main)

            # Test CLI-specific behavior
            assert result.exit_code == 0
            assert "Calendar Triage Demo (Mock Data)" in result.output
            assert "Demo completed successfully!" in result.output

            # Verify CLI called use case with correct arguments
            mock_use_case.execute.assert_called_once_with(
                calendar_id="demo-calendar"
            )

            # Verify CLI handled file output correctly
            mock_file.assert_called_once_with("demo_output.org", "w")

            # Verify CLI used org generator correctly
            mock_generate.assert_called_once()

    def test_successful_execution_custom_output_path(
        self, tmp_path: Any
    ) -> None:
        """Test CLI argument parsing with custom output path."""
        runner = CliRunner()

        mock_schedule = minimal_schedule(schedule_id="test-schedule-456")

        with patch(
            "cal.cli.mock_calendar.CreateScheduleUseCase"
        ) as mock_use_case_class:
            mock_use_case = AsyncMock()
            mock_use_case.execute.return_value = mock_schedule
            mock_use_case_class.return_value = mock_use_case

            with patch("builtins.open", mock_open()) as mock_file:
                with patch("cal.cli.mock_calendar.generate_org_content"):
                    custom_path = str(tmp_path / "custom_output.org")
                    result = runner.invoke(
                        mock_main, ["--output-path", custom_path]
                    )

                    assert result.exit_code == 0
                    assert "Demo completed successfully!" in result.output

                    # Verify CLI parsed custom path argument correctly
                    mock_file.assert_called_once_with(custom_path, "w")

    def test_empty_schedule_display(self) -> None:
        """Test CLI output formatting for empty schedule."""
        runner = CliRunner()

        # Empty schedule
        mock_schedule = minimal_schedule(schedule_id="empty-schedule")

        with patch(
            "cal.cli.mock_calendar.CreateScheduleUseCase"
        ) as mock_use_case_class:
            mock_use_case = AsyncMock()
            mock_use_case.execute.return_value = mock_schedule
            mock_use_case_class.return_value = mock_use_case

            with patch("builtins.open", mock_open()):
                with patch("cal.cli.mock_calendar.generate_org_content"):
                    result = runner.invoke(mock_main)

                    assert result.exit_code == 0
                    # Test CLI displays count correctly
                    assert (
                        "Created schedule with 0 time blocks" in result.output
                    )

    def test_use_case_exception_handling(self) -> None:
        """Test CLI error handling when use case fails."""
        runner = CliRunner()

        with patch(
            "cal.cli.mock_calendar.CreateScheduleUseCase"
        ) as mock_use_case_class:
            mock_use_case = AsyncMock()
            mock_use_case.execute.side_effect = Exception("Use case failed")
            mock_use_case_class.return_value = mock_use_case

            result = runner.invoke(mock_main)

            # Test CLI error handling behavior
            # The CLI should propagate exceptions as exit code 1
            assert result.exit_code == 1


class TestGoogleCalendarCLI:
    """Tests for the Google Calendar CLI program."""

    def test_missing_credentials_error(self) -> None:
        """Test CLI error handling for missing credentials file."""
        runner = CliRunner()

        with patch("pathlib.Path.exists", return_value=False):
            result = runner.invoke(google_main)

            # Test CLI error handling and user feedback
            assert result.exit_code == 1
            assert "Error: credentials.json not found!" in result.output
            assert "Please follow the setup instructions" in result.output

    def test_successful_execution_default_params(self) -> None:
        """Test CLI argument parsing and output with default parameters."""
        runner = CliRunner()

        mock_schedule = minimal_schedule(
            schedule_id="google-schedule-123",
            time_blocks=[
                minimal_time_block(
                    time_block_id="google-block-1",
                    title="Google Meeting",
                    suggested_decision=ExecutiveDecision.ATTEND,
                    decision_reason="Important Google meeting",
                    source_calendar_event_id="google-event-123",
                )
            ],
        )

        # Mock credentials exist
        with patch("pathlib.Path.exists", return_value=True):
            # Mock the factory function to return a configured use case
            with patch(
                "cal.cli.google_calendar.create_google_calendar_use_case"
            ) as mock_factory:
                mock_use_case = AsyncMock()
                mock_use_case.execute.return_value = mock_schedule
                mock_factory.return_value = mock_use_case

                # Mock file operations - this is CLI responsibility
                with patch("builtins.open", mock_open()) as mock_file:
                    # Mock template rendering - this is presentation layer
                    # responsibility
                    with patch(
                        "cal.cli.google_calendar.generate_org_content"
                    ) as mock_generate:
                        mock_generate.return_value = "* Mock Org Content\n"

                        result = runner.invoke(google_main)

                        # Test CLI behavior
                        assert result.exit_code == 0
                        assert "Google Calendar Triage Demo" in result.output
                        assert (
                            "Google Calendar demo completed successfully!"
                            in result.output
                        )

                        # Verify CLI called factory with default calendar
                        # Note: factory now takes config_repo as second arg
                        mock_factory.assert_called_once()
                        call_args = mock_factory.call_args
                        assert call_args[0][0] == "primary"  # calendar_id
                        # Second argument should be config repo instance
                        assert hasattr(call_args[0][1], "get_collection")

                        # Verify CLI called use case with correct arguments
                        mock_use_case.execute.assert_called_once()
                        call_args = mock_use_case.execute.call_args
                        assert call_args[1]["calendar_id"] == "primary"

                        # Verify CLI used default output file
                        mock_file.assert_called_once_with(
                            "google_demo_output.org", "w"
                        )

    def test_successful_execution_custom_params(self, tmp_path: Any) -> None:
        """Test CLI argument parsing with custom parameters."""
        runner = CliRunner()

        mock_schedule = minimal_schedule(
            schedule_id="custom-schedule",
            time_blocks=[
                minimal_time_block(
                    time_block_id="custom-block-1",
                    title="Custom Meeting",
                    suggested_decision=ExecutiveDecision.ATTEND,
                    decision_reason="Important custom meeting",
                    source_calendar_event_id="custom-event-123",
                )
            ],
        )

        with patch("pathlib.Path.exists", return_value=True):
            # Mock the factory function to return a configured use case
            with patch(
                "cal.cli.google_calendar.create_google_calendar_use_case"
            ) as mock_factory:
                mock_use_case = AsyncMock()
                mock_use_case.execute.return_value = mock_schedule
                mock_factory.return_value = mock_use_case

                # Mock file operations - this is CLI responsibility
                with patch("builtins.open", mock_open()) as mock_file:
                    # Mock template rendering - this is presentation layer
                    # responsibility
                    with patch(
                        "cal.cli.google_calendar.generate_org_content"
                    ) as mock_generate:
                        mock_generate.return_value = "* Custom Org Content\n"

                        custom_output = str(tmp_path / "custom_google.org")
                        custom_calendar = "custom@example.com"

                        result = runner.invoke(
                            google_main,
                            [
                                "--output-path",
                                custom_output,
                                "--calendar-id",
                                custom_calendar,
                            ],
                        )

                        assert result.exit_code == 0

                        # Verify CLI called factory with correct calendar ID
                        # Note: factory now takes config_repo as second arg
                        mock_factory.assert_called_once()
                        call_args = mock_factory.call_args
                        assert (
                            call_args[0][0] == custom_calendar
                        )  # calendar_id
                        # Second argument should be config repo instance
                        assert hasattr(call_args[0][1], "get_collection")

                        # Verify CLI called use case with correct arguments
                        mock_use_case.execute.assert_called_once()
                        call_args = mock_use_case.execute.call_args
                        assert call_args[1]["calendar_id"] == custom_calendar

                        # Verify CLI wrote to correct file
                        mock_file.assert_called_once_with(custom_output, "w")

    def test_no_events_found_message(self) -> None:
        """Test CLI output formatting when no events are found."""
        runner = CliRunner()

        # Empty schedule
        mock_schedule = minimal_schedule(schedule_id="empty-google-schedule")

        with patch("pathlib.Path.exists", return_value=True):
            # Mock the factory function to return a configured use case
            with patch(
                "cal.cli.google_calendar.create_google_calendar_use_case"
            ) as mock_factory:
                mock_use_case = AsyncMock()
                mock_use_case.execute.return_value = mock_schedule
                mock_factory.return_value = mock_use_case

                # Mock file operations
                with patch("builtins.open", mock_open()):
                    with patch(
                        "cal.cli.google_calendar.generate_org_content"
                    ):
                        result = runner.invoke(google_main)

                        assert result.exit_code == 0
                        # Test CLI displays appropriate user feedback
                        assert (
                            "No calendar events found in the specified "
                            "time range." in result.output
                        )
                        assert (
                            "Try scheduling some events in your Google "
                            "Calendar" in result.output
                        )

    def test_google_api_exception_handling(self) -> None:
        """Test CLI error handling for Google API failures."""
        runner = CliRunner()

        with patch("pathlib.Path.exists", return_value=True):
            # Mock factory to raise an exception - CLI should handle any
            # exception
            with patch(
                "cal.cli.google_calendar.create_google_calendar_use_case",
                side_effect=Exception("Google API error"),
            ):

                result = runner.invoke(google_main)

                # Test CLI error handling and user feedback
                assert result.exit_code == 1
                assert "Demo failed: Google API error" in result.output
                assert "Common issues:" in result.output
                assert (
                    "- Missing or invalid credentials.json" in result.output
                )

    def test_use_case_exception_in_google_cli(self) -> None:
        """Test CLI error handling when use case fails."""
        runner = CliRunner()

        with patch("pathlib.Path.exists", return_value=True):
            # Mock factory to return a use case that fails
            with patch(
                "cal.cli.google_calendar.create_google_calendar_use_case"
            ) as mock_factory:
                mock_use_case = AsyncMock()
                mock_use_case.execute.side_effect = Exception(
                    "Use case failed"
                )
                mock_factory.return_value = mock_use_case

                result = runner.invoke(google_main)

                # Test CLI error handling
                assert result.exit_code == 1
                assert "Demo failed: Use case failed" in result.output

    def test_triage_results_display(self) -> None:
        """Test CLI output formatting for triage analysis results."""
        runner = CliRunner()

        # Schedule with multiple time blocks for display testing
        mock_schedule = minimal_schedule(
            schedule_id="display-test-schedule",
            time_blocks=[
                minimal_time_block(
                    time_block_id="block-1",
                    title="Important Meeting",
                    start_time=datetime(
                        2024, 1, 1, 9, 0, tzinfo=timezone.utc
                    ),
                    end_time=datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc),
                    suggested_decision=ExecutiveDecision.ATTEND,
                    decision_reason="Critical stakeholder meeting",
                    source_calendar_event_id="event-123",
                ),
                minimal_time_block(
                    time_block_id="block-2",
                    title="Optional Training",
                    start_time=datetime(
                        2024, 1, 1, 14, 0, tzinfo=timezone.utc
                    ),
                    end_time=datetime(2024, 1, 1, 15, 0, tzinfo=timezone.utc),
                    suggested_decision=ExecutiveDecision.SKIP,
                    decision_reason=(
                        "Optional session, can review materials later"
                    ),
                    source_calendar_event_id="event-456",
                ),
            ],
        )

        with patch("pathlib.Path.exists", return_value=True):
            # Mock the factory function to return a configured use case
            with patch(
                "cal.cli.google_calendar.create_google_calendar_use_case"
            ) as mock_factory:
                mock_use_case = AsyncMock()
                mock_use_case.execute.return_value = mock_schedule
                mock_factory.return_value = mock_use_case

                # Mock file operations
                with patch("builtins.open", mock_open()):
                    with patch(
                        "cal.cli.google_calendar.generate_org_content"
                    ):
                        result = runner.invoke(google_main)

                        assert result.exit_code == 0

                        # Test CLI displays triage results correctly
                        assert "1. Important Meeting" in result.output
                        assert (
                            "Time: 2024-01-01 09:00 - 10:00" in result.output
                        )
                        assert "Decision: ATTEND" in result.output
                        assert (
                            "Reason: Critical stakeholder meeting"
                            in result.output
                        )
                        assert "Google Event ID: event-123" in result.output

                        assert "2. Optional Training" in result.output
                        assert (
                            "Time: 2024-01-01 14:00 - 15:00" in result.output
                        )
                        assert "Decision: SKIP" in result.output
                        assert (
                            "Reason: Optional session, can review materials "
                            "later" in result.output
                        )
                        assert "Google Event ID: event-456" in result.output

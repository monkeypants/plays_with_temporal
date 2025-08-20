"""
Tests for calendar workflows.

These tests focus on verifying the orchestration of activities by workflows,
not on testing business logic which should be tested in use case tests.
"""

import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone

from cal.workflows import PublishScheduleWorkflow
from cal.tests.factories import minimal_schedule


class TestPublishScheduleWorkflow:
    """Tests for the PublishScheduleWorkflow.

    These tests verify that the workflow correctly orchestrates activities
    without testing the business logic of those activities.
    """

    @pytest.mark.asyncio
    async def test_workflow_orchestrates_schedule_creation_and_file_writing(
        self, tmp_path
    ):
        """Test that the workflow calls the expected activities in the right
        order when using a mock calendar source."""

        # Create a mock schedule that would be returned by the use case
        mock_schedule = minimal_schedule(schedule_id="test-schedule-123")

        # Mock the workflow's activity execution
        with patch(
            "temporalio.workflow.execute_activity"
        ) as mock_execute_activity:
            # Configure the mock to return True for the file writing activity
            mock_execute_activity.return_value = True

            # Mock the use case execution
            with patch(
                "cal.usecase.CreateScheduleUseCase"
            ) as mock_use_case_class:
                mock_use_case_instance = AsyncMock()
                mock_use_case_instance.execute.return_value = mock_schedule
                mock_use_case_class.return_value = mock_use_case_instance

                # Mock the specific Temporal proxy classes expected by the
                # workflow
                with patch(
                    "cal.repos.temporal.proxies.schedule.WorkflowScheduleRepositoryProxy"
                ), patch(
                    "cal.repos.temporal.proxies.time_block_classifier.WorkflowTimeBlockClassifierRepositoryProxy"
                ), patch(
                    "cal.repos.temporal.proxies.calendar.WorkflowMockCalendarRepositoryProxy"
                ), patch(
                    "cal.repos.temporal.proxies.calendar_config.WorkflowCalendarConfigurationRepositoryProxy"
                ), patch(
                    "util.repos.temporal.proxies.file_storage.WorkflowFileStorageRepositoryProxy"
                ):
                    # Create workflow instance and run it, specifying mock
                    # source type
                    workflow = PublishScheduleWorkflow()
                    test_output_path = str(tmp_path / "test.org")
                    result = await workflow.run(
                        calendar_id="test-calendar",
                        output_path=test_output_path,
                        start_date=None,
                        end_date=None,
                        calendar_source_type="mock",  # Explicitly use mock
                        # for this test
                    )

                    # Verify the workflow completed successfully
                    assert result is True

                    # Verify the use case was called with correct parameters
                    mock_use_case_instance.execute.assert_called_once_with(
                        calendar_id="test-calendar",
                        start_date=None,
                        end_date=None,
                    )

                    # Verify the file writing activity was called
                    from temporalio import workflow as temporal_workflow

                    mock_execute_activity.assert_called_once_with(
                        "cal.publish_schedule.org_file_writer.local.write_schedule_to_org_file",
                        [
                            "test-schedule-123",
                            test_output_path,
                        ],
                        start_to_close_timeout=temporal_workflow.timedelta(
                            seconds=30
                        ),
                    )

    @pytest.mark.asyncio
    async def test_workflow_handles_different_calendar_parameters(self):
        """Test that the workflow passes through different parameter
        combinations and uses the correct calendar source type."""

        mock_schedule = minimal_schedule(schedule_id="test-schedule-456")

        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2024, 1, 2, tzinfo=timezone.utc)

        with patch(
            "temporalio.workflow.execute_activity"
        ) as mock_execute_activity:
            mock_execute_activity.return_value = True

            with patch(
                "cal.usecase.CreateScheduleUseCase"
            ) as mock_use_case_class:
                mock_use_case_instance = AsyncMock()
                mock_use_case_instance.execute.return_value = mock_schedule
                mock_use_case_class.return_value = mock_use_case_instance

                # Mock the specific Temporal proxy classes expected by the
                # workflow
                with patch(
                    "cal.repos.temporal.proxies.schedule.WorkflowScheduleRepositoryProxy"
                ), patch(
                    "cal.repos.temporal.proxies.time_block_classifier.WorkflowTimeBlockClassifierRepositoryProxy"
                ), patch(
                    "cal.repos.temporal.proxies.google_calendar.WorkflowGoogleCalendarRepositoryProxy"
                ), patch(
                    "cal.repos.temporal.proxies.calendar_config.WorkflowCalendarConfigurationRepositoryProxy"
                ), patch(
                    "util.repos.temporal.proxies.file_storage.WorkflowFileStorageRepositoryProxy"
                ):
                    workflow = PublishScheduleWorkflow()
                    result = await workflow.run(
                        calendar_id="custom-calendar",
                        output_path="/custom/path.org",
                        start_date=start_date,
                        end_date=end_date,
                        calendar_source_type="google",
                        # Explicitly use google for this test
                    )

                    assert result is True

                    # Verify the use case was called with the custom
                    # parameters.
                    # The workflow passed an instance of
                    # WorkflowGoogleCalendarRepositoryProxy as calendar_repo,
                    # but the execute method receives only the calendar_id
                    # string as before.
                    mock_use_case_instance.execute.assert_called_once_with(
                        calendar_id="custom-calendar",
                        start_date=start_date,
                        end_date=end_date,
                    )

    @pytest.mark.asyncio
    async def test_workflow_handles_unsupported_calendar_source_type(
        self, tmp_path
    ):
        """Test that the workflow gracefully handles an unsupported
        calendar_source_type."""

        with patch(
            "temporalio.workflow.execute_activity"
        ) as mock_execute_activity:
            workflow = PublishScheduleWorkflow()
            test_output_path = str(tmp_path / "unsupported.org")
            result = await workflow.run(
                calendar_id="unsupported-calendar",
                output_path=test_output_path,
                calendar_source_type="unsupported",  # type: ignore[arg-type]
            )

            assert result is False
            # No activities should be executed
            mock_execute_activity.assert_not_called()

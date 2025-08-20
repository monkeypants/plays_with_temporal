import pytest
import asyncio
from typing import Any, Dict, List, Generator, AsyncGenerator
from temporalio.testing import WorkflowEnvironment
from unittest.mock import patch, AsyncMock


@pytest.fixture(scope="session")
def event_loop() -> asyncio.AbstractEventLoop:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def temporal_env() -> AsyncGenerator[WorkflowEnvironment, None]:
    """Provide a Temporal test environment for integration tests."""
    async with await WorkflowEnvironment.start_time_skipping() as env:
        yield env


@pytest.fixture
async def temporal_client(temporal_env: WorkflowEnvironment) -> Any:
    """Provide a Temporal client connected to the test environment."""
    return temporal_env.client


@pytest.fixture
def mock_workflow_activities() -> Dict[str, Any]:
    """Provide utilities for mocking workflow activities in unit tests."""

    def create_activity_mock(
        activity_name: str, return_value: Any = None
    ) -> AsyncMock:
        """Create a mock for a specific activity."""
        mock = AsyncMock(return_value=return_value)
        mock._activity_name = activity_name
        return mock

    def patch_execute_activity(activity_responses: List[Any]) -> Any:
        """
        Patch workflow.execute_activity with a sequence of responses.

        Args:
            activity_responses: List of return values for activities in call
                order
        """
        return patch(
            "temporalio.workflow.execute_activity",
            side_effect=activity_responses,
        )

    return {
        "create_activity_mock": create_activity_mock,
        "patch_execute_activity": patch_execute_activity,
    }

"""
System Initialization Service for the julee_example CEAP system.

This module provides the service layer for system initialization,
orchestrating the use cases needed to ensure required system data
exists on application startup.

The service acts as a facade between the API layer and domain use cases,
handling application-level concerns while delegating business logic
to the appropriate use cases.
"""

import logging
from typing import Dict, Any

from julee_example.domain.use_cases.initialize_system_data import (
    InitializeSystemDataUseCase,
)

logger = logging.getLogger(__name__)


class SystemInitializationService:
    """
    Service for orchestrating system initialization on application startup.

    This service coordinates the execution of use cases needed to initialize
    required system data, such as knowledge service configurations and
    other essential data needed for the application to function properly.

    The service provides error handling, logging, and coordination between
    multiple initialization tasks while keeping the business logic in
    the domain use cases.
    """

    def __init__(
        self,
        initialize_system_data_use_case: InitializeSystemDataUseCase,
    ) -> None:
        """Initialize the service with required use cases.

        Args:
            initialize_system_data_use_case: Use case for initializing
                system data
        """
        self.initialize_system_data_use_case = initialize_system_data_use_case
        self.logger = logging.getLogger("SystemInitializationService")

    async def initialize(self) -> Dict[str, Any]:
        """
        Initialize all required system data and configuration.

        This method orchestrates all initialization tasks needed for the
        application to start successfully. It coordinates multiple use cases
        and provides comprehensive error handling and logging.

        Returns:
            Dict containing initialization results and metadata

        Raises:
            Exception: If any critical initialization step fails
        """
        self.logger.info("Starting system initialization")

        initialization_results: Dict[str, Any] = {
            "status": "in_progress",
            "tasks_completed": [],
            "tasks_failed": [],
            "metadata": {},
        }

        try:
            # Execute system data initialization
            await self._execute_system_data_initialization(
                initialization_results
            )

            # Future initialization tasks can be added here
            # await self._execute_additional_initialization_tasks(
            #     initialization_results
            # )

            # Mark initialization as successful
            initialization_results["status"] = "completed"

            self.logger.info(
                "System initialization completed successfully",
                extra={
                    "tasks_completed": initialization_results[
                        "tasks_completed"
                    ],
                    "total_tasks": len(
                        initialization_results["tasks_completed"]
                    ),
                },
            )

            return initialization_results

        except Exception as e:
            initialization_results["status"] = "failed"
            initialization_results["error"] = {
                "type": type(e).__name__,
                "message": str(e),
            }

            self.logger.error(
                "System initialization failed",
                exc_info=True,
                extra={
                    "tasks_completed": initialization_results[
                        "tasks_completed"
                    ],
                    "tasks_failed": initialization_results["tasks_failed"],
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
            )

            raise

    async def _execute_system_data_initialization(
        self, results: Dict[str, Any]
    ) -> None:
        """
        Execute system data initialization use case.

        Args:
            results: Dictionary to track initialization results

        Raises:
            Exception: If system data initialization fails
        """
        task_name = "system_data_initialization"

        try:
            self.logger.debug("Starting task: %s", task_name)

            await self.initialize_system_data_use_case.execute()

            results["tasks_completed"].append(task_name)
            results["metadata"][task_name] = {
                "status": "completed",
                "description": "System data initialization completed",
            }

            self.logger.debug("Completed task: %s", task_name)

        except Exception as e:
            results["tasks_failed"].append(
                {
                    "task": task_name,
                    "error": str(e),
                    "error_type": type(e).__name__,
                }
            )

            self.logger.error(
                f"Failed task: {task_name}",
                exc_info=True,
                extra={
                    "task_name": task_name,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
            )

            raise

    async def get_initialization_status(self) -> Dict[str, Any]:
        """
        Get the current initialization status.

        This method can be used to check if the system has been properly
        initialized, useful for health checks or debugging.

        Returns:
            Dict containing current initialization status and metadata
        """
        # This is a simple implementation - in a more complex system,
        # you might want to persist initialization status
        return {
            "system_initialized": True,
            "last_initialization": None,  # Could track timestamps
            "required_components": [
                "knowledge_service_configs",
            ],
            "status": "ready",
        }

    async def reinitialize(self) -> Dict[str, Any]:
        """
        Reinitialize system data.

        This method can be used to force reinitalization of system data,
        useful for development, testing, or recovery scenarios.

        Returns:
            Dict containing reinitialization results

        Raises:
            Exception: If reinitialization fails
        """
        self.logger.info("Starting system reinitialization")

        try:
            results = await self.initialize()
            results["reinitialization"] = True

            self.logger.info("System reinitialization completed successfully")
            return results

        except Exception as e:
            self.logger.error(
                "System reinitialization failed",
                exc_info=True,
                extra={
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
            )
            raise

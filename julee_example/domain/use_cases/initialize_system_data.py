"""
Initialize System Data Use Case for the julee_example CEAP system.

This module provides the use case for initializing required system data
on application startup, such as knowledge service configurations that
are needed for the system to function properly.

The use case follows clean architecture principles:
- Contains business logic for what system data is required
- Uses repository interfaces for persistence
- Is idempotent and safe to run multiple times
- Can be tested independently of infrastructure concerns
"""

import logging
import yaml
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any

from julee_example.domain.models.knowledge_service_config import (
    KnowledgeServiceConfig,
    ServiceApi,
)
from julee_example.domain.repositories.knowledge_service_config import (
    KnowledgeServiceConfigRepository,
)

logger = logging.getLogger(__name__)


class InitializeSystemDataUseCase:
    """
    Use case for initializing required system data on application startup.

    This use case ensures that essential configuration data exists in the
    system, such as knowledge service configurations that are required
    for the application to function properly.

    All operations are idempotent - running this multiple times will not
    create duplicate data or cause errors.
    """

    def __init__(
        self,
        knowledge_service_config_repository: KnowledgeServiceConfigRepository,
    ) -> None:
        """Initialize the use case with required repositories.

        Args:
            knowledge_service_config_repository: Repository for knowledge
                service configurations
        """
        self.config_repo = knowledge_service_config_repository
        self.logger = logging.getLogger("InitializeSystemDataUseCase")

    async def execute(self) -> None:
        """
        Execute system data initialization.

        This method orchestrates the creation of all required system data.
        It's idempotent and can be safely called multiple times.

        Raises:
            Exception: If any critical system data cannot be initialized
        """
        self.logger.info("Starting system data initialization")

        try:
            await self._ensure_knowledge_service_configs_exist()

            self.logger.info(
                "System data initialization completed successfully"
            )

        except Exception as e:
            self.logger.error(
                "Failed to initialize system data",
                exc_info=True,
                extra={
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
            )
            raise

    async def _ensure_knowledge_service_configs_exist(self) -> None:
        """
        Ensure all knowledge service configurations from fixture exist.

        This loads configurations from the YAML fixture file and creates
        any that don't already exist in the repository. The operation is
        idempotent - existing configurations are not modified.
        """
        self.logger.info(
            "Loading knowledge service configurations from fixture"
        )

        try:
            # Load configurations from YAML fixture
            fixture_configs = self._load_fixture_configurations()

            created_count = 0
            skipped_count = 0

            for config_data in fixture_configs:
                config_id = config_data["knowledge_service_id"]

                # Check if configuration already exists
                existing_config = await self.config_repo.get(config_id)
                if existing_config:
                    self.logger.debug(
                        "Knowledge service config already exists, skipping",
                        extra={
                            "config_id": config_id,
                            "config_name": existing_config.name,
                        },
                    )
                    skipped_count += 1
                    continue

                # Create new configuration from fixture data
                config = self._create_config_from_fixture_data(config_data)
                await self.config_repo.save(config)

                self.logger.info(
                    "Knowledge service config created successfully",
                    extra={
                        "config_id": config.knowledge_service_id,
                        "config_name": config.name,
                        "service_api": config.service_api.value,
                    },
                )
                created_count += 1

            self.logger.info(
                "Knowledge service configurations processed",
                extra={
                    "created_count": created_count,
                    "skipped_count": skipped_count,
                    "total_count": len(fixture_configs),
                },
            )

        except Exception as e:
            self.logger.error(
                "Failed to ensure knowledge service configurations exist",
                exc_info=True,
                extra={
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
            )
            raise

    def _load_fixture_configurations(self) -> List[Dict[str, Any]]:
        """
        Load knowledge service configurations from the YAML fixture file.

        Returns:
            List of configuration dictionaries from the fixture file

        Raises:
            FileNotFoundError: If the fixture file doesn't exist
            yaml.YAMLError: If the fixture file is invalid YAML
            KeyError: If required fields are missing from the fixture
        """
        # Get the fixture file path relative to this module
        current_file = Path(__file__)
        julee_example_dir = current_file.parent.parent.parent
        fixture_path = julee_example_dir / "knowledge_services_fixture.yaml"

        self.logger.debug(
            "Loading fixture file",
            extra={"fixture_path": str(fixture_path)},
        )

        if not fixture_path.exists():
            raise FileNotFoundError(
                f"Knowledge services fixture file not found: {fixture_path}"
            )

        try:
            with open(fixture_path, "r", encoding="utf-8") as f:
                fixture_data = yaml.safe_load(f)

            if not fixture_data or "knowledge_services" not in fixture_data:
                raise KeyError(
                    "Fixture file must contain 'knowledge_services' key"
                )

            configs = fixture_data["knowledge_services"]
            if not isinstance(configs, list):
                raise ValueError(
                    "'knowledge_services' must be a list of configurations"
                )

            self.logger.debug(
                "Loaded fixture configurations",
                extra={"count": len(configs)},
            )

            return configs

        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"Invalid YAML in fixture file: {e}")

    def _create_config_from_fixture_data(
        self, config_data: Dict[str, Any]
    ) -> KnowledgeServiceConfig:
        """
        Create a KnowledgeServiceConfig from fixture data.

        Args:
            config_data: Dictionary containing configuration data from fixture

        Returns:
            KnowledgeServiceConfig instance

        Raises:
            KeyError: If required fields are missing
            ValueError: If field values are invalid
        """
        required_fields = [
            "knowledge_service_id",
            "name",
            "description",
            "service_api",
        ]

        # Validate required fields
        for field in required_fields:
            if field not in config_data:
                raise KeyError(
                    f"Required field '{field}' missing from config"
                )

        # Parse service API enum
        try:
            service_api = ServiceApi(config_data["service_api"])
        except ValueError:
            raise ValueError(
                f"Invalid service_api '{config_data['service_api']}'. "
                f"Must be one of: {[api.value for api in ServiceApi]}"
            )

        # Create configuration
        config = KnowledgeServiceConfig(
            knowledge_service_id=config_data["knowledge_service_id"],
            name=config_data["name"],
            description=config_data["description"],
            service_api=service_api,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        self.logger.debug(
            "Created config from fixture data",
            extra={
                "config_id": config.knowledge_service_id,
                "config_name": config.name,
            },
        )

        return config

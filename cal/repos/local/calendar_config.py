"""
Local YAML-based implementation of CalendarConfigurationRepository.
"""

import logging
import yaml
from pathlib import Path
from typing import List, Optional

from cal.domain import CalendarCollection, CalendarSource
from cal.repositories import CalendarConfigurationRepository

logger = logging.getLogger(__name__)


class LocalCalendarConfigurationRepository(CalendarConfigurationRepository):
    """
    Local YAML file implementation of CalendarConfigurationRepository.

    Loads calendar configuration from a YAML file, typically stored in
    the user's home directory or a specified path.
    """

    def __init__(
        self, config_path: str = "~/.config/calendar-assistant/calendars.yaml"
    ):
        """
        Initialize with path to configuration file.

        Args:
            config_path: Path to YAML configuration file, supports ~ expansion
        """
        self.config_path = Path(config_path).expanduser()
        logger.debug(
            f"Initialized LocalCalendarConfigurationRepository with path: "
            f"{self.config_path}"
        )

    async def get_collection(
        self, collection_id: str
    ) -> Optional[CalendarCollection]:
        """Retrieve a calendar collection by its ID from YAML file."""
        collections = await self.list_collections()

        for collection in collections:
            if collection.collection_id == collection_id:
                logger.debug(f"Found collection: {collection_id}")
                return collection

        logger.debug(f"Collection not found: {collection_id}")
        return None

    async def list_collections(self) -> List[CalendarCollection]:
        """List all available calendar collections from YAML file."""
        if not self.config_path.exists():
            logger.warning(
                f"Configuration file not found: {self.config_path}"
            )
            return []

        try:
            with open(self.config_path, "r") as f:
                config_data = yaml.safe_load(f)

            if not config_data:
                logger.error(
                    f"Configuration file is empty or invalid YAML: "
                    f"{self.config_path}"
                )
                return []

            if not isinstance(config_data, dict):
                logger.error(
                    f"Configuration file must contain a YAML dictionary: "
                    f"{self.config_path}"
                )
                return []

            if "collections" not in config_data:
                logger.warning(
                    f"No 'collections' key found in configuration file: "
                    f"{self.config_path}"
                )
                return []

            if not isinstance(config_data["collections"], list):
                logger.error(
                    f"'collections' must be a list in configuration file: "
                    f"{self.config_path}"
                )
                return []

            collections = []
            for collection_data in config_data["collections"]:
                try:
                    # Parse calendar sources
                    calendar_sources = [
                        CalendarSource(**source_data)
                        for source_data in collection_data.get(
                            "calendar_sources", []
                        )
                    ]

                    # Create collection
                    collection = CalendarCollection(
                        collection_id=collection_data["collection_id"],
                        display_name=collection_data["display_name"],
                        calendar_sources=calendar_sources,
                        default_calendar_id=collection_data.get(
                            "default_calendar_id"
                        ),
                    )
                    collections.append(collection)

                except Exception as e:
                    collection_id = collection_data.get(
                        "collection_id", "unknown"
                    )
                    logger.error(
                        f"Failed to parse collection {collection_id}: {e}"
                    )
                    continue

            logger.info(
                f"Loaded {len(collections)} calendar collections from "
                f"{self.config_path}"
            )
            return collections

        except Exception as e:
            logger.error(
                f"Failed to load configuration from {self.config_path}: {e}"
            )
            return []

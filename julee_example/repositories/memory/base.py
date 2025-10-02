"""
Memory repository base classes and mixins.

This module provides common functionality for in-memory repository
implementations, reducing code duplication and ensuring consistent patterns
across all memory-based repositories in the julee_example domain.

The MemoryRepositoryMixin encapsulates common patterns like:
- Dictionary-based storage management
- Standardized logging patterns
- ID generation with consistent prefixes
- Timestamp management (created_at, updated_at)
- Generic CRUD operations with proper error handling

Classes using this mixin must provide:
- self.storage_dict: Dict[str, T] for entity storage
- self.entity_name: str for logging and ID generation
- self.logger: logging.Logger instance
"""

import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, TypeVar, Generic, List
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class MemoryRepositoryMixin(Generic[T]):
    """
    Mixin that provides common repository patterns for memory implementations.

    This mixin encapsulates common functionality used across all memory
    repository implementations, including:
    - Dictionary-based entity storage and retrieval
    - Standardized logging patterns with consistent messaging
    - ID generation with configurable prefixes
    - Timestamp management (created_at if None, always updated_at)
    - Generic error handling patterns

    Classes using this mixin must provide:
    - self.storage_dict: Dict[str, T] instance for entity storage
    - self.entity_name: str for logging and ID generation prefixes
    - self.logger: logging.Logger instance (typically set in __init__)
    """

    # Type annotations for attributes that implementing classes must provide
    storage_dict: Dict[str, T]
    entity_name: str
    logger: Any  # logging.Logger, but avoiding import

    def get_entity(self, entity_id: str) -> Optional[T]:
        """Get an entity from memory storage with standardized logging.

        Args:
            entity_id: Unique entity identifier

        Returns:
            Entity if found, None otherwise
        """
        self.logger.debug(
            f"Memory{self.entity_name}Repository: Attempting to retrieve "
            f"{self.entity_name.lower()}",
            extra={f"{self.entity_name.lower()}_id": entity_id},
        )

        entity = self.storage_dict.get(entity_id)
        if entity is None:
            self.logger.debug(
                f"Memory{self.entity_name}Repository: {self.entity_name} "
                f"not found",
                extra={f"{self.entity_name.lower()}_id": entity_id},
            )
            return None

        # Log success with entity-specific details
        extra_data = {f"{self.entity_name.lower()}_id": entity_id}
        self._add_entity_specific_log_data(entity, extra_data)

        self.logger.info(
            f"Memory{self.entity_name}Repository: {self.entity_name} "
            f"retrieved successfully",
            extra=extra_data,
        )

        return entity

    def get_many_entities(
        self, entity_ids: List[str]
    ) -> Dict[str, Optional[T]]:
        """Get multiple entities from memory storage with standardized
        logging.

        Args:
            entity_ids: List of unique entity identifiers

        Returns:
            Dict mapping entity_id to entity (or None if not found)
        """
        self.logger.debug(
            f"Memory{self.entity_name}Repository: Attempting to retrieve "
            f"multiple {self.entity_name.lower()}s",
            extra={
                f"{self.entity_name.lower()}_ids": entity_ids,
                "count": len(entity_ids),
            },
        )

        result: Dict[str, Optional[T]] = {}
        found_count = 0

        for entity_id in entity_ids:
            entity = self.storage_dict.get(entity_id)
            result[entity_id] = entity
            if entity is not None:
                found_count += 1

        self.logger.info(
            f"Memory{self.entity_name}Repository: Retrieved "
            f"{found_count}/{len(entity_ids)} {self.entity_name.lower()}s",
            extra={
                f"{self.entity_name.lower()}_ids": entity_ids,
                "requested_count": len(entity_ids),
                "found_count": found_count,
                "missing_count": len(entity_ids) - found_count,
            },
        )

        return result

    def save_entity(self, entity: T, entity_id_field: str) -> None:
        """Save an entity to memory storage with timestamp management.

        Args:
            entity: Entity to save
            entity_id_field: Name of the ID field on the entity
        """
        entity_id = getattr(entity, entity_id_field)

        # Log save attempt with entity-specific details
        log_extra = {f"{self.entity_name.lower()}_id": entity_id}
        self._add_entity_specific_log_data(entity, log_extra)

        self.logger.debug(
            f"Memory{self.entity_name}Repository: Saving "
            f"{self.entity_name.lower()}",
            extra=log_extra,
        )

        # Update timestamps
        self.update_timestamps(entity)

        # Store the entity (idempotent - will overwrite if exists)
        self.storage_dict[entity_id] = entity

        # Log success with final state
        success_extra = {f"{self.entity_name.lower()}_id": entity_id}
        self._add_entity_specific_log_data(entity, success_extra)

        self.logger.info(
            f"Memory{self.entity_name}Repository: {self.entity_name} "
            f"saved successfully",
            extra=success_extra,
        )

    def generate_entity_id(self, prefix: Optional[str] = None) -> str:
        """Generate a unique entity ID with consistent format.

        Args:
            prefix: Optional prefix for the ID. If None, uses entity_name

        Returns:
            Unique entity ID string in format "{prefix}-{uuid}"
        """
        if prefix is None:
            prefix = self.entity_name.lower()

        entity_id = f"{prefix}-{uuid.uuid4()}"

        self.logger.debug(
            f"Memory{self.entity_name}Repository: Generated "
            f"{self.entity_name.lower()} ID",
            extra={f"{self.entity_name.lower()}_id": entity_id},
        )

        return entity_id

    def update_timestamps(self, entity: T) -> None:
        """Update timestamps on an entity (created_at if None, always
        updated_at).

        Args:
            entity: Pydantic model with created_at and updated_at fields
        """
        now = datetime.now(timezone.utc)

        # Set created_at if it's None (for new objects)
        if (
            hasattr(entity, "created_at")
            and getattr(entity, "created_at", None) is None
        ):
            setattr(entity, "created_at", now)

        # Always update updated_at
        if hasattr(entity, "updated_at"):
            setattr(entity, "updated_at", now)

    def _add_entity_specific_log_data(
        self, entity: T, log_data: Dict[str, Any]
    ) -> None:
        """Add entity-specific data to log entries for richer logging.

        This method can be overridden by specific repository implementations
        to add domain-specific logging information.

        Args:
            entity: The entity being logged
            log_data: Dictionary to add logging data to
        """
        # Default implementation adds basic model info
        if hasattr(entity, "status"):
            status = getattr(entity, "status")
            log_data["status"] = (
                status.value if hasattr(status, "value") else str(status)
            )

        if hasattr(entity, "updated_at"):
            updated_at = getattr(entity, "updated_at")
            if updated_at:
                log_data["updated_at"] = updated_at.isoformat()

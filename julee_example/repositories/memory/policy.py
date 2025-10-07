"""
Memory implementation of PolicyRepository.

This module provides an in-memory implementation of the PolicyRepository
protocol that follows the Clean Architecture patterns defined in the
Fun-Police Framework. It handles policy storage in memory dictionaries,
ensuring idempotency and proper error handling.

The implementation uses Python dictionaries to store policy data, making it
ideal for testing scenarios where external dependencies should be avoided.
All operations are still async to maintain interface compatibility.
"""

import logging
from typing import Optional, Dict, Any, List

from julee_example.domain.models.policy import Policy
from julee_example.domain.repositories.policy import PolicyRepository
from .base import MemoryRepositoryMixin

logger = logging.getLogger(__name__)


class MemoryPolicyRepository(PolicyRepository, MemoryRepositoryMixin[Policy]):
    """
    Memory implementation of PolicyRepository using Python dictionaries.

    This implementation stores policy data in memory using a dictionary
    keyed by policy_id. This provides a lightweight, dependency-free
    option for testing.
    """

    def __init__(self) -> None:
        """Initialize repository with empty in-memory storage."""
        self.logger = logger
        self.entity_name = "Policy"
        self.storage_dict: Dict[str, Policy] = {}

        logger.debug("Initializing MemoryPolicyRepository")

    async def get(self, policy_id: str) -> Optional[Policy]:
        """Retrieve a policy by ID.

        Args:
            policy_id: Unique policy identifier

        Returns:
            Policy if found, None otherwise
        """
        return self.get_entity(policy_id)

    async def save(self, policy: Policy) -> None:
        """Save a policy.

        Args:
            policy: Complete Policy to save
        """
        self.save_entity(policy, "policy_id")

    async def generate_id(self) -> str:
        """Generate a unique policy identifier.

        Returns:
            Unique policy ID string
        """
        return self.generate_entity_id("policy")

    async def get_many(
        self, policy_ids: List[str]
    ) -> Dict[str, Optional[Policy]]:
        """Retrieve multiple policies by ID.

        Args:
            policy_ids: List of unique policy identifiers

        Returns:
            Dict mapping policy_id to Policy (or None if not found)
        """
        return self.get_many_entities(policy_ids)

    def _add_entity_specific_log_data(
        self, entity: Policy, log_data: Dict[str, Any]
    ) -> None:
        """Add policy-specific data to log entries."""
        super()._add_entity_specific_log_data(entity, log_data)
        log_data["title"] = entity.title
        log_data["validation_scores_count"] = len(entity.validation_scores)
        log_data["has_transformations"] = entity.has_transformations
        log_data["is_validation_only"] = entity.is_validation_only

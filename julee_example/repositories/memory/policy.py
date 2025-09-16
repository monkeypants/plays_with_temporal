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
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict

from julee_example.domain import Policy
from julee_example.repositories.policy import PolicyRepository

logger = logging.getLogger(__name__)


class MemoryPolicyRepository(PolicyRepository):
    """
    Memory implementation of PolicyRepository using Python dictionaries.

    This implementation stores policy data in memory using a dictionary
    keyed by policy_id. This provides a lightweight, dependency-free
    option for testing.
    """

    def __init__(self) -> None:
        """Initialize repository with empty in-memory storage."""
        logger.debug("Initializing MemoryPolicyRepository")

        # Storage dictionary
        self._policies: Dict[str, Policy] = {}

    async def get(self, policy_id: str) -> Optional[Policy]:
        """Retrieve a policy by ID.

        Args:
            policy_id: Unique policy identifier

        Returns:
            Policy if found, None otherwise
        """
        logger.debug(
            "MemoryPolicyRepository: Attempting to retrieve policy",
            extra={
                "policy_id": policy_id,
            },
        )

        policy = self._policies.get(policy_id)
        if policy is None:
            logger.debug(
                "MemoryPolicyRepository: Policy not found",
                extra={"policy_id": policy_id},
            )
            return None

        logger.info(
            "MemoryPolicyRepository: Policy retrieved successfully",
            extra={
                "policy_id": policy_id,
                "title": policy.title,
                "status": policy.status.value,
                "is_validation_only": policy.is_validation_only,
            },
        )

        return policy

    async def save(self, policy: Policy) -> None:
        """Save a policy.

        Args:
            policy: Complete Policy to save
        """
        logger.debug(
            "MemoryPolicyRepository: Saving policy",
            extra={
                "policy_id": policy.policy_id,
                "title": policy.title,
                "status": policy.status.value,
            },
        )

        # Update timestamp
        policy_dict = policy.model_dump()
        policy_dict["updated_at"] = datetime.now(timezone.utc)

        updated_policy = Policy(**policy_dict)
        self._policies[policy.policy_id] = updated_policy

        logger.info(
            "MemoryPolicyRepository: Policy saved successfully",
            extra={
                "policy_id": policy.policy_id,
                "title": policy.title,
                "status": policy.status.value,
                "validation_scores_count": len(policy.validation_scores),
                "has_transformations": policy.has_transformations,
                "updated_at": policy_dict["updated_at"].isoformat(),
            },
        )

    async def generate_id(self) -> str:
        """Generate a unique policy identifier.

        Returns:
            Unique policy ID string
        """
        policy_id = f"policy-{uuid.uuid4()}"

        logger.debug(
            "MemoryPolicyRepository: Generated policy ID",
            extra={"policy_id": policy_id},
        )

        return policy_id

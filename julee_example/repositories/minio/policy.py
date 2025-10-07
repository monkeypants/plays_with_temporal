"""
Minio implementation of PolicyRepository.

This module provides a Minio-based implementation of the PolicyRepository
protocol that follows the Clean Architecture patterns defined in the
Fun-Police Framework. It handles policy storage as JSON objects in Minio,
ensuring idempotency and proper error handling.

The implementation stores policies as JSON objects in Minio, following the
large payload handling pattern from the architectural guidelines. Each
policy is stored as a complete JSON document with its validation scores
and transformation queries.
"""

import logging
from typing import Optional, List, Dict

from julee_example.domain.models.policy import Policy
from julee_example.domain.repositories.policy import PolicyRepository
from .client import MinioClient, MinioRepositoryMixin


class MinioPolicyRepository(PolicyRepository, MinioRepositoryMixin):
    """
    Minio implementation of PolicyRepository using Minio for persistence.

    This implementation stores policies as JSON objects in the "policies"
    bucket. Each policy includes its complete validation scores and optional
    transformation queries.
    """

    def __init__(self, client: MinioClient) -> None:
        """Initialize repository with Minio client.

        Args:
            client: MinioClient protocol implementation (real or fake)
        """
        self.client = client
        self.logger = logging.getLogger("MinioPolicyRepository")
        self.policies_bucket = "policies"
        self.ensure_buckets_exist(self.policies_bucket)

    async def get(self, policy_id: str) -> Optional[Policy]:
        """Retrieve a policy by ID."""
        return self.get_json_object(
            bucket_name=self.policies_bucket,
            object_name=policy_id,
            model_class=Policy,
            not_found_log_message="Policy not found",
            error_log_message="Error retrieving policy",
            extra_log_data={"policy_id": policy_id},
        )

    async def save(self, policy: Policy) -> None:
        """Save a policy to Minio."""
        # Update timestamps
        self.update_timestamps(policy)

        self.put_json_object(
            bucket_name=self.policies_bucket,
            object_name=policy.policy_id,
            model=policy,
            success_log_message="Policy saved successfully",
            error_log_message="Error saving policy",
            extra_log_data={
                "policy_id": policy.policy_id,
                "title": policy.title,
                "status": policy.status.value,
                "validation_scores_count": len(policy.validation_scores),
                "has_transformations": policy.has_transformations,
                "version": policy.version,
            },
        )

    async def get_many(
        self, policy_ids: List[str]
    ) -> Dict[str, Optional[Policy]]:
        """Retrieve multiple policies by ID.

        Args:
            policy_ids: List of unique policy identifiers

        Returns:
            Dict mapping policy_id to Policy (or None if not found)
        """
        # Convert policy IDs to object names (direct mapping in this case)
        object_names = policy_ids

        # Get objects from Minio using batch method
        object_results = self.get_many_json_objects(
            bucket_name=self.policies_bucket,
            object_names=object_names,
            model_class=Policy,
            not_found_log_message="Policy not found",
            error_log_message="Error retrieving policy",
            extra_log_data={"policy_ids": policy_ids},
        )

        # Convert object names back to policy IDs for the result
        result: Dict[str, Optional[Policy]] = {}
        for policy_id in policy_ids:
            result[policy_id] = object_results[policy_id]

        return result

    async def generate_id(self) -> str:
        """Generate a unique policy identifier."""
        return self.generate_id_with_prefix("policy")

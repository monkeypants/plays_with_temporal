"""
Minio implementation of AssemblyRepository.

This module provides a Minio-based implementation of the AssemblyRepository
protocol that follows the Clean Architecture patterns defined in the
Fun-Police Framework. It handles assembly storage, ensuring idempotency and
proper error handling.

The implementation stores assembly data as JSON objects in Minio, following
the large payload handling pattern from the architectural guidelines.
"""

import logging
from typing import Optional, List, Dict

from julee_example.domain.models.assembly import Assembly
from julee_example.domain.repositories.assembly import AssemblyRepository
from .client import MinioClient, MinioRepositoryMixin


class MinioAssemblyRepository(AssemblyRepository, MinioRepositoryMixin):
    """
    Minio implementation of AssemblyRepository using Minio for persistence.

    This implementation stores assembly data as JSON objects in the
    "assemblies" bucket.
    """

    def __init__(self, client: MinioClient) -> None:
        """Initialize repository with Minio client.

        Args:
            client: MinioClient protocol implementation (real or fake)
        """
        self.client = client
        self.logger = logging.getLogger("MinioAssemblyRepository")
        self.assembly_bucket = "assemblies"
        self.ensure_buckets_exist([self.assembly_bucket])

    async def get(self, assembly_id: str) -> Optional[Assembly]:
        """Retrieve an assembly by ID."""
        # Get the assembly using mixin methods
        assembly = self.get_json_object(
            bucket_name=self.assembly_bucket,
            object_name=assembly_id,
            model_class=Assembly,
            not_found_log_message="Assembly not found",
            error_log_message="Error retrieving assembly",
            extra_log_data={"assembly_id": assembly_id},
        )

        return assembly

    async def save(self, assembly: Assembly) -> None:
        """Save assembly metadata (status, updated_at, etc.)."""
        # Update timestamp
        self.update_timestamps(assembly)

        self.put_json_object(
            bucket_name=self.assembly_bucket,
            object_name=assembly.assembly_id,
            model=assembly,
            success_log_message="Assembly saved successfully",
            error_log_message="Error saving assembly",
            extra_log_data={
                "assembly_id": assembly.assembly_id,
                "status": assembly.status.value,
                "assembled_document_id": assembly.assembled_document_id,
            },
        )

    async def get_many(
        self, assembly_ids: List[str]
    ) -> Dict[str, Optional[Assembly]]:
        """Retrieve multiple assemblies by ID.

        Args:
            assembly_ids: List of unique assembly identifiers

        Returns:
            Dict mapping assembly_id to Assembly (or None if not found)
        """
        # Convert assembly IDs to object names (direct mapping in this case)
        object_names = assembly_ids

        # Get objects from Minio using batch method
        object_results = self.get_many_json_objects(
            bucket_name=self.assembly_bucket,
            object_names=object_names,
            model_class=Assembly,
            not_found_log_message="Assembly not found",
            error_log_message="Error retrieving assembly",
            extra_log_data={"assembly_ids": assembly_ids},
        )

        # Convert object names back to assembly IDs for the result
        result: Dict[str, Optional[Assembly]] = {}
        for assembly_id in assembly_ids:
            result[assembly_id] = object_results[assembly_id]

        return result

    async def generate_id(self) -> str:
        """Generate a unique assembly identifier."""
        return self.generate_id_with_prefix("assembly")

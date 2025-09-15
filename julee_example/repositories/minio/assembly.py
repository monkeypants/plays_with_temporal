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
from datetime import datetime, timezone
from typing import Optional

from julee_example.domain import Assembly, AssemblyStatus
from julee_example.repositories.assembly import AssemblyRepository
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

    async def set_assembled_document(
        self, assembly_id: str, document_id: str
    ) -> Assembly:
        """Set the assembled document for an assembly."""

        # Get current assembly
        assembly = await self.get(assembly_id)
        if not assembly:
            raise ValueError(f"Assembly not found: {assembly_id}")

        # Check idempotency - if document_id already set to this value
        if assembly.assembled_document_id == document_id:
            return assembly

        # Update assembly with assembled document
        assembly_dict = assembly.model_dump()
        assembly_dict["assembled_document_id"] = document_id
        assembly_dict["status"] = AssemblyStatus.COMPLETED
        assembly_dict["updated_at"] = datetime.now(timezone.utc)
        updated_assembly = Assembly(**assembly_dict)

        # Save the updated assembly
        await self.save(updated_assembly)

        return updated_assembly

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

    async def generate_id(self) -> str:
        """Generate a unique assembly identifier."""
        return self.generate_id_with_prefix("assembly")

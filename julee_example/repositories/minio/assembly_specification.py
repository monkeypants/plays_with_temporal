"""
Minio implementation of AssemblySpecificationRepository.

This module provides a Minio-based implementation of the
AssemblySpecificationRepository protocol that follows the Clean Architecture
patterns defined in the Fun-Police Framework. It handles assembly
specification storage with complete JSON schemas and knowledge service query
configurations, ensuring idempotency and proper error handling.

The implementation stores assembly specifications as JSON objects in Minio,
following the large payload handling pattern from the architectural
guidelines. Each specification is stored as a complete JSON document with its
schema and query mappings.
"""

import logging
from typing import Optional

from julee_example.domain import AssemblySpecification
from julee_example.repositories.assembly_specification import (
    AssemblySpecificationRepository,
)
from .client import MinioClient, MinioRepositoryMixin


class MinioAssemblySpecificationRepository(AssemblySpecificationRepository, MinioRepositoryMixin):
    """
    Minio implementation of AssemblySpecificationRepository using Minio for
    persistence.

    This implementation stores assembly specifications as JSON objects in the
    "assembly-specifications" bucket. Each specification includes its complete
    JSON schema definition and knowledge service query mappings.
    """

    def __init__(self, client: MinioClient) -> None:
        """Initialize repository with Minio client.

        Args:
            client: MinioClient protocol implementation (real or fake)
        """
        self.client = client
        self.logger = logging.getLogger("MinioAssemblySpecificationRepository")
        self.specifications_bucket = "assembly-specifications"
        self.ensure_buckets_exist(self.specifications_bucket)

    async def get(
        self, assembly_specification_id: str
    ) -> Optional[AssemblySpecification]:
        """Retrieve an assembly specification by ID."""
        return self.get_json_object(
            bucket_name=self.specifications_bucket,
            object_name=assembly_specification_id,
            model_class=AssemblySpecification,
            not_found_log_message="Specification not found",
            error_log_message="Error retrieving specification",
            extra_log_data={"assembly_specification_id": assembly_specification_id}
        )

    async def save(
        self, assembly_specification: AssemblySpecification
    ) -> None:
        """Save an assembly specification to Minio."""
        # Update timestamps
        self.update_timestamps(assembly_specification)

        self.put_json_object(
            bucket_name=self.specifications_bucket,
            object_name=assembly_specification.assembly_specification_id,
            model=assembly_specification,
            success_log_message="Specification saved successfully",
            error_log_message="Error saving specification",
            extra_log_data={
                "assembly_specification_id": assembly_specification.assembly_specification_id,
                "spec_name": assembly_specification.name,
                "status": assembly_specification.status.value,
                "version": assembly_specification.version,
            }
        )

    async def generate_id(self) -> str:
        """Generate a unique assembly specification identifier."""
        return self.generate_id_with_prefix("spec")

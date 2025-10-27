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
from typing import Optional, List, Dict

from julee_example.domain.models.assembly_specification import (
    AssemblySpecification,
)
from julee_example.domain.repositories.assembly_specification import (
    AssemblySpecificationRepository,
)
from .client import MinioClient, MinioRepositoryMixin


class MinioAssemblySpecificationRepository(
    AssemblySpecificationRepository, MinioRepositoryMixin
):
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
        self.logger = logging.getLogger(
            "MinioAssemblySpecificationRepository"
        )
        self.specifications_bucket = "assembly-specifications"
        self.ensure_buckets_exist(self.specifications_bucket)

    async def get(
        self, assembly_specification_id: str
    ) -> Optional[AssemblySpecification]:
        """Retrieve an assembly specification by ID."""
        object_name = f"spec/{assembly_specification_id}"

        return self.get_json_object(
            bucket_name=self.specifications_bucket,
            object_name=object_name,
            model_class=AssemblySpecification,
            not_found_log_message="Specification not found",
            error_log_message="Error retrieving specification",
            extra_log_data={
                "assembly_specification_id": assembly_specification_id
            },
        )

    async def save(
        self, assembly_specification: AssemblySpecification
    ) -> None:
        """Save an assembly specification to Minio."""
        # Update timestamps
        self.update_timestamps(assembly_specification)

        object_name = (
            f"spec/{assembly_specification.assembly_specification_id}"
        )

        self.put_json_object(
            bucket_name=self.specifications_bucket,
            object_name=object_name,
            model=assembly_specification,
            success_log_message="Specification saved successfully",
            error_log_message="Error saving specification",
            extra_log_data={
                "assembly_specification_id": (
                    assembly_specification.assembly_specification_id
                ),
                "spec_name": assembly_specification.name,
                "status": assembly_specification.status.value,
                "version": assembly_specification.version,
            },
        )

    async def get_many(
        self, assembly_specification_ids: List[str]
    ) -> Dict[str, Optional[AssemblySpecification]]:
        """Retrieve multiple assembly specifications by ID.

        Args:
            assembly_specification_ids: List of unique specification
            identifiers

        Returns:
            Dict mapping specification_id to AssemblySpecification (or None if
            not found)
        """
        # Convert specification IDs to object names
        object_names = [
            f"spec/{spec_id}" for spec_id in assembly_specification_ids
        ]

        # Get objects from Minio using batch method
        object_results = self.get_many_json_objects(
            bucket_name=self.specifications_bucket,
            object_names=object_names,
            model_class=AssemblySpecification,
            not_found_log_message="Specification not found",
            error_log_message="Error retrieving specification",
            extra_log_data={
                "assembly_specification_ids": assembly_specification_ids
            },
        )

        # Convert object names back to specification IDs for the result
        result: Dict[str, Optional[AssemblySpecification]] = {}
        for i, spec_id in enumerate(assembly_specification_ids):
            object_name = object_names[i]
            result[spec_id] = object_results[object_name]

        return result

    async def generate_id(self) -> str:
        """Generate a unique assembly specification identifier."""
        return self.generate_id_with_prefix("spec")

    async def list_all(self) -> List[AssemblySpecification]:
        """List all assembly specifications.

        Returns:
            List of all assembly specifications, sorted by
            assembly_specification_id
        """
        try:
            # Extract specification IDs from objects with the spec/ prefix
            spec_ids = self.list_objects_with_prefix_extract_ids(
                bucket_name=self.specifications_bucket,
                prefix="spec/",
                entity_type_name="specs",
            )

            if not spec_ids:
                return []

            # Get all specifications using the existing get_many method
            spec_results = await self.get_many(spec_ids)

            # Filter out None results and sort by assembly_specification_id
            specs = [
                spec for spec in spec_results.values() if spec is not None
            ]
            specs.sort(key=lambda x: x.assembly_specification_id)

            self.logger.debug(
                "Retrieved specs",
                extra={"count": len(specs)},
            )

            return specs

        except Exception as e:
            self.logger.error(
                "Error listing specs",
                exc_info=True,
                extra={
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "bucket": self.specifications_bucket,
                },
            )
            # Return empty list on error to avoid breaking the API
            return []

"""
Minio implementation of AssemblyRepository.

This module provides a Minio-based implementation of the AssemblyRepository
protocol that follows the Clean Architecture patterns defined in the
Fun-Police Framework. It handles assembly storage with both assembly metadata
and iteration data, ensuring idempotency and proper error handling.

The implementation stores assembly metadata and iterations as JSON objects
in Minio, following the large payload handling pattern from the architectural
guidelines. Each assembly and its iterations are stored separately for
efficient queries and updates.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Optional

from minio.error import S3Error  # type: ignore[import-untyped]

from julee_example.domain import Assembly, AssemblyIteration
from julee_example.repositories.assembly import AssemblyRepository
from .client import MinioClient, MinioRepositoryMixin


class MinioAssemblyRepository(AssemblyRepository, MinioRepositoryMixin):
    """
    Minio implementation of AssemblyRepository using Minio for persistence.

    This implementation stores assembly metadata and iterations separately:
    - Assembly metadata: JSON objects in the "assemblies" bucket
    - Iterations: JSON objects in the "assembly-iterations" bucket

    This separation allows for efficient metadata queries and supports the
    aggregate pattern where assemblies contain their iterations.
    """

    def __init__(self, client: MinioClient) -> None:
        """Initialize repository with Minio client.

        Args:
            client: MinioClient protocol implementation (real or fake)
        """
        self.client = client
        self.logger = logging.getLogger("MinioAssemblyRepository")
        self.assembly_bucket = "assemblies"
        self.iterations_bucket = "assembly-iterations"
        self.ensure_buckets_exist(
            [self.assembly_bucket, self.iterations_bucket]
        )

    async def get(self, assembly_id: str) -> Optional[Assembly]:
        """Retrieve an assembly with all its iterations."""
        # Get the assembly metadata using mixin methods
        assembly = self.get_json_object(
            bucket_name=self.assembly_bucket,
            object_name=assembly_id,
            model_class=Assembly,
            not_found_log_message="Assembly not found",
            error_log_message="Error retrieving assembly",
            extra_log_data={"assembly_id": assembly_id},
        )

        if assembly is None:
            return None

        # Get all iterations for this assembly
        iterations = []
        try:
            # List all objects in iterations bucket with assembly_id prefix
            objects = self.client.list_objects(
                bucket_name=self.iterations_bucket,
                prefix=f"{assembly_id}/",
            )

            for obj in objects:
                iteration_response = self.client.get_object(
                    bucket_name=self.iterations_bucket,
                    object_name=obj.object_name,
                )
                iteration_data = iteration_response.read()
                iteration_response.close()
                iteration_response.release_conn()

                iteration_json = iteration_data.decode("utf-8")
                iteration_dict = json.loads(iteration_json)
                iterations.append(AssemblyIteration(**iteration_dict))

            # Sort iterations by iteration_id (use 0 for None values)
            iterations.sort(key=lambda x: x.iteration_id or 0)
            assembly.iterations = iterations

        except S3Error as iterations_error:
            # If no iterations found, assembly has empty iterations list
            if getattr(iterations_error, "code", None) == "NoSuchKey":
                assembly.iterations = []
            else:
                raise

        return assembly

    async def add_iteration(
        self, assembly_id: str, assembly_iteration: AssemblyIteration
    ) -> Assembly:
        """Add a new iteration to an assembly and persist it immediately."""

        # Get current assembly to check for existing iterations
        assembly = await self.get(assembly_id)
        if not assembly:
            raise ValueError(f"Assembly not found: {assembly_id}")

        # Check idempotency - if document_id already exists, return unchanged
        for iteration in assembly.iterations:
            if iteration.document_id == assembly_iteration.document_id:

                return assembly

        # Use provided iteration but set sequential ID and update timestamps
        new_iteration = AssemblyIteration(
            iteration_id=len(assembly.iterations) + 1,
            document_id=assembly_iteration.document_id,
            scorecard_results=assembly_iteration.scorecard_results,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        # Persist the iteration
        iteration_key = f"{assembly_id}/{new_iteration.iteration_id}"

        self.put_json_object(
            bucket_name=self.iterations_bucket,
            object_name=iteration_key,
            model=new_iteration,
            success_log_message="Iteration added successfully",
            error_log_message="Error adding iteration",
            extra_log_data={
                "assembly_id": assembly_id,
                "iteration_id": new_iteration.iteration_id,
                "document_id": assembly_iteration.document_id,
            },
        )

        # Update assembly's updated_at timestamp and save
        assembly.iterations.append(new_iteration)
        await self.save(assembly)

        return assembly

    async def save(self, assembly: Assembly) -> None:
        """Save assembly metadata (status, updated_at, etc.)."""
        # Update timestamp
        self.update_timestamps(assembly)

        # Create a temporary assembly without iterations for metadata storage
        assembly_for_storage = Assembly(
            assembly_id=assembly.assembly_id,
            assembly_specification_id=assembly.assembly_specification_id,
            input_document_id=assembly.input_document_id,
            status=assembly.status,
            iterations=[],  # Empty iterations - stored separately
            created_at=assembly.created_at,
            updated_at=assembly.updated_at,
        )

        self.put_json_object(
            bucket_name=self.assembly_bucket,
            object_name=assembly.assembly_id,
            model=assembly_for_storage,
            success_log_message="Assembly saved successfully",
            error_log_message="Error saving assembly",
            extra_log_data={
                "assembly_id": assembly.assembly_id,
                "status": assembly.status.value,
            },
        )

    async def generate_id(self) -> str:
        """Generate a unique assembly identifier."""
        return self.generate_id_with_prefix("assembly")

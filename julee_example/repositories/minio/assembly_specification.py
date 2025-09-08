"""
Minio implementation of AssemblySpecificationRepository.

This module provides a Minio-based implementation of the
AssemblySpecificationRepository protocol that follows the Clean Architecture
patterns defined in the Fun-Police Framework. It handles assembly specification
storage with complete JSON schemas and knowledge service query configurations,
ensuring idempotency and proper error handling.

The implementation stores assembly specifications as JSON objects in Minio,
following the large payload handling pattern from the architectural guidelines.
Each specification is stored as a complete JSON document with its schema and
query mappings.
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from minio.error import S3Error  # type: ignore[import-untyped]

from julee_example.domain import AssemblySpecification
from julee_example.repositories.assembly_specification import (
    AssemblySpecificationRepository,
)
from .client import MinioClient

logger = logging.getLogger(__name__)


class MinioAssemblySpecificationRepository(AssemblySpecificationRepository):
    """
    Minio implementation of AssemblySpecificationRepository using Minio for persistence.

    This implementation stores assembly specifications as JSON objects in the
    "assembly-specifications" bucket. Each specification includes its complete
    JSON schema definition and knowledge service query mappings.
    """

    def __init__(self, client: MinioClient) -> None:
        """Initialize repository with Minio client.

        Args:
            client: MinioClient protocol implementation (real or fake)
        """
        logger.debug("Initializing MinioAssemblySpecificationRepository")

        self.client = client
        self.specifications_bucket = "assembly-specifications"
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self) -> None:
        """Ensure specifications bucket exists."""
        try:
            if not self.client.bucket_exists(self.specifications_bucket):
                logger.info(
                    "Creating assembly specifications bucket",
                    extra={"bucket_name": self.specifications_bucket},
                )
                self.client.make_bucket(self.specifications_bucket)
            else:
                logger.debug(
                    "Assembly specifications bucket already exists",
                    extra={"bucket_name": self.specifications_bucket},
                )
        except S3Error as e:
            logger.error(
                "Failed to create assembly specifications bucket",
                extra={
                    "bucket_name": self.specifications_bucket,
                    "error": str(e),
                },
            )
            raise

    async def get(
        self, assembly_specification_id: str
    ) -> Optional[AssemblySpecification]:
        """Retrieve an assembly specification by ID."""
        logger.debug(
            "MinioAssemblySpecificationRepository: Attempting to retrieve specification",
            extra={
                "assembly_specification_id": assembly_specification_id,
                "bucket": self.specifications_bucket,
            },
        )

        try:
            response = self.client.get_object(
                bucket_name=self.specifications_bucket,
                object_name=assembly_specification_id,
            )
            data = response.read()
            response.close()
            response.release_conn()

            specification_json = data.decode("utf-8")
            specification_dict = json.loads(specification_json)

            logger.info(
                "MinioAssemblySpecificationRepository: Specification retrieved successfully",
                extra={
                    "assembly_specification_id": assembly_specification_id,
                    "name": specification_dict.get("name"),
                    "status": specification_dict.get("status"),
                    "version": specification_dict.get("version"),
                    "retrieved_at": datetime.now(timezone.utc).isoformat(),
                },
            )

            return AssemblySpecification(**specification_dict)

        except S3Error as e:
            if getattr(e, "code", None) == "NoSuchKey":
                logger.debug(
                    "MinioAssemblySpecificationRepository: Specification not found",
                    extra={
                        "assembly_specification_id": assembly_specification_id
                    },
                )
                return None
            else:
                logger.error(
                    "MinioAssemblySpecificationRepository: Error retrieving specification",
                    extra={
                        "assembly_specification_id": assembly_specification_id,
                        "error": str(e),
                    },
                )
                raise

    async def save(
        self, assembly_specification: AssemblySpecification
    ) -> None:
        """Save an assembly specification."""
        logger.debug(
            "MinioAssemblySpecificationRepository: Saving specification",
            extra={
                "assembly_specification_id": assembly_specification.assembly_specification_id,
                "name": assembly_specification.name,
                "status": assembly_specification.status.value,
            },
        )

        try:
            # Update timestamp
            assembly_specification.updated_at = datetime.now(timezone.utc)

            # Use Pydantic's JSON serialization for proper datetime handling
            specification_json = assembly_specification.model_dump_json()

            self.client.put_object(
                bucket_name=self.specifications_bucket,
                object_name=assembly_specification.assembly_specification_id,
                data=specification_json.encode("utf-8"),
                length=len(specification_json.encode("utf-8")),
                content_type="application/json",
            )

            logger.info(
                "MinioAssemblySpecificationRepository: Specification saved successfully",
                extra={
                    "assembly_specification_id": assembly_specification.assembly_specification_id,
                    "name": assembly_specification.name,
                    "status": assembly_specification.status.value,
                    "version": assembly_specification.version,
                    "updated_at": assembly_specification.updated_at.isoformat(),
                },
            )

        except S3Error as e:
            logger.error(
                "MinioAssemblySpecificationRepository: Error saving specification",
                extra={
                    "assembly_specification_id": assembly_specification.assembly_specification_id,
                    "error": str(e),
                },
            )
            raise

    async def generate_id(self) -> str:
        """Generate a unique assembly specification identifier."""
        specification_id = str(uuid.uuid4())

        logger.debug(
            "MinioAssemblySpecificationRepository: Generated specification ID",
            extra={"assembly_specification_id": specification_id},
        )

        return specification_id

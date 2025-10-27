"""
MinioClient protocol definition and repository utilities.

This module defines the protocol interface that both the real Minio client
and our fake test client must implement. This follows Clean Architecture
dependency inversion principles by depending on abstractions rather than
concrete implementations.

It also provides MinioRepositoryMixin, a mixin that encapsulates
common patterns used across all Minio repository implementations to reduce
code duplication and ensure consistent error handling and logging.
"""

import io
import json
from datetime import datetime, timezone
from typing import (
    Protocol,
    Any,
    Dict,
    Optional,
    runtime_checkable,
    List,
    Union,
    TypeVar,
    BinaryIO,
)
from urllib3.response import BaseHTTPResponse
from minio.datatypes import Object
from minio.api import ObjectWriteResult
from minio.error import S3Error  # type: ignore[import-untyped]
from pydantic import BaseModel

# Import ContentStream here to avoid circular imports
from julee_example.domain.models.custom_fields.content_stream import (
    ContentStream,
)

T = TypeVar("T", bound=BaseModel)


@runtime_checkable
class MinioClient(Protocol):
    """
    Protocol defining the MinIO client interface used by the repository.

    This protocol captures only the methods we actually use, making our
    dependency explicit and testable. Both the real minio.Minio client and
    our FakeMinioClient implement this protocol.
    """

    def bucket_exists(self, bucket_name: str) -> bool:
        """Check if a bucket exists.

        Args:
            bucket_name: Name of the bucket to check

        Returns:
            True if bucket exists, False otherwise
        """
        ...

    def make_bucket(self, bucket_name: str) -> None:
        """Create a bucket.

        Args:
            bucket_name: Name of the bucket to create

        Raises:
            S3Error: If bucket creation fails
        """
        ...

    def put_object(
        self,
        bucket_name: str,
        object_name: str,
        data: BinaryIO,
        length: int,
        content_type: str = "application/octet-stream",
        metadata: Optional[
            Dict[str, Union[str, List[str], tuple[str]]]
        ] = None,
    ) -> ObjectWriteResult:
        """Store an object in the bucket.

        Args:
            bucket_name: Name of the bucket
            object_name: Name of the object to store
            data: Object data (stream or bytes)
            length: Size of the object in bytes
            content_type: MIME type of the object
            metadata: Optional metadata dict

        Returns:
            Object upload result

        Raises:
            S3Error: If object storage fails
        """
        ...

    def get_object(
        self, bucket_name: str, object_name: str
    ) -> BaseHTTPResponse:
        """Retrieve an object from the bucket.

        Args:
            bucket_name: Name of the bucket
            object_name: Name of the object to retrieve

        Returns:
            HTTPResponse containing the object data

        Raises:
            S3Error: If object retrieval fails (e.g., NoSuchKey)
        """
        ...

    def stat_object(self, bucket_name: str, object_name: str) -> Object:
        """Get object metadata without retrieving the object data.

        Args:
            bucket_name: Name of the bucket
            object_name: Name of the object

        Returns:
            Object metadata

        Raises:
            S3Error: If object doesn't exist (NoSuchKey) or other errors
        """
        ...

    def list_objects(self, bucket_name: str, prefix: str = "") -> Any:
        """List objects in a bucket with optional prefix filter.

        Args:
            bucket_name: Name of the bucket
            prefix: Optional prefix to filter objects

        Returns:
            Iterator or list of objects matching the prefix

        Raises:
            S3Error: If bucket doesn't exist or other errors
        """
        ...


class MinioRepositoryMixin:
    """
    Mixin that provides common repository patterns for Minio implementations.

    This mixin encapsulates common functionality used across all Minio
    repository
    implementations, including:
    - Bucket creation and management
    - JSON serialization/deserialization with proper error handling
    - Standardized S3Error handling for NoSuchKey cases
    - Consistent logging patterns
    - Response cleanup
    - ID generation with logging

    Classes using this mixin must provide:
    - self.client: MinioClient instance
    - self.logger: logging.Logger instance (typically set in __init__)
    """

    # Type annotations for attributes that implementing classes must provide
    client: MinioClient
    logger: Any  # logging.Logger, but avoiding import

    def ensure_buckets_exist(
        self, bucket_names: Union[str, List[str]]
    ) -> None:
        """Ensure one or more buckets exist, creating them if necessary.

        Args:
            bucket_names: Single bucket name or list of bucket names

        Raises:
            S3Error: If bucket creation fails
        """
        if isinstance(bucket_names, str):
            bucket_names = [bucket_names]

        for bucket_name in bucket_names:
            try:
                if not self.client.bucket_exists(bucket_name):
                    self.logger.info(
                        "Creating bucket",
                        extra={"bucket_name": bucket_name},
                    )
                    self.client.make_bucket(bucket_name)
                else:
                    self.logger.debug(
                        "Bucket already exists",
                        extra={"bucket_name": bucket_name},
                    )
            except S3Error as e:
                self.logger.error(
                    "Failed to create bucket",
                    extra={"bucket_name": bucket_name, "error": str(e)},
                )
                raise

    def get_many_json_objects(
        self,
        bucket_name: str,
        object_names: List[str],
        model_class: type[T],
        not_found_log_message: str,
        error_log_message: str,
        extra_log_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Optional[T]]:
        """Get multiple JSON objects from Minio and deserialize them.

        Note: S3/MinIO does not have native batch retrieval operations.
        This method makes individual GetObject calls for each object but
        provides consolidated error handling, logging, and connection reuse.
        The real benefit comes with other backends (PostgreSQL, Redis, etc.)
        that support true batch operations.

        Args:
            bucket_name: Name of the bucket
            object_names: List of object names to retrieve
            model_class: Pydantic model class to deserialize to
            not_found_log_message: Message to log when objects are not found
            error_log_message: Message to log on other errors
            extra_log_data: Additional data to include in log entries

        Returns:
            Dict mapping object_name to deserialized model (or None if not
            found)

        Raises:
            S3Error: For non-NoSuchKey errors
        """
        extra_log_data = extra_log_data or {}
        result: Dict[str, Optional[T]] = {}
        found_count = 0

        self.logger.debug(
            "Attempting to retrieve multiple objects",
            extra={
                **extra_log_data,
                "object_count": len(object_names),
                "bucket_name": bucket_name,
            },
        )

        for object_name in object_names:
            try:
                response = self.client.get_object(
                    bucket_name=bucket_name, object_name=object_name
                )

                # Read and clean up response
                data = response.read()
                response.close()
                response.release_conn()

                # Deserialize JSON to Pydantic model
                json_str = data.decode("utf-8")
                json_dict = json.loads(json_str)

                entity = model_class(**json_dict)
                result[object_name] = entity
                found_count += 1

            except S3Error as e:
                if getattr(e, "code", None) == "NoSuchKey":
                    self.logger.debug(
                        not_found_log_message,
                        extra={**extra_log_data, "object_name": object_name},
                    )
                    result[object_name] = None
                else:
                    self.logger.error(
                        error_log_message,
                        extra={
                            **extra_log_data,
                            "object_name": object_name,
                            "error": str(e),
                        },
                    )
                    raise

        self.logger.info(
            f"Retrieved {found_count}/{len(object_names)} objects",
            extra={
                **extra_log_data,
                "requested_count": len(object_names),
                "found_count": found_count,
                "missing_count": len(object_names) - found_count,
                "bucket_name": bucket_name,
            },
        )

        return result

    def get_many_binary_objects(
        self,
        bucket_name: str,
        object_names: List[str],
        not_found_log_message: str,
        error_log_message: str,
        extra_log_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Optional[ContentStream]]:
        """Get multiple binary objects from Minio as ContentStreams.

        Note: S3/MinIO does not have native batch retrieval operations.
        This method makes individual GetObject calls for each object but
        provides consolidated error handling, logging, and connection reuse.

        Args:
            bucket_name: Name of the bucket
            object_names: List of object names to retrieve
            not_found_log_message: Message to log when objects are not found
            error_log_message: Message to log on other errors
            extra_log_data: Additional data to include in log entries

        Returns:
            Dict mapping object_name to ContentStream (or None if not found)

        Raises:
            S3Error: For non-NoSuchKey errors
        """
        extra_log_data = extra_log_data or {}
        result: Dict[str, Optional[ContentStream]] = {}
        found_count = 0

        self.logger.debug(
            "Attempting to retrieve multiple binary objects",
            extra={
                **extra_log_data,
                "object_count": len(object_names),
                "bucket_name": bucket_name,
            },
        )

        for object_name in object_names:
            try:
                response = self.client.get_object(
                    bucket_name=bucket_name, object_name=object_name
                )

                # Create ContentStream directly from the response
                content_stream = ContentStream(response)
                result[object_name] = content_stream
                found_count += 1

            except S3Error as e:
                if getattr(e, "code", None) == "NoSuchKey":
                    self.logger.debug(
                        not_found_log_message,
                        extra={**extra_log_data, "object_name": object_name},
                    )
                    result[object_name] = None
                else:
                    self.logger.error(
                        error_log_message,
                        extra={
                            **extra_log_data,
                            "object_name": object_name,
                            "error": str(e),
                        },
                    )
                    raise

        self.logger.info(
            f"Retrieved {found_count}/{len(object_names)} binary objects",
            extra={
                **extra_log_data,
                "requested_count": len(object_names),
                "found_count": found_count,
                "missing_count": len(object_names) - found_count,
                "bucket_name": bucket_name,
            },
        )

        return result

    def get_json_object(
        self,
        bucket_name: str,
        object_name: str,
        model_class: type[T],
        not_found_log_message: str,
        error_log_message: str,
        extra_log_data: Optional[Dict[str, Any]] = None,
    ) -> Optional[T]:
        """Get a JSON object from Minio and deserialize it to a Pydantic
        model.

        Args:
            bucket_name: Name of the bucket
            object_name: Name of the object
            model_class: Pydantic model class to deserialize to
            not_found_log_message: Message to log when object is not found
            error_log_message: Message to log on other errors
            extra_log_data: Additional data to include in log entries

        Returns:
            Deserialized Pydantic model instance, or None if not found

        Raises:
            S3Error: For non-NoSuchKey errors
        """
        extra_log_data = extra_log_data or {}

        try:
            response = self.client.get_object(
                bucket_name=bucket_name, object_name=object_name
            )

            # Read and clean up response
            data = response.read()
            response.close()
            response.release_conn()

            # Deserialize JSON to Pydantic model
            json_str = data.decode("utf-8")
            json_dict = json.loads(json_str)

            return model_class(**json_dict)

        except S3Error as e:
            if getattr(e, "code", None) == "NoSuchKey":
                self.logger.debug(
                    not_found_log_message,
                    extra=extra_log_data,
                )
                return None
            else:
                self.logger.error(
                    error_log_message,
                    extra={**extra_log_data, "error": str(e)},
                )
                raise

    def put_json_object(
        self,
        bucket_name: str,
        object_name: str,
        model: BaseModel,
        success_log_message: str,
        error_log_message: str,
        extra_log_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Store a Pydantic model as a JSON object in Minio.

        Args:
            bucket_name: Name of the bucket
            object_name: Name of the object
            model: Pydantic model instance to serialize
            success_log_message: Message to log on successful storage
            error_log_message: Message to log on error
            extra_log_data: Additional data to include in log entries

        Raises:
            S3Error: If object storage fails
        """
        extra_log_data = extra_log_data or {}

        try:
            # Serialize using Pydantic's JSON serialization
            json_data = model.model_dump_json()

            json_bytes = json_data.encode("utf-8")
            self.client.put_object(
                bucket_name=bucket_name,
                object_name=object_name,
                data=io.BytesIO(json_bytes),
                length=len(json_bytes),
                content_type="application/json",
            )

            self.logger.info(
                success_log_message,
                extra=extra_log_data,
            )

        except S3Error as e:
            self.logger.error(
                error_log_message,
                extra={**extra_log_data, "error": str(e)},
            )
            raise

    def update_timestamps(self, model: Any) -> None:
        """Update timestamps on a model (created_at if None, always
        updated_at).

        Args:
            model: Pydantic model with created_at and updated_at fields
        """
        now = datetime.now(timezone.utc)

        # Set created_at if it's None (for new objects)
        if (
            hasattr(model, "created_at")
            and getattr(model, "created_at", None) is None
        ):
            setattr(model, "created_at", now)

        # Always update updated_at
        if hasattr(model, "updated_at"):
            setattr(model, "updated_at", now)

    def generate_id_with_prefix(self, prefix: str) -> str:
        """Generate a unique ID with the given prefix and log the generation.

        Args:
            prefix: Prefix for the generated ID (e.g., "ks", "doc")

        Returns:
            Unique ID string in format "{prefix}-{uuid}"
        """
        import uuid
        from datetime import datetime, timezone

        generated_id = f"{prefix}-{uuid.uuid4()}"

        self.logger.debug(
            "Generated ID",
            extra={
                "generated_id": generated_id,
                "prefix": prefix,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            },
        )

        return generated_id

    def list_objects_with_prefix_extract_ids(
        self,
        bucket_name: str,
        prefix: str,
        entity_type_name: str,
    ) -> List[str]:
        """Extract entity IDs from objects with a given prefix.

        This method provides a common implementation for listing objects
        and extracting IDs, eliminating code duplication in list_all methods.

        Args:
            bucket_name: Name of the bucket to list objects from
            prefix: Object name prefix to filter by (e.g., "spec/", "query/")
            entity_type_name: Name for logging (e.g., "specs", "queries")

        Returns:
            List of entity IDs extracted from object names

        Raises:
            Exception: If listing objects fails
        """
        self.logger.debug(
            f"Listing all {entity_type_name}",
            extra={"bucket": bucket_name, "prefix": prefix},
        )

        # List all objects with the specified prefix
        objects = self.client.list_objects(
            bucket_name=bucket_name, prefix=prefix
        )

        # Extract IDs from object names by removing the prefix
        entity_ids = []
        for obj in objects:
            # Extract ID by removing the prefix
            entity_id = obj.object_name[len(prefix) :]
            entity_ids.append(entity_id)

        self.logger.debug(
            f"Found {entity_type_name} objects",
            extra={"count": len(entity_ids), "entity_ids": entity_ids},
        )

        return entity_ids

"""
Fake Minio client for state-based testing.

This module provides a FakeMinioClient that implements the same interface as
the real Minio client but stores objects in memory for testing. This enables
state-based testing where you can verify actual storage state rather than
just mocking method calls.
"""

from typing import Dict, Any, Optional, Callable, BinaryIO, Union, List
from functools import wraps
from unittest.mock import Mock
from datetime import datetime, timezone
from minio.error import S3Error
from minio.datatypes import Object
from minio.api import ObjectWriteResult
from urllib3.response import BaseHTTPResponse
from urllib3 import HTTPHeaderDict

from ..client import MinioClient


def requires_bucket(func: Callable) -> Callable:
    """Decorator to check if bucket exists before method execution."""

    @wraps(func)
    def wrapper(
        self: Any, bucket_name: str, *args: Any, **kwargs: Any
    ) -> Any:
        if bucket_name not in self._buckets:
            raise S3Error(
                code="NoSuchBucket",
                message="Bucket does not exist",
                resource=bucket_name,
                request_id="req123",
                host_id="host123",
                response=Mock(),
            )
        return func(self, bucket_name, *args, **kwargs)

    return wrapper


def requires_object(func: Callable) -> Callable:
    """Decorator to check if object exists before method execution."""

    @wraps(func)
    def wrapper(
        self: Any,
        bucket_name: str,
        object_name: str,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        if bucket_name not in self._objects:
            raise S3Error(
                code="NoSuchBucket",
                message="Bucket does not exist",
                resource=bucket_name,
                request_id="req123",
                host_id="host123",
                response=Mock(),
            )
        if object_name not in self._objects[bucket_name]:
            raise S3Error(
                code="NoSuchKey",
                message="Object not found",
                resource=object_name,
                request_id="req123",
                host_id="host123",
                response=Mock(),
            )
        return func(self, bucket_name, object_name, *args, **kwargs)

    return wrapper


class FakeMinioClient(MinioClient):
    """
    Fake Minio client that stores objects in memory for testing.

    This client implements the MinioClient protocol and stores all data in
    memory, allowing for fast state-based testing without requiring a real
    MinIO server.
    """

    def __init__(self) -> None:
        self._buckets: Dict[str, Dict[str, Any]] = {}
        self._objects: Dict[str, Dict[str, Dict[str, Any]]] = {}

    def bucket_exists(self, bucket_name: str) -> bool:
        """Check if a bucket exists."""
        return bucket_name in self._buckets

    def make_bucket(self, bucket_name: str) -> None:
        """Create a bucket."""
        if bucket_name in self._buckets:
            raise S3Error(
                code="BucketAlreadyExists",
                message="Bucket already exists",
                resource=bucket_name,
                request_id="req123",
                host_id="host123",
                response=Mock(),
            )
        self._buckets[bucket_name] = {}
        self._objects[bucket_name] = {}

    @requires_bucket
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
        """Store an object in the bucket."""

        # Read the data from stream
        if hasattr(data, "read"):
            if hasattr(data, "seek"):
                data.seek(0)  # Ensure we're at the beginning
            content = data.read()
            if hasattr(data, "seek"):
                data.seek(0)  # Reset for potential re-use
        else:
            content = (
                data if isinstance(data, bytes) else str(data).encode("utf-8")
            )

        self._objects[bucket_name][object_name] = {
            "data": content,
            "metadata": metadata or {},
            "content_type": content_type,
            "size": len(content),
        }

        # Return a proper ObjectWriteResult
        return ObjectWriteResult(
            bucket_name=bucket_name,
            object_name=object_name,
            version_id=None,
            etag="fake-etag",
            http_headers=HTTPHeaderDict(),
            last_modified=datetime.now(timezone.utc),
            location=f"/{bucket_name}/{object_name}",
        )

    @requires_object
    def get_object(
        self, bucket_name: str, object_name: str
    ) -> BaseHTTPResponse:
        """Retrieve an object from the bucket."""

        obj_info = self._objects[bucket_name][object_name]
        # Create a mock BaseHTTPResponse with the data
        mock_response = Mock(spec=BaseHTTPResponse)
        mock_response.read = Mock(return_value=obj_info["data"])
        mock_response.close = Mock()
        mock_response.release_conn = Mock()
        return mock_response

    @requires_object
    def stat_object(self, bucket_name: str, object_name: str) -> Object:
        """Get object metadata without retrieving the object data."""

        obj_info = self._objects[bucket_name][object_name]
        # Create a real Minio Object
        return Object(
            bucket_name=bucket_name,
            object_name=object_name,
            last_modified=datetime.now(timezone.utc),
            etag="fake-etag",
            size=obj_info["size"],
            content_type=obj_info["content_type"],
            metadata=obj_info["metadata"],
        )

    def list_objects(self, bucket_name: str, prefix: str = "") -> list:
        """List objects in a bucket with optional prefix filter."""
        if bucket_name not in self._objects:
            return []

        objects = []
        for object_name, obj_info in self._objects[bucket_name].items():
            if object_name.startswith(prefix):
                # Create a simple object info structure
                obj = Mock()
                obj.object_name = object_name
                obj.size = obj_info["size"]
                objects.append(obj)

        return objects

    @requires_object
    def remove_object(self, bucket_name: str, object_name: str) -> None:
        """Remove an object from the bucket."""

        del self._objects[bucket_name][object_name]

    # Inspection methods for testing
    def get_stored_objects(
        self, bucket_name: str
    ) -> Dict[str, Dict[str, Any]]:
        """Get all stored objects in a bucket (for testing purposes)."""
        return self._objects.get(bucket_name, {}).copy()

    def get_object_count(self, bucket_name: str) -> int:
        """Get the number of objects in a bucket (for testing purposes)."""
        return len(self._objects.get(bucket_name, {}))

    def get_total_object_count(self) -> int:
        """Get total number of objects across all buckets (for testing)."""
        return sum(len(objects) for objects in self._objects.values())

    def clear_all_data(self) -> None:
        """Clear all buckets and objects (for testing purposes)."""
        self._buckets.clear()
        self._objects.clear()

"""
MinioClient protocol definition.

This module defines the protocol interface that both the real Minio client
and our fake test client must implement. This follows Clean Architecture
dependency inversion principles by depending on abstractions rather than
concrete implementations.
"""

from typing import Protocol, Any, Dict, Optional, runtime_checkable
from urllib3.response import HTTPResponse
from minio.datatypes import Object


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
        data: Any,
        length: int,
        content_type: str = "application/octet-stream",
        metadata: Optional[Dict[str, str]] = None,
    ) -> Any:
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

    def get_object(self, bucket_name: str, object_name: str) -> HTTPResponse:
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

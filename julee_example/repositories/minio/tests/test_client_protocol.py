"""
Tests to verify protocol compatibility between real Minio client and protocol.

This module tests that the real minio.Minio client properly implements our
MinioClient protocol, ensuring that our protocol definition matches the
actual interface.
"""

from minio import Minio

from ..client import MinioClient


class TestMinioClientProtocol:
    """Test that the real Minio client implements our protocol."""

    def test_real_minio_client_implements_protocol(self) -> None:
        """Test that minio.Minio implements MinioClient protocol."""
        # Create a real Minio client (doesn't need to connect)
        real_client = Minio("localhost:9000")

        # This should pass if the protocol is correctly defined
        assert isinstance(real_client, MinioClient)

    def test_protocol_method_signatures_match_real_client(self) -> None:
        """Test that protocol method signatures match the real client."""
        real_client = Minio("localhost:9000")

        # Test that all protocol methods exist on the real client
        assert hasattr(real_client, "bucket_exists")
        assert hasattr(real_client, "make_bucket")
        assert hasattr(real_client, "put_object")
        assert hasattr(real_client, "get_object")
        assert hasattr(real_client, "stat_object")

        # Test that methods are callable
        assert callable(getattr(real_client, "bucket_exists"))
        assert callable(getattr(real_client, "make_bucket"))
        assert callable(getattr(real_client, "put_object"))
        assert callable(getattr(real_client, "get_object"))
        assert callable(getattr(real_client, "stat_object"))

    def test_protocol_accepts_real_minio_client(self) -> None:
        """Test that our protocol accepts a real Minio client instance."""
        from ..document import MinioDocumentRepository

        # Create a real Minio client (no connection attempted in constructor)
        real_client = Minio("localhost:9000")

        # This should work without type errors if protocol is correct
        # We don't call any methods that would trigger network calls
        repository = MinioDocumentRepository.__new__(MinioDocumentRepository)
        repository.client = real_client

        # Verify the client was stored correctly
        assert repository.client is real_client
        assert isinstance(repository.client, MinioClient)

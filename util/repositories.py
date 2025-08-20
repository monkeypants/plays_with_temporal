from typing import Protocol, Optional, runtime_checkable
from util.domain import FileMetadata, FileUploadArgs


@runtime_checkable
class FileStorageRepository(Protocol):
    """Handles storage and retrieval of large files/payloads.

    Architectural Purpose:
    This repository is designed to manage large data payloads that might
    exceed Temporal's payload size limits or are better stored externally.
    It allows workflows to store references to files rather than the files
    themselves, maintaining workflow determinism while handling large data.
    """

    async def upload_file(self, args: FileUploadArgs) -> FileMetadata:
        """Upload a file to storage.

        Args:
            args: FileUploadArgs containing file_id, data, and metadata.

        Returns:
            FileMetadata object with details about the uploaded file.

        Implementation Notes:
        - Must be idempotent: uploading the same file_id multiple times is
          safe.
        - Should return metadata including the actual size and content type.
        - Must perform security validation: file size limits, content type
          verification, and filename sanitization.
        - Should reject files that don't match declared content type.
        """
        ...

    async def download_file(self, file_id: str) -> Optional[bytes]:
        """Download a file from storage by its ID.

        Args:
            file_id: Unique identifier of the file.

        Returns:
            File content as bytes if found, None otherwise.
        """
        ...

    async def get_file_metadata(self, file_id: str) -> Optional[FileMetadata]:
        """Retrieve metadata for a stored file.

        Args:
            file_id: Unique identifier of the file.

        Returns:
            FileMetadata object if found, None otherwise.
        """
        ...

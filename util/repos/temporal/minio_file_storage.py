import logging
from typing import Optional

from temporalio import activity

from util.domain import FileMetadata, FileUploadArgs
from util.repositories import FileStorageRepository
from util.repos.minio.file_storage import MinioFileStorageRepository

logger = logging.getLogger(__name__)


class TemporalMinioFileStorageRepository(FileStorageRepository):
    """
    Temporal Activity implementation of FileStorageRepository.
    Delegates calls to a concrete MinioFileStorageRepository instance.
    """

    def __init__(
        self,
        file_storage_repo: MinioFileStorageRepository,
    ):
        self._file_storage_repo = file_storage_repo
        logger.debug("Initialized TemporalMinioFileStorageRepository")

    @activity.defn(name="util.file_storage.minio.upload_file")
    async def upload_file(self, args: FileUploadArgs) -> FileMetadata:
        """Upload a file via the underlying Minio repository."""
        logger.info(
            "Activity: util.file_storage.minio.upload_file called",
            extra={"file_id": args.file_id, "filename": args.filename},
        )
        return await self._file_storage_repo.upload_file(args)

    @activity.defn(name="util.file_storage.minio.download_file")
    async def download_file(self, file_id: str) -> Optional[bytes]:
        """Download a file via the underlying Minio repository."""
        logger.info(
            "Activity: util.file_storage.minio.download_file called",
            extra={"file_id": file_id},
        )
        return await self._file_storage_repo.download_file(file_id)

    @activity.defn(name="util.file_storage.minio.get_file_metadata")
    async def get_file_metadata(self, file_id: str) -> Optional[FileMetadata]:
        """Retrieve file metadata via the underlying Minio repository."""
        logger.info(
            "Activity: util.file_storage.minio.get_file_metadata called",
            extra={"file_id": file_id},
        )
        return await self._file_storage_repo.get_file_metadata(file_id)

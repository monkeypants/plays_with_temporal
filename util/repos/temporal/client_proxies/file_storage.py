import logging
from typing import Optional

from temporalio.client import Client

from util.domain import FileMetadata, FileUploadArgs
from util.repositories import FileStorageRepository

logger = logging.getLogger(__name__)


class TemporalFileStorageRepository(FileStorageRepository):
    """
    Client-side proxy for FileStorageRepository that calls activities.
    This proxy ensures that all interactions with the FileStorageRepository
    are performed via Temporal activities, maintaining workflow determinism.
    """

    def __init__(
        self,
        client: Client,
        concrete_repo: Optional[FileStorageRepository] = None,
    ):
        self.client = client
        self.concrete_repo = concrete_repo
        logger.debug("Initialized TemporalFileStorageRepository")

    async def upload_file(self, args: FileUploadArgs) -> FileMetadata:
        """Upload a file via Temporal activity."""
        logger.debug(
            f"Client calling activity to upload file: {args.file_id}"
        )

        handle = await self.client.start_workflow(
            "util.file_storage.minio.upload_file",
            args,
            id=f"upload-{args.file_id}",
            task_queue="order-fulfillment-queue",
        )

        result = await handle.result()
        return result  # type: ignore[no-any-return]

    async def download_file(self, file_id: str) -> Optional[bytes]:
        """Download a file via Temporal activity."""
        logger.debug(f"Client calling activity to download file: {file_id}")

        handle = await self.client.start_workflow(
            "util.file_storage.minio.download_file",
            file_id,
            id=f"download-{file_id}",
            task_queue="order-fulfillment-queue",
        )

        result = await handle.result()
        return result  # type: ignore[no-any-return]

    async def get_file_metadata(self, file_id: str) -> Optional[FileMetadata]:
        """Retrieve file metadata via Temporal activity."""
        logger.debug(
            f"Client calling activity to get file metadata: {file_id}"
        )

        handle = await self.client.start_workflow(
            "util.file_storage.minio.get_file_metadata",
            file_id,
            id=f"metadata-{file_id}",
            task_queue="order-fulfillment-queue",
        )

        result = await handle.result()
        return result  # type: ignore[no-any-return]

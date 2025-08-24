import logging
from typing import Optional

from temporalio import workflow

from util.domain import FileMetadata, FileUploadArgs
from util.repositories import FileStorageRepository

logger = logging.getLogger(__name__)


class WorkflowFileStorageRepositoryProxy(FileStorageRepository):
    """
    Workflow implementation of FileStorageRepository that calls activities.
    This proxy ensures that all interactions with the FileStorageRepository
    are performed via Temporal activities, maintaining workflow determinism.
    """

    def __init__(self) -> None:
        # Activity timeout can be configured, but for simplicity, we use a
        # default here or could retrieve from workflow config.
        # This timeout should be generous enough for large file transfers.
        self.activity_timeout = workflow.timedelta(seconds=600)  # 10 minutes
        logger.debug("Initialized WorkflowFileStorageRepositoryProxy")

    async def upload_file(self, args: FileUploadArgs) -> FileMetadata:
        """Upload a file to storage via Temporal activity."""
        logger.debug(
            f"Workflow calling activity to upload file: {args.file_id}"
        )
        # The activity name follows the general util pattern:
        # {domain}.{subdomain}.{implementation}.{method}
        result = await workflow.execute_activity(
            "util.file_storage.minio.upload_file",
            args,
            start_to_close_timeout=self.activity_timeout,
        )
        return FileMetadata.model_validate(result)

    async def download_file(self, file_id: str) -> Optional[bytes]:
        """Download a file from storage via Temporal activity."""
        logger.debug(f"Workflow calling activity to download file: {file_id}")
        result = await workflow.execute_activity(
            "util.file_storage.minio.download_file",
            file_id,
            start_to_close_timeout=self.activity_timeout,
        )
        return result  # type: ignore[no-any-return]

    async def get_file_metadata(self, file_id: str) -> Optional[FileMetadata]:
        """Retrieve file metadata via Temporal activity."""
        logger.debug(
            f"Workflow calling activity to get file metadata: {file_id}"
        )
        result = await workflow.execute_activity(
            "util.file_storage.minio.get_file_metadata",
            file_id,
            start_to_close_timeout=self.activity_timeout,
        )
        if result is None:
            return None
        return FileMetadata.model_validate(result)

import logging
import os
from typing import Optional, Dict

from minio import Minio
from minio.error import S3Error

from util.domain import FileMetadata, FileUploadArgs
from util.repositories import FileStorageRepository

logger = logging.getLogger(__name__)


class MinioFileStorageRepository(FileStorageRepository):
    """
    Minio implementation of FileStorageRepository.
    Uses Minio for persistence of large files/payloads.
    """

    def __init__(
        self,
        endpoint: Optional[str] = None,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        secure: bool = False,
        bucket_name: Optional[str] = None,
    ):
        self._endpoint = endpoint or os.environ.get("MINIO_ENDPOINT", "localhost:9000")
        self._access_key = access_key or os.environ.get("MINIO_ROOT_USER", "minioadmin")
        self._secret_key = secret_key or os.environ.get("MINIO_ROOT_PASSWORD", "minioadmin")
        self._secure = secure
        self._bucket_name = bucket_name or os.environ.get("MINIO_BUCKET_NAME", "file-storage")
        
        self._client: Optional[Minio] = None
        logger.debug(
            "MinioFileStorageRepository initialized",
            extra={
                "endpoint": self._endpoint,
                "bucket_name": self._bucket_name,
            },
        )

    async def _get_client(self) -> Minio:
        """Lazily initialize and return the Minio client."""
        if self._client is None:
            logger.debug(
                "Creating new Minio client instance",
                extra={"endpoint": self._endpoint, "secure": self._secure},
            )
            self._client = Minio(
                self._endpoint,
                access_key=self._access_key,
                secret_key=self._secret_key,
                secure=self._secure,
            )
            try:
                # Ensure bucket exists
                if not self._client.bucket_exists(self._bucket_name):
                    logger.info(
                        "Minio bucket does not exist, creating now",
                        extra={"bucket_name": self._bucket_name},
                    )
                    self._client.make_bucket(self._bucket_name)
                else:
                    logger.debug(
                        "Minio bucket already exists",
                        extra={"bucket_name": self._bucket_name},
                    )
            except S3Error as e:
                logger.error(
                    f"Error checking or creating Minio bucket: {e}",
                    extra={"bucket_name": self._bucket_name, "error_code": e.code},
                )
                raise
        return self._client

    async def upload_file(self, args: FileUploadArgs) -> FileMetadata:
        """Upload a file to Minio storage."""
        client = await self._get_client()
        logger.info(
            "Uploading file to Minio",
            extra={
                "file_id": args.file_id,
                "filename": args.filename,
                "content_type": args.content_type,
                "size_bytes": len(args.data),
            },
        )
        try:
            # Minio put_object is idempotent if object name is the same
            client.put_object(
                self._bucket_name,
                args.file_id,
                args.data,
                len(args.data),
                content_type=args.content_type,
                metadata=args.metadata,
            )
            logger.info(
                "File uploaded successfully to Minio",
                extra={"file_id": args.file_id},
            )
            return FileMetadata(
                file_id=args.file_id,
                filename=args.filename,
                content_type=args.content_type,
                size_bytes=len(args.data),
                metadata=args.metadata,
            )
        except S3Error as e:
            logger.error(
                f"Error uploading file to Minio: {e}",
                extra={"file_id": args.file_id, "error_code": e.code},
            )
            raise

    async def download_file(self, file_id: str) -> Optional[bytes]:
        """Download a file from Minio storage by its ID."""
        client = await self._get_client()
        logger.info(
            "Attempting to download file from Minio",
            extra={"file_id": file_id},
        )
        try:
            response = client.get_object(self._bucket_name, file_id)
            file_data = response.read()
            response.close()
            response.release_conn()
            logger.info(
                "File downloaded successfully from Minio",
                extra={"file_id": file_id, "size_bytes": len(file_data)},
            )
            return file_data
        except S3Error as e:
            if e.code == "NoSuchKey":
                logger.warning(
                    "File not found in Minio", extra={"file_id": file_id}
                )
                return None
            logger.error(
                f"Error downloading file from Minio: {e}",
                extra={"file_id": file_id, "error_code": e.code},
            )
            raise

    async def get_file_metadata(self, file_id: str) -> Optional[FileMetadata]:
        """Retrieve metadata for a stored file from Minio."""
        client = await self._get_client()
        logger.info(
            "Attempting to get file metadata from Minio",
            extra={"file_id": file_id},
        )
        try:
            stat = client.stat_object(self._bucket_name, file_id)
            logger.info(
                "File metadata retrieved successfully from Minio",
                extra={
                    "file_id": file_id,
                    "size_bytes": stat.size,
                    "content_type": stat.content_type,
                },
            )
            return FileMetadata(
                file_id=file_id,
                filename=stat.user_metadata.get("X-Amz-Meta-Filename"),  # Minio prepends X-Amz-Meta-
                content_type=stat.content_type,
                size_bytes=stat.size,
                uploaded_at=stat.last_modified.isoformat() if stat.last_modified else None,
                metadata={k.replace("X-Amz-Meta-", ""): v for k,v in stat.user_metadata.items()} if stat.user_metadata else {}
            )
        except S3Error as e:
            if e.code == "NoSuchKey":
                logger.warning(
                    "File metadata not found in Minio",
                    extra={"file_id": file_id},
                )
                return None
            logger.error(
                f"Error getting file metadata from Minio: {e}",
                extra={"file_id": file_id, "error_code": e.code},
            )
            raise

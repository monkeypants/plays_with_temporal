from pydantic import (
    BaseModel,
    Field,
    field_validator,
)
from typing import Optional, Dict
from datetime import datetime, timezone


class FileMetadata(BaseModel):
    """Metadata about a stored file."""

    file_id: str
    filename: Optional[str] = None
    content_type: Optional[str] = None
    size_bytes: Optional[int] = None
    uploaded_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    metadata: Dict[str, str] = Field(default_factory=dict)


class FileUploadArgs(BaseModel):
    """
    Arguments for file upload with security validation.

    This model enforces security constraints at the domain level,
    ensuring that all file uploads are validated before reaching
    the repository layer.
    """

    file_id: str
    filename: str
    data: bytes
    content_type: str
    metadata: dict = Field(default_factory=dict)

    @field_validator("filename")
    @classmethod
    def validate_filename(cls, v: str) -> str:
        """Validate and sanitize filename to prevent path traversal
        attacks."""
        import os

        if not v or not v.strip():
            raise ValueError("Filename cannot be empty")

        # Remove any path components to prevent directory traversal
        sanitized = os.path.basename(v.strip())

        # Check for dangerous patterns
        dangerous_patterns = [
            "..",
            "~",
            "$",
            "`",
            "|",
            "&",
            ";",
            "(",
            ")",
            "{",
            "}",
            "[",
            "]",
        ]
        for pattern in dangerous_patterns:
            if pattern in sanitized:
                raise ValueError(
                    f"Filename contains dangerous pattern: {pattern}"
                )

        # Ensure filename has reasonable length
        if len(sanitized) > 255:
            raise ValueError("Filename too long (max 255 characters)")

        # Ensure filename is not empty after sanitization
        if not sanitized:
            raise ValueError("Filename is empty after sanitization")

        return sanitized

    @field_validator("data")
    @classmethod
    def validate_file_size(cls, v: bytes) -> bytes:
        """Validate file size to prevent resource exhaustion."""
        max_size = 50 * 1024 * 1024  # 50MB limit
        if len(v) > max_size:
            raise ValueError(
                f"File size {len(v)} bytes exceeds maximum allowed size of "
                f"{max_size} bytes"
            )

        if len(v) == 0:
            raise ValueError("File cannot be empty")

        return v

    @field_validator("content_type")
    @classmethod
    def validate_content_type(cls, v: str) -> str:
        """Validate content type against allowed types."""
        allowed_types = {
            "text/plain",
            "text/csv",
            "application/json",
            "application/pdf",
            "image/jpeg",
            "image/png",
            "image/gif",
            "application/zip",
            "application/octet-stream",
        }

        if v not in allowed_types:
            raise ValueError(
                f"Content type '{v}' not allowed. Allowed types: "
                f"{', '.join(sorted(allowed_types))}"
            )

        return v

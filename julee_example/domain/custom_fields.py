"""
Custom Pydantic field types for the CEAP workflow domain.

This module contains custom field types that provide proper Pydantic
validation
for specialized data types used in the document processing workflow.
"""

from pydantic import GetCoreSchemaHandler
from pydantic_core import core_schema
from typing import Any
import io


class ContentStream:
    """Wrapper for IO streams that provides proper Pydantic validation.

    This class wraps io.IOBase instances to provide proper Pydantic validation
    without requiring arbitrary_types_allowed. It ensures that only valid
    stream objects are accepted while providing a clean interface for
    stream operations.
    """

    def __init__(self, stream: io.IOBase):
        if not isinstance(stream, io.IOBase):
            raise ValueError(
                "ContentStream requires an io.IOBase instance, "
                + f"got {type(stream)}"
            )
        self._stream = stream

    def read(self, size: int = -1) -> bytes:
        """Read from the underlying stream."""
        result = self.stream.read(size)
        if not isinstance(result, bytes):
            # Handle case where stream returns str (like StringIO)
            if isinstance(result, str):
                return result.encode("utf-8")
            return b""  # Fallback for other types
        return result

    def seek(self, offset: int, whence: int = 0) -> int:
        """Seek in the underlying stream."""
        return self._stream.seek(offset, whence)

    def tell(self) -> int:
        """Get current position in stream."""
        return self._stream.tell()

    @property
    def stream(self) -> io.IOBase:
        """Access the underlying stream."""
        return self._stream

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: type, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        """Define how Pydantic should validate this type."""
        return core_schema.no_info_plain_validator_function(cls._validate)

    @classmethod
    def _validate(cls, value: Any) -> "ContentStream":
        """Validate input and convert to ContentStream."""
        if isinstance(value, cls):
            return value
        if isinstance(value, io.IOBase):
            return cls(value)
        raise ValueError(
            f"ContentStream expects io.IOBase, got {type(value)}"
        )

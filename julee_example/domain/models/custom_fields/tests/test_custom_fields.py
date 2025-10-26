"""
Tests for custom Pydantic field types.

This test module validates the behavior of custom field types used in
the domain models, particularly focusing on ContentStream which wraps
io.IOBase instances for proper Pydantic validation.

Design decisions documented:
- ContentStream accepts any io.IOBase instance
- ContentStream provides read, seek, tell interface
- ContentStream validates input types at creation
- ContentStream works with Pydantic validation without arbitrary_types_allowed
"""

import pytest
import io
from typing import Any

from julee_example.domain.models.custom_fields.content_stream import (
    ContentStream,
)


@pytest.mark.parametrize(
    "stream_input,error_message",
    [
        # Valid inputs - io.IOBase instances
        (io.BytesIO(b"test content"), None),
        (io.StringIO("text content"), None),
        (io.BufferedReader(io.BytesIO(b"buffered")), None),
        (ContentStream(io.BytesIO(b"nested content")).stream, None),
        # Invalid inputs - not io.IOBase
        (b"raw bytes", "ContentStream requires an io.IOBase instance"),
        ("string", "ContentStream requires an io.IOBase instance"),
        (123, "ContentStream requires an io.IOBase instance"),
        (None, "ContentStream requires an io.IOBase instance"),
        ([], "ContentStream requires an io.IOBase instance"),
        ({}, "ContentStream requires an io.IOBase instance"),
    ],
)
def test_content_stream_validation(
    stream_input: Any, error_message: str | None
) -> None:
    """Test ContentStream validation with various input types including nested
    streams."""
    if error_message is None:
        # Should create successfully
        content_stream = ContentStream(stream_input)
        assert content_stream.stream is stream_input
    else:
        # Should raise ValueError with specific message
        with pytest.raises(ValueError, match=error_message):
            ContentStream(stream_input)

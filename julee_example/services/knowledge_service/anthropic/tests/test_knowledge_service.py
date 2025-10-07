"""
Tests for AnthropicKnowledgeService implementation.

This module contains tests for the Anthropic implementation of the
KnowledgeService protocol, verifying file registration and query
execution functionality.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
import io

from julee_example.domain.models.knowledge_service_config import (
    KnowledgeServiceConfig,
)
from julee_example.domain.models.document import Document, DocumentStatus
from julee_example.domain.models.knowledge_service_config import ServiceApi
from julee_example.domain.models.custom_fields.content_stream import (
    ContentStream,
)
from julee_example.services.knowledge_service.anthropic import (
    knowledge_service as anthropic_ks,
)
from julee_example.services.knowledge_service.anthropic import (
    knowledge_service as anthropic_ks_module,
)


@pytest.fixture
def test_document() -> Document:
    """Create a test Document for testing."""
    content_text = (
        "This is test document content for knowledge service testing."
    )
    content_bytes = content_text.encode("utf-8")
    content_stream = ContentStream(io.BytesIO(content_bytes))

    return Document(
        document_id="test-doc-123",
        original_filename="test_document.txt",
        content_type="text/plain",
        size_bytes=len(content_bytes),
        content_multihash="test-hash-123",
        status=DocumentStatus.CAPTURED,
        content=content_stream,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def knowledge_service_config() -> KnowledgeServiceConfig:
    """Create a test KnowledgeServiceConfig for Anthropic."""
    return KnowledgeServiceConfig(
        knowledge_service_id="ks-anthropic-test",
        name="Test Anthropic Service",
        description="Anthropic service for testing",
        service_api=ServiceApi.ANTHROPIC,
    )


@pytest.fixture
def mock_anthropic_client() -> MagicMock:
    """Create a mock Anthropic client."""
    mock_client = MagicMock()

    # Mock the messages.create response
    mock_response = MagicMock()
    mock_content_block = MagicMock()
    mock_content_block.type = "text"
    mock_content_block.text = "This is a test response from Anthropic."
    mock_response.content = [mock_content_block]
    mock_response.usage.input_tokens = 150
    mock_response.usage.output_tokens = 25
    mock_response.stop_reason = "end_turn"

    mock_client.messages.create = AsyncMock(return_value=mock_response)

    return mock_client


class TestAnthropicKnowledgeService:
    """Test cases for AnthropicKnowledgeService."""

    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"})
    async def test_execute_query_without_files(
        self,
        knowledge_service_config: KnowledgeServiceConfig,
        mock_anthropic_client: MagicMock,
    ) -> None:
        """Test execute_query without service file IDs."""
        with patch(
            "julee_example.services.knowledge_service.anthropic.knowledge_service.AsyncAnthropic"
        ) as mock_anthropic:
            mock_anthropic.return_value = mock_anthropic_client

            service = anthropic_ks.AnthropicKnowledgeService()

            query_text = "What is machine learning?"
            result = await service.execute_query(
                knowledge_service_config, query_text
            )

            # Verify the result structure
            assert result.query_text == query_text
            assert (
                result.result_data["response"]
                == "This is a test response from Anthropic."
            )
            assert (
                result.result_data["model"]
                == anthropic_ks_module.DEFAULT_MODEL
            )
            assert result.result_data["service"] == "anthropic"
            assert result.result_data["sources"] == []
            assert result.result_data["usage"]["input_tokens"] == 150
            assert result.result_data["usage"]["output_tokens"] == 25
            assert result.result_data["stop_reason"] == "end_turn"
            assert result.execution_time_ms is not None
            assert result.execution_time_ms >= 0
            assert isinstance(result.created_at, datetime)

            # Verify the API call was made correctly
            mock_anthropic_client.messages.create.assert_called_once()
            call_args = mock_anthropic_client.messages.create.call_args
            assert call_args[1]["model"] == anthropic_ks_module.DEFAULT_MODEL
            assert (
                call_args[1]["max_tokens"]
                == anthropic_ks_module.DEFAULT_MAX_TOKENS
            )
            assert len(call_args[1]["messages"]) == 1
            assert call_args[1]["messages"][0]["role"] == "user"

            # Should have only one content part (the text query)
            content_parts = call_args[1]["messages"][0]["content"]
            assert len(content_parts) == 1
            assert content_parts[0]["type"] == "text"
            assert content_parts[0]["text"] == query_text

    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"})
    async def test_execute_query_with_files(
        self,
        knowledge_service_config: KnowledgeServiceConfig,
        mock_anthropic_client: MagicMock,
    ) -> None:
        """Test execute_query with service file IDs."""
        with patch(
            "julee_example.services.knowledge_service.anthropic.knowledge_service.AsyncAnthropic"
        ) as mock_anthropic:
            mock_anthropic.return_value = mock_anthropic_client

            service = anthropic_ks.AnthropicKnowledgeService()

            query_text = "What is in the document?"
            service_file_ids = ["file_123", "file_456"]
            result = await service.execute_query(
                knowledge_service_config,
                query_text,
                service_file_ids=service_file_ids,
            )

            # Verify the result structure
            assert result.query_text == query_text
            assert result.result_data["sources"] == service_file_ids
            assert result.execution_time_ms is not None
            assert result.execution_time_ms >= 0

            # Verify the API call was made with file attachments
            mock_anthropic_client.messages.create.assert_called_once()
            call_args = mock_anthropic_client.messages.create.call_args

            # Should have file attachments plus text query
            content_parts = call_args[1]["messages"][0]["content"]
            assert len(content_parts) == 3  # 2 files + 1 text query

            # Check file attachments
            assert content_parts[0]["type"] == "document"
            assert content_parts[0]["source"]["type"] == "file"
            assert content_parts[0]["source"]["file_id"] == "file_123"

            assert content_parts[1]["type"] == "document"
            assert content_parts[1]["source"]["type"] == "file"
            assert content_parts[1]["source"]["file_id"] == "file_456"

            # Check text query
            assert content_parts[2]["type"] == "text"
            assert content_parts[2]["text"] == query_text

    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"})
    async def test_execute_query_handles_api_error(
        self,
        knowledge_service_config: KnowledgeServiceConfig,
    ) -> None:
        """Test execute_query handles API errors gracefully."""
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(
            side_effect=Exception("API Error")
        )

        with patch(
            "julee_example.services.knowledge_service.anthropic.knowledge_service.AsyncAnthropic"
        ) as mock_anthropic:
            mock_anthropic.return_value = mock_client

            service = anthropic_ks.AnthropicKnowledgeService()

            with pytest.raises(Exception):
                await service.execute_query(
                    knowledge_service_config, "Test query"
                )

    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"})
    async def test_query_id_generation(
        self,
        knowledge_service_config: KnowledgeServiceConfig,
        mock_anthropic_client: MagicMock,
    ) -> None:
        """Test that query IDs are unique and properly formatted."""
        with patch(
            "julee_example.services.knowledge_service.anthropic.knowledge_service.AsyncAnthropic"
        ) as mock_anthropic:
            mock_anthropic.return_value = mock_anthropic_client

            service = anthropic_ks.AnthropicKnowledgeService()

            # Execute two queries
            result1 = await service.execute_query(
                knowledge_service_config, "First query"
            )
            result2 = await service.execute_query(
                knowledge_service_config, "Second query"
            )

            # Query IDs should be unique and follow expected format
            assert result1.query_id != result2.query_id
            assert result1.query_id.startswith("anthropic_")
            assert result2.query_id.startswith("anthropic_")
            assert (
                len(result1.query_id) == len("anthropic_") + 12
            )  # UUID hex[:12]
            assert len(result2.query_id) == len("anthropic_") + 12

    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"})
    async def test_empty_service_file_ids(
        self,
        knowledge_service_config: KnowledgeServiceConfig,
        mock_anthropic_client: MagicMock,
    ) -> None:
        """Test execute_query with empty service_file_ids list."""
        with patch(
            "julee_example.services.knowledge_service.anthropic.knowledge_service.AsyncAnthropic"
        ) as mock_anthropic:
            mock_anthropic.return_value = mock_anthropic_client

            service = anthropic_ks.AnthropicKnowledgeService()

            query_text = "What is in the document?"
            result = await service.execute_query(
                knowledge_service_config, query_text, service_file_ids=[]
            )

            # Should behave the same as None
            assert result.result_data["sources"] == []

            # Verify API call structure
            call_args = mock_anthropic_client.messages.create.call_args
            content_parts = call_args[1]["messages"][0]["content"]
            assert len(content_parts) == 1  # Only text query, no files
            assert content_parts[0]["type"] == "text"

    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"})
    async def test_execute_query_with_metadata(
        self,
        knowledge_service_config: KnowledgeServiceConfig,
        mock_anthropic_client: MagicMock,
    ) -> None:
        """Test execute_query with query_metadata configuration."""
        with patch(
            "julee_example.services.knowledge_service.anthropic.knowledge_service.AsyncAnthropic"
        ) as mock_anthropic:
            mock_anthropic.return_value = mock_anthropic_client

            service = anthropic_ks.AnthropicKnowledgeService()

            metadata = {
                "model": "claude-opus-4-1-20250805",
                "max_tokens": 2000,
                "temperature": 0.7,
            }

            query_text = "Custom query with metadata"
            result = await service.execute_query(
                knowledge_service_config, query_text, query_metadata=metadata
            )

            # Verify the result uses metadata values
            assert result.result_data["model"] == "claude-opus-4-1-20250805"
            assert result.execution_time_ms is not None
            assert result.execution_time_ms >= 0

            # Verify API call used metadata values
            mock_anthropic_client.messages.create.assert_called_once()
            call_args = mock_anthropic_client.messages.create.call_args
            assert call_args[1]["model"] == "claude-opus-4-1-20250805"
            assert call_args[1]["max_tokens"] == 2000
            assert call_args[1]["temperature"] == 0.7

    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"})
    async def test_execute_query_metadata_defaults(
        self,
        knowledge_service_config: KnowledgeServiceConfig,
        mock_anthropic_client: MagicMock,
    ) -> None:
        """Test execute_query uses default values when metadata is None."""
        with patch(
            "julee_example.services.knowledge_service.anthropic.knowledge_service.AsyncAnthropic"
        ) as mock_anthropic:
            mock_anthropic.return_value = mock_anthropic_client

            service = anthropic_ks.AnthropicKnowledgeService()

            result = await service.execute_query(
                knowledge_service_config, "Test query", query_metadata=None
            )

            # Verify defaults are used
            assert (
                result.result_data["model"]
                == anthropic_ks_module.DEFAULT_MODEL
            )

            # Verify API call used defaults
            call_args = mock_anthropic_client.messages.create.call_args
            assert call_args[1]["model"] == anthropic_ks_module.DEFAULT_MODEL
            assert (
                call_args[1]["max_tokens"]
                == anthropic_ks_module.DEFAULT_MAX_TOKENS
            )
            assert "temperature" not in call_args[1]  # Not set by default

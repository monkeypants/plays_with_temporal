"""
Tests for AnthropicKnowledgeService implementation.

This module contains tests for the Anthropic implementation of the
KnowledgeService protocol, verifying file registration and query
execution functionality.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from julee_example.domain import KnowledgeServiceConfig
from julee_example.domain.knowledge_service_config import ServiceApi
from julee_example.repositories.memory import MemoryDocumentRepository
from julee_example.services.knowledge_service.anthropic import (
    knowledge_service as anthropic_ks,
)


@pytest.fixture
def document_repo() -> MemoryDocumentRepository:
    """Create a MemoryDocumentRepository for testing."""
    return MemoryDocumentRepository()


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
def mock_anthropic_client():
    """Create a mock Anthropic client."""
    mock_client = MagicMock()

    # Mock the messages.create response
    mock_response = MagicMock()
    mock_response.content = [MagicMock()]
    mock_response.content[0].text = "This is a test response from Anthropic."
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
        document_repo: MemoryDocumentRepository,
        mock_anthropic_client,
    ) -> None:
        """Test execute_query without service file IDs."""
        with patch(
            "julee_example.services.knowledge_service.anthropic.knowledge_service.AsyncAnthropic"
        ) as mock_anthropic:
            mock_anthropic.return_value = mock_anthropic_client

            service = anthropic_ks.AnthropicKnowledgeService(
                knowledge_service_config, document_repo
            )

            query_text = "What is machine learning?"
            result = await service.execute_query(query_text)

            # Verify the result structure
            assert result.query_text == query_text
            assert (
                result.result_data["response"]
                == "This is a test response from Anthropic."
            )
            assert result.result_data["model"] == "claude-sonnet-4-20250514"
            assert result.result_data["service"] == "anthropic"
            assert result.result_data["sources"] == []
            assert result.result_data["usage"]["input_tokens"] == 150
            assert result.result_data["usage"]["output_tokens"] == 25
            assert result.result_data["stop_reason"] == "end_turn"
            assert result.execution_time_ms >= 0
            assert isinstance(result.created_at, datetime)

            # Verify the API call was made correctly
            mock_anthropic_client.messages.create.assert_called_once()
            call_args = mock_anthropic_client.messages.create.call_args
            assert call_args[1]["model"] == "claude-sonnet-4-20250514"
            assert call_args[1]["max_tokens"] == 4000
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
        document_repo: MemoryDocumentRepository,
        mock_anthropic_client,
    ) -> None:
        """Test execute_query with service file IDs."""
        with patch(
            "julee_example.services.knowledge_service.anthropic.knowledge_service.AsyncAnthropic"
        ) as mock_anthropic:
            mock_anthropic.return_value = mock_anthropic_client

            service = anthropic_ks.AnthropicKnowledgeService(
                knowledge_service_config, document_repo
            )

            query_text = "What is in these documents?"
            service_file_ids = ["file_123", "file_456"]

            result = await service.execute_query(
                query_text, service_file_ids=service_file_ids
            )

            # Verify the result structure
            assert result.query_text == query_text
            assert result.result_data["sources"] == service_file_ids
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
        document_repo: MemoryDocumentRepository,
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

            service = anthropic_ks.AnthropicKnowledgeService(
                knowledge_service_config, document_repo
            )

            with pytest.raises(Exception, match="API Error"):
                await service.execute_query("test query")

    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"})
    async def test_query_id_generation(
        self,
        knowledge_service_config: KnowledgeServiceConfig,
        document_repo: MemoryDocumentRepository,
        mock_anthropic_client,
    ) -> None:
        """Test that query IDs are unique and properly formatted."""
        with patch(
            "julee_example.services.knowledge_service.anthropic.knowledge_service.AsyncAnthropic"
        ) as mock_anthropic:
            mock_anthropic.return_value = mock_anthropic_client

            service = anthropic_ks.AnthropicKnowledgeService(
                knowledge_service_config, document_repo
            )

            # Execute two queries
            result1 = await service.execute_query("First query")
            result2 = await service.execute_query("Second query")

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
        document_repo: MemoryDocumentRepository,
        mock_anthropic_client,
    ) -> None:
        """Test execute_query with empty service_file_ids list."""
        with patch(
            "julee_example.services.knowledge_service.anthropic.knowledge_service.AsyncAnthropic"
        ) as mock_anthropic:
            mock_anthropic.return_value = mock_anthropic_client

            service = anthropic_ks.AnthropicKnowledgeService(
                knowledge_service_config, document_repo
            )

            query_text = "Test query"
            result = await service.execute_query(
                query_text, service_file_ids=[]
            )

            # Should behave the same as None
            assert result.result_data["sources"] == []

            # Verify API call structure
            call_args = mock_anthropic_client.messages.create.call_args
            content_parts = call_args[1]["messages"][0]["content"]
            assert len(content_parts) == 1  # Only text query, no files
            assert content_parts[0]["type"] == "text"

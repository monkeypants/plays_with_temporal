"""
Tests for AssembleDataUseCase.

This module provides tests for the data assembly use case, ensuring proper
business logic execution and repository interaction patterns following
the Clean Architecture principles.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from julee_example.use_cases.assemble_data import AssembleDataUseCase
from julee_example.domain import Assembly
from julee_example.repositories import (
    DocumentRepository,
    AssemblyRepository,
    AssemblySpecificationRepository,
)


class TestAssembleDataUseCase:
    """Test cases for AssembleDataUseCase business logic."""

    @pytest.fixture
    def mock_document_repo(self) -> DocumentRepository:
        """Create a mock DocumentRepository for testing."""
        mock = MagicMock(spec=DocumentRepository)
        return mock

    @pytest.fixture
    def mock_assembly_repo(self) -> AssemblyRepository:
        """Create a mock AssemblyRepository for testing."""
        mock = MagicMock(spec=AssemblyRepository)
        return mock

    @pytest.fixture
    def mock_assembly_specification_repo(
        self,
    ) -> AssemblySpecificationRepository:
        """Create a mock AssemblySpecificationRepository for testing."""
        mock = MagicMock(spec=AssemblySpecificationRepository)
        return mock

    @pytest.fixture
    def use_case(
        self,
        mock_document_repo: DocumentRepository,
        mock_assembly_repo: AssemblyRepository,
        mock_assembly_specification_repo: AssemblySpecificationRepository,
    ) -> AssembleDataUseCase:
        """Create AssembleDataUseCase with mocked dependencies."""
        return AssembleDataUseCase(
            document_repo=mock_document_repo,
            assembly_repo=mock_assembly_repo,
            assembly_specification_repo=mock_assembly_specification_repo,
        )

    @pytest.mark.asyncio
    async def test_assemble_data_generates_assembly_id(
        self,
        use_case: AssembleDataUseCase,
        mock_assembly_repo: AssemblyRepository,
    ) -> None:
        """Test that assemble_data generates a unique assembly ID."""
        # Arrange
        expected_assembly_id = "assembly-12345"
        document_id = "doc-456"
        assembly_specification_id = "spec-789"

        mock_assembly_repo.generate_id = AsyncMock(  # type: ignore[method-assign]
            return_value=expected_assembly_id
        )

        # Act
        result = await use_case.assemble_data(
            document_id=document_id,
            assembly_specification_id=assembly_specification_id,
        )

        # Assert
        mock_assembly_repo.generate_id.assert_called_once()
        assert isinstance(result, Assembly)
        assert result.assembly_id == expected_assembly_id
        assert result.assembly_specification_id == assembly_specification_id
        assert result.input_document_id == document_id
        from julee_example.domain import AssemblyStatus

        assert result.status == AssemblyStatus.PENDING
        assert result.iterations == []
        assert isinstance(result.created_at, datetime)
        assert isinstance(result.updated_at, datetime)

    @pytest.mark.asyncio
    async def test_assemble_data_propagates_id_generation_error(
        self,
        use_case: AssembleDataUseCase,
        mock_assembly_repo: AssemblyRepository,
    ) -> None:
        """Test that ID generation errors are properly propagated."""
        # Arrange
        document_id = "doc-456"
        assembly_specification_id = "spec-789"
        expected_error = RuntimeError("ID generation failed")

        mock_assembly_repo.generate_id = AsyncMock(side_effect=expected_error)  # type: ignore[method-assign]

        # Act & Assert
        with pytest.raises(RuntimeError, match="ID generation failed"):
            await use_case.assemble_data(
                document_id=document_id,
                assembly_specification_id=assembly_specification_id,
            )

        mock_assembly_repo.generate_id.assert_called_once()

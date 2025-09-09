"""
Tests for AssembleDataUseCase.

This module provides tests for the data assembly use case, ensuring proper
business logic execution and repository interaction patterns following
the Clean Architecture principles.
"""

import pytest
from unittest.mock import AsyncMock
from datetime import datetime

from julee_example.use_cases.assemble_data import AssembleDataUseCase
from julee_example.domain import Assembly, AssemblyStatus
from julee_example.repositories.memory import (
    MemoryDocumentRepository,
    MemoryAssemblyRepository,
    MemoryAssemblySpecificationRepository,
)


class TestAssembleDataUseCase:
    """Test cases for AssembleDataUseCase business logic."""

    @pytest.fixture
    def document_repo(self) -> MemoryDocumentRepository:
        """Create a memory DocumentRepository for testing."""
        return MemoryDocumentRepository()

    @pytest.fixture
    def assembly_repo(self) -> MemoryAssemblyRepository:
        """Create a memory AssemblyRepository for testing."""
        return MemoryAssemblyRepository()

    @pytest.fixture
    def assembly_specification_repo(
        self,
    ) -> MemoryAssemblySpecificationRepository:
        """Create a memory AssemblySpecificationRepository for testing."""
        return MemoryAssemblySpecificationRepository()

    @pytest.fixture
    def use_case(
        self,
        document_repo: MemoryDocumentRepository,
        assembly_repo: MemoryAssemblyRepository,
        assembly_specification_repo: MemoryAssemblySpecificationRepository,
    ) -> AssembleDataUseCase:
        """Create AssembleDataUseCase with memory repository dependencies."""
        return AssembleDataUseCase(
            document_repo=document_repo,
            assembly_repo=assembly_repo,
            assembly_specification_repo=assembly_specification_repo,
        )

    @pytest.mark.asyncio
    async def test_assemble_data_generates_assembly_id(
        self, use_case: AssembleDataUseCase
    ) -> None:
        """Test that assemble_data generates a unique assembly ID."""
        # Arrange
        document_id = "doc-456"
        assembly_specification_id = "spec-789"

        # Act
        result = await use_case.assemble_data(
            document_id=document_id,
            assembly_specification_id=assembly_specification_id,
        )

        # Assert
        assert isinstance(result, Assembly)
        assert result.assembly_id is not None
        assert result.assembly_id.startswith("assembly-")
        assert result.assembly_specification_id == assembly_specification_id
        assert result.input_document_id == document_id
        assert result.status == AssemblyStatus.PENDING
        assert result.iterations == []
        assert isinstance(result.created_at, datetime)
        assert isinstance(result.updated_at, datetime)

    @pytest.mark.asyncio
    async def test_assemble_data_multiple_calls_generate_different_ids(
        self, use_case: AssembleDataUseCase
    ) -> None:
        """Test that multiple calls to assemble_data generate different
        assembly IDs."""
        # Arrange
        document_id_1 = "doc-456"
        document_id_2 = "doc-789"
        assembly_specification_id = "spec-123"

        # Act
        result_1 = await use_case.assemble_data(
            document_id=document_id_1,
            assembly_specification_id=assembly_specification_id,
        )
        result_2 = await use_case.assemble_data(
            document_id=document_id_2,
            assembly_specification_id=assembly_specification_id,
        )

        # Assert
        assert result_1.assembly_id != result_2.assembly_id
        assert result_1.input_document_id == document_id_1
        assert result_2.input_document_id == document_id_2
        assert result_1.assembly_specification_id == assembly_specification_id
        assert result_2.assembly_specification_id == assembly_specification_id

    @pytest.mark.asyncio
    async def test_assemble_data_propagates_id_generation_error(
        self,
        use_case: AssembleDataUseCase,
        assembly_repo: MemoryAssemblyRepository,
    ) -> None:
        """Test that ID generation errors are properly propagated."""
        # Arrange
        document_id = "doc-456"
        assembly_specification_id = "spec-789"
        expected_error = RuntimeError("ID generation failed")

        # Mock the generate_id method to raise an error
        assembly_repo.generate_id = AsyncMock(  # type: ignore[method-assign]
            side_effect=expected_error
        )

        # Act & Assert
        with pytest.raises(RuntimeError, match="ID generation failed"):
            await use_case.assemble_data(
                document_id=document_id,
                assembly_specification_id=assembly_specification_id,
            )

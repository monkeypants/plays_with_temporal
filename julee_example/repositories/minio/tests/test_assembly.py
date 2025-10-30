"""
Tests for MinioAssemblyRepository implementation.

This module provides comprehensive tests for the Minio-based assembly
repository implementation, using the fake client to avoid external
dependencies during testing.
"""

import pytest
from datetime import datetime, timezone

from julee_example.domain.models.assembly import Assembly, AssemblyStatus
from julee_example.repositories.minio.assembly import MinioAssemblyRepository
from .fake_client import FakeMinioClient


@pytest.fixture
def fake_client() -> FakeMinioClient:
    """Create a fresh fake Minio client for each test."""
    return FakeMinioClient()


@pytest.fixture
def assembly_repo(fake_client: FakeMinioClient) -> MinioAssemblyRepository:
    """Create assembly repository with fake client."""
    return MinioAssemblyRepository(fake_client)


@pytest.fixture
def sample_assembly() -> Assembly:
    """Create a sample assembly for testing."""
    return Assembly(
        assembly_id="test-assembly-123",
        assembly_specification_id="spec-456",
        input_document_id="input-doc-789",
        workflow_id="test-workflow-123",
        status=AssemblyStatus.PENDING,
        assembled_document_id=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


class TestMinioAssemblyRepositoryBasicOperations:
    """Test basic CRUD operations on assemblies."""

    @pytest.mark.asyncio
    async def test_save_and_get_assembly(
        self,
        assembly_repo: MinioAssemblyRepository,
        sample_assembly: Assembly,
    ) -> None:
        """Test saving and retrieving an assembly."""
        # Save assembly
        await assembly_repo.save(sample_assembly)

        # Retrieve assembly
        retrieved = await assembly_repo.get(sample_assembly.assembly_id)

        assert retrieved is not None
        assert retrieved.assembly_id == sample_assembly.assembly_id
        assert (
            retrieved.assembly_specification_id
            == sample_assembly.assembly_specification_id
        )
        assert (
            retrieved.input_document_id == sample_assembly.input_document_id
        )
        assert retrieved.status == sample_assembly.status
        assert retrieved.assembled_document_id is None

    @pytest.mark.asyncio
    async def test_get_nonexistent_assembly(
        self, assembly_repo: MinioAssemblyRepository
    ) -> None:
        """Test retrieving a non-existent assembly returns None."""
        result = await assembly_repo.get("nonexistent-assembly")
        assert result is None

    @pytest.mark.asyncio
    async def test_generate_id(
        self, assembly_repo: MinioAssemblyRepository
    ) -> None:
        """Test generating unique assembly IDs."""
        id1 = await assembly_repo.generate_id()
        id2 = await assembly_repo.generate_id()

        assert isinstance(id1, str)
        assert isinstance(id2, str)
        assert id1 != id2
        assert len(id1) > 0
        assert len(id2) > 0


class TestMinioAssemblyRepositoryDirectCompletion:
    """Test assembly completion using direct field assignment."""

    @pytest.mark.asyncio
    async def test_complete_assembly_with_direct_assignment(
        self,
        assembly_repo: MinioAssemblyRepository,
        sample_assembly: Assembly,
    ) -> None:
        """Test completing assembly using direct field assignment + save."""
        # Save initial assembly
        await assembly_repo.save(sample_assembly)

        # Complete assembly using direct assignment (new approach)
        sample_assembly.assembled_document_id = "output-doc-123"
        sample_assembly.status = AssemblyStatus.COMPLETED
        await assembly_repo.save(sample_assembly)

        # Verify completion by retrieving again
        retrieved = await assembly_repo.get(sample_assembly.assembly_id)
        assert retrieved is not None
        assert retrieved.assembled_document_id == "output-doc-123"
        assert retrieved.status == AssemblyStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_assembly_completion_idempotency(
        self,
        assembly_repo: MinioAssemblyRepository,
        sample_assembly: Assembly,
    ) -> None:
        """Test that direct assignment approach maintains idempotency."""
        # Save initial assembly
        await assembly_repo.save(sample_assembly)

        # Complete assembly first time
        sample_assembly.assembled_document_id = "output-doc-456"
        sample_assembly.status = AssemblyStatus.COMPLETED
        await assembly_repo.save(sample_assembly)

        first_updated_at = sample_assembly.updated_at

        # "Complete" same assembly again with same values (idempotent)
        sample_assembly.assembled_document_id = "output-doc-456"
        sample_assembly.status = AssemblyStatus.COMPLETED
        await assembly_repo.save(sample_assembly)

        # Verify state and that updated_at changed (save updates timestamp)
        retrieved = await assembly_repo.get(sample_assembly.assembly_id)
        assert retrieved is not None
        assert retrieved.assembled_document_id == "output-doc-456"
        assert retrieved.status == AssemblyStatus.COMPLETED
        assert retrieved.updated_at is not None
        assert first_updated_at is not None
        assert retrieved.updated_at > first_updated_at


class TestMinioAssemblyRepositoryStatusUpdates:
    """Test assembly status management."""

    @pytest.mark.asyncio
    async def test_update_assembly_status(
        self,
        assembly_repo: MinioAssemblyRepository,
        sample_assembly: Assembly,
    ) -> None:
        """Test updating assembly status."""
        # Save initial assembly
        await assembly_repo.save(sample_assembly)

        # Update status
        sample_assembly.status = AssemblyStatus.IN_PROGRESS
        await assembly_repo.save(sample_assembly)

        # Verify update
        retrieved = await assembly_repo.get(sample_assembly.assembly_id)
        assert retrieved is not None
        assert retrieved.status == AssemblyStatus.IN_PROGRESS

        # Update to completed
        sample_assembly.status = AssemblyStatus.COMPLETED
        await assembly_repo.save(sample_assembly)

        # Verify final state
        retrieved = await assembly_repo.get(sample_assembly.assembly_id)
        assert retrieved is not None
        assert retrieved.status == AssemblyStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_save_updates_timestamp(
        self,
        assembly_repo: MinioAssemblyRepository,
        sample_assembly: Assembly,
    ) -> None:
        """Test that save operations update the updated_at timestamp."""
        original_updated_at = sample_assembly.updated_at

        # Save assembly
        await assembly_repo.save(sample_assembly)

        # Retrieve and check timestamp was updated
        retrieved = await assembly_repo.get(sample_assembly.assembly_id)
        assert retrieved is not None
        assert retrieved.updated_at is not None
        assert original_updated_at is not None
        assert retrieved.updated_at > original_updated_at

    @pytest.mark.asyncio
    async def test_save_preserves_assembled_document_id(
        self,
        assembly_repo: MinioAssemblyRepository,
        sample_assembly: Assembly,
    ) -> None:
        """Test that save operations preserve assembled_document_id."""
        # Set assembled document first
        sample_assembly.assembled_document_id = "test-doc-123"
        sample_assembly.status = AssemblyStatus.COMPLETED
        await assembly_repo.save(sample_assembly)

        # Update other fields and save again
        sample_assembly.status = AssemblyStatus.FAILED
        await assembly_repo.save(sample_assembly)

        # Verify assembled_document_id is preserved
        retrieved = await assembly_repo.get(sample_assembly.assembly_id)
        assert retrieved is not None
        assert retrieved.assembled_document_id == "test-doc-123"
        assert retrieved.status == AssemblyStatus.FAILED


class TestMinioAssemblyRepositoryEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.mark.asyncio
    async def test_assembly_with_no_assembled_document(
        self,
        assembly_repo: MinioAssemblyRepository,
        sample_assembly: Assembly,
    ) -> None:
        """Test handling assembly with no assembled document."""
        await assembly_repo.save(sample_assembly)

        retrieved = await assembly_repo.get(sample_assembly.assembly_id)
        assert retrieved is not None
        assert retrieved.assembled_document_id is None

    @pytest.mark.asyncio
    async def test_complex_workflow_scenario(
        self,
        assembly_repo: MinioAssemblyRepository,
        sample_assembly: Assembly,
    ) -> None:
        """Test complex scenario with multiple operations."""
        # Save initial assembly
        await assembly_repo.save(sample_assembly)

        # Start processing
        sample_assembly.status = AssemblyStatus.IN_PROGRESS
        await assembly_repo.save(sample_assembly)

        # Set assembled document using direct assignment
        sample_assembly.assembled_document_id = "final-output-doc"
        sample_assembly.status = AssemblyStatus.COMPLETED
        await assembly_repo.save(sample_assembly)

        # Verify final state
        updated_assembly = await assembly_repo.get(
            sample_assembly.assembly_id
        )
        assert updated_assembly is not None

        # Verify final state
        assert updated_assembly.assembled_document_id == "final-output-doc"
        assert updated_assembly.status == AssemblyStatus.COMPLETED

        # Double-check by retrieving fresh
        retrieved = await assembly_repo.get(sample_assembly.assembly_id)
        assert retrieved is not None
        assert retrieved.assembled_document_id == "final-output-doc"
        assert retrieved.status == AssemblyStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_assembly_failure_scenario(
        self,
        assembly_repo: MinioAssemblyRepository,
        sample_assembly: Assembly,
    ) -> None:
        """Test assembly that fails during processing."""
        # Save initial assembly
        await assembly_repo.save(sample_assembly)

        # Start processing
        sample_assembly.status = AssemblyStatus.IN_PROGRESS
        await assembly_repo.save(sample_assembly)

        # Mark as failed (without setting assembled document)
        sample_assembly.status = AssemblyStatus.FAILED
        await assembly_repo.save(sample_assembly)

        # Verify final state - no assembled document
        retrieved = await assembly_repo.get(sample_assembly.assembly_id)
        assert retrieved is not None
        assert retrieved.assembled_document_id is None
        assert retrieved.status == AssemblyStatus.FAILED


class TestMinioAssemblyRepositoryRoundtrip:
    """Test full round-trip scenarios."""

    @pytest.mark.asyncio
    async def test_full_assembly_lifecycle_success(
        self, assembly_repo: MinioAssemblyRepository
    ) -> None:
        """Test complete successful assembly lifecycle from creation to
        completion."""
        # Generate new assembly
        assembly_id = await assembly_repo.generate_id()

        # Create and save initial assembly
        assembly = Assembly(
            assembly_id=assembly_id,
            assembly_specification_id="spec-test",
            input_document_id="input-test",
            workflow_id="test-workflow-success",
            status=AssemblyStatus.PENDING,
            assembled_document_id=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        await assembly_repo.save(assembly)

        # Start processing
        assembly.status = AssemblyStatus.IN_PROGRESS
        await assembly_repo.save(assembly)

        # Complete assembly with output document
        assembly.assembled_document_id = "final-output-document"
        assembly.status = AssemblyStatus.COMPLETED
        await assembly_repo.save(assembly)

        final_assembly = await assembly_repo.get(assembly_id)
        assert final_assembly is not None

        # Final verification
        assert final_assembly.status == AssemblyStatus.COMPLETED
        assert final_assembly.assembled_document_id == "final-output-document"

        # Verify persistence
        retrieved = await assembly_repo.get(assembly_id)
        assert retrieved is not None
        assert retrieved.status == AssemblyStatus.COMPLETED
        assert retrieved.assembled_document_id == "final-output-document"

    @pytest.mark.asyncio
    async def test_full_assembly_lifecycle_failure(
        self, assembly_repo: MinioAssemblyRepository
    ) -> None:
        """Test complete failed assembly lifecycle."""
        # Generate new assembly
        assembly_id = await assembly_repo.generate_id()

        # Create and save initial assembly
        assembly = Assembly(
            assembly_id=assembly_id,
            assembly_specification_id="spec-test",
            input_document_id="input-test",
            workflow_id="test-workflow-failure",
            status=AssemblyStatus.PENDING,
            assembled_document_id=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        await assembly_repo.save(assembly)

        # Start processing
        assembly.status = AssemblyStatus.IN_PROGRESS
        await assembly_repo.save(assembly)

        # Fail assembly (without setting output document)
        assembly.status = AssemblyStatus.FAILED
        await assembly_repo.save(assembly)

        # Final verification
        retrieved = await assembly_repo.get(assembly_id)
        assert retrieved is not None
        assert retrieved.status == AssemblyStatus.FAILED
        assert retrieved.assembled_document_id is None

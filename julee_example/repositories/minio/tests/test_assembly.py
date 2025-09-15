"""
Tests for MinioAssemblyRepository implementation.

This module provides comprehensive tests for the Minio-based assembly
repository implementation, using the fake client to avoid external
dependencies during testing.
"""

import pytest
from datetime import datetime, timezone


from julee_example.domain import Assembly, AssemblyStatus
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


class TestMinioAssemblyRepositoryDocumentManagement:
    """Test assembled document management operations."""

    @pytest.mark.asyncio
    async def test_set_assembled_document(
        self,
        assembly_repo: MinioAssemblyRepository,
        sample_assembly: Assembly,
    ) -> None:
        """Test setting assembled document for an assembly."""
        # Save assembly first
        await assembly_repo.save(sample_assembly)

        # Set assembled document
        updated_assembly = await assembly_repo.set_assembled_document(
            sample_assembly.assembly_id, "output-doc-1"
        )

        assert updated_assembly.assembled_document_id == "output-doc-1"
        assert updated_assembly.status == AssemblyStatus.COMPLETED

        # Verify persistence by retrieving again
        retrieved = await assembly_repo.get(sample_assembly.assembly_id)
        assert retrieved is not None
        assert retrieved.assembled_document_id == "output-doc-1"
        assert retrieved.status == AssemblyStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_set_assembled_document_idempotency(
        self,
        assembly_repo: MinioAssemblyRepository,
        sample_assembly: Assembly,
    ) -> None:
        """Test that setting same document_id is idempotent."""
        # Save assembly first
        await assembly_repo.save(sample_assembly)

        # Set assembled document first time
        updated_assembly1 = await assembly_repo.set_assembled_document(
            sample_assembly.assembly_id, "output-doc-1"
        )
        assert updated_assembly1.assembled_document_id == "output-doc-1"
        assert updated_assembly1.status == AssemblyStatus.COMPLETED

        # Set same document_id again - should be idempotent
        updated_assembly2 = await assembly_repo.set_assembled_document(
            sample_assembly.assembly_id, "output-doc-1"
        )
        assert updated_assembly2.assembled_document_id == "output-doc-1"
        assert updated_assembly2.status == AssemblyStatus.COMPLETED

        # Verify persistence - should still have same document
        retrieved = await assembly_repo.get(sample_assembly.assembly_id)
        assert retrieved is not None
        assert retrieved.assembled_document_id == "output-doc-1"

    @pytest.mark.asyncio
    async def test_set_assembled_document_overwrites_previous(
        self,
        assembly_repo: MinioAssemblyRepository,
        sample_assembly: Assembly,
    ) -> None:
        """Test that setting assembled document overwrites previous value."""
        # Save assembly first
        await assembly_repo.save(sample_assembly)

        # Set first assembled document
        updated_assembly1 = await assembly_repo.set_assembled_document(
            sample_assembly.assembly_id, "output-doc-1"
        )
        assert updated_assembly1.assembled_document_id == "output-doc-1"

        # Set different assembled document - should overwrite
        updated_assembly2 = await assembly_repo.set_assembled_document(
            sample_assembly.assembly_id, "output-doc-2"
        )
        assert updated_assembly2.assembled_document_id == "output-doc-2"
        assert updated_assembly2.status == AssemblyStatus.COMPLETED

        # Verify persistence
        retrieved = await assembly_repo.get(sample_assembly.assembly_id)
        assert retrieved is not None
        assert retrieved.assembled_document_id == "output-doc-2"

    @pytest.mark.asyncio
    async def test_set_assembled_document_for_nonexistent_assembly(
        self, assembly_repo: MinioAssemblyRepository
    ) -> None:
        """Test setting assembled document for non-existent assembly raises
        error."""
        with pytest.raises(ValueError, match="Assembly not found"):
            await assembly_repo.set_assembled_document(
                "nonexistent-assembly", "doc-123"
            )


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

        # Set assembled document
        updated_assembly = await assembly_repo.set_assembled_document(
            sample_assembly.assembly_id, "final-output-doc"
        )

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
        final_assembly = await assembly_repo.set_assembled_document(
            assembly_id, "final-output-document"
        )

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

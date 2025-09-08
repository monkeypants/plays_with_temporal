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
        iterations=[],
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
        assert retrieved.iterations == []

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


class TestMinioAssemblyRepositoryIterations:
    """Test iteration management operations."""

    @pytest.mark.asyncio
    async def test_add_iteration_to_empty_assembly(
        self,
        assembly_repo: MinioAssemblyRepository,
        sample_assembly: Assembly,
    ) -> None:
        """Test adding first iteration to an assembly."""
        # Save assembly first
        await assembly_repo.save(sample_assembly)

        # Add iteration
        updated_assembly = await assembly_repo.add_iteration(
            sample_assembly.assembly_id, "output-doc-1"
        )

        assert len(updated_assembly.iterations) == 1
        assert updated_assembly.iterations[0].iteration_id == 1
        assert updated_assembly.iterations[0].document_id == "output-doc-1"

        # Verify persistence by retrieving again
        retrieved = await assembly_repo.get(sample_assembly.assembly_id)
        assert retrieved is not None
        assert len(retrieved.iterations) == 1
        assert retrieved.iterations[0].iteration_id == 1
        assert retrieved.iterations[0].document_id == "output-doc-1"

    @pytest.mark.asyncio
    async def test_add_multiple_iterations(
        self,
        assembly_repo: MinioAssemblyRepository,
        sample_assembly: Assembly,
    ) -> None:
        """Test adding multiple iterations in sequence."""
        # Save assembly first
        await assembly_repo.save(sample_assembly)

        # Add first iteration
        updated_assembly = await assembly_repo.add_iteration(
            sample_assembly.assembly_id, "output-doc-1"
        )
        assert len(updated_assembly.iterations) == 1
        assert updated_assembly.iterations[0].iteration_id == 1

        # Add second iteration
        updated_assembly = await assembly_repo.add_iteration(
            sample_assembly.assembly_id, "output-doc-2"
        )
        assert len(updated_assembly.iterations) == 2
        assert updated_assembly.iterations[0].iteration_id == 1
        assert updated_assembly.iterations[1].iteration_id == 2
        assert updated_assembly.iterations[1].document_id == "output-doc-2"

        # Add third iteration
        updated_assembly = await assembly_repo.add_iteration(
            sample_assembly.assembly_id, "output-doc-3"
        )
        assert len(updated_assembly.iterations) == 3
        assert updated_assembly.iterations[2].iteration_id == 3
        assert updated_assembly.iterations[2].document_id == "output-doc-3"

    @pytest.mark.asyncio
    async def test_add_iteration_idempotency(
        self,
        assembly_repo: MinioAssemblyRepository,
        sample_assembly: Assembly,
    ) -> None:
        """Test that adding same document_id is idempotent."""
        # Save assembly first
        await assembly_repo.save(sample_assembly)

        # Add iteration first time
        updated_assembly1 = await assembly_repo.add_iteration(
            sample_assembly.assembly_id, "output-doc-1"
        )
        assert len(updated_assembly1.iterations) == 1
        assert updated_assembly1.iterations[0].iteration_id == 1

        # Add same document_id again - should be idempotent
        updated_assembly2 = await assembly_repo.add_iteration(
            sample_assembly.assembly_id, "output-doc-1"
        )
        assert len(updated_assembly2.iterations) == 1
        assert updated_assembly2.iterations[0].iteration_id == 1
        assert updated_assembly2.iterations[0].document_id == "output-doc-1"

        # Verify persistence - should still have only one iteration
        retrieved = await assembly_repo.get(sample_assembly.assembly_id)
        assert retrieved is not None
        assert len(retrieved.iterations) == 1

    @pytest.mark.asyncio
    async def test_add_iteration_to_nonexistent_assembly(
        self, assembly_repo: MinioAssemblyRepository
    ) -> None:
        """Test adding iteration to non-existent assembly raises error."""
        with pytest.raises(ValueError, match="Assembly not found"):
            await assembly_repo.add_iteration(
                "nonexistent-assembly", "doc-123"
            )

    @pytest.mark.asyncio
    async def test_iteration_ordering_preserved(
        self,
        assembly_repo: MinioAssemblyRepository,
        sample_assembly: Assembly,
    ) -> None:
        """Test that iterations maintain correct ordering."""
        # Save assembly first
        await assembly_repo.save(sample_assembly)

        # Add iterations in sequence
        documents = ["doc-1", "doc-2", "doc-3", "doc-4", "doc-5"]
        for i, doc_id in enumerate(documents, 1):
            updated_assembly = await assembly_repo.add_iteration(
                sample_assembly.assembly_id, doc_id
            )
            assert len(updated_assembly.iterations) == i
            assert updated_assembly.iterations[i - 1].iteration_id == i
            assert updated_assembly.iterations[i - 1].document_id == doc_id

        # Verify final state by retrieving
        retrieved = await assembly_repo.get(sample_assembly.assembly_id)
        assert retrieved is not None
        assert len(retrieved.iterations) == 5

        for i, iteration in enumerate(retrieved.iterations, 1):
            assert iteration.iteration_id == i
            assert iteration.document_id == f"doc-{i}"


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


class TestMinioAssemblyRepositoryEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.mark.asyncio
    async def test_assembly_with_no_iterations(
        self,
        assembly_repo: MinioAssemblyRepository,
        sample_assembly: Assembly,
    ) -> None:
        """Test handling assembly with no iterations."""
        await assembly_repo.save(sample_assembly)

        retrieved = await assembly_repo.get(sample_assembly.assembly_id)
        assert retrieved is not None
        assert retrieved.iterations == []

    @pytest.mark.asyncio
    async def test_complex_iteration_scenario(
        self,
        assembly_repo: MinioAssemblyRepository,
        sample_assembly: Assembly,
    ) -> None:
        """Test complex scenario with multiple operations."""
        # Save initial assembly
        await assembly_repo.save(sample_assembly)

        # Add some iterations
        await assembly_repo.add_iteration(
            sample_assembly.assembly_id, "doc-1"
        )
        await assembly_repo.add_iteration(
            sample_assembly.assembly_id, "doc-2"
        )

        # Update assembly status
        sample_assembly.status = AssemblyStatus.IN_PROGRESS
        await assembly_repo.save(sample_assembly)

        # Add more iterations
        await assembly_repo.add_iteration(
            sample_assembly.assembly_id, "doc-3"
        )

        # Try to add duplicate (should be idempotent)
        updated_assembly = await assembly_repo.add_iteration(
            sample_assembly.assembly_id, "doc-2"
        )

        # Verify final state
        assert len(updated_assembly.iterations) == 3
        assert updated_assembly.status == AssemblyStatus.IN_PROGRESS
        assert updated_assembly.iterations[0].document_id == "doc-1"
        assert updated_assembly.iterations[1].document_id == "doc-2"
        assert updated_assembly.iterations[2].document_id == "doc-3"

        # Double-check by retrieving fresh
        retrieved = await assembly_repo.get(sample_assembly.assembly_id)
        assert retrieved is not None
        assert len(retrieved.iterations) == 3
        assert retrieved.status == AssemblyStatus.IN_PROGRESS


class TestMinioAssemblyRepositoryRoundtrip:
    """Test full round-trip scenarios."""

    @pytest.mark.asyncio
    async def test_full_assembly_lifecycle(
        self, assembly_repo: MinioAssemblyRepository
    ) -> None:
        """Test complete assembly lifecycle from creation to completion."""
        # Generate new assembly
        assembly_id = await assembly_repo.generate_id()

        # Create and save initial assembly
        assembly = Assembly(
            assembly_id=assembly_id,
            assembly_specification_id="spec-test",
            input_document_id="input-test",
            status=AssemblyStatus.PENDING,
            iterations=[],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        await assembly_repo.save(assembly)

        # Start processing
        assembly.status = AssemblyStatus.IN_PROGRESS
        await assembly_repo.save(assembly)

        # Add iterations as assembly progresses
        assembly = await assembly_repo.add_iteration(assembly_id, "output-1")
        assembly = await assembly_repo.add_iteration(assembly_id, "output-2")
        assembly = await assembly_repo.add_iteration(assembly_id, "output-3")

        # Complete assembly
        assembly.status = AssemblyStatus.COMPLETED
        await assembly_repo.save(assembly)

        # Final verification
        final_assembly = await assembly_repo.get(assembly_id)
        assert final_assembly is not None
        assert final_assembly.status == AssemblyStatus.COMPLETED
        assert len(final_assembly.iterations) == 3
        assert final_assembly.iterations[0].iteration_id == 1
        assert final_assembly.iterations[1].iteration_id == 2
        assert final_assembly.iterations[2].iteration_id == 3
        assert final_assembly.iterations[0].document_id == "output-1"
        assert final_assembly.iterations[1].document_id == "output-2"
        assert final_assembly.iterations[2].document_id == "output-3"

"""
Tests for MinioKnowledgeServiceConfigRepository implementation.

This module provides comprehensive tests for the Minio-based knowledge service
configuration repository implementation, using the fake client to avoid
external dependencies during testing.
"""

import pytest
from datetime import datetime, timezone

from julee_example.domain.models.knowledge_service_config import (
    KnowledgeServiceConfig,
)
from julee_example.domain.models.knowledge_service_config import ServiceApi
from julee_example.repositories.minio.knowledge_service_config import (
    MinioKnowledgeServiceConfigRepository,
)
from .fake_client import FakeMinioClient


@pytest.fixture
def fake_client() -> FakeMinioClient:
    """Create a fresh fake Minio client for each test."""
    return FakeMinioClient()


@pytest.fixture
def knowledge_service_config_repo(
    fake_client: FakeMinioClient,
) -> MinioKnowledgeServiceConfigRepository:
    """Create knowledge service config repository with fake client."""
    return MinioKnowledgeServiceConfigRepository(fake_client)


@pytest.fixture
def sample_knowledge_service_config() -> KnowledgeServiceConfig:
    """Create a sample knowledge service config for testing."""
    return KnowledgeServiceConfig(
        knowledge_service_id="ks-test-123",
        name="Test Anthropic Service",
        description="A test knowledge service using Anthropic API",
        service_api=ServiceApi.ANTHROPIC,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


class TestMinioKnowledgeServiceConfigRepositoryBasicOperations:
    """Test basic CRUD operations on knowledge service configurations."""

    @pytest.mark.asyncio
    async def test_save_and_get_knowledge_service_config(
        self,
        knowledge_service_config_repo: MinioKnowledgeServiceConfigRepository,
        sample_knowledge_service_config: KnowledgeServiceConfig,
    ) -> None:
        """Test saving and retrieving a knowledge service configuration."""
        # Save knowledge service config
        await knowledge_service_config_repo.save(
            sample_knowledge_service_config
        )

        # Retrieve knowledge service config
        retrieved = await knowledge_service_config_repo.get(
            sample_knowledge_service_config.knowledge_service_id
        )

        assert retrieved is not None
        assert (
            retrieved.knowledge_service_id
            == sample_knowledge_service_config.knowledge_service_id
        )
        assert retrieved.name == sample_knowledge_service_config.name
        assert (
            retrieved.description
            == sample_knowledge_service_config.description
        )
        assert (
            retrieved.service_api
            == sample_knowledge_service_config.service_api
        )
        assert retrieved.created_at is not None
        assert retrieved.updated_at is not None

    @pytest.mark.asyncio
    async def test_get_nonexistent_knowledge_service_config(
        self,
        knowledge_service_config_repo: MinioKnowledgeServiceConfigRepository,
    ) -> None:
        """Test retrieving a non-existent knowledge service config returns
        None."""
        result = await knowledge_service_config_repo.get(
            "nonexistent-ks-config"
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_generate_id(
        self,
        knowledge_service_config_repo: MinioKnowledgeServiceConfigRepository,
    ) -> None:
        """Test generating unique knowledge service configuration IDs."""
        id1 = await knowledge_service_config_repo.generate_id()
        id2 = await knowledge_service_config_repo.generate_id()

        assert isinstance(id1, str)
        assert isinstance(id2, str)
        assert id1 != id2
        assert len(id1) > 0
        assert len(id2) > 0
        assert id1.startswith("ks-")
        assert id2.startswith("ks-")


class TestMinioKnowledgeServiceConfigRepositoryUpdates:
    """Test knowledge service configuration update operations."""

    @pytest.mark.asyncio
    async def test_update_knowledge_service_config(
        self,
        knowledge_service_config_repo: MinioKnowledgeServiceConfigRepository,
        sample_knowledge_service_config: KnowledgeServiceConfig,
    ) -> None:
        """Test updating a knowledge service configuration."""
        # Save initial config
        await knowledge_service_config_repo.save(
            sample_knowledge_service_config
        )

        # Update the config
        sample_knowledge_service_config.name = "Updated Test Service"
        sample_knowledge_service_config.description = (
            "Updated description for the test service"
        )
        await knowledge_service_config_repo.save(
            sample_knowledge_service_config
        )

        # Verify update
        retrieved = await knowledge_service_config_repo.get(
            sample_knowledge_service_config.knowledge_service_id
        )
        assert retrieved is not None
        assert retrieved.name == "Updated Test Service"
        assert (
            retrieved.description
            == "Updated description for the test service"
        )
        assert (
            retrieved.service_api
            == sample_knowledge_service_config.service_api
        )

    @pytest.mark.asyncio
    async def test_save_updates_timestamp(
        self,
        knowledge_service_config_repo: MinioKnowledgeServiceConfigRepository,
        sample_knowledge_service_config: KnowledgeServiceConfig,
    ) -> None:
        """Test that save operations update the updated_at timestamp."""
        original_updated_at = sample_knowledge_service_config.updated_at

        # Save config
        await knowledge_service_config_repo.save(
            sample_knowledge_service_config
        )

        # Retrieve and check timestamp was updated
        retrieved = await knowledge_service_config_repo.get(
            sample_knowledge_service_config.knowledge_service_id
        )
        assert retrieved is not None
        assert retrieved.updated_at is not None
        assert original_updated_at is not None
        assert retrieved.updated_at > original_updated_at

    @pytest.mark.asyncio
    async def test_save_sets_created_at_for_new_config(
        self,
        knowledge_service_config_repo: MinioKnowledgeServiceConfigRepository,
    ) -> None:
        """Test that save operations set created_at for new configurations."""
        # Create config without created_at
        config = KnowledgeServiceConfig(
            knowledge_service_id="ks-new-test",
            name="New Test Service",
            description="A new test service",
            service_api=ServiceApi.ANTHROPIC,
            created_at=None,  # Explicitly set to None
            updated_at=None,  # Explicitly set to None
        )

        # Save config
        await knowledge_service_config_repo.save(config)

        # Retrieve and check timestamps were set
        retrieved = await knowledge_service_config_repo.get("ks-new-test")
        assert retrieved is not None
        assert retrieved.created_at is not None
        assert retrieved.updated_at is not None


class TestMinioKnowledgeServiceConfigRepositoryIdempotency:
    """Test idempotent operations on knowledge service configurations."""

    @pytest.mark.asyncio
    async def test_save_idempotency(
        self,
        knowledge_service_config_repo: MinioKnowledgeServiceConfigRepository,
        sample_knowledge_service_config: KnowledgeServiceConfig,
    ) -> None:
        """Test that saving the same config multiple times is idempotent."""
        # Save config first time
        await knowledge_service_config_repo.save(
            sample_knowledge_service_config
        )

        # Get the config to check initial state
        retrieved1 = await knowledge_service_config_repo.get(
            sample_knowledge_service_config.knowledge_service_id
        )
        assert retrieved1 is not None
        first_updated_at = retrieved1.updated_at

        # Save same config again (should update timestamp but maintain other
        # data)
        await knowledge_service_config_repo.save(
            sample_knowledge_service_config
        )

        # Verify config is still there with updated timestamp
        retrieved2 = await knowledge_service_config_repo.get(
            sample_knowledge_service_config.knowledge_service_id
        )
        assert retrieved2 is not None
        assert (
            retrieved2.knowledge_service_id
            == sample_knowledge_service_config.knowledge_service_id
        )
        assert retrieved2.name == sample_knowledge_service_config.name
        assert (
            retrieved2.description
            == sample_knowledge_service_config.description
        )
        assert (
            retrieved2.service_api
            == sample_knowledge_service_config.service_api
        )
        assert retrieved2.updated_at is not None
        assert first_updated_at is not None
        assert retrieved2.updated_at > first_updated_at


class TestMinioKnowledgeServiceConfigRepositoryServiceApiTypes:
    """Test handling of different service API types."""

    @pytest.mark.asyncio
    async def test_anthropic_service_api(
        self,
        knowledge_service_config_repo: MinioKnowledgeServiceConfigRepository,
    ) -> None:
        """Test saving and retrieving config with Anthropic service API."""
        config = KnowledgeServiceConfig(
            knowledge_service_id="ks-anthropic-test",
            name="Anthropic Service",
            description="Service using Anthropic API",
            service_api=ServiceApi.ANTHROPIC,
        )

        await knowledge_service_config_repo.save(config)
        retrieved = await knowledge_service_config_repo.get(
            "ks-anthropic-test"
        )

        assert retrieved is not None
        assert retrieved.service_api == ServiceApi.ANTHROPIC
        assert retrieved.service_api.value == "anthropic"


class TestMinioKnowledgeServiceConfigRepositoryRoundtrip:
    """Test full round-trip scenarios."""

    @pytest.mark.asyncio
    async def test_full_knowledge_service_config_lifecycle(
        self,
        knowledge_service_config_repo: MinioKnowledgeServiceConfigRepository,
    ) -> None:
        """Test complete knowledge service config lifecycle."""
        # Generate new config ID
        config_id = await knowledge_service_config_repo.generate_id()

        # Create and save initial config
        config = KnowledgeServiceConfig(
            knowledge_service_id=config_id,
            name="Lifecycle Test Service",
            description="Testing full lifecycle",
            service_api=ServiceApi.ANTHROPIC,
        )
        await knowledge_service_config_repo.save(config)

        # Retrieve and verify initial state
        retrieved = await knowledge_service_config_repo.get(config_id)
        assert retrieved is not None
        assert retrieved.name == "Lifecycle Test Service"
        assert retrieved.service_api == ServiceApi.ANTHROPIC

        # Update the configuration
        config.name = "Updated Lifecycle Service"
        config.description = "Updated description after lifecycle test"
        await knowledge_service_config_repo.save(config)

        # Final verification
        final_config = await knowledge_service_config_repo.get(config_id)
        assert final_config is not None
        assert final_config.name == "Updated Lifecycle Service"
        assert (
            final_config.description
            == "Updated description after lifecycle test"
        )
        assert final_config.service_api == ServiceApi.ANTHROPIC
        assert final_config.created_at is not None
        assert final_config.updated_at is not None

    @pytest.mark.asyncio
    async def test_multiple_configs_independence(
        self,
        knowledge_service_config_repo: MinioKnowledgeServiceConfigRepository,
    ) -> None:
        """Test that multiple configs are stored and retrieved
        independently."""
        # Create multiple configs
        config1 = KnowledgeServiceConfig(
            knowledge_service_id="ks-test-1",
            name="Service One",
            description="First test service",
            service_api=ServiceApi.ANTHROPIC,
        )

        config2 = KnowledgeServiceConfig(
            knowledge_service_id="ks-test-2",
            name="Service Two",
            description="Second test service",
            service_api=ServiceApi.ANTHROPIC,
        )

        # Save both configs
        await knowledge_service_config_repo.save(config1)
        await knowledge_service_config_repo.save(config2)

        # Retrieve both and verify independence
        retrieved1 = await knowledge_service_config_repo.get("ks-test-1")
        retrieved2 = await knowledge_service_config_repo.get("ks-test-2")

        assert retrieved1 is not None
        assert retrieved2 is not None
        assert retrieved1.knowledge_service_id == "ks-test-1"
        assert retrieved2.knowledge_service_id == "ks-test-2"
        assert retrieved1.name == "Service One"
        assert retrieved2.name == "Service Two"
        assert retrieved1.description == "First test service"
        assert retrieved2.description == "Second test service"

        # Update one config and verify the other is unchanged
        config1.name = "Updated Service One"
        await knowledge_service_config_repo.save(config1)

        retrieved1_updated = await knowledge_service_config_repo.get(
            "ks-test-1"
        )
        retrieved2_unchanged = await knowledge_service_config_repo.get(
            "ks-test-2"
        )

        assert retrieved1_updated is not None
        assert retrieved2_unchanged is not None
        assert retrieved1_updated.name == "Updated Service One"
        assert (
            retrieved2_unchanged.name == "Service Two"
        )  # Should be unchanged


class TestMinioKnowledgeServiceConfigRepositoryEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.mark.asyncio
    async def test_empty_string_id_handling(
        self,
        knowledge_service_config_repo: MinioKnowledgeServiceConfigRepository,
    ) -> None:
        """Test handling of empty string knowledge service ID."""
        result = await knowledge_service_config_repo.get("")
        assert result is None

    @pytest.mark.asyncio
    async def test_special_characters_in_id(
        self,
        knowledge_service_config_repo: MinioKnowledgeServiceConfigRepository,
    ) -> None:
        """Test handling knowledge service IDs with special characters."""
        # Note: This test ensures the repository can handle various ID formats
        # that might be generated by different ID generation strategies
        special_id = "ks-test-with-dashes-and-numbers-123"

        config = KnowledgeServiceConfig(
            knowledge_service_id=special_id,
            name="Special ID Service",
            description="Service with special characters in ID",
            service_api=ServiceApi.ANTHROPIC,
        )

        await knowledge_service_config_repo.save(config)
        retrieved = await knowledge_service_config_repo.get(special_id)

        assert retrieved is not None
        assert retrieved.knowledge_service_id == special_id
        assert retrieved.name == "Special ID Service"

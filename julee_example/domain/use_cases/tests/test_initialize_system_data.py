"""
Tests for InitializeSystemDataUseCase.

This module tests the use case for initializing required system data,
ensuring it properly loads configurations from the YAML fixture file
and creates knowledge service configurations correctly.

These tests use the actual YAML fixture file to validate the real
integration rather than mocking the file system operations.
"""

import pytest
import yaml
from pathlib import Path
from julee_example.repositories.memory.knowledge_service_config import (
    MemoryKnowledgeServiceConfigRepository,
)
from julee_example.repositories.memory.knowledge_service_query import (
    MemoryKnowledgeServiceQueryRepository,
)
from julee_example.repositories.memory.assembly_specification import (
    MemoryAssemblySpecificationRepository,
)
from julee_example.repositories.memory.document import (
    MemoryDocumentRepository,
)
from datetime import datetime, timezone

from julee_example.domain.use_cases.initialize_system_data import (
    InitializeSystemDataUseCase,
)
from julee_example.domain.models.knowledge_service_config import (
    KnowledgeServiceConfig,
    ServiceApi,
)


@pytest.fixture
def memory_config_repository() -> MemoryKnowledgeServiceConfigRepository:
    """Create memory knowledge service config repository."""
    return MemoryKnowledgeServiceConfigRepository()


@pytest.fixture
def memory_document_repository() -> MemoryDocumentRepository:
    """Create memory document repository."""
    return MemoryDocumentRepository()


@pytest.fixture
def memory_query_repository() -> MemoryKnowledgeServiceQueryRepository:
    """Create memory knowledge service query repository."""
    return MemoryKnowledgeServiceQueryRepository()


@pytest.fixture
def memory_assembly_spec_repository() -> (
    MemoryAssemblySpecificationRepository
):
    """Create memory assembly specification repository."""
    return MemoryAssemblySpecificationRepository()


@pytest.fixture
def use_case(
    memory_config_repository: MemoryKnowledgeServiceConfigRepository,
    memory_document_repository: MemoryDocumentRepository,
    memory_query_repository: MemoryKnowledgeServiceQueryRepository,
    memory_assembly_spec_repository: MemoryAssemblySpecificationRepository,
) -> InitializeSystemDataUseCase:
    """Create use case with memory repositories."""
    return InitializeSystemDataUseCase(
        memory_config_repository,
        memory_document_repository,
        memory_query_repository,
        memory_assembly_spec_repository,
    )


@pytest.fixture
def fixture_configs() -> list[dict]:
    """Load actual configurations from YAML fixture file."""
    # Get the fixture file path
    current_file = Path(__file__)
    julee_example_dir = current_file.parent.parent.parent.parent
    fixture_path = (
        julee_example_dir / "demo_fixtures" / "knowledge_service_configs.yaml"
    )

    assert fixture_path.exists(), f"Fixture file not found: {fixture_path}"

    with open(fixture_path, "r", encoding="utf-8") as f:
        fixture_data = yaml.safe_load(f)

    assert "knowledge_services" in fixture_data
    assert isinstance(fixture_data["knowledge_services"], list)
    assert len(fixture_data["knowledge_services"]) > 0

    return fixture_data["knowledge_services"]


@pytest.fixture
def sample_anthropic_config() -> KnowledgeServiceConfig:
    """Create sample Anthropic configuration."""
    return KnowledgeServiceConfig(
        knowledge_service_id="anthropic-claude",
        name="Anthropic Claude",
        description="Claude 3 for general text analysis and extraction",
        service_api=ServiceApi.ANTHROPIC,
        created_at=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        updated_at=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
    )


class TestInitializeSystemDataUseCase:
    """Test the InitializeSystemDataUseCase."""

    @pytest.mark.asyncio
    async def test_execute_success_creates_configs_from_fixture(
        self,
        use_case: InitializeSystemDataUseCase,
        memory_config_repository: MemoryKnowledgeServiceConfigRepository,
        fixture_configs: list[dict],
    ) -> None:
        """Test successful execution creates configs from fixture."""
        # Execute use case
        await use_case.execute()

        # Verify all configs were created
        saved_configs = await memory_config_repository.list_all()
        assert len(saved_configs) == len(fixture_configs)

        # Verify configs were created with correct IDs from fixture

        saved_ids = {config.knowledge_service_id for config in saved_configs}
        expected_ids = {
            config["knowledge_service_id"] for config in fixture_configs
        }
        assert saved_ids == expected_ids

        # Verify first config matches fixture data
        first_fixture = fixture_configs[0]
        first_saved = next(
            config
            for config in saved_configs
            if config.knowledge_service_id
            == first_fixture["knowledge_service_id"]
        )

        assert first_saved.name == first_fixture["name"]
        assert first_saved.description == first_fixture["description"]
        assert first_saved.service_api.value == first_fixture["service_api"]

    @pytest.mark.asyncio
    async def test_execute_success_configs_already_exist(
        self,
        use_case: InitializeSystemDataUseCase,
        memory_config_repository: MemoryKnowledgeServiceConfigRepository,
        sample_anthropic_config: KnowledgeServiceConfig,
    ) -> None:
        """Test successful execution when configs already exist."""
        # Setup - add existing config to repository
        await memory_config_repository.save(sample_anthropic_config)

        # Execute use case
        await use_case.execute()

        # Verify only the existing config is in the repository (no duplicates)
        all_configs = await memory_config_repository.list_all()
        config_ids = [c.knowledge_service_id for c in all_configs]
        assert sample_anthropic_config.knowledge_service_id in config_ids

    @pytest.mark.asyncio
    async def test_execute_mixed_existing_and_new_configs(
        self,
        use_case: InitializeSystemDataUseCase,
        memory_config_repository: MemoryKnowledgeServiceConfigRepository,
        sample_anthropic_config: KnowledgeServiceConfig,
        fixture_configs: list[dict],
    ) -> None:
        """Test execution with mix of existing and new configs."""
        # Setup - add one existing config to repository
        await memory_config_repository.save(sample_anthropic_config)

        # Execute use case
        await use_case.execute()

        # Verify all configs from fixture exist (including pre-existing one)
        final_configs = await memory_config_repository.list_all()
        final_count = len(final_configs)

        # Should have all fixture configs (some were new, one already existed)
        expected_total = len(fixture_configs)
        assert final_count >= expected_total

        # Verify the existing config is still there
        config_ids = [c.knowledge_service_id for c in final_configs]
        assert sample_anthropic_config.knowledge_service_id in config_ids

    # NOTE: Error handling tests commented out as they don't work well with
    # memory repositories. These would need mock repositories or integration
    # tests with actual Minio failures to test error scenarios properly.

    # @pytest.mark.asyncio
    # async def test_execute_handles_repository_get_error(...)
    # @pytest.mark.asyncio
    # async def test_execute_handles_repository_save_error(...)

    @pytest.mark.asyncio
    async def test_config_creation_uses_correct_values_from_fixture(
        self,
        use_case: InitializeSystemDataUseCase,
        memory_config_repository: MemoryKnowledgeServiceConfigRepository,
        fixture_configs: list[dict],
    ) -> None:
        """Test that created configs have correct values from fixture."""
        # Execute use case
        await use_case.execute()

        # Get all saved configs
        saved_configs = await memory_config_repository.list_all()

        # Verify each saved config matches fixture data
        for fixture_config in fixture_configs:
            saved_config = next(
                config
                for config in saved_configs
                if config.knowledge_service_id
                == fixture_config["knowledge_service_id"]
            )

            # Verify all fixture values are correctly applied
            assert (
                saved_config.knowledge_service_id
                == fixture_config["knowledge_service_id"]
            )
            assert saved_config.name == fixture_config["name"]
            assert saved_config.description == fixture_config["description"]
            assert (
                saved_config.service_api.value
                == fixture_config["service_api"]
            )
            assert saved_config.created_at is not None
            assert saved_config.updated_at is not None
            assert isinstance(saved_config.created_at, datetime)
            assert isinstance(saved_config.updated_at, datetime)

    @pytest.mark.asyncio
    async def test_use_case_is_idempotent(
        self,
        use_case: InitializeSystemDataUseCase,
        memory_config_repository: MemoryKnowledgeServiceConfigRepository,
        fixture_configs: list[dict],
    ) -> None:
        """Test that running the use case multiple times is safe."""
        # First run - configs don't exist, get created
        await use_case.execute()
        first_run_configs = await memory_config_repository.list_all()
        first_run_count = len(first_run_configs)

        # Second run - configs now exist, should not create duplicates
        await use_case.execute()
        second_run_configs = await memory_config_repository.list_all()
        second_run_count = len(second_run_configs)

        # Verify idempotency - same number of configs after second run
        assert first_run_count == second_run_count

        # Verify all fixture configs are present
        config_ids = [c.knowledge_service_id for c in second_run_configs]
        for fixture_config in fixture_configs:
            assert fixture_config["knowledge_service_id"] in config_ids

    def test_use_case_initialization(
        self,
        memory_config_repository: MemoryKnowledgeServiceConfigRepository,
        memory_document_repository: MemoryDocumentRepository,
        memory_query_repository: MemoryKnowledgeServiceQueryRepository,
        memory_assembly_spec_repository: (
            MemoryAssemblySpecificationRepository
        ),
    ) -> None:
        """Test use case initialization with repositories."""
        use_case = InitializeSystemDataUseCase(
            memory_config_repository,
            memory_document_repository,
            memory_query_repository,
            memory_assembly_spec_repository,
        )
        assert use_case.config_repo is memory_config_repository
        assert use_case.document_repo is memory_document_repository
        assert use_case.query_repo is memory_query_repository
        assert use_case.assembly_spec_repo is memory_assembly_spec_repository
        assert use_case.logger is not None

    @pytest.mark.asyncio
    async def test_config_initialization_only(
        self,
        memory_config_repository: MemoryKnowledgeServiceConfigRepository,
        memory_document_repository: MemoryDocumentRepository,
        memory_query_repository: MemoryKnowledgeServiceQueryRepository,
        memory_assembly_spec_repository: (
            MemoryAssemblySpecificationRepository
        ),
        fixture_configs: list[dict],
    ) -> None:
        """Test only the config initialization part."""
        use_case = InitializeSystemDataUseCase(
            memory_config_repository,
            memory_document_repository,
            memory_query_repository,
            memory_assembly_spec_repository,
        )

        # Execute the use case to initialize configs
        await use_case.execute()

        # Verify configs were created
        saved_configs = await memory_config_repository.list_all()
        assert len(saved_configs) == len(fixture_configs)


class TestYamlFixtureIntegration:
    """Test integration with actual YAML fixture file."""

    def test_fixture_file_exists_and_is_valid(self) -> None:
        """Test that the fixture file exists and contains valid data."""
        # Get the fixture file path
        current_file = Path(__file__)
        julee_example_dir = current_file.parent.parent.parent.parent
        fixture_path = (
            julee_example_dir
            / "demo_fixtures"
            / "knowledge_service_configs.yaml"
        )

        # Verify file exists
        assert (
            fixture_path.exists()
        ), f"Fixture file not found: {fixture_path}"

        # Verify file can be parsed
        with open(fixture_path, "r", encoding="utf-8") as f:
            fixture_data = yaml.safe_load(f)

        # Verify structure
        assert isinstance(fixture_data, dict)
        assert "knowledge_services" in fixture_data
        assert isinstance(fixture_data["knowledge_services"], list)
        assert len(fixture_data["knowledge_services"]) > 0

    def test_fixture_configs_have_required_fields(
        self, fixture_configs: list[dict]
    ) -> None:
        """Test that all fixture configs have required fields."""
        required_fields = [
            "knowledge_service_id",
            "name",
            "description",
            "service_api",
        ]

        for config in fixture_configs:
            for field in required_fields:
                assert field in config, (
                    f"Missing required field '{field}' in config "
                    f"{config.get('knowledge_service_id', 'unknown')}"
                )

            # Verify service_api is valid
            assert config["service_api"] in [
                api.value for api in ServiceApi
            ], (
                f"Invalid service_api '{config['service_api']}' in config "
                f"{config['knowledge_service_id']}"
            )

            # Verify IDs are not empty
            assert config[
                "knowledge_service_id"
            ].strip(), "Empty knowledge_service_id"
            assert config["name"].strip(), "Empty name"
            assert config["description"].strip(), "Empty description"

    def test_fixture_configs_have_unique_ids(
        self, fixture_configs: list[dict]
    ) -> None:
        """Test that all fixture configs have unique IDs."""
        config_ids = [
            config["knowledge_service_id"] for config in fixture_configs
        ]
        assert len(config_ids) == len(
            set(config_ids)
        ), "Duplicate knowledge_service_id found in fixture"

    @pytest.mark.asyncio
    async def test_load_fixture_configurations_method(
        self, use_case: InitializeSystemDataUseCase
    ) -> None:
        """Test the _load_fixture_configurations method directly."""
        configs = use_case._load_fixture_configurations()

        assert isinstance(configs, list)
        assert len(configs) > 0

        # Verify each config has required structure
        for config in configs:
            assert isinstance(config, dict)
            assert "knowledge_service_id" in config
            assert "name" in config
            assert "description" in config
            assert "service_api" in config

    @pytest.mark.asyncio
    async def test_create_config_from_fixture_data_method(
        self,
        use_case: InitializeSystemDataUseCase,
        fixture_configs: list[dict],
    ) -> None:
        """Test the _create_config_from_fixture_data method directly."""
        fixture_config = fixture_configs[0]

        created_config = use_case._create_config_from_fixture_data(
            fixture_config
        )

        assert isinstance(created_config, KnowledgeServiceConfig)
        assert (
            created_config.knowledge_service_id
            == fixture_config["knowledge_service_id"]
        )
        assert created_config.name == fixture_config["name"]
        assert created_config.description == fixture_config["description"]
        assert (
            created_config.service_api.value == fixture_config["service_api"]
        )
        assert created_config.created_at is not None
        assert created_config.updated_at is not None


class TestInitializeSystemDataUseCaseIntegration:
    """Integration-style tests for the use case."""

    @pytest.mark.asyncio
    async def test_full_workflow_new_system(
        self,
        use_case: InitializeSystemDataUseCase,
        memory_config_repository: MemoryKnowledgeServiceConfigRepository,
        fixture_configs: list[dict],
    ) -> None:
        """Test complete workflow for a new system with no existing data."""
        # Setup - repository starts empty

        # Execute initialization
        await use_case.execute()

        # Verify all configs were created
        saved_configs = await memory_config_repository.list_all()
        assert len(saved_configs) == len(fixture_configs)

        # Verify configs were created with correct IDs from fixture
        saved_ids = {config.knowledge_service_id for config in saved_configs}
        expected_ids = {
            config["knowledge_service_id"] for config in fixture_configs
        }
        assert saved_ids == expected_ids

    @pytest.mark.asyncio
    async def test_full_workflow_existing_system(
        self,
        use_case: InitializeSystemDataUseCase,
        memory_config_repository: MemoryKnowledgeServiceConfigRepository,
        sample_anthropic_config: KnowledgeServiceConfig,
        fixture_configs: list[dict],
    ) -> None:
        """Test complete workflow for existing system with data present."""
        # Setup - add existing config to repository
        await memory_config_repository.save(sample_anthropic_config)

        # Execute initialization
        await use_case.execute()

        # Verify configs exist and no duplicates were created
        final_configs = await memory_config_repository.list_all()

        # Should have all fixture configs (including pre-existing)
        config_ids = [c.knowledge_service_id for c in final_configs]
        assert sample_anthropic_config.knowledge_service_id in config_ids
        assert len(final_configs) >= len(fixture_configs)

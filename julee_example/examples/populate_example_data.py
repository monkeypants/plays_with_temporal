"""
Script to populate example data for julee_example workflows.

This script loads the example data files (meeting transcript, assembly spec,
knowledge service queries) and stores them in the repositories so that
the workflow examples can use real data instead of hardcoded IDs.
"""

import asyncio
import io
import json
import logging
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict

from minio import Minio

from julee_example.domain.models import (
    Document,
    DocumentStatus,
    ContentStream,
    AssemblySpecification,
    KnowledgeServiceQuery,
    KnowledgeServiceConfig,
    Policy,
    PolicyStatus,
)
from julee_example.domain.models.knowledge_service_config import ServiceApi
from julee_example.repositories.minio.assembly_specification import (
    MinioAssemblySpecificationRepository,
)
from julee_example.repositories.minio.document import MinioDocumentRepository
from julee_example.repositories.minio.knowledge_service_query import (
    MinioKnowledgeServiceQueryRepository,
)
from julee_example.repositories.minio.knowledge_service_config import (
    MinioKnowledgeServiceConfigRepository,
)
from julee_example.repositories.minio.policy import (
    MinioPolicyRepository,
)

logger = logging.getLogger(__name__)


def setup_logging() -> None:
    """Configure logging for the populate script."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


async def create_minio_client() -> Minio:
    """Create and return a Minio client."""
    minio_endpoint = os.environ.get("MINIO_ENDPOINT", "localhost:9000")

    return Minio(
        endpoint=minio_endpoint,
        access_key="minioadmin",
        secret_key="minioadmin",
        secure=False,
    )


async def load_example_document(
    document_repo: MinioDocumentRepository,
    data_dir: Path,
) -> str:
    """
    Load the meeting transcript as a document.

    Returns:
        The document_id of the loaded document
    """
    transcript_path = data_dir / "meeting_transcript.txt"

    logger.info(f"Loading meeting transcript from {transcript_path}")

    # Read the transcript content
    with open(transcript_path, "r", encoding="utf-8") as f:
        content = f.read()

    content_bytes = content.encode("utf-8")
    content_stream = ContentStream(io.BytesIO(content_bytes))

    # Generate document ID
    document_id = await document_repo.generate_id()

    # Create the document
    document = Document(
        document_id=document_id,
        original_filename="meeting_transcript.txt",
        content_type="text/plain",
        size_bytes=len(content_bytes),
        content_multihash="placeholder_hash",  # Would normally calculate this
        status=DocumentStatus.CAPTURED,
        content=content_stream,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    # Save the document
    await document_repo.save(document)

    logger.info(f"Document saved with ID: {document_id}")
    return document_id


async def load_assembly_specification(
    assembly_spec_repo: MinioAssemblySpecificationRepository,
    data_dir: Path,
    query_ids: Dict[str, str],
) -> str:
    """
    Load the meeting minutes assembly specification.

    Args:
        assembly_spec_repo: Repository for assembly specifications
        data_dir: Directory containing the spec file
        query_ids: Mapping of query names to actual generated IDs

    Returns:
        The assembly_specification_id of the loaded spec
    """
    spec_path = data_dir / "meeting_minutes_assembly_spec.json"

    logger.info(f"Loading assembly specification from {spec_path}")

    # Read and parse the spec file
    with open(spec_path, "r", encoding="utf-8") as f:
        spec_data = json.load(f)

    # Generate assembly specification ID
    spec_id = await assembly_spec_repo.generate_id()

    # Update knowledge_service_queries to use actual generated IDs
    updated_queries = {}
    for json_pointer, old_query_name in spec_data[
        "knowledge_service_queries"
    ].items():
        # Map old hardcoded names to actual query IDs
        if old_query_name == "extract-meeting-info-query":
            updated_queries[json_pointer] = query_ids["extract_meeting_info"]
        elif old_query_name == "extract-agenda-items-query":
            updated_queries[json_pointer] = query_ids["extract_agenda_items"]
        elif old_query_name == "extract-action-items-query":
            updated_queries[json_pointer] = query_ids["extract_action_items"]
        else:
            logger.warning(f"Unknown query reference: {old_query_name}")
            updated_queries[json_pointer] = old_query_name

    # Create the assembly specification
    assembly_spec = AssemblySpecification(
        assembly_specification_id=spec_id,
        name=spec_data["name"],
        applicability=spec_data["applicability"],
        jsonschema=spec_data["jsonschema"],
        knowledge_service_queries=updated_queries,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    # Save the assembly specification
    await assembly_spec_repo.save(assembly_spec)

    logger.info(f"Assembly specification saved with ID: {spec_id}")
    return spec_id


async def load_knowledge_service_queries(
    query_repo: MinioKnowledgeServiceQueryRepository,
    data_dir: Path,
    knowledge_service_config_id: str,
) -> Dict[str, str]:
    """
    Load all knowledge service queries.

    Args:
        query_repo: Repository for knowledge service queries
        data_dir: Directory containing the query files
        knowledge_service_config_id: Actual generated knowledge service
            config ID

    Returns:
        Dict mapping query names to query IDs
    """
    query_files = [
        "extract-meeting-info-query.json",
        "extract-agenda-items-query.json",
        "extract-action-items-query.json",
    ]

    query_ids = {}

    for query_file in query_files:
        query_path = data_dir / query_file

        logger.info(f"Loading knowledge service query from {query_path}")

        # Read and parse the query file
        with open(query_path, "r", encoding="utf-8") as f:
            query_data = json.load(f)

        # Generate query ID
        query_id = await query_repo.generate_id()

        # Create the knowledge service query with actual config ID
        query = KnowledgeServiceQuery(
            query_id=query_id,
            name=query_data["name"],
            knowledge_service_id=knowledge_service_config_id,  # Use actual ID
            prompt=query_data["prompt"],
            query_metadata=query_data["query_metadata"],
            assistant_prompt=query_data.get("assistant_prompt"),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        # Save the query
        await query_repo.save(query)

        # Store the mapping using the filename (without extension) as key
        query_name = query_file.replace("-query.json", "").replace("-", "_")
        query_ids[query_name] = query_id

        logger.info(
            f"Knowledge service query '{query_data['name']}' saved with ID: "
            f"{query_id}"
        )

    return query_ids


async def create_anthropic_knowledge_service_config(
    config_repo: MinioKnowledgeServiceConfigRepository,
) -> str:
    """
    Create the Anthropic knowledge service configuration.

    Returns:
        The knowledge service config ID
    """
    logger.info("Creating Anthropic knowledge service configuration")

    # Generate config ID
    config_id = await config_repo.generate_id()

    # Create the knowledge service configuration
    # Note: This is a basic configuration - in practice you'd want
    # actual API keys and more detailed configuration
    config = KnowledgeServiceConfig(
        knowledge_service_id=config_id,
        name="Anthropic Knowledge Service",
        description="Anthropic Claude API for document analysis",
        service_api=ServiceApi.ANTHROPIC,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    # Save the configuration
    await config_repo.save(config)

    logger.info(
        f"Anthropic knowledge service configuration saved with ID: "
        f"{config_id}"
    )
    return config_id


async def load_validation_checks(
    query_repo: MinioKnowledgeServiceQueryRepository,
    data_dir: Path,
    knowledge_service_config_id: str,
) -> Dict[str, str]:
    """
    Load validation check queries (offensive language and professionalism).

    Args:
        query_repo: Repository for knowledge service queries
        data_dir: Directory containing the query files
        knowledge_service_config_id: Actual generated knowledge service
            config ID

    Returns:
        Dict mapping check names to query IDs
    """
    check_files = [
        "offensive_language_check.json",
        "professionalism_check.json",
    ]

    check_ids = {}

    for check_file in check_files:
        check_path = data_dir / check_file

        logger.info(f"Loading validation check from {check_path}")

        # Read and parse the check file
        with open(check_path, "r", encoding="utf-8") as f:
            check_data = json.load(f)

        # Generate query ID
        check_id = await query_repo.generate_id()

        # Create the knowledge service query with actual config ID
        query = KnowledgeServiceQuery(
            query_id=check_id,
            name=check_data["name"],
            knowledge_service_id=knowledge_service_config_id,  # Use actual ID
            prompt=check_data["prompt"],
            query_metadata=check_data["query_metadata"],
            assistant_prompt=check_data.get("assistant_prompt"),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        # Save the query
        await query_repo.save(query)

        # Store the mapping using the filename (without extension) as key
        check_name = check_file.replace("_check.json", "_check")
        check_ids[check_name] = check_id

        logger.info(
            f"Validation check '{check_data['name']}' saved with ID: "
            f"{check_id}"
        )

    return check_ids


async def load_policy(
    policy_repo: MinioPolicyRepository,
    data_dir: Path,
    validation_check_ids: Dict[str, str],
) -> str:
    """
    Load the offensive language policy.

    Args:
        policy_repo: Repository for policies
        data_dir: Directory containing the policy file
        validation_check_ids: Mapping of validation check names to query IDs

    Returns:
        The policy_id of the loaded policy
    """
    policy_path = data_dir / "offensive_language_policy.json"

    logger.info(f"Loading policy from {policy_path}")

    # Read and parse the policy file
    with open(policy_path, "r", encoding="utf-8") as f:
        policy_data = json.load(f)

    # Generate policy ID - use a fixed ID that matches the client example
    policy_id = "policy-demo-001"

    # Map validation scores to use actual query IDs
    validation_scores = []
    for check_name, required_score in policy_data["validation_scores"]:
        if check_name in validation_check_ids:
            validation_scores.append(
                (validation_check_ids[check_name], required_score)
            )
        else:
            logger.warning(f"Unknown validation check: {check_name}")

    # Create the policy
    policy = Policy(
        policy_id=policy_id,
        title=policy_data["title"],
        description=policy_data["description"],
        status=PolicyStatus.ACTIVE,
        validation_scores=validation_scores,
        transformation_queries=policy_data.get("transformation_queries"),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    # Save the policy
    await policy_repo.save(policy)

    logger.info(f"Policy saved with ID: {policy_id}")
    return policy_id


async def populate_example_data() -> Dict[str, str]:
    """
    Populate all example data and return the IDs for use in workflows.

    Returns:
        Dict containing the IDs of all created entities:
        {
            "document_id": "...",
            "assembly_specification_id": "...",
            "knowledge_service_config_id": "...",
            "policy_id": "...",
            "extract_meeting_info_query_id": "...",
            "extract_agenda_items_query_id": "...",
            "extract_action_items_query_id": "...",
            "offensive_language_check_id": "...",
            "professionalism_check_id": "...",
        }
    """
    logger.info("Starting example data population")

    # Get the data directory
    current_dir = Path(__file__).parent
    data_dir = current_dir / "data"

    if not data_dir.exists():
        raise FileNotFoundError(f"Data directory not found: {data_dir}")

    # Create Minio client
    minio_client = await create_minio_client()

    # Create repository instances
    document_repo = MinioDocumentRepository(client=minio_client)
    assembly_spec_repo = MinioAssemblySpecificationRepository(
        client=minio_client
    )
    query_repo = MinioKnowledgeServiceQueryRepository(client=minio_client)
    config_repo = MinioKnowledgeServiceConfigRepository(client=minio_client)
    policy_repo = MinioPolicyRepository(client=minio_client)

    # Load all the data (create config first so queries can reference it)
    document_id = await load_example_document(document_repo, data_dir)
    config_id = await create_anthropic_knowledge_service_config(config_repo)
    query_ids = await load_knowledge_service_queries(
        query_repo, data_dir, config_id
    )
    validation_check_ids = await load_validation_checks(
        query_repo, data_dir, config_id
    )
    policy_id = await load_policy(policy_repo, data_dir, validation_check_ids)
    assembly_spec_id = await load_assembly_specification(
        assembly_spec_repo, data_dir, query_ids
    )

    # Prepare the result
    result = {
        "document_id": document_id,
        "assembly_specification_id": assembly_spec_id,
        "knowledge_service_config_id": config_id,
        "policy_id": policy_id,
        **{
            f"{name}_query_id": query_id
            for name, query_id in query_ids.items()
        },
        **{
            f"{name}_id": check_id
            for name, check_id in validation_check_ids.items()
        },
    }

    logger.info("Example data population completed successfully")
    logger.info("Created entities:")
    for key, value in result.items():
        logger.info(f"  {key}: {value}")

    return result


async def main() -> Dict[str, str]:
    """Main function to populate example data."""
    setup_logging()

    try:
        result = await populate_example_data()

        print("\n" + "=" * 60)
        print("EXAMPLE DATA POPULATED SUCCESSFULLY")
        print("=" * 60)
        print("\nUse these IDs in your workflow examples:")
        print()
        for key, value in result.items():
            print(f"{key}: {value}")
        print()
        print("You can now run workflows using these real data IDs!")
        print("=" * 60)

        return result

    except Exception as e:
        logger.error(f"Failed to populate example data: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())

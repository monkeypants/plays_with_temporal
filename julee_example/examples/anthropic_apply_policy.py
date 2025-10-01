#!/usr/bin/env python3
"""
Example script to test ValidateDocumentUseCase with Anthropic knowledge
services.

This script demonstrates how to:
1. Load a meeting minutes JSON document from an external data file
2. Create test documents and policy configurations
3. Set up knowledge service configurations and queries
4. Use the ValidateDocumentUseCase to validate documents against policies
   using Anthropic
5. View the complete validation results

Requirements:
    - Set ANTHROPIC_API_KEY environment variable
    - Install dependencies: pip install anthropic
    - Meeting minutes data file: data/extracted_meeting_minutes.json

Usage:
    export ANTHROPIC_API_KEY="your-api-key-here"
    python -m julee_example.examples.anthropic_apply_policy [options]

Options:
    --input, -i FILE    Use custom meeting minutes file
    --policy, -p FILE   Use custom policy file
    --help, -h          Show help message

Examples:
    # Use default meeting minutes and policy
    python -m julee_example.examples.anthropic_apply_policy

    # Use custom meeting minutes file
    python -m julee_example.examples.anthropic_apply_policy \
        --input my_meeting_minutes.json

    # Use custom policy file
    python -m julee_example.examples.anthropic_apply_policy \
        --policy my_policy.json
"""

import argparse
import asyncio
import hashlib
import io

import json
import logging
import os
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
import multihash

from julee_example.domain import (
    Document,
    DocumentStatus,
    ContentStream,
    KnowledgeServiceConfig,
    KnowledgeServiceQuery,
)
from julee_example.domain.policy import (
    Policy,
    PolicyStatus,
    DocumentPolicyValidationStatus,
)
from julee_example.domain.knowledge_service_config import ServiceApi
from julee_example.repositories.memory import (
    MemoryDocumentRepository,
    MemoryDocumentPolicyValidationRepository,
    MemoryKnowledgeServiceConfigRepository,
    MemoryKnowledgeServiceQueryRepository,
    MemoryPolicyRepository,
)
from julee_example.services.knowledge_service.memory import (
    MemoryKnowledgeService,
)
from julee_example.use_cases.validate_document import (
    ValidateDocumentUseCase,
)


def setup_logging() -> None:
    """Configure logging to see debug output."""
    log_level = os.environ.get("LOG_LEVEL", "ERROR").upper()

    # Validate log level
    numeric_level = getattr(logging, log_level, None)
    if not isinstance(numeric_level, int):
        print(f"Invalid log level: {log_level}, defaulting to INFO")
        numeric_level = logging.INFO

    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        force=True,  # Override any existing configuration
    )

    print(f"Logging configured at {log_level} level")


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Test ValidateDocumentUseCase with Anthropic knowledge services"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Use default meeting minutes and policy
  python -m julee_example.examples.anthropic_apply_policy

  # Use custom meeting minutes file
  python -m julee_example.examples.anthropic_apply_policy \
      --input my_meeting_minutes.json

  # Use custom policy file
  python -m julee_example.examples.anthropic_apply_policy \
      --policy my_policy.json

  # Enable debug logging
  LOG_LEVEL=DEBUG \
      python -m julee_example.examples.anthropic_apply_policy
        """,
    )

    parser.add_argument(
        "--input",
        "-i",
        type=str,
        help=(
            "Path to meeting minutes JSON file. Can be absolute or relative "
            "to script directory "
            "(default: data/extracted_meeting_minutes.json)"
        ),
        default=None,
    )

    parser.add_argument(
        "--policy",
        "-p",
        type=str,
        help=(
            "Path to policy file. Can be absolute or "
            "relative to script directory "
            "(default: data/offensive_language_policy.json)"
        ),
        default=None,
    )

    return parser.parse_args()


async def create_meeting_minutes_document(
    input_file_path: Optional[str] = None,
) -> Document:
    """Create a meeting minutes document for testing.

    Loads the meeting minutes content from the specified file or the
    default data/extracted_meeting_minutes.json to make the demo more
    modular and allow for easy customization of the input content.

    Args:
        input_file_path: Optional path to meeting minutes file. If None, uses
            default.
    """
    # Load meeting minutes from specified file or default
    if input_file_path:
        minutes_file = Path(input_file_path)
    else:
        current_dir = Path(__file__).parent
        minutes_file = current_dir / "data" / "extracted_meeting_minutes.json"

    if not minutes_file.exists():
        raise FileNotFoundError(
            f"Meeting minutes file not found: {minutes_file}"
        )

    # Generate document ID
    document_id = f"meeting-minutes-{int(datetime.now().timestamp())}"

    # Read file content and create content stream
    with minutes_file.open("rb") as file_handle:
        file_content = file_handle.read()
    content_stream = ContentStream(io.BytesIO(file_content))

    # Calculate size and multihash from file
    file_size = minutes_file.stat().st_size

    # Calculate multihash using streaming approach
    sha256_hasher = hashlib.sha256()
    with minutes_file.open("rb") as f:
        while chunk := f.read(8192):  # Read in 8KB chunks
            sha256_hasher.update(chunk)
    sha256_hash = sha256_hasher.digest()
    mhash = multihash.encode(sha256_hash, multihash.SHA2_256)
    proper_multihash = str(mhash.hex())

    document = Document(
        document_id=document_id,
        original_filename=minutes_file.name,
        content_type="text/plain",
        size_bytes=file_size,
        content_multihash=proper_multihash,
        status=DocumentStatus.ASSEMBLED,
        content=content_stream,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    print(f"✅ Created meeting minutes document: {document.document_id}")
    print(f"   Filename: {document.original_filename}")
    print(f"   Size: {document.size_bytes} bytes")
    print(f"   Content type: {document.content_type}")
    print(f"   Loaded from: {minutes_file}")

    return document


async def create_policy(
    policy_file_path: Optional[str] = None,
) -> Policy:
    """Create a policy for document validation.

    Args:
        policy_file_path: Optional path to policy file. If None,
            uses default.
    """

    # Load policy from specified file or default
    if policy_file_path:
        policy_file = Path(policy_file_path)
    else:
        current_dir = Path(__file__).parent
        policy_file = current_dir / "data" / "offensive_language_policy.json"

    if not policy_file.exists():
        raise FileNotFoundError(f"Policy file not found: {policy_file}")

    with policy_file.open("r", encoding="utf-8") as f:
        policy_data = json.load(f)

    # Create policy
    policy_id = f"policy-{int(datetime.now().timestamp())}"

    policy = Policy(
        policy_id=policy_id,
        title=policy_data["title"],
        description=policy_data["description"],
        status=PolicyStatus.ACTIVE,
        validation_scores=policy_data["validation_scores"],
        transformation_queries=policy_data.get("transformation_queries"),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    print("✅ Created policy:")
    print(f"   ID: {policy.policy_id}")
    print(f"   Title: {policy.title}")
    print(f"   Validation queries: {len(policy.validation_scores)}")
    if policy.transformation_queries:
        print(
            f"   Transformation queries: {len(policy.transformation_queries)}"
        )
    else:
        print("   No transformation queries (validation-only policy)")
    print(f"   Loaded from: {policy_file}")

    return policy


async def create_knowledge_service_config() -> KnowledgeServiceConfig:
    """Create Anthropic knowledge service configuration."""

    config_id = f"anthropic-ks-{int(datetime.now().timestamp())}"

    config = KnowledgeServiceConfig(
        knowledge_service_id=config_id,
        name="Anthropic Policy Validation Service",
        description=(
            "Anthropic Claude service for validating documents against "
            "policy criteria"
        ),
        service_api=ServiceApi.ANTHROPIC,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    print(
        f"✅ Created knowledge service config: {config.knowledge_service_id}"
    )
    print(f"   Name: {config.name}")
    print(f"   API: {config.service_api.value}")

    return config


async def create_knowledge_service_queries(
    knowledge_service_id: str,
    policy: Policy,
    base_path: Optional[Path] = None,
) -> list[KnowledgeServiceQuery]:
    """Create knowledge service queries by loading from external files.

    Args:
        knowledge_service_id: ID of the knowledge service to use
        policy: Policy containing validation and transformation query IDs
        base_path: Base path for resolving relative query file paths
    """

    queries = []

    if base_path is None:
        base_path = Path(__file__).parent / "data"

    # Collect all query IDs from the policy
    all_query_ids = set()

    # Add validation query IDs
    for query_id, required_score in policy.validation_scores:
        all_query_ids.add(query_id)

    # Add transformation query IDs if they exist
    if policy.transformation_queries:
        for query_id in policy.transformation_queries:
            all_query_ids.add(query_id)

    # Load queries from external files
    for query_id in all_query_ids:
        # Dynamically construct filename from query ID
        query_file_path = f"{query_id}.json"
        query_file = base_path / query_file_path

        if not query_file.exists():
            raise FileNotFoundError(f"Query file not found: {query_file}")

        # Load query data from file
        with query_file.open("r", encoding="utf-8") as f:
            query_data = json.load(f)

        # Create query object with the correct ID expected by the use case
        query = KnowledgeServiceQuery(
            query_id=query_id,
            name=query_data["name"],
            knowledge_service_id=knowledge_service_id,
            prompt=query_data["prompt"],
            query_metadata=query_data.get("query_metadata", {}),
            assistant_prompt=query_data.get("assistant_prompt", ""),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        queries.append(query)
        print(f"   📋 Loaded query from {query_file.name} -> {query_id}")

    print(
        f"✅ Created {len(queries)} knowledge service queries from external "
        f"files:"
    )
    for query in queries:
        print(f"   - {query.name} ({query.query_id})")

    return queries


async def setup_repositories_with_test_data(
    input_file_path: Optional[str] = None,
    policy_file_path: Optional[str] = None,
) -> tuple:
    """Set up in-memory repositories with test data.

    Args:
        input_file_path: Optional path to meeting minutes file to load.
        policy_file_path: Optional path to policy file to load.
    """

    print("\n🔧 Setting up repositories with test data...")

    # Create repositories
    document_repo = MemoryDocumentRepository()
    policy_repo = MemoryPolicyRepository()
    document_policy_validation_repo = (
        MemoryDocumentPolicyValidationRepository()
    )
    ks_config_repo = MemoryKnowledgeServiceConfigRepository()
    ks_query_repo = MemoryKnowledgeServiceQueryRepository()

    # Create test data
    document = await create_meeting_minutes_document(input_file_path)
    policy = await create_policy(policy_file_path)
    ks_config = await create_knowledge_service_config()

    # Determine base path for query files
    if policy_file_path:
        base_path = Path(policy_file_path).parent
    else:
        base_path = Path(__file__).parent / "data"

    ks_queries = await create_knowledge_service_queries(
        ks_config.knowledge_service_id, policy, base_path
    )

    # Store test data in repositories
    await document_repo.save(document)
    await policy_repo.save(policy)
    await ks_config_repo.save(ks_config)

    for query in ks_queries:
        await ks_query_repo.save(query)

    print("✅ Test data stored in repositories")

    return (
        document_repo,
        policy_repo,
        document_policy_validation_repo,
        ks_config_repo,
        ks_query_repo,
        document,
        policy,
    )


async def test_validate_document_use_case(
    input_file_path: Optional[str] = None,
    policy_file_path: Optional[str] = None,
) -> None:
    """Test the ValidateDocumentUseCase with Anthropic knowledge
    services.

    Args:
        input_file_path: Optional path to meeting minutes file to load.
        policy_file_path: Optional path to policy file to load.
    """

    # Check for API key
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("❌ Error: ANTHROPIC_API_KEY environment variable not set")
        print("   Set it with: export ANTHROPIC_API_KEY='your-api-key-here'")
        return

    print(
        "🚀 Testing ValidateDocumentUseCase with Anthropic knowledge services"
    )
    if input_file_path:
        print(f"📁 Using input file: {input_file_path}")
    else:
        print("📁 Using default meeting minutes")
    if policy_file_path:
        print(f"📄 Using policy file: {policy_file_path}")
    else:
        print("📄 Using default policy")
    print("=" * 70)

    try:
        # Set up repositories and test data
        (
            document_repo,
            policy_repo,
            document_policy_validation_repo,
            ks_config_repo,
            ks_query_repo,
            document,
            policy,
        ) = await setup_repositories_with_test_data(
            input_file_path, policy_file_path
        )

        # Create the use case with knowledge service
        # Create a test config for the memory knowledge service
        test_config = KnowledgeServiceConfig(
            knowledge_service_id="ks-example",
            name="Example Knowledge Service",
            description="Memory service for example",
            service_api=ServiceApi.ANTHROPIC,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        knowledge_service = MemoryKnowledgeService(test_config)

        use_case = ValidateDocumentUseCase(
            document_repo=document_repo,
            knowledge_service_query_repo=ks_query_repo,
            knowledge_service_config_repo=ks_config_repo,
            policy_repo=policy_repo,
            document_policy_validation_repo=document_policy_validation_repo,
            knowledge_service=knowledge_service,
            now_fn=lambda: datetime.now(timezone.utc),
        )

        print("\n✅ Created ValidateDocumentUseCase with all repositories")

        # Execute the validation
        print("\n🔄 Executing validation...")
        print(f"   Document: {document.document_id}")
        print(f"   Policy: {policy.policy_id}")

        validation_result = await use_case.validate_document(
            document_id=document.document_id,
            policy_id=policy.policy_id,
        )

        print("✅ Validation completed successfully!")
        print(f"   Validation ID: {validation_result.validation_id}")
        print(f"   Status: {validation_result.status.value}")
        print(f"   Passed: {validation_result.passed}")

        # Display validation details
        print("\n📊 Validation Results:")
        print("=" * 50)

        if validation_result.validation_scores:
            print("Initial Validation Scores:")
            for query_id, score in validation_result.validation_scores:
                # Find the required score for this query
                required_score = next(
                    req_score
                    for q_id, req_score in policy.validation_scores
                    if q_id == query_id
                )
                passed = "✅ PASS" if score >= required_score else "❌ FAIL"
                print(
                    f"   {query_id}: {score}/100 (required: "
                    f"{required_score}) {passed}"
                )

        if validation_result.transformed_document_id:
            print(
                f"\nTransformed Document ID: "
                f"{validation_result.transformed_document_id}"
            )

            # Retrieve and display the transformed document content
            transformed_doc = await document_repo.get(
                validation_result.transformed_document_id
            )
            if transformed_doc:
                print("\n📄 Transformed Document Content:")
                print("=" * 50)

                # Read and display the transformed content
                transformed_doc.content.seek(0)
                content_bytes = transformed_doc.content.read()
                content_text = content_bytes.decode("utf-8")

                try:
                    transformed_data = json.loads(content_text)
                    print(json.dumps(transformed_data, indent=2))
                except json.JSONDecodeError:
                    print("Raw Transformed Content:")
                    print(content_text)

                print("=" * 50)

            if validation_result.post_transform_validation_scores:
                print("Post-Transformation Validation Scores:")
                for (
                    query_id,
                    score,
                ) in validation_result.post_transform_validation_scores:
                    required_score = next(
                        req_score
                        for q_id, req_score in policy.validation_scores
                        if q_id == query_id
                    )
                    passed = (
                        "✅ PASS" if score >= required_score else "❌ FAIL"
                    )
                    print(
                        f"   {query_id}: {score}/100 (required: "
                        f"{required_score}) {passed}"
                    )

        # Display timing information
        print("\nTiming:")
        print(f"   Started: {validation_result.started_at}")
        print(f"   Completed: {validation_result.completed_at}")
        if validation_result.started_at and validation_result.completed_at:
            duration = (
                validation_result.completed_at - validation_result.started_at
            )
            print(f"   Duration: {duration.total_seconds():.2f} seconds")

        # Show error message if any
        if validation_result.error_message:
            print(f"\n❌ Error: {validation_result.error_message}")

        # Display final result summary
        print("\n🏁 Final Result:")
        if validation_result.passed:
            print("   ✅ Document PASSED policy validation")
        else:
            print("   ❌ Document FAILED policy validation")

        if validation_result.status == DocumentPolicyValidationStatus.PASSED:
            if validation_result.transformed_document_id:
                print(
                    "   📝 Document was transformed to meet policy "
                    "requirements"
                )
            else:
                print(
                    "   📝 Document passed without requiring transformation"
                )
        elif (
            validation_result.status == DocumentPolicyValidationStatus.FAILED
        ):
            if validation_result.transformed_document_id:
                print(
                    "   📝 Document was transformed but still failed policy "
                    "requirements"
                )
            else:
                print(
                    "   📝 Document failed and no transformations were "
                    "available"
                )

        print("\nTest completed successfully!")

    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        traceback.print_exc()


async def main() -> None:
    """Main function to run the test."""
    print("Anthropic Policy Validation Use Case Test")
    print("=========================================")

    # Parse command-line arguments
    args = parse_arguments()

    # Get script directory for resolving relative paths
    script_dir = Path(__file__).parent

    # Convert relative paths to be relative to script directory
    input_file_path = args.input
    if input_file_path and not Path(input_file_path).is_absolute():
        input_file_path = str(script_dir / input_file_path)

    policy_file_path = args.policy
    if policy_file_path and not Path(policy_file_path).is_absolute():
        policy_file_path = str(script_dir / policy_file_path)

    # Validate input file if provided
    if input_file_path:
        input_path = Path(input_file_path)
        if not input_path.exists():
            print(f"❌ Error: Input file does not exist: {input_path}")
            sys.exit(1)
        if not input_path.is_file():
            print(f"❌ Error: Input path is not a file: {input_path}")
            sys.exit(1)

    # Validate policy file if provided
    if policy_file_path:
        policy_path = Path(policy_file_path)
        if not policy_path.exists():
            print(f"❌ Error: Policy file does not exist: {policy_path}")
            sys.exit(1)
        if not policy_path.is_file():
            print(f"❌ Error: Policy path is not a file: {policy_path}")
            sys.exit(1)

    # Setup logging first
    setup_logging()
    print()

    await test_validate_document_use_case(input_file_path, policy_file_path)


if __name__ == "__main__":
    # Run the async test
    asyncio.run(main())

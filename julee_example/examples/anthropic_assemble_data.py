#!/usr/bin/env python3
"""
Example script to test ExtractAssembleDataUseCase with Anthropic knowledge
services.

This script demonstrates how to:
1. Load a meeting transcript from an external data file
2. Create test documents and assembly specifications
3. Set up knowledge service configurations and queries
4. Use the ExtractAssembleDataUseCase to extract and assemble documents using
   Anthropic
5. View the complete assembled output

Requirements:
    - Set ANTHROPIC_API_KEY environment variable
    - Install dependencies: pip install anthropic
    - Meeting transcript data file: data/meeting_transcript.txt

Usage:
    export ANTHROPIC_API_KEY="your-api-key-here"
    python -m julee_example.examples.anthropic_assemble_data_test [options]

Options:
    --input, -i FILE    Use custom meeting transcript file
    --spec, -s FILE     Use custom assembly specification file
    --help, -h          Show help message

Examples:
    # Use default meeting transcript and schema
    python -m julee_example.examples.anthropic_assemble_data_test

    # Use custom transcript file
    python -m julee_example.examples.anthropic_assemble_data_test \
        --input my_meeting.txt

    # Use custom assembly specification file
    python -m julee_example.examples.anthropic_assemble_data_test \
        --spec my_assembly_spec.json
"""

import argparse
import asyncio
import hashlib

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
    AssemblySpecification,
    AssemblySpecificationStatus,
    KnowledgeServiceConfig,
    KnowledgeServiceQuery,
)
from julee_example.domain.knowledge_service_config import ServiceApi
from julee_example.repositories.memory import (
    MemoryDocumentRepository,
    MemoryAssemblyRepository,
    MemoryAssemblySpecificationRepository,
    MemoryKnowledgeServiceConfigRepository,
    MemoryKnowledgeServiceQueryRepository,
)
from julee_example.use_cases.extract_assemble_data import (
    ExtractAssembleDataUseCase,
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
            "Test ExtractAssembleDataUseCase with Anthropic knowledge "
            "services"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Use default meeting transcript and schema
  python -m julee_example.examples.anthropic_assemble_data_test

  # Use custom transcript file
  python -m julee_example.examples.anthropic_assemble_data_test \
      --input my_meeting.txt

  # Use custom assembly specification file
  python -m julee_example.examples.anthropic_assemble_data_test \
      --spec my_assembly_spec.json

  # Use both custom transcript and specification
  python -m julee_example.examples.anthropic_assemble_data_test \
      --input my_meeting.txt --spec my_assembly_spec.json

  # Enable debug logging
  LOG_LEVEL=DEBUG \
      python -m julee_example.examples.anthropic_assemble_data_test
        """,
    )

    parser.add_argument(
        "--input",
        "-i",
        type=str,
        help=(
            "Path to meeting transcript file. Can be absolute or relative "
            "to script directory (default: data/meeting_transcript.txt)"
        ),
        default=None,
    )

    parser.add_argument(
        "--spec",
        "-s",
        type=str,
        help=(
            "Path to assembly specification file. Can be absolute or "
            "relative to script directory "
            "(default: data/meeting_minutes_assembly_spec.json)"
        ),
        default=None,
    )

    return parser.parse_args()


async def create_meeting_transcript_document(
    input_file_path: Optional[str] = None,
) -> Document:
    """Create a meeting transcript document for testing.

    Loads the meeting transcript content from the specified file or the
    default data/meeting_transcript.txt to make the demo more modular and
    allow for easy customization of the input content.

    Args:
        input_file_path: Optional path to transcript file. If None, uses
            default.
    """
    # Load meeting transcript from specified file or default
    if input_file_path:
        transcript_file = Path(input_file_path)
    else:
        current_dir = Path(__file__).parent
        transcript_file = current_dir / "data" / "meeting_transcript.txt"

    if not transcript_file.exists():
        raise FileNotFoundError(
            f"Meeting transcript file not found: {transcript_file}"
        )

    # Generate document ID
    document_id = f"meeting-transcript-{int(datetime.now().timestamp())}"

    # Open file and create content stream directly from file handle
    file_handle = transcript_file.open("rb")
    content_stream = ContentStream(file_handle)

    # Calculate size and multihash from file
    file_size = transcript_file.stat().st_size

    # Calculate multihash using streaming approach
    sha256_hasher = hashlib.sha256()
    with transcript_file.open("rb") as f:
        while chunk := f.read(8192):  # Read in 8KB chunks
            sha256_hasher.update(chunk)
    sha256_hash = sha256_hasher.digest()
    mhash = multihash.encode(sha256_hash, multihash.SHA2_256)
    proper_multihash = str(mhash.hex())

    document = Document(
        document_id=document_id,
        original_filename=transcript_file.name,
        content_type="text/plain",
        size_bytes=file_size,
        content_multihash=proper_multihash,
        status=DocumentStatus.CAPTURED,
        content=content_stream,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    print(f"✅ Created meeting transcript: {document.document_id}")
    print(f"   Filename: {document.original_filename}")
    print(f"   Size: {document.size_bytes} bytes")
    print(f"   Content type: {document.content_type}")
    print(f"   Loaded from: {transcript_file}")

    return document


async def create_assembly_specification(
    spec_file_path: Optional[str] = None,
) -> AssemblySpecification:
    """Create an assembly specification for meeting minutes.

    Args:
        spec_file_path: Optional path to assembly specification file. If None,
            uses default.
    """

    # Load assembly specification from specified file or default
    if spec_file_path:
        spec_file = Path(spec_file_path)
    else:
        current_dir = Path(__file__).parent
        spec_file = (
            current_dir / "data" / "meeting_minutes_assembly_spec.json"
        )

    if not spec_file.exists():
        raise FileNotFoundError(
            f"Assembly specification file not found: {spec_file}"
        )

    with spec_file.open("r", encoding="utf-8") as f:
        spec_data = json.load(f)

    # Create assembly specification
    spec_id = f"meeting-minutes-spec-{int(datetime.now().timestamp())}"

    assembly_spec = AssemblySpecification(
        assembly_specification_id=spec_id,
        name=spec_data["name"],
        applicability=spec_data["applicability"],
        jsonschema=spec_data["jsonschema"],
        status=AssemblySpecificationStatus.ACTIVE,
        knowledge_service_queries=spec_data["knowledge_service_queries"],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    print("✅ Created assembly specification:")
    print(f"   ID: {assembly_spec.assembly_specification_id}")
    print(f"   Name: {assembly_spec.name}")
    print(
        f"   Query mappings: {len(assembly_spec.knowledge_service_queries)}"
    )
    print(f"   Loaded from: {spec_file}")

    return assembly_spec


async def create_knowledge_service_config() -> KnowledgeServiceConfig:
    """Create Anthropic knowledge service configuration."""

    config_id = f"anthropic-ks-{int(datetime.now().timestamp())}"

    config = KnowledgeServiceConfig(
        knowledge_service_id=config_id,
        name="Anthropic Meeting Analysis Service",
        description=(
            "Anthropic Claude service for analyzing meeting transcripts and "
            "extracting structured data"
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
    assembly_spec: AssemblySpecification,
    base_path: Optional[Path] = None,
) -> list[KnowledgeServiceQuery]:
    """Create knowledge service queries by loading from external files.

    Args:
        knowledge_service_id: ID of the knowledge service to use
        assembly_spec: Assembly specification containing query IDs
        base_path: Base path for resolving relative query file paths
    """

    queries = []

    if base_path is None:
        base_path = Path(__file__).parent

    # Load queries from external files based on what's referenced in spec
    for (
        schema_pointer,
        query_id,
    ) in assembly_spec.knowledge_service_queries.items():
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
    spec_file_path: Optional[str] = None,
) -> tuple:
    """Set up in-memory repositories with test data.

    Args:
        input_file_path: Optional path to transcript file to load.
        spec_file_path: Optional path to assembly specification file to load.
    """

    print("\n🔧 Setting up repositories with test data...")

    # Create repositories
    document_repo = MemoryDocumentRepository()
    assembly_repo = MemoryAssemblyRepository()
    assembly_spec_repo = MemoryAssemblySpecificationRepository()
    ks_config_repo = MemoryKnowledgeServiceConfigRepository()
    ks_query_repo = MemoryKnowledgeServiceQueryRepository()

    # Create test data
    document = await create_meeting_transcript_document(input_file_path)
    assembly_spec = await create_assembly_specification(spec_file_path)
    ks_config = await create_knowledge_service_config()

    # Determine base path for query files
    if spec_file_path:
        base_path = Path(spec_file_path).parent
    else:
        base_path = Path(__file__).parent / "data"

    ks_queries = await create_knowledge_service_queries(
        ks_config.knowledge_service_id, assembly_spec, base_path
    )

    # Store test data in repositories
    await document_repo.save(document)
    await assembly_spec_repo.save(assembly_spec)
    await ks_config_repo.save(ks_config)

    for query in ks_queries:
        await ks_query_repo.save(query)

    print("✅ Test data stored in repositories")

    return (
        document_repo,
        assembly_repo,
        assembly_spec_repo,
        ks_config_repo,
        ks_query_repo,
        document,
        assembly_spec,
    )


async def test_assemble_data_use_case(
    input_file_path: Optional[str] = None,
    spec_file_path: Optional[str] = None,
) -> None:
    """Test the ExtractAssembleDataUseCase with Anthropic knowledge
    services.

    Args:
        input_file_path: Optional path to transcript file to load.
        spec_file_path: Optional path to assembly specification file to load.
    """

    # Check for API key
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("❌ Error: ANTHROPIC_API_KEY environment variable not set")
        print("   Set it with: export ANTHROPIC_API_KEY='your-api-key-here'")
        return

    print(
        "🚀 Testing ExtractAssembleDataUseCase with Anthropic knowledge "
        "services"
    )
    if input_file_path:
        print(f"📁 Using input file: {input_file_path}")
    else:
        print("📁 Using default meeting transcript")
    if spec_file_path:
        print(f"📄 Using assembly spec file: {spec_file_path}")
    else:
        print("📄 Using default assembly specification")
    print("=" * 70)

    try:
        # Set up repositories and test data
        (
            document_repo,
            assembly_repo,
            assembly_spec_repo,
            ks_config_repo,
            ks_query_repo,
            document,
            assembly_spec,
        ) = await setup_repositories_with_test_data(
            input_file_path, spec_file_path
        )

        # Create the use case
        use_case = ExtractAssembleDataUseCase(
            document_repo=document_repo,
            assembly_repo=assembly_repo,
            assembly_specification_repo=assembly_spec_repo,
            knowledge_service_query_repo=ks_query_repo,
            knowledge_service_config_repo=ks_config_repo,
        )

        print("\n✅ Created ExtractAssembleDataUseCase with all repositories")

        # Execute the assembly
        print("\n🔄 Executing assembly...")
        print(f"   Document: {document.document_id}")
        print(f"   Specification: {assembly_spec.assembly_specification_id}")

        assembly_result = await use_case.assemble_data(
            document_id=document.document_id,
            assembly_specification_id=assembly_spec.assembly_specification_id,
        )

        print("✅ Assembly completed successfully!")
        print(f"   Assembly ID: {assembly_result.assembly_id}")
        print(f"   Status: {assembly_result.status.value}")
        print(
            f"   Assembled document ID: "
            f"{assembly_result.assembled_document_id}"
        )

        if assembly_result.assembled_document_id:
            # Retrieve and display the assembled document
            assembled_doc = await document_repo.get(
                assembly_result.assembled_document_id
            )
            if assembled_doc:
                print("\n📄 Assembled Document Details:")
                print(f"   Document ID: {assembled_doc.document_id}")
                print(f"   Filename: {assembled_doc.original_filename}")
                print(f"   Size: {assembled_doc.size_bytes} bytes")
                print(f"   Status: {assembled_doc.status.value}")

                # Read and parse the assembled content
                assembled_doc.content.seek(0)
                content_bytes = assembled_doc.content.read()
                content_text = content_bytes.decode("utf-8")
                assembled_doc.content.seek(0)

                try:
                    assembled_data = json.loads(content_text)

                    print()
                    print("Assembled Meeting Minutes:")
                    print("=" * 50)
                    print(json.dumps(assembled_data, indent=2))

                    meeting_info = assembled_data.get("meeting_info", {})
                    agenda_items = assembled_data.get("agenda_items", [])
                    action_items = assembled_data.get("action_items", [])

                    print()
                    print("Assembly Statistics:")
                    print(
                        "   Meeting Title:", meeting_info.get("title", "N/A")
                    )
                    print(
                        "   Attendees:",
                        len(meeting_info.get("attendees", [])),
                    )
                    print("   Agenda Items:", len(agenda_items))
                    print("   Action Items:", len(action_items))

                except json.JSONDecodeError:
                    print()
                    print("Raw Assembled Content:")
                    print(content_text)

        print("\nTest completed successfully!")

    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        traceback.print_exc()


async def main() -> None:
    """Main function to run the test."""
    print("Anthropic Extract Assemble Data Use Case Test")
    print("=============================================")

    # Parse command-line arguments
    args = parse_arguments()

    # Get script directory for resolving relative paths
    script_dir = Path(__file__).parent

    # Convert relative paths to be relative to script directory
    input_file_path = args.input
    if input_file_path and not Path(input_file_path).is_absolute():
        input_file_path = str(script_dir / input_file_path)

    spec_file_path = args.spec
    if spec_file_path and not Path(spec_file_path).is_absolute():
        spec_file_path = str(script_dir / spec_file_path)

    # Validate input file if provided
    if input_file_path:
        input_path = Path(input_file_path)
        if not input_path.exists():
            print(f"❌ Error: Input file does not exist: {input_path}")
            sys.exit(1)
        if not input_path.is_file():
            print(f"❌ Error: Input path is not a file: {input_path}")
            sys.exit(1)

    # Validate assembly specification file if provided
    if spec_file_path:
        spec_path = Path(spec_file_path)
        if not spec_path.exists():
            print(f"❌ Error: Assembly spec file does not exist: {spec_path}")
            sys.exit(1)
        if not spec_path.is_file():
            print(f"❌ Error: Assembly spec path is not a file: {spec_path}")
            sys.exit(1)

    # Setup logging first
    setup_logging()
    print()

    await test_assemble_data_use_case(input_file_path, spec_file_path)


if __name__ == "__main__":
    # Run the async test
    asyncio.run(main())

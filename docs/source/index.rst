...plays with temporal
======================

This repository contains experiments that combine Temporal.io workflows with clean architecture patterns.

Applications:

* :doc:`sample <sample>`
  The main experiment, demonstrating Temporal workflow patterns using a clean architecture.
* :doc:`julee_example <julee_example>`
  One definition of AI "agent" is something that runs in a loop to achieve a goal.
  By this definition, Julee is *not* an agent.
  It's a deterministic orchestration (a "pipeline" rather than a "loop")
  that combines services in a structured, repeatable, monitorable and accountable way.
* :doc:`cal <cal>`
  A calendar integration/synchronisation workflow.

There is also:

* util/
  Shared utilities and common functionality.
* bin/
  Command-line utilities and daemon scripts.
* fun-police/
  Project documentation and methodology.

.. toctree::
   :maxdepth: 2
   :caption: Architecture:

   clean_architecture
   patterns


Sample App
----------

The main experiment, demonstrating Temporal workflow patterns using a clean architecture.

.. toctree::
   :maxdepth: 2
   :caption: Sample:

   sample
   sample/api
   sample/api/requests
   sample/api/responses
   sample/repos
   sample/repos/minio
   sample/repos/temporal

Julee Example
-------------

One definition of AI "agent" is something that runs in a loop to achieve a goal.
By this definition, Julee is *not* an agent.
It's a deterministic orchestration (a "pipeline" rather than a "loop")
that combines services in a structured, repeatable, monitorable and accountable way.

.. toctree::
   :maxdepth: 2
   :caption: Julee Example:

   julee_example
   julee_example/domain
   julee_example/domain/assembly/assembly
   julee_example/domain/assembly_specification/assembly_specification
   julee_example/domain/assembly_specification/knowledge_service_query
   julee_example/domain/custom_fields/content_stream
   julee_example/domain/document/document
   julee_example/domain/knowledge_service_config/knowledge_service_config
   julee_example/domain/policy/document_policy_validation
   julee_example/domain/policy/policy
   julee_example/repositories
   julee_example/repositories/assembly
   julee_example/repositories/assembly_specification
   julee_example/repositories/base
   julee_example/repositories/document
   julee_example/repositories/document_policy_validation
   julee_example/repositories/knowledge_service_config
   julee_example/repositories/knowledge_service_query
   julee_example/repositories/memory
   julee_example/repositories/minio
   julee_example/repositories/policy
   julee_example/repositories/temporal
   julee_example/services/knowledge_service/knowledge_service
   julee_example/use_cases
   julee_example/use_cases/decorators
   julee_example/use_cases/extract_assemble_data
   julee_example/use_cases/validate_document

Calendar App
------------

A calendar integration/synchronisation workflow.

.. toctree::
   :maxdepth: 2
   :caption: Calendar:

   cal
   cal/activities
   cal/repos
   cal/repositories
   cal/worker
   cal/workflows

Utilities
---------

Shared utilities and common functionality.

.. toctree::
   :maxdepth: 2
   :caption: Utilities:

   util/domain
   util/repositories
   util/repos
   util/repos/minio
   util/repos/minio/file_storage
   util/repos/temporal
   util/repos/temporal/decorators
   util/repos/temporal/minio_file_storage


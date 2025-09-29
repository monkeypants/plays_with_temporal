Julee Example Application
=========================

The julee_example application demonstrates a deterministic orchestration pipeline that combines AI services in a structured, repeatable, monitorable and accountable way. Unlike traditional "agent" patterns that run in loops, Julee implements a pipeline architecture for document policy validation and knowledge service integration.

Architecture Overview
---------------------

The julee_example follows clean architecture principles with domain-driven design:

* **Domain Layer**: Policy models, document entities, and validation rules
* **Use Cases**: Document processing workflows and policy validation orchestration
* **Interface Adapters**: Repository implementations for different storage backends
* **Infrastructure**: Temporal workflows and external service integrations

Key Components
--------------

Domain Models
~~~~~~~~~~~~~

.. toctree::
   :maxdepth: 2

   julee_example/domain/__init__

Use Cases
~~~~~~~~~

.. toctree::
   :maxdepth: 2

   julee_example/use_cases/document_processing

Repository Implementations
~~~~~~~~~~~~~~~~~~~~~~~~~~

The application includes memory-based repositories and Temporal activity repositories. These are implemented but documentation is being generated dynamically.
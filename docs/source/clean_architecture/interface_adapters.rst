.. _clean_architecture:interface_adapters:

Interface Adapters
==================

**Interface adapters** convert data between the format most convenient for use cases and entities, and the format most convenient for external agencies like databases and web frameworks. This layer isolates the business logic from the technical details of how data enters and leaves the system.

Interface adapters serve as translation boundaries that allow use cases to remain pure while connecting to the messy external world. They implement the repository protocols defined in the entity layer and handle the conversion between domain objects and external formats. This architectural pattern enables the same use case to work with different external systems without modification - switching from MinIO to PostgreSQL, or from REST APIs to GraphQL, requires only changes in this layer.

API Controllers
---------------

**API controllers** handle HTTP requests and responses, converting web-specific data formats into use case inputs and domain objects back into HTTP responses. Controllers coordinate between the web framework and use cases without containing business logic themselves.

* :doc:`../sample/api/app` - FastAPI controllers for order processing endpoints
* :doc:`../sample/api/dependencies` - Dependency injection configuration for web layer

Repository Implementations
---------------------------

**Repository implementations** provide concrete implementations of the repository protocols defined in the entity layer. These adapters handle the technical details of data persistence, caching, and retrieval while presenting a clean interface to use cases.

* :doc:`../sample/repos/minio` - MinIO object storage implementations for orders and payments
* :doc:`../sample/repos/temporal` - Temporal workflow-based repository implementations
* :doc:`../cal/repos` - Calendar repository implementations (Google Calendar, PostgreSQL, mock)
* :doc:`../julee_example/repositories/minio` - Document storage using MinIO
* :doc:`../julee_example/repositories/memory` - In-memory implementations for testing
* :doc:`../julee_example/repositories/temporal` - Temporal workflow adapters for document processing
* :doc:`../util/repos/minio` - Shared MinIO file storage implementations
* :doc:`../util/repos/temporal` - Shared Temporal infrastructure and decorators

Service Adapters
----------------

**Service adapters** integrate with external services and APIs, translating between domain objects and third-party service formats. These adapters encapsulate the complexity of external service communication while providing clean interfaces to use cases.

* :doc:`../julee_example/services/knowledge_service/knowledge_service` - AI service adapters for document processing

Infrastructure Adapters
------------------------

**Infrastructure adapters** connect use cases to platform services like workflow engines, message queues, and distributed systems. These adapters handle the technical aspects of distributed computing while keeping business logic isolated.

* :doc:`../sample/worker` - Temporal worker infrastructure for order processing
* :doc:`../sample/workflow` - Temporal workflow definitions and orchestration
* :doc:`../cal/worker` - Calendar synchronization worker infrastructure
* :doc:`../cal/workflows` - Calendar workflow definitions

Future interface adapters might include PostgreSQL database implementations, Redis caching layers, message queue handlers, external payment gateway adapters, notification service integrations, and event streaming connectors. The clean architecture makes adding these adapters straightforward without affecting existing business logic.

.. uml:: ../../img/interface-adapter-dependencies.puml
   :align: center
   :alt: Interface Adapter Layer Dependencies
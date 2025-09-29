Clean Architecture
==================

Clean Architecture, as defined by Robert C. Martin (Uncle Bob),
is an architecture that puts the business logic at the center of the design.
Source code dependencies can only point inwards (The Dependency Rule),
toward higher-level policies.

.. uml:: ../img/clean-architecture-dependencies.puml
   :align: center
   :alt: Clean Architecture Dependencies

The architecture creates a separation between:

* the **essential** complexity (what the software does - use cases and entities); and
* the **accidental** complexity (how it does it - interface adapters, frameworks & drivers).

This isn't just about layering - it's about putting "what the application does" at the centre,
and pushing "how it works" to the periphery.
Database, web frameworks, and external services are just implementation details
that can be deferred and changed without affecting the core business logic.


.. _clean_architecture:entities:

Entities
~~~~~~~~

The fundamental business concepts of the system,
the canonical nouns, the subjects of the business rules.

The **domain model** is essentially a rich type system for business concepts.
The software architecture decision here is to implement them using pydantic,
because it provides convenient ways to implement data validation
(as part of the type system/domain model) and serialization/deserialisation
(where the domain objects are used elsewhare in the code).

* :doc:`sample/domain` - Order processing business
* :doc:`cal/domain` - Calendar and scheduling
* :doc:`util/domain` - Otherwise repetitive concepts (e.g. files)
* :doc:`julee_example/domain/__init__` - intelligent document processing and policy implementation

Entities encapsulate the most general and high-level business rules.
They are the least likely to change when something external changes.
An entity can be an object with methods, or a set of data structures and functions.

**Repository protocols** are domain-specific interfaces defined using Python Protocols that specify contracts for data access operations. These protocols enable dependency inversion - use cases depend on interfaces, not implementations.

Repository protocols define *what* data operations are needed without specifying *how* they're implemented. This allows the same use case to work with different storage mechanisms: in-memory for testing, databases for production, or workflow stubs for Temporal contexts. All protocols use ``@runtime_checkable`` for structural typing and include comprehensive behavioral contracts with idempotency guarantees. These are internal contracts between layers of the system.

* :doc:`sample/repositories` - Order processing repository contracts
* :doc:`julee_example/repositories/base` - Generic base repository protocol
* :doc:`util/repositories` - Shared infrastructure repository protocols

**Request and response objects** are Pydantic-based data structures that define the contract between external interfaces and internal domain logic. These objects isolate external API concerns from domain models and provide validation at system boundaries.

Request and response objects enable API evolution without affecting core business logic. They serve as translation layers that convert external data formats into domain objects and vice versa. The objects use Pydantic validation to ensure data integrity before it reaches use cases, catching malformed data early in the request lifecycle. These are public contracts with external systems.

* :doc:`sample/api/requests` - API request models for order processing
* :doc:`sample/api/responses` - API response models with status tracking

Both repository protocols and request/response objects are part of the entity layer because they define interface contracts that protect domain integrity - repository protocols as internal boundaries between system layers, and request/response objects as external boundaries with client systems.

.. uml:: ../img/domain-dependencies.puml
   :align: center
   :alt: Entity Layer Dependencies

**Domain validation and security** utilities ensure architectural contracts and provide security boundaries for the domain layer. These components perform runtime validation that complements static type checking, catching configuration errors and data integrity issues at critical system boundaries.

Domain validation includes protocol compliance checking using ``@runtime_checkable``, ensuring repository implementations satisfy their contracts. Security validation provides defense against malicious file uploads and data corruption. Domain-specific exceptions like ``RepositoryValidationError`` and ``DomainValidationError`` provide clear error boundaries that bubble up through the architecture layers.

* :doc:`sample/validation` - Comprehensive validation utilities and security patterns

Domain validation belongs to the entity layer because it enforces the business rules and architectural contracts that protect domain integrity, ensuring the system maintains its invariants regardless of external inputs or internal implementation changes.


.. _clean_architecture:use_cases:

Use Cases
~~~~~~~~~

**Use cases** are application-specific business rules that orchestrate the flow of data to and from entities. They direct entities to use their enterprise-wide business rules to achieve specific application goals.

Use cases contain the workflows and coordination logic that make your application unique. While entities represent what your business *is*, use cases represent what your business *does*. For example, "Validate Document Use Case" validates documents against policies using general ``Document`` and ``Policy`` entities, but the validation workflow is specific to the document processing application. Use cases depend only on entities, never on outer layers like databases or web frameworks.

* :doc:`sample/usecase` - **Order processing workflows**: OrderFulfillmentUseCase (saga pattern for payment/inventory), GetOrderUseCase (order retrieval), CancelOrderUseCase (order cancellation with compensation)
* :doc:`cal/usecase` - **Calendar and scheduling workflows**: CalendarSyncUseCase (bidirectional calendar synchronization), CreateScheduleUseCase (schedule generation from calendar events with AI classification)
* :doc:`julee_example/use_cases/extract_assemble_data` - **Document assembly workflows**: ExtractAssembleDataUseCase (document extraction and assembly according to specifications)
* :doc:`julee_example/use_cases/validate_document` - **Document validation workflows**: ValidateDocumentUseCase (document validation against organizational policies using AI services)

.. uml:: ../img/usecase-dependencies.puml
   :align: center
   :alt: Use Case Layer Dependencies


.. _clean_architecture:interface_adapters:

Interface Adapters
~~~~~~~~~~~~~~~~~~

**Interface adapters** convert data between the format most convenient for use cases and entities, and the format most convenient for external agencies like databases and web frameworks. This layer isolates the business logic from the technical details of how data enters and leaves the system.

Interface adapters serve as translation boundaries that allow use cases to remain pure while connecting to the messy external world. They implement the repository protocols defined in the entity layer and handle the conversion between domain objects and external formats. This architectural pattern enables the same use case to work with different external systems without modification - switching from MinIO to PostgreSQL, or from REST APIs to GraphQL, requires only changes in this layer.

**API controllers** handle HTTP requests and responses, converting web-specific data formats into use case inputs and domain objects back into HTTP responses. Controllers coordinate between the web framework and use cases without containing business logic themselves.

* :doc:`sample/api/app` - FastAPI controllers for order processing endpoints
* :doc:`sample/api/dependencies` - Dependency injection configuration for web layer

**Repository implementations** provide concrete implementations of the repository protocols defined in the entity layer. These adapters handle the technical details of data persistence, caching, and retrieval while presenting a clean interface to use cases.

* :doc:`sample/repos/minio` - MinIO object storage implementations for orders and payments
* :doc:`sample/repos/temporal` - Temporal workflow-based repository implementations
* :doc:`cal/repos` - Calendar repository implementations (Google Calendar, PostgreSQL, mock)
* :doc:`julee_example/repositories/minio` - Document storage using MinIO
* :doc:`julee_example/repositories/memory` - In-memory implementations for testing
* :doc:`julee_example/repositories/temporal` - Temporal workflow adapters for document processing
* :doc:`util/repos/minio` - Shared MinIO file storage implementations
* :doc:`util/repos/temporal` - Shared Temporal infrastructure and decorators

**Service adapters** integrate with external services and APIs, translating between domain objects and third-party service formats. These adapters encapsulate the complexity of external service communication while providing clean interfaces to use cases.

* :doc:`julee_example/services/knowledge_service/knowledge_service` - AI service adapters for document processing

**Infrastructure adapters** connect use cases to platform services like workflow engines, message queues, and distributed systems. These adapters handle the technical aspects of distributed computing while keeping business logic isolated.

* :doc:`sample/worker` - Temporal worker infrastructure for order processing
* :doc:`sample/workflow` - Temporal workflow definitions and orchestration
* :doc:`cal/worker` - Calendar synchronization worker infrastructure
* :doc:`cal/workflows` - Calendar workflow definitions

Future interface adapters might include PostgreSQL database implementations, Redis caching layers, message queue handlers, external payment gateway adapters, notification service integrations, and event streaming connectors. The clean architecture makes adding these adapters straightforward without affecting existing business logic.

.. uml:: ../img/interface-adapter-dependencies.puml
   :align: center
   :alt: Interface Adapter Layer Dependencies


.. _clean_architecture:frameworks_and_drivers:

Frameworks and Drivers
~~~~~~~~~~~~~~~~~~~~~~

**Location**: ``worker.py``, Docker files, configuration files, framework setup

This is where all the details go: web frameworks, databases, external services. These are tools and delivery mechanisms, not the core of your application.

**Contains**:
* Web frameworks (FastAPI)
* Databases (PostgreSQL, Redis)
* External services (Temporal workflows)
* Configuration and main functions
* Dependency injection containers

**Dependencies**: Everything - this layer uses all the inner layers


Directory Structure Mapping
----------------------------

Here's how the clean architecture layers map to the actual directory structure in this project:

::

    sample/
    ├── domain.py              # Domain Layer (Entities)
    ├── repositories.py        # Domain Layer (Repository Protocols)
    ├── validation.py          # Domain Layer (Domain Validation)
    ├── usecase.py             # Use Cases Layer
    ├── api/
    │   ├── requests.py        # Domain Layer (Request Objects)
    │   ├── responses.py       # Domain Layer (Response Objects)
    │   └── controllers.py     # Interface Adapters Layer
    ├── worker.py              # Infrastructure Layer
    └── workflow.py            # Infrastructure Layer (Temporal-specific)

    julee_example/
    ├── domain/                # Domain Layer
    ├── use_cases/             # Use Cases Layer
    ├── repositories/          # Interface Adapters Layer
    └── services/              # Interface Adapters Layer

    util/
    ├── domain.py              # Shared Domain Layer
    └── repositories.py        # Shared Interface Adapters Layer


Key Patterns in the Code
------------------------


Repository Pattern
~~~~~~~~~~~~~~~~~~

Repositories provide a uniform interface for accessing domain objects, regardless of the underlying storage mechanism. This codebase uses Python Protocols and the type system for enforcing repository interfaces, leveraging structural typing:

.. code-block:: python

    # Domain layer defines the protocol interface
    from typing import Protocol

    class UserRepository(Protocol):
        async def find_by_id(self, user_id: UserId) -> Optional[User]:
            ...

    # Infrastructure layer provides the implementation
    # No explicit inheritance needed - structural typing
    class SqlUserRepository:
        async def find_by_id(self, user_id: UserId) -> Optional[User]:
            # Database-specific implementation
            pass

This approach provides several advantages over ABC-based interfaces:

* **Structural typing**: No explicit inheritance required - any class with matching methods satisfies the protocol
* **Type safety**: MyPy enforces protocol compliance at static analysis time
* **Flexibility**: Easier to retrofit existing classes to satisfy protocols
* **Pythonic**: Leverages Python's duck typing philosophy with static type checking


Dependency Injection
~~~~~~~~~~~~~~~~~~~~

Dependencies flow inward - use cases depend on repository interfaces (not implementations), and implementations are injected from the outer layers.


Request and Response Objects
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Use cases define their own data structures for input and output, preventing external concerns from leaking into the business logic.


Protocol Validation
~~~~~~~~~~~~~~~~~~~

Runtime validation ensures that repository implementations satisfy their protocol contracts using ``@runtime_checkable``. This catches configuration errors early and provides clear failure modes:

.. code-block:: python

    from sample.validation import validate_repository_protocol
    from sample.repositories import PaymentRepository

    # Validate at startup - fails fast if implementation is incorrect
    validate_repository_protocol(payment_repo, PaymentRepository)

    # Or ensure with type safety
    validated_repo = ensure_repository_protocol(payment_repo, PaymentRepository)

This approach combines the benefits of structural typing with runtime safety, ensuring that dependency injection configurations are correct and that implementations remain compliant as code evolves.


Why This Matters
-----------------

Uncle Bob's Clean Architecture addresses the fundamental problems of software architecture:

1. **Framework Independence**: The architecture doesn't depend on frameworks. Frameworks are tools, not architectures. You can use them without cramming your system into their limited constraints.

2. **Testable**: Business rules can be tested without the UI, database, web server, or any other external element.

3. **UI Independent**: The UI can change easily without changing the rest of the system. A web UI could be replaced with a console UI without changing business rules.

4. **Database Independent**: You can swap out Oracle or SQL Server for MongoDB, BigTable, CouchDB, or something else. Your business rules are not bound to the database.

5. **External Agency Independent**: Your business rules don't know anything about the outside world.

The goal is to create a system architecture that allows these concerns to be changeable and pluggable. The business logic - the thing that makes your application valuable - should be the center, not an afterthought built around database schemas or framework constraints.


Common Patterns You'll See
---------------------------

* **Interfaces in Use Cases**: Abstract base classes define contracts that infrastructure must implement
* **No Framework Dependencies in Domain**: Business logic never imports FastAPI, Temporal, or database libraries
* **Validation in Domain**: Business rules and validation logic live in domain entities, not controllers
* **Error Handling**: Domain-specific exceptions bubble up through the layers

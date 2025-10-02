.. _clean_architecture:entities:

Entities
========

The fundamental business concepts of the system,
the canonical nouns, the subjects of the business rules.

The **domain model** is essentially a rich type system for business concepts.
The software architecture decision here is to implement them using pydantic,
because it provides convenient ways to implement data validation
(as part of the type system/domain model) and serialization/deserialisation
(where the domain objects are used elsewhare in the code).

* :doc:`../sample/domain` - Order processing business
* :doc:`../cal/domain` - Calendar and scheduling
* :doc:`../util/domain` - Otherwise repetitive concepts (e.g. files)
* :doc:`../julee_example/domain/__init__` - intelligent document processing and policy implementation

Entities encapsulate the most general and high-level business rules.
They are the least likely to change when something external changes.
An entity can be an object with methods, or a set of data structures and functions.

Repository Protocols
---------------------

**Repository protocols** are domain-specific interfaces defined using Python Protocols that specify contracts for data access operations. These protocols enable dependency inversion - use cases depend on interfaces, not implementations.

Repository protocols define *what* data operations are needed without specifying *how* they're implemented. This allows the same use case to work with different storage mechanisms: in-memory for testing, databases for production, or workflow stubs for Temporal contexts. All protocols use ``@runtime_checkable`` for structural typing and include comprehensive behavioral contracts with idempotency guarantees. These are internal contracts between layers of the system.

* :doc:`../sample/repositories` - Order processing repository contracts
* :doc:`../julee_example/repositories/base` - Generic base repository protocol
* :doc:`../util/repositories` - Shared infrastructure repository protocols

Request and Response Objects
----------------------------

**Request and response objects** are Pydantic-based data structures that define the contract between external interfaces and internal domain logic. These objects isolate external API concerns from domain models and provide validation at system boundaries.

Request and response objects enable API evolution without affecting core business logic. They serve as translation layers that convert external data formats into domain objects and vice versa. The objects use Pydantic validation to ensure data integrity before it reaches use cases, catching malformed data early in the request lifecycle. These are public contracts with external systems.

* :doc:`../sample/api/requests` - API request models for order processing
* :doc:`../sample/api/responses` - API response models with status tracking

Both repository protocols and request/response objects are part of the entity layer because they define interface contracts that protect domain integrity - repository protocols as internal boundaries between system layers, and request/response objects as external boundaries with client systems.

.. uml:: ../../img/domain-dependencies.puml
   :align: center
   :alt: Entity Layer Dependencies

Domain Validation and Security
-------------------------------

**Domain validation and security** utilities ensure architectural contracts and provide security boundaries for the domain layer. These components perform runtime validation that complements static type checking, catching configuration errors and data integrity issues at critical system boundaries.

Domain validation includes protocol compliance checking using ``@runtime_checkable``, ensuring repository implementations satisfy their contracts. Security validation provides defense against malicious file uploads and data corruption. Domain-specific exceptions like ``RepositoryValidationError`` and ``DomainValidationError`` provide clear error boundaries that bubble up through the architecture layers.

* :doc:`../sample/validation` - Comprehensive validation utilities and security patterns

Domain validation belongs to the entity layer because it enforces the business rules and architectural contracts that protect domain integrity, ensuring the system maintains its invariants regardless of external inputs or internal implementation changes.
Key Patterns in the Code
========================


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
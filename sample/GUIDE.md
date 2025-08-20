# Architecture and Testing Guide

This document explains the architectural principles and testing approach used in this codebase. While the examples are from the `sample/` directory, these principles apply to the entire repository.

## Architecture Overview

The architecture follows the principles of Clean Architecture (by Robert C. Martin) and Hexagonal Architecture (also known as Ports and Adapters, by Alistair Cockburn). These architectural styles emphasize separation of concerns, dependency inversion, and domain-centric design.

## Core Architectural Principles

### 1. Separation of Concerns

The codebase is organized into distinct layers:

-   **Domain Layer**: Contains business entities and logic ([domain.py](domain.py))
-   **Use Case Layer**: Orchestrates business logic ([usecase.py](usecase.py))
-   **Interface Adapters**: Convert between external and internal models
    -   API adapters ([api/](api/))
    -   Repository implementations ([repos/](repos/))
-   **Frameworks & Drivers**: External technologies and tools
    -   FastAPI for HTTP ([api/app.py](api/app.py))
    -   Temporal for workflows ([workflow.py](workflow.py), [worker.py](worker.py))

### 2. Dependency Rule

Dependencies point inward. Outer layers depend on inner layers, but inner layers never depend on outer layers:

-   Domain entities have no external dependencies
-   Use cases depend only on domain entities and repository interfaces
-   Interface adapters depend on use cases and domain entities
-   Frameworks depend on interface adapters

### 3. Dependency Inversion

High-level modules (use cases) don't depend on low-level modules (repositories) directly. Instead, both depend on abstractions (repository interfaces):

-   Repository interfaces are defined as Python Protocols ([repositories.py](repositories.py))
-   Concrete implementations satisfy these protocols ([repos/minio/](repos/minio/))
-   Use cases accept repository interfaces in their constructors

## Workflow Determinism and Non-Deterministic Operations

In Temporal workflows, the workflow code itself must be deterministic to support replay. This means operations like:
-   ID generation (UUID, timestamps)
-   Random number generation  
-   External API calls
-   Database writes

Must be delegated to Activities, not performed in workflow code directly.

This is why `OrderRepository.generate_order_id()` exists as a repository method. The `OrderFulfillmentUseCase` orchestrates the order creation process, and when it needs a unique ID, it calls `self.order_repo.generate_order_id()`. In a Temporal workflow context, `self.order_repo` is a workflow stub that delegates this non-deterministic operation to a Temporal Activity, ensuring the use case remains deterministic.

### Key Architectural Insights

-   **Use cases do not "know" they are running inside a workflow** - they remain pure business logic
-   **Repository implementations do not "know" they are running inside an activity** - they focus on their data access responsibilities
-   **Repository implementations must be idempotent** - they can be retried safely
-   **Use case implementations must be deterministic** - they produce the same output given the same input
-   **Repository implementations can be non-deterministic** - they can generate IDs, make network calls, etc.
-   **The workflow's responsibility** is to instantiate the use case with repositories that are registered appropriately

### How Repository Registration Works

The workflow acts as a dependency injection container:

1.  **Worker Initialization**: Concrete repository instances are created and their methods registered as activities
2.  **Workflow Execution**: Workflow-specific repository stubs are created that delegate to activities
3.  **Use Case Injection**: The workflow injects these stubs into the use case constructor
4.  **Transparent Operation**: The use case operates normally, unaware of the underlying workflow mechanics

## Saga Pattern Implementation

The order fulfillment process implements the saga pattern for distributed transaction management:

1.  **Forward Actions**: Reserve inventory → Process payment
2.  **Compensation Actions**: Release inventory ← Cancel payment

Each forward action has a corresponding compensation action that can undo its effects. The use case orchestrates both the forward flow and compensation on failure.

### Compensation Requirements

-   **Every forward action must have a compensation** - we must be able to undo any state change
-   **Compensations must be idempotent** - they can be called multiple times safely
-   **Program defensively around compensation failures** - log errors and escalate to humans when compensations fail
-   **Graceful degradation** - the system should continue operating even when some compensations fail

### Idempotency Requirements

All repository operations must be idempotent to handle:
-   Workflow retries
-   Activity retries  
-   Partial failure recovery

This is achieved through:
-   Unique identifiers for all operations
-   State checking before state changes
-   Graceful handling of duplicate operations

## Structured Logging Strategy

The codebase uses structured logging with consistent patterns:

1.  **Context Fields**: Always include relevant business identifiers (order_id, customer_id)
2.  **Action/Result Pairs**: Log before and after significant operations
3.  **Error Context**: Include error type, message, and business context
4.  **Performance Data**: Include counts, amounts, and timing where relevant

Example:
```python
logger.info("Payment processing started", extra={
    "order_id": order.order_id,
    "customer_id": order.customer_id,
    "amount": str(order.total_amount)
})
```

### Error Handling and Compensation

Robust error handling is crucial for reliable distributed systems. This codebase employs a layered approach to error management, focusing on early detection, clear logging, and graceful degradation.

1.  **Fail Fast (Validation Layer)**:
    *   Errors are caught as early as possible, typically at validation boundaries (e.g., API request parsing, domain model instantiation, repository injection).
    *   The `sample/validation.py` module plays a key role here, ensuring data integrity and architectural compliance before business logic executes.
    *   Example: `OrderFulfillmentUseCase` validates incoming `CreateOrderRequest` data and raises `ValueError` if invalid, preventing further processing.

2.  **Business Outcome Handling (Domain and Use Case Layer)**:
    *   For *expected business failures* (e.g., insufficient funds, out of stock), activities return specific "outcome" domain objects (e.g., `PaymentOutcome`, `InventoryReservationOutcome`) with a `status` and `reason`. These are defined in `sample/domain.py`.
    *   The **Use Case** (`sample/usecase.py`) checks the `status` of these outcome objects to determine the next steps (e.g., triggering compensation) and to return precise, business-meaningful status and reason messages (e.g., "PAYMENT_FAILED" with "Simulated payment service error") to the API layer. This avoids "juggling exceptions" for normal business flows.
    *   For *unexpected system errors* (e.g., network issues, database connection problems), activities *do* raise standard Python `Exception`s. These are caught by the use case's generic `except Exception as e:` block.

3.  **Saga Compensation (Use Case Layer)**:
    *   For multi-step operations (sagas), the `OrderFulfillmentUseCase` orchestrates both forward actions and their corresponding compensation actions.
    *   If a forward action fails (e.g., payment processing returns a "failed" outcome, or an unexpected exception occurs), the use case attempts to undo any previously successful forward actions (e.g., releasing reserved inventory).
    *   **Defensive Compensation**: Compensation actions themselves are programmed defensively. If a compensation fails (e.g., `inventory_repo.release_items` throws an error), it is logged but *not* re-raised. This ensures that the primary error response can still be returned to the caller, and the system doesn't get stuck in a compensation loop. Such failures typically trigger alerts for manual intervention.
    *   Example: In `usecase.py`, the `try...except Exception as e:` block around `fulfill_order` includes a nested `try...except` for `self.inventory_repo.release_items`, logging any compensation errors without re-raising them.

4.  **API Error Handling (API Layer)**:
    *   The FastAPI application (`sample/api/app.py`) handles exceptions by converting them into appropriate HTTP responses.
    *   For internal server errors (e.g., unexpected exceptions from use cases or repositories), generic `HTTPException(status_code=500, detail="...")` messages are returned to external clients. This prevents sensitive internal details from leaking.
    *   Detailed error information (stack traces, specific error messages) is captured in structured logs for debugging and monitoring.
    *   Example: `create_order`, `get_request_status`, and `get_order_status` endpoints all use `try...except Exception as e:` blocks to catch errors, log them with `exc_info=True`, and raise a generic `HTTPException`.

5.  **Repository Error Handling**:
    *   Repository implementations ([repos/minio/](repos/minio/)) are responsible for interacting with external systems (Minio, payment gateways).
    *   They are designed to handle common external system failures gracefully (e.g., `get_payment` returns `None` if a payment is not found, rather than raising an exception for a "not found" scenario).
    *   More severe errors (e.g., network issues, service unavailability) are typically propagated as exceptions, allowing the calling use case or workflow to handle them (e.g., triggering compensation).
    *   Example: `MinioPaymentRepository.get_payment` catches `S3Error` for `NoSuchKey` and returns `None`. Other `S3Error` types are re-raised.

This comprehensive approach ensures that errors are managed effectively across all layers, maintaining system stability and providing clear insights for operational teams.

## Runtime Type Safety and Validation

While static type checking with mypy catches most type issues during development,
runtime validation provides additional safety at critical boundaries:

#### Idiomatic Protocol Validation with @runtime_checkable
```python
from typing import Protocol, runtime_checkable, Optional

@runtime_checkable
class PaymentRepository(Protocol):
    async def process_payment(self, order: "Order") -> "Payment": ...
    async def get_payment(self, payment_id: str) -> Optional["Payment"]: ...

# Simple, idiomatic validation
# Assuming 'repo' is an instance of a repository implementation
# from sample.repositories import PaymentRepository
# if isinstance(repo, PaymentRepository):
#     # Guaranteed to satisfy the protocol
#     pass
    
# Or use validation functions
from sample.validation import ensure_payment_repository
# validated_repo = ensure_payment_repository(repo)  # Type-safe
```

#### Benefits of @runtime_checkable Approach
-   **Idiomatic Python**: Uses built-in isinstance() checks
-   **Better Performance**: Optimised C code vs Python introspection
-   **More Robust**: Handles edge cases automatically
-   **Type Safety**: Static checkers understand isinstance() checks
-   **Cleaner Code**: Much simpler than manual introspection

#### Domain Model Validation
```python
from sample.validation import validate_domain_model
from sample.domain import Order

# Validate external data before creating domain objects
order_data = {"order_id": "123", "customer_id": "cust1", "items": [{"product_id": "p1", "quantity": 1, "price": "10.00"}], "total_amount": "10.00"}
order = validate_domain_model(order_data, Order)  # Pydantic validation
```

#### Validated Repository Factories
```python
from sample.validation import create_validated_repository_factory
from sample.repositories import PaymentRepository
from sample.repos.temporal.minio_payments import TemporalMinioPaymentRepository

factory = create_validated_repository_factory(PaymentRepository, TemporalMinioPaymentRepository)
# repo = factory()  # Automatically validated on creation
```

This approach provides runtime safety while leveraging Python's built-in protocol
system and existing Pydantic validation, avoiding the need for custom type checking logic.

### Protocol Validation Evolution

The codebase has evolved from manual protocol introspection to idiomatic 
@runtime_checkable usage:

#### Before: Manual Introspection
-   Complex signature checking (~100+ lines of code)
-   Custom Temporal activity detection
-   Potential edge cases and bugs
-   Slower performance (Python introspection)

#### After: @runtime_checkable + isinstance()
-   Simple, idiomatic isinstance() checks
-   Leverages Python's built-in protocol system
-   Robust handling of edge cases
-   Better performance (optimised C code)
-   Type checker integration

This change reduces complexity while improving reliability and performance.

## API Flow

1.  **HTTP Request Handling**:
    -   FastAPI routes receive HTTP requests and parse them into Pydantic models ([api/requests.py](api/requests.py))

2.  **Boundary Crossing**:
    -   Before starting a workflow, the Pydantic request model is converted into a JSON-serializable dictionary using `model_dump(mode="json")`. This is a critical step that ensures types like `Decimal` are converted to strings, making the data safe for Temporal's default JSON serializer. This conversion acts as an "adapter" at the boundary between our API framework and the workflow engine.

3.  **Workflow and Use Case Execution**:
    -   The workflow receives the dictionary and reconstructs the Pydantic model.
    -   The workflow instantiates the use case and passes the Pydantic model to it.
    -   The use case converts the Pydantic model to internal domain objects.
    -   Business logic is executed using these domain objects.
    -   The use case interacts with repositories using domain objects.
    -   Results are converted back to Pydantic response models ([api/responses.py](api/responses.py)).

4.  **HTTP Response**:
    -   FastAPI converts the final Pydantic response model to a JSON response.

The detailed flow is:
```
HTTP Request → FastAPI → Pydantic Request → JSON-serializable dict → [Temporal] → dict → Pydantic Request → Use Case → Domain Objects → Repositories → Domain Results → Pydantic Response → HTTP Response
```

See [create_order](api/app.py) for an example of this flow.

## Workflow Flow

The workflow execution involves several layers of indirection to maintain the separation between business logic and the workflow engine. Here is a detailed breakdown of the flow of control:

1.  **Worker Initialization (`worker.py`)**:
    -   The `worker.py` script starts a Temporal Worker process.
    -   It instantiates the **pure backend repository implementations** (e.g., `MinioPaymentRepository`). These implementations are stateful and may contain their own clients to backing services (like a Minio client for object storage).
    -   It then instantiates the **Temporal Activity Implementations** (e.g., `TemporalMinioPaymentRepository`), injecting the pure backend instances into them.
    -   It registers the methods of these Temporal Activity Implementations as **Activities** with the worker (e.g., `temporal_payment_repo.process_payment` is registered under the name `"process_payment"`).
    -   It also registers the available **Workflow** definitions (e.g., `OrderFulfillmentWorkflow`, `CancelOrderWorkflow`).
    -   The worker then begins polling a task queue for work.

2.  **Workflow Execution (`workflow.py`)**:
    -   When a workflow is started (e.g., via the API), the worker receives a task to execute the `OrderFulfillmentWorkflow.run` or `CancelOrderWorkflow.run` method.
    -   Inside the `run` method, special **workflow-specific repository proxies** are instantiated (e.g., `WorkflowPaymentRepositoryProxy` from `sample/repos/temporal/proxies/`). These proxies satisfy the repository protocols defined in `repositories.py`.

3.  **Use Case Instantiation (`workflow.py`)**:
    -   The workflow then instantiates the `OrderFulfillmentUseCase` or `CancelOrderUseCase`.
    -   It injects the **repository proxies** (from the previous step) into the use case's constructor. The use case is completely unaware that it's receiving proxies; it only knows it's receiving objects that match the required protocol.

4.  **Business Logic Execution (`usecase.py`)**:
    -   The workflow calls a method on the use case, like `fulfill_order()` or `cancel_order()`.
    -   The use case executes its business logic. When it needs to interact with a dependency (e.g., to process a payment or refund it), it calls a method on the repository object it was given, for example, `self.payment_repo.process_payment(...)` or `self.payment_repo.refund_payment(...)`.

5.  **Activity Invocation (`workflow.py`)**:
    -   The call from the use case is received by the **workflow proxy** (e.g., `WorkflowPaymentRepositoryProxy.process_payment`).
    -   The proxy's only purpose is to translate this call into a Temporal command. It calls `workflow.execute_activity("process_payment", ...)`, passing the arguments along.
    -   This instructs the Temporal engine to schedule the activity named `"process_payment"` for execution. The workflow code then pauses deterministically until a result is available.

6.  **Activity Execution (`sample/repos/temporal/`)**:
    -   The worker picks up the activity task from the task queue.
    -   It looks up `"process_payment"` in its registry and finds that it maps to the `process_payment` method of the `TemporalMinioPaymentRepository` instance it created during initialization.
    -   The worker executes this method. This code runs **outside** the workflow's sandboxed, deterministic environment, so it is free to perform I/O, make network calls, and use non-deterministic libraries. This is where the repository's implementation details (e.g., writing to an object store like Minio) live.

7.  **Result Propagation**:
    -   The activity method completes and returns a result.
    -   The worker reports this result back to the Temporal engine.
    -   The engine delivers the result to the paused workflow.
    -   The `workflow.execute_activity()` call unblocks and returns the result.
    -   The result is then returned from the proxy method back to the `OrderFulfillmentUseCase` or `CancelOrderUseCase`, which continues its execution.

This layered approach ensures that the core business logic in `usecase.py` remains pure and testable, completely decoupled from the specifics of the Temporal workflow engine and the persistence mechanisms of the repositories.

The flow can be visualized as:
```
Workflow Start
     │
     ▼
[workflow.py] instantiates Usecase with Repository Proxies
     │
     ▼
[usecase.py] calls repository method (e.g., `process_payment` or `refund_payment`)
     │
     ▼
[sample/repos/temporal/proxies/] Proxy translates call to `workflow.execute_activity("activity_name", ...)`
     │
     ▼
[Temporal Engine + worker.py] schedules and dispatches Activity Task
     │
     ▼
[sample/repos/temporal/] Activity implementation executes (delegates to [sample/repos/minio/])
     │
     ▼
Result is returned up the call stack
```

See [OrderFulfillmentWorkflow](workflow.py) and [CancelOrderWorkflow](workflow.py) for examples of this flow.

## Reconciling Clean Architecture and Temporal's Execution Model

A common challenge when integrating Temporal is feeling like you are "fighting the framework." This often stems from a misunderstanding of how Temporal's execution model interacts with architectural patterns like Clean Architecture.

Temporal code looks like normal asynchronous Python, but it's fundamentally different. It's a declarative language for building a **durable, recoverable execution graph**. Every `await workflow.execute_activity(...)` is not just an async call; it's a **durable checkpoint**. The workflow's state is saved, and the process can be resumed from that exact point, even if the worker crashes.

To align these concepts, it's helpful to think of the application as two distinct worlds:

1.  **The World of Pure Business Logic (Your Clean Architecture Core)**
    *   **Where it lives:** `usecase.py`, `domain.py`, `repositories.py` (the protocols).
    *   **What it does:** Executes business rules. It's standard, testable code that knows nothing about durability or workflows.
    *   **Its "Time":** It runs in the "now."

2.  **The World of Workflow Definition (Temporal's Realm)**
    *   **Where it lives:** `workflow.py`.
    *   **What it does:** Defines the *steps* of a long-running process. It's a sandboxed, deterministic environment that orchestrates calls to the outside world (Activities).
    *   **Its "Time":** It is "timeless" and re-entrant. The code can be re-executed ("replayed") to reconstruct its state.

### The Bridge: Aligning the Abstractions

The key to making these two worlds cooperate is to build a clean, explicit bridge between them. In this architecture, that bridge has two parts:

1.  **The Workflow Proxies:** The `Workflow...RepositoryProxy` classes inside `sample/repos/temporal/proxies/` act as the first part of the bridge. When the use case calls a repository method (e.g., `process_payment`), the proxy receives the call. Its job is to translate this business-logic call into a command for the workflow execution graph by calling `workflow.execute_activity(...)`.

2.  **The Data Converter:** When `execute_activity` is called, the data passed to it must be serialized to be stored in the checkpoint. This is a framework-specific concern. A **Temporal Data Converter is the idiomatic, framework-provided adapter for this task.** It handles the serialization and deserialization of data crossing the boundary between the workflow and the activity.

Using a `DataConverter` does not violate Clean Architecture; it **is** the Clean Architecture adapter for data serialization. It is configured at the outermost layer of the application (where the `Client` and `Worker` are initialized) and keeps framework-specific serialization logic out of your business code, your workflow definitions, and even your repository implementations.

This approach ensures the abstractions remain aligned:
*   **Core:** `usecase.py` (pure logic)
*   **Boundary:** `repositories.py` (protocols)
*   **Adapter (Workflow Side):** `sample/repos/temporal/proxies/` (proxies that translate calls to `execute_activity`)
*   **Adapter (Framework Serialization):** The `pydantic_data_converter` from `temporalio.contrib.pydantic` (handles data translation automatically, e.g., `Decimal` -> `str`).
*   **Adapter (Implementation):** `sample/repos/temporal/` (the concrete activity code, delegating to `sample/repos/minio/`).

By using `pydantic_data_converter`, we let the framework handle the serialization concerns at the correct boundary, which simplifies the workflow proxies and keeps the core logic clean.

## Large Payload Handling with FileStorageRepository

Temporal workflows have payload size limits (typically 2MB by default). For larger data, such as order attachments, documents, or extensive logs, it's best practice to store them externally and pass only a reference (like a file ID or URL) through the workflow.

The `FileStorageRepository` protocol and its implementations (`MinioFileStorageRepository`, `TemporalMinioFileStorageRepository`, `WorkflowFileStorageRepositoryProxy`) provide a clean way to manage this:

-   **`FileStorageRepository` Protocol**: Defines the contract for `upload_file`, `download_file`, and `get_file_metadata`.
-   **`MinioFileStorageRepository`**: The pure backend implementation that directly interacts with Minio to store and retrieve file bytes. It's unaware of Temporal.
-   **`TemporalMinioFileStorageRepository`**: The Temporal activity implementation. Its methods are decorated with `@activity.defn` and delegate to the `MinioFileStorageRepository`. This is where the actual I/O for large files happens, outside the deterministic workflow.
-   **`WorkflowFileStorageRepositoryProxy`**: The workflow-specific proxy. Used inside the workflow, its methods call `workflow.execute_activity` to invoke the corresponding `TemporalMinioFileStorageRepository` activities. This ensures workflow determinism.
-   **`OrderFulfillmentUseCase`**: Can optionally accept a `FileStorageRepository` instance. It uses this repository to orchestrate the upload/download of attachments, keeping the business logic clean.
-   **API Endpoints**: New endpoints (`/orders/{order_id}/attachments` for POST, GET, and GET metadata) allow external clients to interact with the file storage, with the API layer handling the conversion of `UploadFile` objects to raw bytes for the use case.

This pattern ensures that large payloads are handled efficiently and robustly, without impacting workflow determinism or exceeding Temporal's internal limits.

## Key Components

### Domain Models

Domain models ([domain.py](domain.py)) are pure Python dataclasses with no external dependencies. They represent the core business entities and are used throughout the business logic.

### Repository Interfaces

Repository interfaces ([repositories.py](repositories.py)) define the contract for data access. They:
-   Are defined as Python Protocols
-   Accept and return domain objects or primitives
-   Have no knowledge of external systems

### Use Cases

Use cases ([usecase.py](usecase.py)) contain the business logic. They:
-   Accept repository interfaces through constructor injection
-   Convert between API models and domain models
-   Orchestrate the business logic using domain models
-   Handle error cases and compensation logic (sagas)

### API Layer

The API layer ([api/](api/)) handles HTTP communication. It:
-   Defines request/response contracts using Pydantic models
-   Routes requests to appropriate use cases
-   Handles HTTP-specific concerns (status codes, headers)
-   Has no business logic

### Workflow Layer

The workflow layer ([workflow.py](workflow.py)) handles long-running processes. It:
-   Defines workflows using Temporal
-   Instantiates use cases with appropriate repositories
-   Handles workflow-specific concerns (state, queries)
-   Has minimal business logic

### Repository Implementations

Repository implementations ([repos/minio/](repos/minio/)) provide concrete implementations of repository interfaces. They:
-   Implement the repository protocols
-   Handle external system interactions (e.g., calling a payment gateway, writing to an object store)
-   Are pure backend implementations, unaware of Temporal.

### Temporal Activity Implementations

Temporal Activity Implementations ([repos/temporal/](repos/temporal/)) act as the bridge between pure backend repositories and Temporal activities. They:
-   Implement the repository protocols
-   Wrap calls to the pure backend repositories
-   Are decorated with `@activity.defn` to be registered as Temporal activities

### Workflow Proxies

Workflow Proxies ([repos/temporal/proxies/](repos/temporal/proxies/)) are used inside workflows. They:
-   Implement the repository protocols
-   Delegate calls to `workflow.execute_activity()`
-   Ensure workflow determinism

## Testing Strategy

### 1. Use Case Testing (Business Logic)

Use cases contain our core business logic and should be thoroughly unit tested with mocked repositories:

-   Create test files in a `tests/` directory that mirror the structure of the codebase
-   For each use case, create a corresponding test file (e.g., `tests/test_usecase.py`, `tests/test_cancel_order.py`)
-   Use pytest's AsyncMock to mock asynchronous repository methods
-   Test both happy paths and error scenarios

See [tests/test_usecase.py](tests/test_usecase.py) and [tests/test_cancel_order.py](tests/test_cancel_order.py) for examples of use case tests.

#### Business Rule Documentation

Use descriptive test names and docstrings to document business rules:

-   Name tests to reflect the business rule being tested
-   Include detailed docstrings that explain the business rule
-   Organize tests by business capability

See [tests/test_business_rules.py](tests/test_business_rules.py) for examples of business rule documentation through tests.

### 2. Type Safety

#### Static Type Checking

Leverage Python's type hints and static type checkers (mypy) to ensure repository implementations correctly satisfy their protocols:

-   Add type hints to all function signatures
-   Run mypy regularly to catch type errors
-   Use Protocol classes to define interfaces

This eliminates the need for explicit protocol implementation tests, as the type checker will catch these issues at development time.

#### Runtime Considerations

While static type checking catches most issues, consider adding runtime assertions in critical paths:

-   Add assertions in factory methods or dependency injection points
-   Keep runtime checks minimal and focused on critical interfaces
-   Use __debug__ to ensure checks are disabled in production

### 3. API Testing

API tests should focus on validating the HTTP interface, request/response formats, and routing logic:

-   Create test files for each API endpoint (e.g., `tests/api/test_orders.py`)
-   Use FastAPI's TestClient to simulate HTTP requests
-   Mock the use case layer to isolate API tests from business logic

See [tests/api/test_orders.py](tests/api/test_orders.py) for examples of API tests.

#### Mock Injection Strategy

For API tests, mock at the use case level rather than the repository level:

1.  **Pros**:
    -   Tests API layer in isolation
    -   Faster tests that don't depend on business logic implementation
    -   Clearer test failures (API issue vs. business logic issue)

2.  **Cons**:
    -   Doesn't test integration between API and business logic
    -   Requires more mocking setup

### 4. End-to-End Testing

End-to-end tests validate the entire system with real dependencies:

-   Create a small number of critical path tests
-   Use environment variables to connect to test infrastructure
-   Implement polling or waiting mechanisms for asynchronous processes

See [tests/e2e/test_order_fulfillment.py](tests/e2e/test_order_fulfillment.py) for examples of end-to-end tests.

#### Running End-to-End Tests

To run the end-to-end tests, you need to start the test environment using Docker Compose and then run `pytest`.

1.  **Start the test environment:**

    Open a terminal and run the following command from the root of the repository:

    ```bash
    docker-compose -f sample/docker-compose.test.yml up -d --remove-orphans
    ```

    -   `-f sample/docker-compose.test.yml`: Specifies the test environment compose file.
    -   `up`: Creates and starts the containers.
    -   `-d`: Runs the containers in detached mode (in the background).
    -   `--remove-orphans`: Removes containers for services that are no longer defined in the compose file. This helps keep your environment clean after making changes to `docker-compose.test.yml`.

    The `WARN[...] Found orphan containers` message you saw is normal if you've run services before without a clean shutdown. The `--remove-orphans` flag is the correct way to handle this. The `unknown flag` error you encountered was because `--remove-orphans` must be placed *after* the `up` command, not before it.

2.  **Run the tests:**

    Once the containers are running (you can check with `docker ps`), execute the end-to-end tests using `pytest`:

    ```bash
    pytest sample/tests/e2e/
    ```

    The tests are configured to connect to the services running in Docker on `localhost`.

3.  **Tear down the environment:**

    After you've finished running the tests, you can stop and remove the containers:

    ```bash
    docker-compose -f sample/docker-compose.test.yml down
    ```

#### Test Environment Management

For end-to-end tests:

1.  **Dedicated Test Environment**:
    -   Use Docker Compose to create isolated test environments
    -   Create a `docker-compose.test.yml` that includes all dependencies
    -   Initialize with known state before tests

2.  **Test Data Management**:
    -   Create fixtures to populate test data
    -   Clean up after tests to prevent test pollution
    -   Use unique identifiers (UUIDs) to prevent collisions

### Testing Pyramid

Follow the testing pyramid approach:
-   Many unit tests (use cases, domain logic)
-   Fewer integration tests (repositories with real dependencies)
-   Few end-to-end tests (critical user journeys only)

This ensures fast feedback during development while still validating the system works as a whole.

## Benefits of This Architecture

1.  **Testability**: Business logic can be tested in isolation without external dependencies
2.  **Flexibility**: External systems can be replaced without changing business logic
3.  **Maintainability**: Clear separation of concerns makes the codebase easier to understand
4.  **Scalability**: Different components can be scaled independently
5.  **Durability**: Long-running processes are handled by Temporal workflows

## Conclusion

This architecture provides a clean, maintainable, and flexible foundation for building complex applications. By following these principles, the codebase remains adaptable to changing requirements and technologies while keeping the business logic clear and focused.

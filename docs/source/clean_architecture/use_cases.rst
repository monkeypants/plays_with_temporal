.. _clean_architecture:use_cases:

Use Cases
=========

**Use cases** are application-specific business rules that orchestrate the flow of data to and from entities. They direct entities to use their enterprise-wide business rules to achieve specific application goals.

Use cases contain the workflows and coordination logic that make your application unique. While entities represent what your business *is*, use cases represent what your business *does*. For example, "Validate Document Use Case" validates documents against policies using general ``Document`` and ``Policy`` entities, but the validation workflow is specific to the document processing application. Use cases depend only on entities, never on outer layers like databases or web frameworks.

* :doc:`../sample/usecase` - **Order processing workflows**: OrderFulfillmentUseCase (saga pattern for payment/inventory), GetOrderUseCase (order retrieval), CancelOrderUseCase (order cancellation with compensation)
* :doc:`../cal/usecase` - **Calendar and scheduling workflows**: CalendarSyncUseCase (bidirectional calendar synchronization), CreateScheduleUseCase (schedule generation from calendar events with AI classification)
* :doc:`../julee_example/use_cases/extract_assemble_data` - **Document assembly workflows**: ExtractAssembleDataUseCase (document extraction and assembly according to specifications)
* :doc:`../julee_example/use_cases/validate_document` - **Document validation workflows**: ValidateDocumentUseCase (document validation against organizational policies using AI services)

.. uml:: ../../img/usecase-dependencies.puml
   :align: center
   :alt: Use Case Layer Dependencies

Temporal Integration
--------------------

It's worth noting that in this codebase,
we use the temporal framework to orchestrate deterministic workflows.
These workflows are strait usecases (which "know nothing" about temporal),
but they are imported to the frameworks and drivers layer
and are integrated with the temporal system through dependency injection.

TODO:
 * insert cross-references to workflow and activity decorators.
 * insert cross-references to example code where this happens.
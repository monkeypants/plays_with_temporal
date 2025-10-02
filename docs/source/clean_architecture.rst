Clean Architecture
==================

This codebase combines *clean architecture* with workflow determinism.

Clean Architecture, `as defined <https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html>`__
by Robert C. Martin (Uncle Bob),
is an architecture that puts the business logic at the center of the design.
Source code dependencies can only point inwards (The Dependency Rule),
toward higher-level policies.

The architecture creates a separation between:

* the **essential** complexity (what the software does - use cases and entities); and
* the **accidental** complexity (how it does it - interface adapters, frameworks & drivers).

This isn't just about layering - it's about putting "what the application does" at the centre,
and pushing "how it works" to the periphery.
Database, web frameworks, and external services are just implementation details
that can be deferred and changed without affecting the core business logic.

.. uml:: ../img/clean-architecture-dependencies.puml
   :align: center
   :alt: Clean Architecture Dependencies

:doc:`clean_architecture/entities` are the fundamental business concept layer. It contains domain models, repository protocols, request/response objects, and validation utilities that protect domain integrity.

The :doc:`clean_architecture/use_cases` layer contains application-specific business processes and rules that orchestrate entities to achieve specific goals. These workflows represent what your business *does*, and it depend only on entities.

The :doc:`clean_architecture/interface_adapters` layer provides "translation boundaries" that convert between use case formats and external system formats. Includes API controllers, repository implementations, service adapters, and infrastructure adapters. These take the abstract/logical business logic of the usecase and make it concrete and usable by other systems.

The :doc:`clean_architecture/frameworks_and_drivers` is the outermost layer. It contains web frameworks, databases, external services, configuration, and main functions. These are tools and delivery mechanisms.

.. toctree::
   :maxdepth: 1
   :hidden:

   clean_architecture/entities
   clean_architecture/use_cases
   clean_architecture/interface_adapters
   clean_architecture/frameworks_and_drivers


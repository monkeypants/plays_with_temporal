.. _clean_architecture:frameworks_and_drivers:

Frameworks and Drivers
======================

**Location**: ``worker.py``, Docker files, configuration files, framework setup

This is where all the details go: web frameworks, databases, external services. These are tools and delivery mechanisms, not the core of your application.

**Contains**:
* Web frameworks (FastAPI)
* Databases (PostgreSQL, Redis)
* External services (Temporal workflows)
* Configuration and main functions
* Dependency injection containers

**Dependencies**: Everything - this layer uses all the inner layers
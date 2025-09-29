Sample Application
==================

The sample application demonstrates Temporal workflow patterns using clean architecture principles. It implements an order processing system with inventory management, payment processing, and cancellation workflows.

Architecture Overview
---------------------

The sample application follows clean architecture with clear separation of concerns:

* **Domain Layer**: Core business entities and rules
* **Use Cases**: Application-specific business workflows
* **Interface Adapters**: Repository implementations and API controllers
* **Infrastructure**: Temporal workers and external service integrations

Key Components
--------------

.. toctree::
   :maxdepth: 2

   sample/domain
   sample/usecase
   sample/validation
   sample/workflow
   sample/worker
   sample/repositories
   sample/repos/temporal/__init__
   sample/repos/temporal/activities
   sample/repos/temporal/activity_names
   sample/repos/temporal/proxies
   sample/repos/minio/__init__
   sample/repos/minio/order
   sample/repos/minio/order_request
   sample/repos/minio/payment
   sample/repos/minio/inventory
   sample/api/app
   sample/api/dependencies
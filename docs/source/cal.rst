Cal Application
===============

The cal application implements a calendar integration and synchronization workflow system. It provides unified access to multiple calendar sources (Google Calendar, local calendars, mock calendars) with time block classification and schedule management capabilities.

Architecture Overview
---------------------

The cal application demonstrates clean architecture with multiple repository patterns:

* **Domain Layer**: Calendar entities, time blocks, and scheduling rules
* **Use Cases**: Calendar synchronization and time classification workflows
* **Interface Adapters**: Multiple calendar service implementations
* **Infrastructure**: PostgreSQL persistence, Google Calendar API, and Temporal workflows

Key Components
--------------

Core Activities
~~~~~~~~~~~~~~~

.. toctree::
   :maxdepth: 2

   cal/domain
   cal/usecase

Repository Implementations
~~~~~~~~~~~~~~~~~~~~~~~~~~

Temporal Activities
^^^^^^^^^^^^^^^^^^^

These components are implemented but documentation is being generated dynamically.
...plays with temporal
======================

This repository contains experiments that combine Temporal.io workflows with clean architecture patterns.

Applications:

* :doc:`sample <sample>`
  The main experiment, demonstrating Temporal workflow patterns using a clean architecture.
* :doc:`julee_example <julee_example>`
  One definition of AI "agent" is something that runs in a loop to achieve a goal.
  By this definition, Julee is *not* an agent.
  It's a deterministic orchestration (a "pipeline" rather than a "loop")
  that combines services in a structured, repeatable, monitorable and accountable way.
* :doc:`cal <cal>`
  A calendar integration/synchronisation workflow.

There is also:

* util/
  Shared utilities and common functionality.
* bin/
  Command-line utilities and daemon scripts.
* fun-police/
  Project documentation and methodology.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   clean_architecture
   sample
   julee_example
   cal
   util/domain


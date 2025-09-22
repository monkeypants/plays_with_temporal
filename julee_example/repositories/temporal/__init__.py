"""
Temporal repository wrappers for the julee_example domain.

This package contains @temporal_activity_registration decorated classes that
wrap pure backend repositories as Temporal activities, and
@temporal_workflow_proxy decorated classes that provide workflow-safe proxies.

The package is organized into separate modules to respect Temporal's workflow
sandbox restrictions:

- activities.py: All temporal activity registrations (for worker use only)
  Contains imports from backend Minio repositories - NOT SANDBOX SAFE

- proxies.py: All workflow-safe proxy classes (for workflow use only)
  Contains no backend imports - SANDBOX SAFE

- activity_names.py: Shared activity name constants - SANDBOX SAFE

IMPORTANT: Do not import everything from __init__.py as this would mix
sandbox-safe and non-sandbox-safe imports. Import directly from the
specific module you need:

- Workers should import from activities.py
- Workflows should import from proxies.py
- Both can import constants from activity_names.py
"""

# This __init__.py intentionally does NOT re-export classes to avoid
# mixing sandbox-safe (proxies) and non-sandbox-safe (activities) imports.
# Import directly from the specific modules instead.

__all__: list[str] = [
    # No re-exports to avoid sandbox violations
    # Import directly from:
    # - .activities for worker use
    # - .proxies for workflow use
    # - .activity_names for constants
]

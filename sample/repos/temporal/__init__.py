"""
Temporal activity implementations package.

This package contains Temporal activity wrappers and workflow proxies.
The __init__.py is intentionally minimal to avoid importing restricted modules
during workflow initialization, which would cause sandbox violations.

Temporal activity classes are created dynamically in worker.py using the
@temporal_activity_registration decorator to avoid importing Minio libraries
during workflow import time.
"""

# Intentionally empty - temporal repository classes are created directly
# in worker.py to avoid workflow sandbox violations

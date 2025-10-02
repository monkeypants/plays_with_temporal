"""
Shared activity name constants for the julee_example domain.

This module contains activity name base constants that are shared between
activities.py and proxies.py, avoiding the need for either module to import
from the other, which would create problematic transitive dependencies.

By isolating these constants in their own module, we maintain DRY principles
while preserving Temporal's workflow sandbox restrictions. The proxies module
can import these constants without transitively importing non-deterministic
backend code from activities.py.
"""

# Activity name bases - shared constants for consistency between
# activity registrations and workflow proxies
ASSEMBLY_ACTIVITY_BASE = "julee.assembly_repo.minio"
ASSEMBLY_SPECIFICATION_ACTIVITY_BASE = (
    "julee.assembly_specification_repo.minio"
)
DOCUMENT_ACTIVITY_BASE = "julee.document_repo.minio"
KNOWLEDGE_SERVICE_CONFIG_ACTIVITY_BASE = (
    "julee.knowledge_service_config_repo.minio"
)
KNOWLEDGE_SERVICE_QUERY_ACTIVITY_BASE = (
    "julee.knowledge_service_query_repo.minio"
)
POLICY_ACTIVITY_BASE = "julee.policy_repo.minio"
DOCUMENT_POLICY_VALIDATION_ACTIVITY_BASE = (
    "julee.document_policy_validation_repo.minio"
)


# Export all constants
__all__ = [
    "ASSEMBLY_ACTIVITY_BASE",
    "ASSEMBLY_SPECIFICATION_ACTIVITY_BASE",
    "DOCUMENT_ACTIVITY_BASE",
    "KNOWLEDGE_SERVICE_CONFIG_ACTIVITY_BASE",
    "KNOWLEDGE_SERVICE_QUERY_ACTIVITY_BASE",
    "POLICY_ACTIVITY_BASE",
    "DOCUMENT_POLICY_VALIDATION_ACTIVITY_BASE",
]

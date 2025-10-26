"""
Tests for API routers in the julee_example CEAP system.

This package contains test modules organized by router, following the same
structure as the main routers package. Each test module focuses on testing
the endpoints and behavior of a specific router.

Organization:
- test_knowledge_service_queries: Tests for knowledge service query endpoints
- test_system: Tests for system endpoints (health, status)

Test modules follow consistent patterns:
1. Use TestClient with dependency overrides
2. Test both success and error cases
3. Verify proper HTTP status codes and response formats
4. Include integration tests where appropriate
"""

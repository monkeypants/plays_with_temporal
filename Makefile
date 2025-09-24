# Makefile for quality checks and testing and E2E testing
.PHONY: quality-fast quality-full quality-types quality-security test-unit test-e2e e2e-test-setup e2e-test-run e2e-test-run-x e2e-test-teardown post-commit install-hooks reports clean help format

# Fast quality checks (for pre-commit)
quality-fast:
	@echo "Running fast quality checks..."
	black --check cal/ sample/ util/ julee_example/
	ruff check cal/ sample/ util/ julee_example/
	pytest -x -m "not e2e" --no-cov -q

# Full quality suite (for post-commit/CI)
quality-full: reports quality-types quality-security test-unit test-e2e
	@echo "All quality checks complete!"

# Type checking
quality-types: reports
	@echo "Type checking..."
	mypy cal/ sample/ util/ julee_example/ --config-file=mypy.ini > reports/mypy.txt 2>&1

# Security scanning
quality-security: reports
	@echo "Security scanning..."
	bandit -c .bandit -r . --severity-level=high -f json -o reports/bandit-high.json 2>/dev/null || true
	bandit -c .bandit -r . --severity-level=medium -f json -o reports/bandit-medium-high.json 2>/dev/null || true
	bandit -c .bandit -r . --severity-level=low -f json -o reports/bandit-all.json 2>/dev/null || true
	bandit -c .bandit -r . --severity-level=high -f txt -o reports/bandit-high.txt 2>/dev/null || true
	@echo "Security scan complete:"
	@echo "  - High severity only: reports/bandit-high.json, reports/bandit-high.txt"
	@echo "  - Medium+High severity: reports/bandit-medium-high.json"
	@echo "  - All severities: reports/bandit-all.json"

# Unit tests with coverage
test-unit: reports
	@echo "Running unit tests with coverage..."
	pytest --cov=cal --cov=sample --cov=julee_example --cov-fail-under=60 --cov-report=html:reports/htmlcov --cov-report=xml:reports/coverage.xml -m "not e2e"

# E2E test setup (starts ephemeral infrastructure)
e2e-test-setup: reports
	@echo "Starting ephemeral test infrastructure..."
	docker compose -f docker-compose.test.yml build
	docker compose -f docker-compose.test.yml up -d --force-recreate
	@echo "Waiting for services to be healthy..."
	@timeout 120 bash -c 'until docker compose -f docker-compose.test.yml ps | grep -q "healthy"; do echo "Waiting for health checks..."; docker compose -f docker-compose.test.yml ps; sleep 5; done' || (echo "Services failed to start, capturing logs..." && docker compose -f docker-compose.test.yml logs > reports/e2e-infrastructure.log 2>&1 && docker compose -f docker-compose.test.yml down -v && exit 1)
	@echo "Ephemeral test infrastructure is healthy."

# E2E test run (runs pytest against running infrastructure)
e2e-test-run: reports
	@echo "Running E2E tests..."
	@pytest -m e2e --junitxml=reports/e2e-results.xml
	@echo "Capturing infrastructure logs for debugging..."
	@docker compose -f docker-compose.test.yml logs > reports/e2e-infrastructure.log 2>&1

# like e2e-test-run but stop on first failure
e2e-test-run-x: reports
	@echo "Running E2E tests..."
	@pytest -m e2e --junitxml=reports/e2e-results.xml -x
	@echo "Capturing infrastructure logs for debugging..."
	@docker compose -f docker-compose.test.yml logs > reports/e2e-infrastructure.log 2>&1

# E2E test teardown (stops and removes ephemeral infrastructure)
e2e-test-teardown:
	@echo "Cleaning up ephemeral test infrastructure..."
	@docker compose -f docker-compose.test.yml down -v
	@echo "Ephemeral test infrastructure cleaned up."

# Full E2E tests (orchestrates setup, run, teardown)
test-e2e: e2e-test-setup
	-$(MAKE) e2e-test-run; E2E_TEST_EXIT_CODE=$$?; \
	$(MAKE) e2e-test-teardown; \
	exit $$E2E_TEST_EXIT_CODE

# Setup reports directory
reports:
	@mkdir -p reports

# Post-commit hook (run in background)
post-commit: reports
	@echo "Running post-commit quality suite in background..."
	@nohup make quality-full > reports/post-commit.log 2>&1 &
	@echo "Quality checks running in background. Check reports/ for results."

# Install project-specific git hooks
install-hooks:
	@echo "#!/bin/bash" > .git/hooks/post-commit
	@echo "make post-commit" >> .git/hooks/post-commit
	@chmod +x .git/hooks/post-commit
	@echo "Post-commit hook installed for this repository only"

# Clean up generated files
clean:
	@echo "Cleaning up..."
	rm -rf reports/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -rf **/__pycache__/
	rm -rf **/*.pyc
	@echo "Cleanup complete"

# Format code with black
format:
	@echo "Formatting code with black..."
	black cal/ sample/ util/ julee_example/

# Help target
help:
	@echo "Available targets:"
	@echo "  quality-fast    - Fast quality checks (black, ruff, quick tests)"
	@echo "  quality-full    - Full quality suite (types, security, all tests)"
	@echo "  quality-types   - Type checking with mypy"
	@echo "  quality-security- Security scanning with bandit"
	@echo "  test-unit       - Unit tests with coverage"
	@echo "  test-e2e        - End-to-end tests"
	@echo "  e2e-test-setup  - Starts ephemeral E2E infrastructure"
	@echo "  e2e-test-run    - Runs E2E tests against running infrastructure"
	@echo "  e2e-test-run-x  - like e2e-test-run but stop on first error"
	@echo "  e2e-test-teardown - Stops and removes ephemeral E2E infrastructure"
	@echo "  post-commit     - Background quality checks (for git hook)"
	@echo "  install-hooks   - Install git post-commit hook"
	@echo "  format          - Format code with black"
	@echo "  clean           - Clean up generated files"
	@echo "  reports         - Create reports directory"
	@echo "  help            - Show this help"

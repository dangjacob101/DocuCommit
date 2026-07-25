# common dev tasks. fresh clone: `make install && make check`

.PHONY: help install backend-deps frontend-deps test build e2e check clean

help:
	@echo "DocuCommit make targets:"
	@echo "  make install   install backend (venv) + frontend deps + playwright browser"
	@echo "  make test      run backend + frontend unit/integration tests"
	@echo "  make build     create a production frontend build"
	@echo "  make e2e       run the playwright end-to-end suite"
	@echo "  make check     run tests, build, and end-to-end checks"
	@echo "  make clean     remove caches, test artifacts, and local databases"

install: backend-deps frontend-deps

backend-deps:
	cd Frank && python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt

frontend-deps:
	cd client && npm ci
	cd client && npx playwright install chromium

# run the python and frontend unit/integration tests (no e2e)
test:
	cd Frank && for t in test_*.py; do echo "--- $$t ---"; ./.venv/bin/python "$$t" || exit 1; done
	cd client && npm run test:run

build:
	cd client && npm run build

e2e:
	cd client && npm run test:e2e

# the full project health check - delegates to the script so behavior is
# identical whether you run `make check` or `./check_health.sh`
check:
	./check_health.sh

clean:
	find . -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null || true
	rm -f Frank/instance/*.db
	rm -rf client/test-results client/playwright-report

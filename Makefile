PYTHON ?= .venv/bin/python
PYTHON_BOOTSTRAP ?= python3.12
PNPM ?= corepack pnpm

.DEFAULT_GOAL := help

.PHONY: help setup samples cola-index cola-index-sync dev dev-fixture stop logs test test-python test-web build-web demo benchmark

help:
	@echo "Local commands:"
	@echo "  make dev       Start the app with local OCR at http://localhost:8080"
	@echo "  make dev-fixture  Start with deterministic fixture OCR (ignores image text)"
	@echo "  make stop      Stop local containers"
	@echo "  make setup     Install native development/test dependencies"
	@echo "  make samples   Download provenance-tracked public TTB test labels"
	@echo "  make cola-index  Build the locked public COLA metadata index offline"
	@echo "  make cola-index-sync  Refresh the metadata lock from the public Registry"
	@echo "  make test      Run Python and web tests"

setup: $(PYTHON)
	$(PYTHON) -m pip install -e './packages/ocr[test]' -e './apps/cola-mock[test]' -e './apps/api[test]'
	$(PNPM) install --frozen-lockfile

samples: $(PYTHON)
	$(PYTHON) tools/data/fetch_public_cola_samples.py

cola-index: $(PYTHON)
	$(PYTHON) tools/data/build_public_cola_index.py

cola-index-sync: $(PYTHON)
	$(PYTHON) tools/data/sync_public_cola_metadata.py

$(PYTHON):
	@command -v $(PYTHON_BOOTSTRAP) >/dev/null || { echo "Python 3.12 is required (install it with: brew install python@3.12)"; exit 1; }
	$(PYTHON_BOOTSTRAP) -m venv .venv

dev:
	docker compose up --build

dev-fixture:
	OCR_STRATEGIES=fake docker compose up --build

stop:
	docker compose down

logs:
	docker compose logs -f

test: test-python test-web

test-python:
	$(PYTHON) -m pytest packages/ocr/tests apps/cola-mock/tests apps/api/tests tools/data/tests

test-web:
	$(PNPM) web:test

build-web:
	$(PNPM) web:build

demo: dev

benchmark:
	$(PYTHON) tools/ocr/benchmark.py --help

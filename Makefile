.DEFAULT_GOAL := help
.PHONY: help install lint format typecheck test cov build clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install: ## Sync the virtualenv with all dev dependencies
	uv sync --all-groups

lint: ## Run ruff (lint + format check)
	uv run ruff check src tests
	uv run ruff format --check src tests

format: ## Apply ruff formatting and autofixes
	uv run ruff check --fix src tests
	uv run ruff format src tests

typecheck: ## Run mypy in strict mode
	uv run mypy

test: ## Run the test suite
	uv run pytest

cov: ## Run tests with a coverage report
	uv run pytest --cov=pyproyecto --cov-report=term-missing

build: ## Build the wheel and sdist
	uv build

clean: ## Remove build and cache artifacts
	rm -rf dist build .pytest_cache .mypy_cache .ruff_cache
	find . -name '__pycache__' -type d -prune -exec rm -rf {} +

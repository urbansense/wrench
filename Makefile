.PHONY: setup clean install test test_unit test_e2e lint lint_src lint_tests lint_types lint-fix format spell_check spell_fix help

setup:
	rm -rf .venv/
	uv venv
	uv sync --group lint --group test --group dev
	uv run pre-commit install

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache
	rm -rf .coverage
	rm -rf .ruff_cache
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name "*.pyc" -exec rm -rf {} +

install: clean
	uv pip install -e "."

test:
	uv run pytest -v --cov-report=term-missing

test_unit:
	uv run pytest ./tests/unit-test --doctest-modules --junitxml="junit/test-results.xml" --cov=wrench --cov-report=xml --cov-report=html

test_e2e:
	uv run pytest ./tests/e2e --doctest-modules --junitxml="junit/test-results.xml" --cov=wrench --cov-report=xml --cov-report=html

# Check source code
lint_src:
	uv run --group lint ruff check wrench
	uv run --group lint ruff format --diff wrench
	uv run --group lint ruff check --select I wrench

# Check test code
lint_tests:
	uv run --group lint ruff check tests
	uv run --group lint ruff format tests --diff
	uv run --group lint ruff check --select I tests

# Check type hints
lint_types:
	uv run --group lint mypy wrench

# Main lint command that runs all groups
lint: lint_src lint_tests

lint-fix:
	uv run --group lint ruff check wrench --fix

## format: Format the project files.
format:
	uv run --group lint ruff format wrench tests
	uv run --group lint ruff check --select I --fix wrench tests

spell_check:
	uv run --group lint codespell --toml pyproject.toml

spell_fix:
	uv run --group lint codespell --toml pyproject.toml -w

# Help target
help:
	@echo "Setup:"
	@echo "  make setup       - Create venv, install all deps, install pre-commit hooks"
	@echo "  make install     - Install package in editable mode"
	@echo "  make clean       - Remove build artifacts and caches"
	@echo ""
	@echo "Testing:"
	@echo "  make test        - Run full test suite with coverage"
	@echo "  make test_unit   - Run unit tests only"
	@echo "  make test_e2e    - Run end-to-end tests only"
	@echo ""
	@echo "Linting:"
	@echo "  make lint        - Run all lint checks (src + tests)"
	@echo "  make lint_src    - Lint source code only"
	@echo "  make lint_tests  - Lint test code only"
	@echo "  make lint_types  - Check type hints with mypy"
	@echo "  make lint-fix    - Auto-fix lint issues in source"
	@echo ""
	@echo "Formatting:"
	@echo "  make format      - Format all code"
	@echo ""
	@echo "Spell checking:"
	@echo "  make spell_check - Check for misspellings"
	@echo "  make spell_fix   - Auto-fix misspellings"

.PHONY: clean test install lint lint_src lint_tests lint_types help

setup:
	uv pip install -e ".[teleclass,sensorthings]"

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
	pytest -v --cov-report=term-missing

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
lint: lint_src lint_tests lint_docs lint_types

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
	@echo "Available lint commands:"
	@echo "  make lint      - Run all lint checks"
	@echo "  make lint_src  - Lint source code only"
	@echo "  make lint_tests- Lint test code only"
	@echo "  make lint_docs - Lint documentation only"
	@echo "  make lint_types- Check type hints"
	@echo ""
	@echo "Available format commands:"
	@echo "  make format      - Format all code"

# Contributing to Wrench

Thank you for your interest in contributing to Wrench! This guide will help you
get set up and explain how the project is structured.

## Development Setup

### Prerequisites

- Python 3.12 or later
- [uv](https://docs.astral.sh/uv/) (recommended package manager)
- Git

### Getting Started

```bash
# Clone the repository
git clone https://github.com/urbansense/wrench.git
cd wrench

# Set up the development environment (creates venv, installs all deps)
make setup

# Or manually:
uv venv
uv sync --group lint --group test --group dev
```

### Running Tests

```bash
# Run the full test suite with coverage
make test

# Run only unit tests
make test_unit

# Run only end-to-end tests
make test_e2e
```

### Linting and Formatting

The project uses [Ruff](https://docs.astral.sh/ruff/) for linting and
formatting, [codespell](https://github.com/codespell-project/codespell) for
spell checking, and [mypy](https://mypy-lang.org/) for type checking.

```bash
# Lint source code
make lint

# Auto-format code
make format

# Type checking
make lint_types

# Spell checking
make spell_check
```

Pre-commit hooks are configured to run these checks automatically. Install them
with:

```bash
pre-commit install
```

## Project Structure

```
wrench/
  cataloger/       # Catalog registration backends (SDDI/CKAN, noop)
  components/      # Pipeline component wrappers
  grouper/         # Device grouping algorithms (KINETIC, LDA, BERTopic)
  harvester/       # Data source harvesters (SensorThings API)
  metadataenricher/ # Metadata building and enrichment
  pipeline/        # Pipeline orchestration and configuration
  scheduler/       # Scheduled pipeline execution
  utils/           # Shared utilities (config, logging, prompts)
tests/
  unit-test/       # Unit tests, organized by module
  e2e/             # End-to-end pipeline tests
docs/              # MkDocs documentation source
tools/             # Developer CLI for experiments and evaluation (not shipped)
```

## Adding a New Component

Wrench is designed around four extensible component types. Each has a base class
you subclass.

### Adding a New Harvester

1. Create a directory under `wrench/harvester/your_source/`.
2. Subclass `BaseHarvester` from `wrench.harvester.base` and implement
   `return_devices()`.
3. Add tests under `tests/unit-test/harvester/your_source/`.

### Adding a New Grouper

1. Create a directory under `wrench/grouper/your_algorithm/`.
2. Subclass `BaseGrouper` from `wrench.grouper.base` and implement
   `group_devices()`.
3. Add tests under `tests/unit-test/grouper/your_algorithm/`.

### Adding a New Cataloger

1. Create a directory under `wrench/cataloger/your_catalog/`.
2. Subclass `BaseCataloger` from `wrench.cataloger.base` and implement
   `register()`.
3. Add tests under `tests/unit-test/cataloger/your_catalog/`.

### Adding a New Metadata Enricher

1. Create a directory under `wrench/metadataenricher/your_source/`.
2. Subclass `BaseMetadataEnricher` from `wrench.metadataenricher.base` and
   implement the abstract methods (`_get_source_type`, `_build_service_urls`,
   `_build_group_urls`, `_calculate_service_spatial_extent`,
   `_calculate_group_spatial_extent`).
3. Add tests under `tests/unit-test/metadataenricher/your_source/`.

## Pull Request Process

1. Fork the repository and create a feature branch from `main`.
2. Make your changes with appropriate tests.
3. Ensure all checks pass: `make lint && make test`.
4. Open a Pull Request against `main` and fill in the PR template.

### Commit Messages

Use clear, descriptive commit messages. We follow conventional-style prefixes:

- `feat:` for new features
- `fix:` for bug fixes
- `docs:` for documentation changes
- `test:` for test additions or fixes
- `refactor:` for code restructuring
- `ci:` for CI/CD changes

## Reporting Issues

- Use the **Bug Report** issue template for bugs.
- Use the **Feature Request** template for enhancement ideas.
- For security vulnerabilities, see [SECURITY.md](SECURITY.md).

## Code of Conduct

This project follows the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md).
By participating, you agree to uphold this code.

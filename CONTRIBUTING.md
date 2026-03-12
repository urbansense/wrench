# Contributing to Wrench

Thank you for your interest in contributing to Wrench! This guide explains
prerequisites, environment setup, project structure, how to implement each
component type, code style conventions, and the pull request process.

---

## Quick start for contributors

```bash
git clone https://github.com/urbansense/wrench.git
cd wrench
make setup                          # create venv, install all deps, install pre-commit
uv pip install -e ".[sensorthings,kinetic]"  # add optional extras you need
make test                           # confirm everything passes
```

---

## Prerequisites

| Tool | Minimum version | Purpose |
|------|----------------|---------|
| Python | 3.12 | Runtime |
| [uv](https://docs.astral.sh/uv/) | latest | Package and venv management |
| Git | any | Version control |

---

## Environment setup

### 1. Clone the repository

```bash
git clone https://github.com/urbansense/wrench.git
cd wrench
```

### 2. Create the development environment

`make setup` creates a virtual environment at `.venv/`, installs all dependency
groups (`lint`, `test`, `dev`), and registers the pre-commit hooks.

```bash
make setup
```

To install manually instead:

```bash
uv venv
uv sync --group lint --group test --group dev
uv run pre-commit install
```

### 3. Install optional component extras

Install the extras for the components you plan to work on:

```bash
uv pip install -e ".[sensorthings]"          # SensorThings harvester
uv pip install -e ".[kinetic]"               # KINETIC grouper
uv pip install -e ".[sensorthings,kinetic]"  # both
```

---

## Project structure

```
wrench/                        # Main package
  cataloger/                   # Catalog registration backends
    base.py                    #   BaseCataloger abstract class
    noop/                      #   No-op cataloger (for testing)
    sddi/                      #   SDDI/CKAN cataloger
  components/                  # Pipeline component wrappers (internal)
  grouper/                     # Device grouping algorithms
    base.py                    #   BaseGrouper abstract class
    kinetic/                   #   KINETIC grouper
    lda/                       #   LDA grouper
    bertopic/                  #   BERTopic grouper
  harvester/                   # Data source harvesters
    base.py                    #   BaseHarvester abstract class
    sensorthings/              #   OGC SensorThings API harvester
  metadataenricher/            # Metadata building and enrichment
    base.py                    #   BaseMetadataEnricher abstract class
    sensorthings/              #   SensorThings-specific enricher
  pipeline/                    # Pipeline orchestration and configuration
    config/                    #   YAML config reading and component registry
    sensor_pipeline.py         #   High-level SensorRegistrationPipeline
    pipeline.py                #   Core async Pipeline execution engine
  scheduler/                   # Scheduled pipeline execution
  utils/                       # Shared utilities (config, logging, prompts)
  models.py                    # Core data models: Device, Group, CommonMetadata
  types.py                     # Shared type aliases

tests/
  unit-test/                   # Unit tests, organized by module
  e2e/                         # End-to-end pipeline tests

examples/                      # Runnable example scripts
docs/                          # MkDocs documentation source
tools/                         # Developer CLI for experiments (not shipped)
```

---

## Running tests

```bash
# Full test suite with coverage report
make test

# Unit tests only
make test_unit

# End-to-end tests only
make test_e2e
```

Tests are located under `tests/`. Unit tests mirror the `wrench/` package
structure. Add new unit tests under `tests/unit-test/<module>/`.

---

## Code style and linting

The project uses [Ruff](https://docs.astral.sh/ruff/) for linting and
formatting, [codespell](https://github.com/codespell-project/codespell) for
spell checking, and [mypy](https://mypy-lang.org/) for type checking.

```bash
# Format all code (wrench/ and tests/)
make format

# Lint source code (check only, no changes)
make lint

# Lint source and test code separately
make lint_src
make lint_tests

# Auto-fix lint issues in source
make lint-fix

# Type checking
make lint_types

# Spell checking
make spell_check
make spell_fix   # auto-fix misspellings
```

Docstrings must follow
[Google style](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings).
Pre-commit hooks run `ruff check` and `ruff format` automatically on every
commit.

---

## Adding a new component

For detailed guides on implementing each component type (Harvester, Grouper,
MetadataEnricher, Cataloger) — including directory layout, required method
signatures, registration, and testing — see:

**[docs/contributor/creating_components.md](docs/contributor/creating_components.md)**

---

## Pull request process

1. Fork the repository and create a feature branch from `main`:

   ```bash
   git checkout -b feat/my-new-harvester
   ```

2. Make your changes with appropriate tests.

3. Ensure all checks pass:

   ```bash
   make format   # format first, then lint
   make lint
   make lint_types
   make test
   ```

4. Open a Pull Request against `main` and fill in the PR template.

### Commit message format

Use [Conventional Commits](https://www.conventionalcommits.org/) prefixes:

| Prefix | When to use |
|--------|-------------|
| `feat:` | New features |
| `fix:` | Bug fixes |
| `docs:` | Documentation changes only |
| `test:` | Adding or fixing tests |
| `refactor:` | Code restructuring without behaviour change |
| `ci:` | CI/CD workflow changes |

### PR checklist

Before requesting a review, confirm:

- [ ] All existing tests pass (`make test`).
- [ ] New functionality has unit tests.
- [ ] Code is formatted and linted (`make format && make lint`).
- [ ] Type hints are present and mypy is satisfied (`make lint_types`).
- [ ] New component is registered in the appropriate `__init__.py` registry.
- [ ] Public classes and methods have Google-style docstrings.
- [ ] The `CONTRIBUTING.md` or `README.md` is updated if you changed a public API.

---

## Reporting issues

- Use the **Bug Report** issue template for bugs.
- Use the **Feature Request** template for enhancement ideas.
- For security vulnerabilities, see [SECURITY.md](SECURITY.md).

## Code of conduct

This project follows the
[Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md).
By participating, you agree to uphold this code.

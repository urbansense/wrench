# Wrench Development Tools

A comprehensive CLI toolkit for managing test data, running evaluations, managing catalog entries, and executing pipelines in the Wrench project.

## Installation

The tools are available as part of the Wrench project. To use them:

```bash
# From the wrench project root
python -m tools.cli --help

# Or create an alias for convenience
alias wrench-tools="python -m tools.cli"
```

## Quick Start

```bash
# Fetch and cache data from Hamburg
wrench-tools data fetch hamburg --embeddings

# List cached data
wrench-tools data list

# Create ground truth for evaluation
wrench-tools evaluate create-ground-truth hamburg output/hamburg_gt.json

# Run a pipeline
wrench-tools pipeline run test_script/pipeline_config.yaml --once

# List catalog entries
wrench-tools catalog list

# Clean up old catalog entries
wrench-tools catalog delete-batch old_entries.txt
```

## Commands

### Data Management (`data`)

Manage test data and caching for different SensorThings sources.

#### `data fetch <source>`
Fetch data from a SensorThings server and cache it locally.

**Options:**
- `--limit, -l <number>`: Limit number of items to fetch (-1 for all)
- `--embeddings`: Also generate and cache embeddings
- `--embedding-model <name>`: Model to use for embeddings (default: intfloat/multilingual-e5-large-instruct)
- `--force, -f`: Force re-fetch even if cached data exists

**Examples:**
```bash
# Fetch all items from Hamburg
wrench-tools data fetch hamburg

# Fetch 100 items from Osnabrück with embeddings
wrench-tools data fetch osnabrueck --limit 100 --embeddings

# Re-fetch München data even if cached
wrench-tools data fetch muenchen --force
```

#### `data list`
List all cached data sources and their status.

```bash
wrench-tools data list
```

#### `data info <source>`
Show detailed information about a cached data source.

```bash
wrench-tools data info hamburg
```

**Available Sources:**
- `hamburg`: Hamburg FROST Server
- `osnabrueck`: Osnabrück FROST Server
- `muenchen`: München FROST Server

---

### Evaluation (`evaluate`)

Tools for creating ground truth datasets and computing clustering metrics.

#### `evaluate create-ground-truth <source> <output>`
Create a ground truth dataset from a data source.

**Arguments:**
- `source`: Name of the data source (hamburg, osnabrueck, muenchen)
- `output`: Path to save the ground truth JSON file

**Options:**
- `--interactive, -i`: Interactive mode to add custom rules (coming soon)

**Examples:**
```bash
# Create ground truth for Hamburg
wrench-tools evaluate create-ground-truth hamburg data/hamburg_gt.json

# Create ground truth for Osnabrück
wrench-tools evaluate create-ground-truth osnabrueck data/osnabrueck_gt.json
```

#### `evaluate metrics <ground_truth> <results>`
Compute clustering metrics by comparing results to ground truth.

**Arguments:**
- `ground_truth`: Path to ground truth JSON file
- `results`: Path to clustering results JSON file

**Options:**
- `--output, -o <path>`: Save metrics to JSON file
- `--handle-missing <strategy>`: How to handle missing items (skip/error/assign_new_cluster)

**Examples:**
```bash
# Compute metrics
wrench-tools evaluate metrics data/hamburg_gt.json results/hamburg_results.json

# Compute and save metrics
wrench-tools evaluate metrics data/gt.json results.json --output metrics.json
```

**Metrics Computed:**
- Normalized Mutual Information (NMI)
- Homogeneity
- Completeness
- V-Measure

#### `evaluate compare <ground_truth> <results>`
Compare clustering results to ground truth and show detailed differences.

**Options:**
- `--detailed/--summary`: Show detailed differences per category (default: summary)

**Examples:**
```bash
# Summary comparison
wrench-tools evaluate compare data/gt.json results.json

# Detailed comparison
wrench-tools evaluate compare data/gt.json results.json --detailed
```

---

### Catalog Management (`catalog`)

Manage SDDI/CKAN catalog entries.

**Environment Variables:**
- `CKAN_BASE_URL`: CKAN base URL (default: http://10.162.246.69:5000)
- `CKAN_API_TOKEN`: CKAN API token (required)

#### `catalog list`
List packages in the SDDI catalog.

**Options:**
- `--base-url <url>`: CKAN base URL
- `--api-key <key>`: CKAN API token
- `--pattern, -p <pattern>`: Filter packages by name pattern

**Examples:**
```bash
# List all packages
wrench-tools catalog list

# List packages matching pattern
wrench-tools catalog list --pattern "hamburg"
```

#### `catalog show <package_id>`
Show details of a specific package.

```bash
wrench-tools catalog show osnabrueck_frost_server
```

#### `catalog delete <package_id>`
Delete a package from the catalog.

**Options:**
- `--force, -f`: Skip confirmation prompt

**Examples:**
```bash
# Delete with confirmation
wrench-tools catalog delete old_package

# Delete without confirmation
wrench-tools catalog delete old_package --force
```

#### `catalog delete-batch <package_file>`
Delete multiple packages from a file (one package ID per line).

**Options:**
- `--force, -f`: Skip confirmation prompt

**Examples:**
```bash
# Create a file with package IDs to delete
cat > packages_to_delete.txt << EOF
old_package_1
old_package_2
test_package
EOF

# Delete all packages in the file
wrench-tools catalog delete-batch packages_to_delete.txt
```

#### `catalog clean-all`
Interactively clean all packages from the catalog.

**Options:**
- `--pattern, -p <pattern>`: Only delete packages matching pattern

**Examples:**
```bash
# Clean all test packages
wrench-tools catalog clean-all --pattern "test_"

# Clean everything (use with caution!)
wrench-tools catalog clean-all
```

---

### Pipeline Execution (`pipeline`)

Run and test pipelines and components.

#### `pipeline run <config_path>`
Run a pipeline from a configuration file.

**Options:**
- `--once`: Run pipeline once and exit (ignore scheduler)
- `--save-results, -s <path>`: Save results to JSON file

**Examples:**
```bash
# Run pipeline once
wrench-tools pipeline run test_script/pipeline_config.yaml --once

# Run pipeline with scheduler
wrench-tools pipeline run test_script/pipeline_config.yaml

# Run and save results
wrench-tools pipeline run config.yaml --once --save-results output/results.json
```

#### `pipeline test <component_type> <config_path>`
Test a single component with its configuration.

**Component Types:**
- `harvester`: Test data harvesting
- `grouper`: Test clustering/grouping
- `cataloger`: Test catalog connection
- `metadataenricher`: Test metadata enrichment

**Options:**
- `--limit, -l <number>`: Limit number of items to process

**Examples:**
```bash
# Test harvester
wrench-tools pipeline test harvester test_script/sta_config.yaml

# Test cataloger
wrench-tools pipeline test cataloger test_script/sddi_config.yaml

# Test harvester with limit
wrench-tools pipeline test harvester config.yaml --limit 10
```

#### `pipeline list-configs`
List available pipeline configuration files.

**Options:**
- `--component, -c <type>`: Filter by component type

**Examples:**
```bash
# List all configs
wrench-tools pipeline list-configs

# List harvester configs only
wrench-tools pipeline list-configs --component harvester
```

---

## Configuration

### Environment Variables

Create a `.env` file in the `test_script` directory or your home directory (`~/.wrench.env`):

```bash
# CKAN/SDDI Configuration
CKAN_BASE_URL=http://10.162.246.69:5000
CKAN_API_TOKEN=your_api_token_here

# LLM Configuration
OLLAMA_URL=http://localhost:11434/v1
OLLAMA_MODEL=llama3.1:8b
OLLAMA_API_KEY=ollama

GEMINI_URL=https://generativelanguage.googleapis.com/v1beta
GEMINI_MODEL=gemini-pro
GEMINI_API_KEY=your_gemini_key_here
```

### Data Cache

Cached data is stored in `tools/fixtures/data/` by default:

```
tools/fixtures/data/
├── hamburg_items.json
├── hamburg_embeddings.npz
├── osnabrueck_items.json
└── osnabrueck_embeddings.npz
```

---

## Migration from test_script

The tools CLI replaces scattered test scripts with a unified interface:

### Before (test_script)
```bash
# Had to know which file to run and modify
python test_script/checkout_sta_server.py  # Manual code edits needed
python test_script/evaluate.py             # Manual code edits needed
python test_script/delete_sddi_entries.py  # Manual list editing needed
```

### After (tools CLI)
```bash
# Clean, documented interface
wrench-tools data fetch hamburg
wrench-tools evaluate metrics gt.json results.json
wrench-tools catalog delete-batch packages.txt
```

### Command Mapping

| Old Script | New Command |
|------------|-------------|
| `dataloader.py` | `wrench-tools data fetch <source>` |
| `checkout_sta_server.py` | `wrench-tools data fetch <source>` |
| `ground_truth.py` | `wrench-tools evaluate create-ground-truth` |
| `evaluate.py` | `wrench-tools evaluate metrics` |
| `check_accuracy.py` | `wrench-tools evaluate compare` |
| `validate_*_results.py` | `wrench-tools evaluate compare` |
| `delete_sddi_entries.py` | `wrench-tools catalog delete-batch` |
| `checkout_sddi_catalog.py` | `wrench-tools catalog list/show` |
| `test_pipeline_framework.py` | `wrench-tools pipeline run --once` |
| `test_teleclass.py` | `wrench-tools pipeline test grouper` |

---

## Architecture

```
tools/
├── cli.py                    # Main CLI entry point
├── commands/                 # Command modules
│   ├── data.py              # Data management commands
│   ├── evaluate.py          # Evaluation commands
│   ├── catalog.py           # Catalog management
│   └── pipeline.py          # Pipeline execution
├── core/                    # Core utilities
│   ├── cache.py             # Unified caching system
│   ├── config_loader.py     # Configuration management
│   └── ground_truth.py      # Ground truth utilities
├── fixtures/                # Test data and configs
│   ├── data_sources.py      # Known SensorThings servers
│   ├── data/               # Cached test data
│   └── configs/            # Template configurations
└── notebooks/              # Exploratory analysis notebooks
```

---

## Development

### Adding New Commands

1. Create a new command module in `tools/commands/`
2. Define command group using Click
3. Register in `tools/cli.py`

Example:
```python
# tools/commands/mynew.py
import click

@click.group()
def mynew():
    """My new command group."""
    pass

@mynew.command()
def hello():
    """Say hello."""
    click.echo("Hello!")

# tools/cli.py
from tools.commands.mynew import mynew
cli.add_command(mynew)
```

### Adding New Data Sources

Edit `tools/fixtures/data_sources.py`:

```python
KNOWN_SOURCES = {
    "mynew": DataSource(
        name="mynew",
        base_url="https://example.com/v1.1",
        identifier="mynew_frost_server",
        title="My New FROST Server",
        description="Description of the server.",
    ),
}
```

---

## Examples

### Complete Workflow: Evaluate Hamburg Data

```bash
# 1. Fetch and cache Hamburg data
wrench-tools data fetch hamburg --embeddings

# 2. Create ground truth
wrench-tools evaluate create-ground-truth hamburg data/hamburg_gt.json

# 3. Run clustering pipeline
wrench-tools pipeline run configs/hamburg_pipeline.yaml --once --save-results results/hamburg_results.json

# 4. Compute metrics
wrench-tools evaluate metrics data/hamburg_gt.json results/hamburg_results.json --output metrics/hamburg_metrics.json

# 5. View detailed comparison
wrench-tools evaluate compare data/hamburg_gt.json results/hamburg_results.json --detailed
```

### Clean Up Test Catalog

```bash
# List current packages
wrench-tools catalog list

# Delete packages matching pattern
wrench-tools catalog clean-all --pattern "test_"

# Or delete specific packages
cat > packages.txt << EOF
test_package_1
test_package_2
EOF
wrench-tools catalog delete-batch packages.txt --force
```

---

## Troubleshooting

### Command not found
Make sure you're running from the wrench project root:
```bash
cd /path/to/wrench
python -m tools.cli --help
```

### CKAN API errors
Ensure your API token is set:
```bash
export CKAN_API_TOKEN=your_token_here
# Or add to .env file
```

### Missing dependencies
Install all optional dependencies:
```bash
uv pip install -e ".[teleclass,sensorthings]"
```

---

## Contributing

When adding new test scripts, consider:
1. Can this be a CLI command instead?
2. Does it fit into existing command groups?
3. Should it use the unified cache system?
4. Does it need new fixtures/configurations?

Keep exploratory notebooks in `tools/notebooks/` but migrate reusable functionality to CLI commands.

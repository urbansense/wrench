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
- `--handle-missing <strategy>`: How to handle devices missing from results
  - `singleton` *(default)*: each unclassified device becomes its own cluster — groupers that drop devices are penalised
  - `skip`: silently ignore devices absent from either dict
  - `assign_new_cluster`: lump all unclassified devices into one shared cluster

**Examples:**

```bash
# Compute metrics (singleton penalisation on by default)
wrench-tools evaluate metrics data/hamburg_gt.json results/hamburg_results.json

# Compute and save metrics
wrench-tools evaluate metrics data/gt.json results.json --output metrics.json
```

**Metrics Computed:**

- Normalized Mutual Information (NMI)
- Homogeneity
- Completeness
- V-Measure

#### `evaluate cross-tab <ground_truth> <results>`

Show a cross-tabulation of ground-truth clusters vs predicted clusters. Each row is a GT category; each column is the predicted cluster its devices actually landed in. Dominant cells are green, leakage is red, unclassified devices are yellow.

**Options:**

- `--show-devices, -d`: List individual device IDs for every non-dominant cell

**Examples:**

```bash
# Cross-tabulation summary
wrench-tools evaluate cross-tab data/hamburg_gt.json results/hamburg_results.json

# Show which devices leaked into wrong clusters
wrench-tools evaluate cross-tab data/gt.json results.json --show-devices
```

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

### Experiment tracking (`experiment`)

Run KINETIC with different configurations, track results, and compare experiments.

#### `experiment run <source>`

Run KINETIC on a cached data source. Results, config, and metrics are saved to `.experiments/`.

**Arguments:**

- `source`: Name of the cached data source (e.g. `hamburg`, `osnabrueck`)

**Options:**

| Flag | Default | Description |
|------|---------|-------------|
| `--name, -n` | auto | Experiment name (auto-generated if omitted) |
| `--classifier` | `embedding` | `embedding` (local cosine similarity) or `jev` (TypeSafe Jev via OpenRouter) |
| `--embedding-provider, -ep` | `sentence-transformers` | `sentence-transformers` or `openai` |
| `--embedding-model, -em` | model-dependent | Embedding model name |
| `--embedding-base-url` | — | Base URL for OpenAI-compatible embedding endpoint |
| `--embedding-api-key` | — | API key for embedding endpoint |
| `--llm-model` | — | LLM model for topic naming |
| `--llm-base-url` | — | LLM base URL |
| `--llm-api-key` | — | LLM API key |
| `--resolution, -r` | `1` | Louvain resolution (higher = smaller clusters) |
| `--ground-truth, -gt` | — | Ground truth JSON for automatic metrics |
| `--lang` | `de` | Language (`de` or `en`) |
| `--env, -e` | — | Load environment variables from a `.env` file |

**Examples:**

```bash
# Default embedding classifier (no API cost)
uv run python -m tools.cli experiment run hamburg \
    --env .env \
    --ground-truth tools/fixtures/data/hamburg_gt.json

# Jev classifier via OpenRouter (⚠ costs API credits)
uv run python -m tools.cli experiment run hamburg \
    --classifier jev \
    --env .env \
    --ground-truth tools/fixtures/data/hamburg_gt.json

# Ollama embeddings instead of local SentenceTransformers
uv run python -m tools.cli experiment run hamburg \
    --embedding-provider openai \
    --embedding-model nomic-embed-text \
    --embedding-base-url http://localhost:11434/v1 \
    --env .env
```

#### `experiment list`

List all tracked experiments, with NMI and V-Measure scores where available.

```bash
uv run python -m tools.cli experiment list
uv run python -m tools.cli experiment list --source hamburg
```

#### `experiment show <exp_id>`

Show full details of a single experiment: config, metrics, and topic breakdown. Opens a per-document similarity score report in the browser when available.

```bash
uv run python -m tools.cli experiment show hamburg_r1_182317_20260922_182449
```

#### `experiment compare <exp_id>...`

Generate an interactive HTML report comparing two or more experiments side by side.

**Options:**

- `--output, -o <path>`: Output HTML path (auto-generated if omitted)
- `--open-browser`: Open report in browser immediately

```bash
uv run python -m tools.cli experiment compare <exp_id_1> <exp_id_2> --open-browser
```

---

### Catalog Management (`catalog`)

Manage SDDI/CKAN catalog entries.

**Environment Variables:**

- `CKAN_BASE_URL`: CKAN base URL (default: http://localhost:5000)
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

Create a `.env` file in the project root (pass via `--env .env`):

```bash
# LLM for topic naming (required for experiment run)
LLM_API_KEY=sk-or-...          # OpenRouter or any OpenAI-compatible key
LLM_BASE_URL=http://localhost:11434/v1
LLM_MODEL=llama3.3:70b-instruct-q4_K_M

# CKAN/SDDI (required for catalog commands)
CKAN_BASE_URL=http://localhost:5000
CKAN_API_TOKEN=your_api_token_here
```

`LLM_API_KEY` is also reused as the Jev API key when `--classifier jev` is set, since both go through OpenRouter.

### Data Cache

Cached data is stored in `tools/fixtures/data/` by default:

```bash
tools/fixtures/data/
├── hamburg_items.json
├── hamburg_embeddings.npz
├── osnabrueck_items.json
└── osnabrueck_embeddings.npz
```

---

## Architecture

```
tools/
├── cli.py                    # Main CLI entry point
├── commands/                 # Command modules
│   ├── data.py              # Data management commands
│   ├── evaluate.py          # Evaluation commands (metrics, cross-tab, compare)
│   ├── experiment.py        # Experiment run/list/show/compare
│   ├── catalog.py           # Catalog management
│   └── pipeline.py          # Pipeline execution
├── core/                    # Core utilities
│   ├── cache.py             # Unified caching system
│   ├── config.py            # LLM config resolution
│   ├── experiment.py        # Experiment tracker
│   ├── metrics.py           # NMI / V-Measure computation
│   ├── ground_truth.py      # Ground truth utilities
│   └── report.py            # HTML report generation
├── fixtures/                # Test data and configs
│   ├── data_sources.py      # Known SensorThings servers
│   ├── data/               # Cached test data and ground-truth files
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
wrench-tools data fetch hamburg

# 2. Create ground truth
wrench-tools evaluate create-ground-truth hamburg tools/fixtures/data/hamburg_gt.json

# 3. Run experiment with default embedding classifier
uv run python -m tools.cli experiment run hamburg \
    --env .env \
    --ground-truth tools/fixtures/data/hamburg_gt.json

# 4. Run the same data with Jev classifier for comparison (⚠ costs API credits)
uv run python -m tools.cli experiment run hamburg \
    --classifier jev \
    --env .env \
    --ground-truth tools/fixtures/data/hamburg_gt.json

# 5. Compare both experiments
uv run python -m tools.cli experiment list --source hamburg
uv run python -m tools.cli experiment compare <embedding_exp_id> <jev_exp_id> --open-browser

# 6. Inspect misclassified devices
uv run python -m tools.cli evaluate cross-tab \
    tools/fixtures/data/hamburg_gt.json \
    .experiments/<exp_id>/results.json --show-devices
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

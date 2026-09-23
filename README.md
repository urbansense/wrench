# Wrench 🔧

A powerful framework for building automated sensor registration pipelines.

[![PyPI version](https://img.shields.io/pypi/v/auto-wrench.svg)](https://pypi.org/project/auto-wrench/)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![CI](https://github.com/urbansense/wrench/actions/workflows/pr-tests.yml/badge.svg)](https://github.com/urbansense/wrench/actions/workflows/pr-tests.yml)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-FFEE8C.svg?logo=ruff)](https://docs.astral.sh/ruff/formatter/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://www.apache.org/licenses/LICENSE-2.0)

## Overview

Wrench is a modular, extensible workflow framework designed to streamline the process of harvesting, enriching, and registering sensor metadata from diverse IoT sources into urban data catalogs. It provides a standardized pipeline architecture with interchangeable components to help make sensor data more discoverable and valuable.

## Features

- 🔄 **Automated Metadata Harvesting**: Extract metadata from various IoT data sources with minimal configuration
- 📊 **Standardized Data Models**: Type-safe data structures using Pydantic for consistent handling of metadata
- 🔍 **Advanced Classification**: Group similar sensors using ML, embeddings, or probabilistic AI (Jev)
- ✨ **Metadata Enrichment**: Enhance sensor descriptions with contextual information using LLM technologies
- 🏗️ **Modular Architecture**: Compose workflows from interchangeable components for maximum flexibility
- 🔌 **Extensible Interfaces**: Easily add support for new data sources, catalog systems, and classifier backends
- 🤖 **LLM Integration**: Leverage AI capabilities for automatic content generation and classification

## Installation

```bash
pip install auto-wrench
```

To install with specific component dependencies:

```bash
# For SensorThings support
pip install 'auto-wrench[sensorthings]'

# For KINETIC grouper
pip install 'auto-wrench[kinetic]'

# Multiple components
pip install 'auto-wrench[sensorthings,kinetic]'
```

## Core Components

Wrench consists of four main component types that can be combined in a pipeline:

1. **Harvesters**: Extract metadata from IoT data sources (e.g., SensorThings API)
2. **Groupers**: Classify and organize sensors into meaningful groups using various ML approaches
3. **MetadataEnrichers**: Build spatial and temporal metadata for services and sensor groups
4. **Catalogers**: Register the processed metadata into data catalogs (e.g., SDDI/CKAN)

Each component type follows a standardized interface, making it easy to extend with custom implementations.

## Quick start

The following example sets up a complete pipeline with a SensorThings API harvester, a KINETIC grouper for classification, and an SDDI cataloger for registration:

```python
import asyncio

from wrench.cataloger.sddi import SDDICataloger
from wrench.grouper.kinetic import KINETIC
from wrench.harvester.sensorthings import SensorThingsHarvester
from wrench.metadataenricher.sensorthings import SensorThingsMetadataEnricher
from wrench.pipeline.sensor_pipeline import SensorRegistrationPipeline
from wrench.utils.config import LLMConfig

llm_config = LLMConfig(base_url="https://my-llm.com", model="llama3.3:70b-instruct-q4_K_M")

# Initialize components
harvester = SensorThingsHarvester(
    base_url="https://example.org/v1.1",
    pagination_config={"page_delay": 0.2, "timeout": 60, "batch_size": 100},
)
grouper = KINETIC(
    llm_config=llm_config,
    embedder="intfloat/multilingual-e5-large-instruct",
    resolution=1,
)
metadata_enricher = SensorThingsMetadataEnricher(
    base_url="https://example.org/v1.1",
    title="City Sensor Network",
    description="Environmental sensors across the city",
    llm_config=llm_config,
)
cataloger = SDDICataloger(
    base_url="https://catalog.example.org",
    api_key="your-api-key",
    owner_org="your-organization",
)

# Assemble and run the pipeline
pipeline = SensorRegistrationPipeline(
    harvester=harvester,
    grouper=grouper,
    metadataenricher=metadata_enricher,
    cataloger=cataloger,
)

result = asyncio.run(pipeline.run_async())
```

## Configuration

Wrench supports YAML-based pipeline configuration through `PipelineRunner.from_config_file()`.
The top-level `template_` key selects the pipeline template. Environment variables are
resolved using `${VAR_NAME}` syntax.

```yaml
# pipeline_config.yaml
template_: SensorPipeline

harvester:
  sensorthings:
    base_url: "https://example.org/v1.1"
    pagination_config:
      page_delay: 0.2
      timeout: 60
      batch_size: 100

grouper:
  kinetic:
    llm_config:
      model: ${OLLAMA_MODEL}
      base_url: ${OLLAMA_URL}
      api_key: ${OLLAMA_API_KEY}

metadataenricher:
  sensorthings:
    base_url: "https://example.org/v1.1"
    title: "City Sensor Network"
    description: "Environmental sensors across the city"
    llm_config:
      model: ${OLLAMA_MODEL}
      base_url: ${OLLAMA_URL}
      api_key: ${OLLAMA_API_KEY}

cataloger:
  noop: {}
```

Run a YAML-configured pipeline with:

```python
import asyncio
from wrench.pipeline.config import PipelineRunner

runner = PipelineRunner.from_config_file("pipeline_config.yaml")
result = asyncio.run(runner.run({}))
```

## Component Overview

### Harvesters

Harvesters connect to data sources and extract metadata. Wrench includes:

- **SensorThingsHarvester**: Connects to OGC SensorThings API endpoints
- Extensible base class for creating custom harvesters

### Groupers

Groupers organize sensors into logical groups using various machine learning approaches:

- **KINETIC**: Keyword-Informed, Network-Enhanced Topical Intelligence Classifier with hierarchical clustering
- **LDAGrouper**: Latent Dirichlet Allocation for topic modeling and device grouping
- **BERTopicGrouper**: BERTopic-based clustering with HDBSCAN and UMAP for topic discovery
- Can be extended with custom grouping algorithms

### MetadataEnrichers

MetadataEnrichers build spatial and temporal metadata for items and groups:

- **SensorThingsMetadataEnricher**: Builds metadata for SensorThings API data sources
- Extensible base class for different data source types

### Catalogers

Catalogers register metadata into data catalogs:

- **SDDICataloger**: Registers metadata into SDDI/CKAN-based catalogs
- Extensible interface for supporting other catalog systems

## Advanced Features

### KINETIC grouper

KINETIC (Keyword-Informed, Network-Enhanced Topical Intelligence Classifier) is the primary grouper. It runs a three-stage pipeline:

1. **Keyword extraction** — KeyBERT extracts keywords from each device's metadata
2. **Co-occurrence clustering** — a Louvain graph detects communities of co-occurring keywords, forming clusters
3. **Classification** — a classifier assigns each device to a cluster; an LLM then names each cluster

#### Embedder backends

By default KINETIC loads a SentenceTransformers model locally. You can pass any `BaseEmbedder` instead:

```python
from wrench.grouper.kinetic import KINETIC
from wrench.grouper.kinetic.embedder import OpenAIEmbedder

# Local SentenceTransformers (default)
grouper = KINETIC(
    llm_config=llm_config,
    embedder="intfloat/multilingual-e5-large-instruct",
)

# Any OpenAI-compatible endpoint (OpenAI, Ollama, etc.)
grouper = KINETIC(
    llm_config=llm_config,
    embedder=OpenAIEmbedder(
        model="text-embedding-3-small",
        base_url="https://api.openai.com/v1",
        api_key="sk-...",
    ),
)

# Ollama locally
grouper = KINETIC(
    llm_config=llm_config,
    embedder=OpenAIEmbedder(
        model="nomic-embed-text",
        base_url="http://localhost:11434/v1",
    ),
)
```

#### Classifier backends

The classifier step is pluggable via the `BaseClassifier` interface. The default `EmbeddingClassifier` assigns devices by cosine similarity against cluster keyword embeddings. `JevClassifier` uses [TypeSafe's Jev model](https://typesafe.ai/jev) — a probabilistic decision model that selects the best-matching category without generating free text.

```python
from wrench.grouper.kinetic import KINETIC
from wrench.grouper.kinetic._classifier import JevClassifier

# Default: embedding-based cosine similarity (no extra API calls)
grouper = KINETIC(llm_config=llm_config)

# Jev via OpenRouter — parallel API calls, one per device
grouper = KINETIC(
    llm_config=llm_config,
    classifier=JevClassifier(
        api_key="sk-or-...",         # OpenRouter key
        model="typesafe/jev-1.13",   # default
        max_workers=20,              # parallel threads
    ),
)
```

Jev receives each device's text description as the `state` and a `choice` question whose `criteria` map cluster keys to their keyword lists. It returns which cluster best fits the device. Results are cached locally by a content hash so re-runs are free.

#### Custom classifier

Implement `BaseClassifier` to plug in any assignment logic:

```python
from wrench.grouper.kinetic._classifier import BaseClassifier, Cluster
import numpy as np

class MyClassifier(BaseClassifier):
    def classify(self, docs: list[str], clusters: list[Cluster]) -> list[np.ndarray]:
        # return a list of length len(clusters);
        # each element is an int array of doc indices assigned to that cluster
        ...

grouper = KINETIC(llm_config=llm_config, classifier=MyClassifier())
```

### Other groupers

```python
# LDA for topic modeling (no extra dependencies required)
from wrench.grouper.lda import LDAGrouper
from wrench.grouper.lda.models import LDAConfig
grouper = LDAGrouper(config=LDAConfig(n_topics=10, alpha=0.1, beta=0.01))

# BERTopic for density-based clustering (requires sentence-transformers, hdbscan, umap-learn, bertopic)
from wrench.grouper.bertopic import BERTopicGrouper
from wrench.grouper.bertopic.models import BERTopicConfig
grouper = BERTopicGrouper(config=BERTopicConfig(min_topic_size=10))
```

## Evaluation tooling

The `tools/` directory contains a CLI for running and evaluating KINETIC experiments against ground-truth datasets.

```bash
# Run an experiment (devices must be cached first)
uv run python -m tools.cli experiment run hamburg \
    --classifier jev \
    --env .env \
    --ground-truth tools/fixtures/data/hamburg_gt.json

# Switch embedding backend
uv run python -m tools.cli experiment run hamburg \
    --embedding-provider openai \
    --embedding-model nomic-embed-text \
    --embedding-base-url http://localhost:11434/v1

# Compute clustering metrics against ground truth
uv run python -m tools.cli evaluate metrics \
    tools/fixtures/data/hamburg_gt.json results.json

# Cross-tabulation: see which GT clusters leaked into which predicted clusters
uv run python -m tools.cli evaluate cross-tab \
    tools/fixtures/data/hamburg_gt.json results.json --show-devices

# Compare multiple experiments
uv run python -m tools.cli experiment compare <exp_id_1> <exp_id_2> --open-browser
```

Metrics use NMI and V-Measure. Devices that the grouper drops are penalised via a **singleton** strategy — each unclassified device becomes its own unique cluster — so a grouper cannot inflate its score by ignoring hard cases.

## Development

### Setting up the Development Environment

```bash
# Clone the repository
git clone https://github.com/urbansense/wrench.git
cd wrench

# Run the make target for full setup
make setup

# Install component dependencies for development
uv pip install -e ".[sensorthings,kinetic]"
```

### Code Style and Testing

This project follows the Ruff code style and uses comprehensive testing:

```bash
# Format and lint code
make format
make lint

# Run tests with coverage
make test

# Run specific test types
make test_unit
make test_e2e

# Type checking
make lint_types
```

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

Please ensure your code follows our coding standards and includes appropriate tests.

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## Support and Documentation

For support, please:

- Open an issue in the GitHub repository
- Check the [documentation](docs/index.md)
- Contact the development team at [jeffrey.limnardy@tum.de](mailto:jeffrey.limnardy@tum.de)

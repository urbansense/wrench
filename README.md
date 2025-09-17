# Wrench 🔧

A powerful framework for building automated sensor registration pipelines.

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-FFEE8C.svg?logo=ruff)](https://docs.astral.sh/ruff/formatter/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Overview

Wrench is a modular, extensible workflow framework designed to streamline the process of harvesting, enriching, and registering sensor metadata from diverse IoT sources into urban data catalogs. It provides a standardized pipeline architecture with interchangeable components to help make sensor data more discoverable and valuable.

## Features

- 🔄 **Automated Metadata Harvesting**: Extract metadata from various IoT data sources with minimal configuration
- 📊 **Standardized Data Models**: Type-safe data structures using Pydantic for consistent handling of metadata
- 🔍 **Advanced Classification**: Group similar sensors using machine learning and taxonomy-based approaches
- ✨ **Metadata Enrichment**: Enhance sensor descriptions with contextual information using LLM technologies
- 🏗️ **Modular Architecture**: Compose workflows from interchangeable components for maximum flexibility
- 🔌 **Extensible Interfaces**: Easily add support for new data sources and catalog systems
- 🤖 **LLM Integration**: Leverage AI capabilities for automatic content generation and classification

## Installation

```bash
pip install auto-wrench
```

To install with specific component dependencies:

```bash
# For TELEClass grouper
pip install 'auto-wrench[teleclass]'

# For SensorThings support
pip install 'auto-wrench[sensorthings]'

# For KINETIC grouper
pip install 'auto-wrench[kinetic]'

# Multiple components
pip install 'auto-wrench[teleclass,sensorthings,kinetic]'
```

## Core Components

Wrench consists of four main component types that can be combined in a pipeline:

1. **Harvesters**: Extract metadata from IoT data sources (e.g., SensorThings API)
2. **Groupers**: Classify and organize sensors into meaningful groups using various ML approaches
3. **MetadataEnrichers**: Build spatial and temporal metadata for services and sensor groups
4. **Catalogers**: Register the processed metadata into data catalogs (e.g., SDDI/CKAN)

Each component type follows a standardized interface, making it easy to extend with custom implementations.

## Quick Start

The following example sets up a complete pipeline with a SensorThings API harvester, a TELEClass grouper for classification, and an SDDI cataloger for registration:

```python
from wrench.cataloger.sddi import SDDICataloger
from wrench.grouper.teleclass import TELEClassGrouper
from wrench.harvester.sensorthings import SensorThingsHarvester
from wrench.metadataenricher.sensorthings import SensorThingsMetadataEnricher
from wrench.pipeline.sensor_pipeline import SensorRegistrationPipeline
from wrench.utils.config import LLMConfig

# Initialize components with their configurations
harvester = SensorThingsHarvester(
    base_url="https://example.org/v1.1",
    pagination_config={"page_delay": 0.2, "timeout": 60, "batch_size": 100}
)
grouper = TELEClassGrouper(config="config/teleclass_config.yaml")
metadata_enricher = SensorThingsMetadataEnricher(
    base_url="https://example.org/v1.1",
    title="City Sensor Network",
    description="Environmental sensors across the city",
    llm_config=LLMConfig(provider="openai", model="gpt-4")
)
cataloger = SDDICataloger(
    base_url="https://catalog.example.org",
    api_key="your-api-key",
    owner_org="your-organization"
)

# Assemble and run the pipeline
pipeline = SensorRegistrationPipeline(
    harvester=harvester,
    grouper=grouper,
    metadataenricher=metadata_enricher,
    cataloger=cataloger
)

result = await pipeline.run_async()
```

## Configuration

Each component can be configured via YAML files. Here's a basic example for the SensorThings harvester:

```yaml
# sta_config.yaml
base_url: "https://example.org/v1.1"
identifier: "city_sensors"
title: "City Sensor Network"
description: "Environmental sensors across the city"

pagination:
  page_delay: 0.2
  timeout: 60
  batch_size: 100
```

## Component Overview

### Harvesters

Harvesters connect to data sources and extract metadata. Wrench includes:

- **SensorThingsHarvester**: Connects to OGC SensorThings API endpoints
- Extensible base class for creating custom harvesters

### Groupers

Groupers organize sensors into logical groups using various machine learning approaches:

- **TELEClassGrouper**: Taxonomy-enhanced classification using LLMs and corpus-based methods
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

### Advanced Grouping with ML

Different groupers offer various approaches for sensor classification:

```python
from wrench.utils.config import LLMConfig

# TELEClass with taxonomy-enhanced learning
from wrench.grouper.teleclass import TELEClassGrouper
grouper = TELEClassGrouper(config="config/teleclass_config.yaml")

# KINETIC for hierarchical topic clustering
from wrench.grouper.kinetic import KINETIC
grouper = KINETIC(
    llm_config=LLMConfig(provider="openai", model="gpt-4"),
    embedder="intfloat/multilingual-e5-large-instruct",
    lang="en",
    resolution=1
)

# LDA for topic modeling
from wrench.grouper.lda import LDAGrouper
grouper = LDAGrouper(config="config/lda_config.yaml")

# BERTopic for advanced clustering
from wrench.grouper.bertopic import BERTopicGrouper
grouper = BERTopicGrouper(config="config/bertopic_config.yaml")
```

## Development

### Setting up the Development Environment

```bash
# Clone the repository
git clone https://github.com/yourusername/wrench.git
cd wrench

# Run the make target for full setup
make setup

# Install component dependencies for development
uv pip install -e ".[teleclass,sensorthings,kinetic]"
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

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support and Documentation

For support, please:

- Open an issue in the GitHub repository
- Check the [documentation](docs/README.md)
- Contact the development team at [jeffrey.limnardy@tum.de](mailto:jeffrey.limnardy@tum.de)

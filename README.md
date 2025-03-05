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
pip install 'auto-wrench[teleclass]'
```

## Core Components

Wrench consists of three main component types that can be combined in a pipeline:

1. **Harvesters**: Extract metadata from IoT data sources (e.g., SensorThings API)
2. **Groupers**: Classify and organize sensors into meaningful groups
3. **Catalogers**: Register the processed metadata into data catalogs (e.g., SDDI/CKAN)

Each component type follows a standardized interface, making it easy to extend with custom implementations.

## Quick Start

The following example sets up a complete pipeline with a SensorThings API harvester, a TELEClass grouper for classification, and an SDDI cataloger for registration:

```python
from wrench.cataloger import SDDICataloger
from wrench.common.pipeline import Pipeline
from wrench.grouper import TELEClassGrouper
from wrench.harvester import CatalogGenerator, SensorThingsHarvester
from wrench.harvester import ContentGenerator

# Initialize components with their respective configurations
harvester = SensorThingsHarvester(
    config="config/sta_config.yaml",
    content_generator=ContentGenerator(config="config/generator_config.yaml")
)

grouper = TELEClassGrouper(config="config/teleclass_config.yaml")

cataloger = SDDICataloger(config="config/sddi_config.yaml")

# Assemble and run the pipeline
pipeline = Pipeline(
    harvester=harvester,
    grouper=grouper,
    cataloger=cataloger
)

pipeline.run()
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

translator:
  url: "https://translate.example.org"
  source_lang: "de"
```

## Component Overview

### Harvesters

Harvesters connect to data sources and extract metadata. Wrench includes:

- **SensorThingsHarvester**: Connects to OGC SensorThings API endpoints
- Extensible base class for creating custom harvesters

### Groupers

Groupers organize sensors into logical groups:

- **TELEClassGrouper**: Taxonomy-enhanced classification using LLMs and corpus-based methods
- Can be extended with custom grouping algorithms

### Catalogers

Catalogers register metadata into data catalogs:

- **SDDICataloger**: Registers metadata into SDDI/CKAN-based catalogs

- Extensible interface for supporting other catalog systems

## Advanced Features

### Translation Support

Wrench includes built-in support for translating metadata using services like LibreTranslate:

```python
# Translation is configured in the harvester configuration
translator:
  url: "https://translate.example.org"
  source_lang: "auto"  # Automatically detect source language
```

### LLM-Enhanced Content Generation

Generate rich descriptions for sensor groups using LLM services:

```python
content_generator = ContentGenerator(config="config/generator_config.yaml")
harvester = SensorThingsHarvester(
    config="config/sta_config.yaml",
    content_generator=content_generator
)
```

## Development

### Setting up the Development Environment

```bash
# Clone the repository
git clone https://github.com/yourusername/wrench.git
cd wrench

# Run the make target
make setup

# Install component dependencies
uv pip install -e ".[teleclass,sensorthings]"
```

### Code Style

This project follows the Ruff code style. Format your code using:

```bash
ruff format .
ruff check .
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

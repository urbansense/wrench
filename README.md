# Wrench

Build automated sensor registration pipelines with wrench 🔧.

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-FFEE8C.svg?logo=ruff)](https://docs.astral.sh/ruff/formatter/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Features

- 🔄 Automated metadata harvesting
- 📊 Standardized data models using Pydantic
- 🔍 Rich metadata extraction and enrichment
- 🏗️ Modular workflow architecture
- 🔌 Extensible harvester interfaces

## Installation

```pip install auto-wrench```

## What is Wrench?

Wrench is a workflow framework to build pipelines for automated registration and enrichment of sensor metadata for IoT devices and sensors into data catalogs. Extract, process, and enrich metadata from various sensor data sources into various urban data catalogs.

Wrench provides generic contracts for different components so that it can be extended to harvest from different IoT data sources and register to various urban data catalogs.

The objectives of wrench are:

- Discoverability: Easier to find sensor data in data catalogs.
- Enrichment: Meaningful descriptions and metadata in catalog entries.
- Extensible: Easy to create new components to use in the pipeline.
- Ease-of-use: Reasonable default configuration, easy to setup and run.
- Automation: Fully automated workflows with LLM agents assisting registration.

## Usage

### Basic Example

The example below sets up a pipeline with a SensorThings API harvester and an SDDI catalogger, with a grouper using TELEClass classifier. More documentation on the components can be found on the documentation page.

```py
from wrench.catalogger.sddi import SDDICatalogger
from wrench.common.pipeline import Pipeline
from wrench.grouper.teleclass.core.teleclass import TELEClassGrouper
from wrench.harvester.sensorthings import SensorThingsHarvester
from wrench.harvester.sensorthings.contentgenerator import ContentGenerator
from wrench.harvester.sensorthings.models import GenericLocation

pipeline = Pipeline(
    harvester=SensorThingsHarvester(
        config="test_script/sta_config.yaml",content_generator=ContentGenerator(config="test_script/generator_config.yaml",
    ),
    grouper=TELEClassGrouper(config="test_script/teleclass_config.yaml"),
    catalogger=SDDICatalogger(config="test_script/sddi_config.yaml"),
    )
)

pipeline.run()

```

## Configuration

The system can be configured through a YAML file:

```bash
```

## Development

### Setting up the Development Environment

### Code Style

This project follows the Ruff code style. Format your code using:

```bash
ruff .
```

## Documentation

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- FROST-Server community for their excellent API documentation
- LibreTranslate for translation services
- Pydantic team for their data validation library

---

## Support

For support, please:

- Open an issue in the GitHub repository
- Check the [documentation](docs/README.md)
- Contact the development team

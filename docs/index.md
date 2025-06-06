# Welcome to Wrench Documentation

![wrench logo](./_static/logo.png)

Wrench is a modular framework for harvesting, classifying, and cataloging sensor data from various sources.

> This documentation is under active development.

## Features

* **Harvesting**: Collection of data from sensor networks (currently SensorThings API)
* **Grouping**: Classification of sensor data using taxonomy-enhanced learning (TELEClass)
* **Cataloging**: Registration of data in standardized catalogs (SDDI)

## Components

The framework is composed of three main components:

**Harvester**
   Fetches data from different sources. Currently implemented for SensorThings API.

**Grouper**
   Classifies data. Includes the TELEClass system for taxonomy-enhanced classification.

**Cataloger**
   Registers data in catalog systems. Currently supports SDDI catalogs.

## Getting Started

### Installation

The wrench framework is built in Python and can be installed using pip, uv or any other Python package manager of your choice.

Using pip
```pip install auto-wrench```

If you want to use certain components, which require their own dependencies, you can install the package with optional dependencies.
```pip install auto-wrench["component-1,component-2"]```

### Basic Usage

The framework provides full-fledged pipelines with predefined components which can be used. Here is a simple usage example of the `SensorRegistrationPipeline`.

```python
from wrench.pipeline.sensor_pipeline import SensorRegistrationPipeline

pipeline = SensorRegistrationPipeline(
    harvester=harvester, # an implementation of BaseHarvester
    grouper=grouper, # an implementation of BaseGrouper
    metadataenricher=metadataenricher, # an implementation of BaseMetadataEnricher
    cataloger=cataloger, # an implementation of BaseCataloger
)

result = await pipeline.run()

```

The `SensorRegistrationPipeline` accepts any implementation of each component, as long as they adhere to the base interfaces.

## Architecture

### System Architecture

The framework is designed for it to be extensible, so that it's easy for users to develop their own components. It provides base interfaces for its main components such as the Harvester, Grouper, MetadataBuider, and Cataloger.

The Pipeline allows for users to orchestrate their own sequence of components, this sequence has to conform to a [direct acyclic graph](https://www.ibm.com/think/topics/directed-acyclic-graph) (DAG). Additionally, the pipeline validates the input/outputs of each component to make sure that they are compatible.

The pipeline can be defined with an optional store, which if provided, will persist the results of the pipeline components over runs, enabling incremental operations, throughout subsequent pipelines runs.

## Component Documentation

### Core Components

   components/harvester
   components/grouper
   components/cataloger

## API Reference

### API Documentation

   api/harvester
   api/grouper
   api/cataloger

   api/common

## Examples and Tutorials

### Examples

   examples/sensorthings
   examples/teleclass
   examples/sddi
   examples/custom_pipeline

## Contributing

### Development

   contributing/setup
   contributing/guidelines
   contributing/testing

## Indices and Tables

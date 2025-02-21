# SensorThings Harvester Documentation

## Overview

The SensorThings Harvester is a component designed to retrieve and process data from SensorThings API endpoints. It provides functionality for fetching sensor data, locations, and enriching metadata about the data source.

## Key Features

- Paginated data retrieval from SensorThings API endpoints
- Support for customizable location models
- Optional translation service integration
- Automatic calculation of geographic extent and timeframes
- Configurable pagination behavior

## Architecture

### Core Components

#### 1. SensorThingsHarvester

The main class that orchestrates the harvesting process. It handles:

- Data retrieval from the API
- Metadata enrichment
- Geographic calculations
- Timeframe determinations

#### 2. Models

- **Thing**: Represents a SensorThings API Thing entity
- **Datastream**: Represents a data stream from a sensor
- **Location**: Represents geographic location information
- **Sensor**: Represents sensor metadata

#### 3. Configuration

The harvester uses a YAML-based configuration system with the following structure:

```yaml
base_url: "https://your-sensorthings-api.com"
identifier: "unique_identifier"
title: "API Title"
description: "API Description"
translator:
  url: "translation-service-url"
  source_lang: "source-language-code"
pagination:
  page_delay: 0.1
  timeout: 60
  batch_size: 100
default_limit: -1
```

## Usage

### Basic Usage

```python
from wrench.harvester.sensorthings import SensorThingsHarvester

# Initialize with config file
harvester = SensorThingsHarvester("config.yaml")

# Fetch data with optional limit
metadata, things = harvester.enrich(limit=20)
```

### Custom Location Model

You can create custom location models by extending the GenericLocation class:

```python
from pydantic import BaseModel
from wrench.harvester.sensorthings import GenericLocation

class CustomLocation(GenericLocation):
    location: dict  # Custom location structure

    def get_coordinates(self) -> tuple[float, float]:
        # Implement custom coordinate extraction
        return (self.location['lon'], self.location['lat'])

# Use custom location model
harvester = SensorThingsHarvester(
    config="config.yaml",
    location_model=CustomLocation
)
```

### Translation Integration

The harvester supports automatic translation of text fields using a translation service:

```yaml
# In your config.yaml
translator:
  url: "http://translate-service.com"
  source_lang: "de" # Source language code
```

When configured, the harvester will automatically translate:

- Thing names and descriptions
- Datastream information
- Sensor descriptions
- Properties

## Configuration Options

### Main Configuration

| Parameter     | Type             | Description                           | Default  |
| ------------- | ---------------- | ------------------------------------- | -------- |
| base_url      | str              | Base URL for the SensorThings server  | Required |
| identifier    | str              | Unique identifier for the data source | Required |
| title         | str              | Title for the API service             | Required |
| description   | str              | Description of the API service        | Required |
| translator    | TranslatorConfig | Translation service configuration     | Optional |
| pagination    | PaginationConfig | Pagination settings                   | Optional |
| default_limit | int              | Default fetch limit (-1 for no limit) | -1       |

### Pagination Configuration

| Parameter  | Type  | Description                                 | Default |
| ---------- | ----- | ------------------------------------------- | ------- |
| page_delay | float | Delay between pagination requests (seconds) | 0.1     |
| timeout    | int   | Request timeout in seconds                  | 60      |
| batch_size | int   | Number of items per page                    | 100     |

## Error Handling

The harvester implements comprehensive error handling:

```python
try:
    metadata, things = harvester.enrich()
except HarvesterError as e:
    # Handle harvester-specific errors
    print(f"Harvesting failed: {e}")
except Exception as e:
    # Handle general errors
    print(f"Unexpected error: {e}")
```

## Data Structures

### Metadata Output

The harvester returns CommonMetadata containing:

- Endpoint URL
- Spatial extent
- Temporal extent
- Source type
- Last update time
- Other relevant metadata

### Thing Entity Structure

```python
class Thing:
    id: int
    name: str
    description: str
    properties: dict
    datastreams: list[Datastream]
    location: list[Location]
```

## Best Practices

1. **Configuration Management**

   - Keep configuration in separate YAML files
   - Use environment variables for sensitive information
   - Validate configuration before use

2. **Error Handling**

   - Always implement proper error handling
   - Log errors appropriately
   - Provide meaningful error messages

3. **Performance Optimization**

   - Use appropriate pagination settings
   - Implement reasonable timeouts
   - Consider rate limiting for large datasets

4. **Data Validation**
   - Validate input configuration
   - Verify API responses
   - Check geographic coordinates

## Common Issues and Solutions

### Connection Issues

```python
harvester = SensorThingsHarvester("config.yaml")
try:
    metadata, things = harvester.enrich()
except requests.RequestException as e:
    logger.error(f"Connection failed: {e}")
    # Implement retry logic or fallback
```

### Data Validation

```python
# Validate geographic extent
if metadata.spatial_extent:
    for coordinate in metadata.spatial_extent:
        if not (-180 <= coordinate.longitude <= 180 and
                -90 <= coordinate.latitude <= 90):
            logger.warning(f"Invalid coordinate: {coordinate}")
```

## Contributing

When contributing to the harvester component:

1. Follow the existing code style
2. Add appropriate tests
3. Update documentation
4. Handle errors gracefully
5. Use type hints
6. Include logging

## Testing

The harvester includes comprehensive tests:

```python
def test_fetch_things():
    harvester = SensorThingsHarvester("test_config.yaml")
    metadata, things = harvester.enrich(limit=5)
    assert len(things) == 5
    assert all(isinstance(thing, Thing) for thing in things)
```

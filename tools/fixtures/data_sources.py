"""Known SensorThings data sources for testing."""

from dataclasses import dataclass


@dataclass
class DataSource:
    """Configuration for a SensorThings data source."""

    name: str
    base_url: str
    identifier: str
    title: str
    description: str


# Known SensorThings servers for testing
KNOWN_SOURCES = {
    "hamburg": DataSource(
        name="hamburg",
        base_url="https://iot.hamburg.de/v1.1",
        identifier="hamburg_frost_server",
        title="City of Hamburg FROST Server",
        description="The FROST Server of the City of Hamburg comprises of various urban sensors around the city with a focus on mobility.",
    ),
    "osnabrueck": DataSource(
        name="osnabrueck",
        base_url="https://daten-api.osnabrueck.de/v1.1",
        identifier="osnabrueck_frost_server",
        title="City of Osnabrück FROST Server",
        description="The FROST Server of the City of Osnabrück comprises of various urban sensors around the city.",
    ),
    "muenchen": DataSource(
        name="muenchen",
        base_url="https://cut.gis.lrg.tum.de/frost/v1.1",
        identifier="muenchen_frost_server",
        title="City of München FROST Server",
        description="City of München FROST Server containing data collected from urban sensors around the city.",
    ),
}


def get_source(name: str) -> DataSource:
    """Get a data source by name.

    Args:
        name: Name of the data source

    Returns:
        DataSource configuration

    Raises:
        ValueError: If source name is unknown
    """
    if name not in KNOWN_SOURCES:
        available = ", ".join(KNOWN_SOURCES.keys())
        raise ValueError(f"Unknown data source: {name}. Available sources: {available}")
    return KNOWN_SOURCES[name]


def list_sources() -> list[str]:
    """List all available data source names.

    Returns:
        List of source names
    """
    return list(KNOWN_SOURCES.keys())

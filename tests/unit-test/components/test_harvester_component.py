import pytest

from wrench.components.harvester import Harvester
from wrench.components.types import Items


class MockBaseHarvester:
    """Mock harvester for testing."""

    def __init__(self, items=None):
        self.items = items if items is not None else []

    def return_items(self):
        return self.items


@pytest.mark.asyncio
async def test_harvester_component_basic():
    """Test the basic functionality of the Harvester component."""
    # Create mock base harvester
    mock_harvester = MockBaseHarvester(items=[{"id": 1, "name": "Test Device"}])

    # Create component
    harvester_component = Harvester(harvester=mock_harvester)

    # Run component
    result = await harvester_component.run()

    # Verify result is Items instance with correct data
    assert isinstance(result, Items)
    assert result.devices == mock_harvester.items
    assert len(result.devices) == 1
    assert result.devices[0]["id"] == 1
    assert result.devices[0]["name"] == "Test Device"


@pytest.mark.asyncio
async def test_harvester_component_empty():
    """Test harvester component with empty results."""
    # Create mock base harvester
    mock_harvester = MockBaseHarvester(items=[])

    # Create component
    harvester_component = Harvester(harvester=mock_harvester)

    # Run component
    result = await harvester_component.run()

    # Verify result
    assert isinstance(result, Items)
    assert result.devices == []
    assert len(result.devices) == 0


@pytest.mark.asyncio
async def test_harvester_component_multiple_items():
    """Test harvester component with multiple items."""
    # Create mock data with multiple items
    mock_items = [
        {"id": 1, "name": "Device 1", "type": "sensor"},
        {"id": 2, "name": "Device 2", "type": "actuator"},
        {"id": 3, "name": "Device 3", "type": "sensor"},
    ]

    # Create mock base harvester
    mock_harvester = MockBaseHarvester(items=mock_items)

    # Create component
    harvester_component = Harvester(harvester=mock_harvester)

    # Run component
    result = await harvester_component.run()

    # Verify result
    assert isinstance(result, Items)
    assert result.devices == mock_items
    assert len(result.devices) == 3

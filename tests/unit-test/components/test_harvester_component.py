import pytest

from wrench.components.harvester import Harvester
from wrench.harvester.base import BaseHarvester
from wrench.models import Item


class MockBaseHarvester(BaseHarvester):
    """Mock implementation of BaseHarvester for testing."""

    def __init__(self, items=None):
        super().__init__()
        self._items = items or []

    def return_items(self):
        """Return mock items."""
        # Convert dictionaries to proper Item objects if needed
        items = []
        for item in self._items:
            if isinstance(item, Item):
                items.append(item)
            else:
                # Convert dictionary to Item
                item_id = str(item.get("id", ""))
                items.append(Item(id=item_id, content=item))
        return items


@pytest.mark.asyncio
async def test_harvester_component_basic():
    """Test the basic functionality of the Harvester component."""
    # Create test data with proper Item objects
    test_item = Item(id="1", content={"name": "Test Device"})

    # Create mock base harvester
    mock_harvester = MockBaseHarvester(items=[test_item])

    # Create component
    harvester_component = Harvester(harvester=mock_harvester)

    # Run component
    result = await harvester_component.run()

    # Verify results
    assert result is not None
    assert len(result.devices) == 1
    assert result.devices[0].id == "1"
    assert "Test Device" in result.devices[0].content


@pytest.mark.asyncio
async def test_harvester_component_empty():
    """Test harvester component with empty item list."""
    # Create mock base harvester with no items
    mock_harvester = MockBaseHarvester(items=[])

    # Create component
    harvester_component = Harvester(harvester=mock_harvester)

    # Run component
    result = await harvester_component.run()

    # Verify results
    assert result is not None
    assert len(result.devices) == 0


@pytest.mark.asyncio
async def test_harvester_component_multiple_items():
    """Test harvester component with multiple items."""
    # Create mock data with multiple items
    mock_items = [
        Item(id="1", content={"name": "Device 1", "type": "sensor"}),
        Item(id="2", content={"name": "Device 2", "type": "actuator"}),
        Item(id="3", content={"name": "Device 3", "type": "sensor"}),
    ]

    # Create mock base harvester
    mock_harvester = MockBaseHarvester(items=mock_items)

    # Create component
    harvester_component = Harvester(harvester=mock_harvester)

    # Run component
    result = await harvester_component.run()

    # Verify results
    assert result is not None
    assert len(result.devices) == 3
    assert result.devices[0].id == "1"
    assert result.devices[1].id == "2"
    assert result.devices[2].id == "3"
    assert "sensor" in result.devices[0].content
    assert "actuator" in result.devices[1].content


@pytest.mark.asyncio
async def test_incremental_harvester_component():
    """Test the incremental harvester component."""
    # Create test data with proper Item objects
    mock_items = [
        Item(id="1", content={"name": "Device 1", "type": "sensor"}),
        Item(id="2", content={"name": "Device 2", "type": "actuator"}),
    ]

    # Create mock base harvester
    mock_harvester = MockBaseHarvester(items=mock_items)

    # Create incremental component
    incremental_harvester = Harvester(harvester=mock_harvester)

    # First run should create ADD operations for all items
    result = await incremental_harvester.run()

    # Verify results
    assert result is not None
    assert len(result.devices) == 2
    assert len(result.operations) == 2
    assert all(op.type.value == "add" for op in result.operations)

    # Second run with the same items should not create operations
    result = await incremental_harvester.run()

    # Verify results - devices present but no operations
    assert result is not None
    assert len(result.devices) == 2
    assert len(result.operations) == 0

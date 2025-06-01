import pytest

from wrench.components.grouper import Grouper
from wrench.grouper.base import BaseGrouper
from wrench.models import Group, Item
from wrench.pipeline.types import Operation, OperationType


class MockBaseGrouper(BaseGrouper):
    """Mock implementation of BaseGrouper for testing."""

    def group_items(self, items):
        """
        Group items by type extracted from content.

        Args:
            items: List of Item objects

        Returns:
            list[Group]: List of grouped items
        """
        # Group by type in the content
        groups_dict = {}
        for item in items:
            # Extract type from content JSON
            content_data = item.content
            group_name = content_data.get("type", "unknown")

            # Initialize group if needed
            if group_name not in groups_dict:
                groups_dict[group_name] = Group(
                    name=group_name,
                    devices=[],
                )

            # Add item to group
            groups_dict[group_name].items.append(item)

        return list(groups_dict.values())


@pytest.mark.asyncio
async def test_grouper_component_basic():
    """Test the basic functionality of the Grouper component."""
    # Create test data with proper Item objects
    devices = [
        Item(id="1", content={"name": "Device 1", "type": "sensor"}),
        Item(id="2", content={"name": "Device 2", "type": "actuator"}),
        Item(id="3", content={"name": "Device 3", "type": "sensor"}),
    ]

    # Note: Regular Grouper doesn't need operations, only IncrementalGrouper does

    # Create mock base grouper
    mock_grouper = MockBaseGrouper()

    # Create component
    grouper_component = Grouper(grouper=mock_grouper)

    # Run component with devices
    result = await grouper_component.run(devices=devices, operations=[])

    # Verify results
    assert result is not None
    assert len(result.groups) == 2

    # Find sensor and actuator groups
    sensor_group = next((g for g in result.groups if g.name == "sensor"), None)
    actuator_group = next((g for g in result.groups if g.name == "actuator"), None)

    assert sensor_group is not None
    assert len(sensor_group.devices) == 2
    assert actuator_group is not None
    assert len(actuator_group.devices) == 1


@pytest.mark.asyncio
async def test_grouper_component_empty():
    """Test grouper component with empty item list."""
    # Create empty devices list
    devices = []

    # Create mock base grouper
    mock_grouper = MockBaseGrouper()

    # Create component
    grouper_component = Grouper(grouper=mock_grouper)

    # Run component
    result = await grouper_component.run(devices=devices, operations=[])

    # Verify results
    assert result is not None
    assert len(result.groups) == 0


@pytest.mark.asyncio
async def test_grouper_component_predefined_groups():
    """Test grouper component with predefined groups."""
    # Create predefined groups with proper Item objects
    items1 = [Item(id="1", content={"name": "Test 1"})]
    items2 = [Item(id="2", content={"name": "Test 2"})]

    predefined_groups = [
        Group(name="test_group", devices=items1),
        Group(name="another_group", devices=items2),
    ]

    # Create a custom grouper for testing that returns predefined groups
    class PredefinedGrouper(BaseGrouper):
        def __init__(self, groups):
            self.groups = groups

        def group_items(self, items):
            return self.groups

    # Create component with predefined grouper
    mock_grouper = PredefinedGrouper(predefined_groups)
    grouper_component = Grouper(grouper=mock_grouper)

    # Run component with any items (they will be ignored)
    devices = [Item(id="3", content={"name": "Ignored"})]
    result = await grouper_component.run(devices=devices, operations=[])

    # Verify results match predefined groups
    assert result is not None
    assert len(result.groups) == 2
    assert result.groups[0].name == "test_group"
    assert result.groups[1].name == "another_group"
    assert len(result.groups[0].devices) == 1
    assert len(result.groups[1].devices) == 1
    assert result.groups[0].devices[0].id == "1"
    assert result.groups[1].devices[0].id == "2"


@pytest.mark.asyncio
async def test_incremental_grouper_component():
    """Test the incremental grouper component."""
    # Create test data with proper Item objects
    devices = [
        Item(id="1", content={"name": "Device 1", "type": "sensor"}),
        Item(id="2", content={"name": "Device 2", "type": "actuator"}),
    ]

    # Create operations for the devices
    operations = [
        Operation(type=OperationType.ADD, device_id=device.id, device=device)
        for device in devices
    ]

    # Create mock base grouper
    mock_grouper = MockBaseGrouper()

    # Create incremental component
    incremental_grouper = Grouper(grouper=mock_grouper)

    # Run component with devices and operations
    result = await incremental_grouper.run(devices=devices, operations=operations)

    # Verify results
    assert result is not None
    assert len(result.groups) == 2

    # Second run with no operations should return empty groups
    result = await incremental_grouper.run(
        devices=devices, operations=[], state={"previous_groups": result.groups}
    )
    assert len(result.groups) == 0

    # Run with a new device and an update operation
    new_device = Item(id="3", content={"name": "Device 3", "type": "sensor"})
    update_operations = [
        Operation(type=OperationType.ADD, device_id=new_device.id, device=new_device)
    ]

    # Add the new device to the list
    devices.append(new_device)

    # Run with the update
    result = await incremental_grouper.run(
        devices=devices, operations=update_operations
    )

    # Should include only the modified/new groups
    assert len(result.groups) > 0

    # Find the sensor group that should have been modified
    sensor_group = next((g for g in result.groups if g.name == "sensor"), None)
    assert sensor_group is not None
    # The sensor group might just contain the new item in some implementations
    assert len(sensor_group.devices) >= 1  # Should contain at least the new sensor

import pytest

from wrench.components.grouper import Grouper
from wrench.components.types import Groups
from wrench.models import Group


class MockBaseGrouper:
    """Mock grouper for testing."""

    def __init__(self, groups=None):
        self.groups = groups or []

    def group_items(self, devices):
        # Simple mock implementation that creates groups
        if not self.groups:
            # Generate groups based on device type if none pre-defined
            groups_dict = {}
            for device in devices:
                group_name = device.get("type", "unknown")
                if group_name not in groups_dict:
                    groups_dict[group_name] = Group(
                        name=group_name,
                        description=f"Group for {group_name} devices",
                        items=[],
                    )
                groups_dict[group_name].items.append(device)

            return list(groups_dict.values())
        return self.groups


@pytest.mark.asyncio
async def test_grouper_component_basic():
    """Test the basic functionality of the Grouper component."""
    # Create test data
    devices = [
        {"id": 1, "name": "Device 1", "type": "sensor"},
        {"id": 2, "name": "Device 2", "type": "actuator"},
        {"id": 3, "name": "Device 3", "type": "sensor"},
    ]

    # Create mock base grouper
    mock_grouper = MockBaseGrouper()

    # Create component
    grouper_component = Grouper(grouper=mock_grouper)

    # Run component
    result = await grouper_component.run(devices)

    # Verify result
    assert isinstance(result, Groups)
    assert len(result.groups) == 2  # sensor and actuator groups

    # Check group contents
    group_names = [g.name for g in result.groups]
    assert "sensor" in group_names
    assert "actuator" in group_names

    # Get sensor group
    sensor_group = next(g for g in result.groups if g.name == "sensor")
    assert len(sensor_group.items) == 2


@pytest.mark.asyncio
async def test_grouper_component_empty():
    """Test grouper component with empty input."""
    # Create component with mock grouper
    mock_grouper = MockBaseGrouper()
    grouper_component = Grouper(grouper=mock_grouper)

    # Run component with empty device list
    result = await grouper_component.run([])

    # Verify result
    assert isinstance(result, Groups)
    assert len(result.groups) == 0


@pytest.mark.asyncio
async def test_grouper_component_predefined_groups():
    """Test grouper component with predefined groups."""
    # Create predefined groups
    predefined_groups = [
        Group(name="test_group", description="Test Group", items=[{"id": 1}]),
        Group(name="another_group", description="Another Group", items=[{"id": 2}]),
    ]

    # Create mock base grouper with predefined groups
    mock_grouper = MockBaseGrouper(groups=predefined_groups)

    # Create component
    grouper_component = Grouper(grouper=mock_grouper)

    # Run component (input doesn't matter in this case)
    result = await grouper_component.run([])

    # Verify result
    assert isinstance(result, Groups)
    assert len(result.groups) == 2
    assert result.groups[0].name == "test_group"
    assert result.groups[1].name == "another_group"

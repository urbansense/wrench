from unittest.mock import Mock

import pytest

from wrench.models import CommonMetadata, Group


@pytest.fixture
def sample_devices():
    """Sample device data for testing."""
    return [
        {"id": 1, "name": "Device 1", "type": "sensor"},
        {"id": 2, "name": "Device 2", "type": "actuator"},
        {"id": 3, "name": "Device 3", "type": "sensor"},
    ]


@pytest.fixture
def sample_groups(sample_devices):
    """Sample group data for testing."""
    groups = [
        Group(
            name="sensors",
            description="Group of sensors",
            items=[d for d in sample_devices if d["type"] == "sensor"],
        ),
        Group(
            name="actuators",
            description="Group of actuators",
            items=[d for d in sample_devices if d["type"] == "actuator"],
        ),
    ]
    return groups


@pytest.fixture
def sample_metadata():
    """Sample metadata for testing."""
    return CommonMetadata(
        title="Test Service",
        description="This is a test service",
        identifier="test-service-id",
        keywords=["test", "service"],
        license="MIT",
    )


@pytest.fixture
def sample_group_metadata():
    """Sample group metadata for testing."""
    return [
        CommonMetadata(
            title="Sensor Group",
            description="Group of sensors",
            identifier="sensor-group-id",
            keywords=["sensors"],
        ),
        CommonMetadata(
            title="Actuator Group",
            description="Group of actuators",
            identifier="actuator-group-id",
            keywords=["actuators"],
        ),
    ]


@pytest.fixture
def mock_base_harvester():
    """Mock base harvester."""
    harvester = Mock()
    harvester.return_items.return_value = [
        {"id": 1, "name": "Device 1", "type": "sensor"},
        {"id": 2, "name": "Device 2", "type": "actuator"},
    ]
    return harvester


@pytest.fixture
def mock_base_grouper():
    """Mock base grouper."""
    grouper = Mock()
    grouper.group_items.return_value = [
        Group(name="group1", description="Group 1", items=[{"id": 1}]),
        Group(name="group2", description="Group 2", items=[{"id": 2}]),
    ]
    return grouper


@pytest.fixture
def mock_base_metadata_builder():
    """Mock base metadata builder."""
    builder = Mock()
    builder.build_service_metadata.return_value = CommonMetadata(
        title="Test Service", description="Test service", identifier="test-id"
    )
    builder.build_group_metadata.side_effect = lambda group: CommonMetadata(
        title=f"Group: {group.name}",
        description=f"Description for {group.name}",
        identifier=f"group-{group.name}",
    )
    return builder


@pytest.fixture
def mock_base_cataloger():
    """Mock base cataloger."""
    cataloger = Mock()
    cataloger.register.return_value = True
    return cataloger

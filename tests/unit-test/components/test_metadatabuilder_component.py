import json

import pytest

from wrench.components.metadatabuilder import MetadataBuilder
from wrench.metadatabuilder.base import BaseMetadataBuilder
from wrench.models import CommonMetadata, Group, Item
from wrench.pipeline.types import Operation, OperationType


class MockBaseMetadataBuilder(BaseMetadataBuilder):
    """Mock implementation of BaseMetadataBuilder for testing."""

    def build_service_metadata(self, source_data):
        """Build mock service metadata."""
        return CommonMetadata(
            endpoint_url="http://test.com",
            source_type="test",
            title="Test Service",
            description="Test Description",
            identifier="test-service",
        )

    def build_group_metadata(self, group):
        """Build mock group metadata."""
        return CommonMetadata(
            endpoint_url=f"http://test.com/group/{group.name}",
            source_type="test",
            title=f"Group: {group.name}",
            description=f"Group Description: {group.name}",
            identifier=f"group-{group.name}",
        )


@pytest.mark.asyncio
async def test_metadatabuilder_component_basic():
    """Test the basic functionality of the MetadataBuilder component."""
    # Create test data with proper Item objects instead of dictionaries
    devices = [
        Item(id="1", content=json.dumps({"name": "Device 1"})),
        Item(id="2", content=json.dumps({"name": "Device 2"})),
    ]

    # Create operations for these items
    operations = [
        Operation(type=OperationType.ADD, item_id="1", item=devices[0]),
        Operation(type=OperationType.ADD, item_id="2", item=devices[1]),
    ]

    # Create groups with Item objects
    groups = [
        Group(name="group1", items=[devices[0]]),
        Group(name="group2", items=[devices[1]]),
    ]

    # Create mock base metadata builder
    mock_builder = MockBaseMetadataBuilder()

    # Create component
    metadata_builder_component = MetadataBuilder(metadatabuilder=mock_builder)

    # Run component
    result = await metadata_builder_component.run(
        devices=devices, operations=operations, groups=groups
    )

    # Verify results
    assert result.service_metadata is not None
    assert result.service_metadata.title == "Test Service"
    assert len(result.group_metadata) == 2
    assert result.group_metadata[0].title == "Group: group1"
    assert result.group_metadata[1].title == "Group: group2"


@pytest.mark.asyncio
async def test_metadatabuilder_component_empty_groups():
    """Test metadata builder with empty group list."""
    # Create test data with proper Item objects
    devices = [Item(id="1", content=json.dumps({"name": "Device 1"}))]

    # Create operations for the items
    operations = [
        Operation(type=OperationType.ADD, item_id="1", item=devices[0]),
    ]

    # Empty groups list
    groups = []

    # Create mock base metadata builder
    mock_builder = MockBaseMetadataBuilder()

    # Create component
    metadata_builder_component = MetadataBuilder(metadatabuilder=mock_builder)

    # Run component with named parameters
    result = await metadata_builder_component.run(
        devices=devices, operations=operations, groups=groups
    )

    # Verify results
    assert result.service_metadata is not None
    assert result.service_metadata.title == "Test Service"
    assert len(result.group_metadata) == 0


@pytest.mark.asyncio
async def test_metadatabuilder_component_custom_metadata():
    """Test metadata builder with custom metadata."""
    # Create test data with proper Item objects
    devices = [Item(id="1", content=json.dumps({"name": "Device 1"}))]

    # Create operations for the items
    operations = [
        Operation(type=OperationType.ADD, item_id="1", item=devices[0]),
    ]

    # Create a group with an Item
    groups = [Group(name="custom", items=devices)]

    # Create a custom metadata builder that returns specific metadata
    class CustomMetadataBuilder(BaseMetadataBuilder):
        def build_service_metadata(self, source_data):
            return CommonMetadata(
                endpoint_url="http://custom.com",
                source_type="custom",
                title="Custom Service",
                description="Custom Description",
                identifier="custom-service",
                tags=["tag1", "tag2"],
            )

        def build_group_metadata(self, group):
            return CommonMetadata(
                endpoint_url=f"http://custom.com/group/{group.name}",
                source_type="custom",
                title=f"Custom Group: {group.name}",
                description=f"Custom Group Description: {group.name}",
                identifier=f"custom-group-{group.name}",
                tags=["group-tag"],
            )

    # Create component with custom builder
    metadata_builder_component = MetadataBuilder(
        metadatabuilder=CustomMetadataBuilder()
    )

    # Run component
    result = await metadata_builder_component.run(
        devices=devices, operations=operations, groups=groups
    )

    # Verify results
    assert result.service_metadata is not None
    assert result.service_metadata.title == "Custom Service"
    assert len(result.service_metadata.tags) == 2
    assert "tag1" in result.service_metadata.tags
    assert len(result.group_metadata) == 1
    assert result.group_metadata[0].title == "Custom Group: custom"
    assert "group-tag" in result.group_metadata[0].tags

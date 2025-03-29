from unittest.mock import Mock

import pytest

from wrench.components.cataloger import Cataloger
from wrench.components.grouper import Grouper
from wrench.components.harvester import Harvester
from wrench.components.metadatabuilder import MetadataBuilder
from wrench.models import CommonMetadata, Group, Item
from wrench.pipeline.types import Operation, OperationType


@pytest.mark.asyncio
async def test_harvester_with_failing_base_harvester():
    """Test harvester component with a failing base harvester."""

    # Create a mock harvester that raises an exception
    class FailingMockHarvester:
        def return_items(self):
            raise ValueError("Failed to harvest items")

    # Create component
    harvester_component = Harvester(harvester=FailingMockHarvester())

    # Should propagate the error
    with pytest.raises(ValueError, match="Failed to harvest items"):
        await harvester_component.run()


@pytest.mark.asyncio
async def test_grouper_with_failing_base_grouper():
    """Test grouper component with a failing base grouper."""

    # Create a mock grouper that raises an exception
    class FailingMockGrouper:
        def group_items(self, devices):
            raise ValueError("Failed to group items")

    # Create component
    grouper_component = Grouper(grouper=FailingMockGrouper())

    # Create valid Item objects to test with
    devices = [Item(id="1", content={"name": "Device 1"})]

    # Should propagate the error
    with pytest.raises(ValueError, match="Failed to group items"):
        await grouper_component.run(devices=devices, operations=[])


@pytest.mark.asyncio
async def test_metadatabuilder_with_empty_inputs():
    """Test metadata builder with empty inputs."""

    # Create a metadata builder that returns valid metadata
    class TestMetadataBuilder:
        def build_service_metadata(self, devices):
            return CommonMetadata(
                endpoint_url="http://test-url.com/",
                source_type="mock-source",
                title="Empty Service",
                description="Service with no devices",
                identifier="empty-service",
            )

        def build_group_metadata(self, group):
            return CommonMetadata(
                endpoint_url=f"http://test-url.com/group/{group.name}",
                source_type="mock-source",
                title=f"Empty Group {group.name}",
                description="Empty group",
                identifier=f"empty-group-{group.name}",
            )

    # Create component
    metadata_builder_component = MetadataBuilder(metadatabuilder=TestMetadataBuilder())

    # Test with empty operations (should return None for service_metadata)
    devices = [Item(id="1", content={"name": "Device 1"})]
    empty_ops_result = await metadata_builder_component.run(
        devices=devices, operations=[], groups=[]
    )

    # Verify early return behavior with empty operations
    assert empty_ops_result.service_metadata is None
    assert len(empty_ops_result.group_metadata) == 0

    # Test with non-empty operations (should call the builder methods)
    operations = [Operation(type=OperationType.ADD, item_id="1", item=devices[0])]
    result = await metadata_builder_component.run(
        devices=devices, operations=operations, groups=[]
    )

    # Verify normal behavior with operations
    assert result.service_metadata is not None
    assert result.service_metadata.title == "Empty Service"
    assert len(result.group_metadata) == 0


@pytest.mark.asyncio
async def test_validate_call_validation():
    """Test that @validate_call validation works correctly."""
    # Create a component with a mock harvester
    mock_harvester = Mock()
    mock_harvester.return_items.return_value = []
    harvester_component = Harvester(harvester=mock_harvester)

    # This should work fine
    await harvester_component.run()

    # Create a component with a mock grouper
    mock_grouper = Mock()
    mock_grouper.group_items.return_value = []
    grouper_component = Grouper(grouper=mock_grouper)

    # Valid Items list
    valid_items = [Item(id="1", content={"name": "Device 1"})]

    # This should work fine (proper Item list input)
    await grouper_component.run(devices=valid_items, operations=[])

    # This should raise a validation error (wrong input type)
    with pytest.raises(Exception):
        await grouper_component.run(devices="not a list")


@pytest.mark.asyncio
async def test_cataloger_with_invalid_inputs():
    """Test cataloger with invalid inputs."""
    mock_cataloger = Mock()
    cataloger_component = Cataloger(cataloger=mock_cataloger)

    # Test with valid service metadata but None for groups
    service_metadata = CommonMetadata(
        endpoint_url="http://test-url.com/",
        source_type="mock-source",
        title="Test Service",
        description="Test service",
        identifier="test-service",
    )

    # This should work (empty list)
    result = await cataloger_component.run(
        service_metadata=service_metadata, group_metadata=[]
    )
    assert result.success is True
    assert len(result.groups) == 0

    # But None instead of list should raise validation error
    with pytest.raises(Exception):
        await cataloger_component.run(
            service_metadata=service_metadata, group_metadata=None
        )


@pytest.mark.asyncio
async def test_incremental_harvester_empty_results():
    """Test IncrementalHarvester when base harvester returns empty results."""

    # Create a mock harvester that returns an empty list
    class EmptyHarvester:
        def return_items(self):
            return []

    # Create component
    incremental_harvester = Harvester(harvester=EmptyHarvester())

    # Should return empty results without error
    result = await incremental_harvester.run()
    assert len(result.devices) == 0
    assert len(result.operations) == 0


@pytest.mark.asyncio
async def test_grouper_edge_cases():
    """Test grouper with various edge cases."""

    # Create a mock grouper
    class EdgeCaseGrouper:
        def group_items(self, items):
            # Group by ID for simplicity
            groups = {}
            for item in items:
                group_name = f"Group-{item.id}"
                if group_name not in groups:
                    groups[group_name] = Group(name=group_name, items=[])
                groups[group_name].items.append(item)
            return list(groups.values())

    # Create component
    grouper_component = Grouper(grouper=EdgeCaseGrouper())

    # Test with empty list
    result = await grouper_component.run(devices=[], operations=[])
    assert len(result.groups) == 0

    # Test with single item
    single_item = [Item(id="1", content={"name": "Single Item"})]
    result = await grouper_component.run(devices=single_item, operations=[])
    print(result)
    assert len(result.groups) == 1
    assert result.groups[0].name == "Group-1"

    # Test with duplicate IDs (should be grouped together)
    duplicate_items = [
        Item(id="dup", content={"name": "Duplicate 1"}),
        Item(id="dup", content={"name": "Duplicate 2"}),
    ]
    result = await grouper_component.run(
        devices=duplicate_items,
        operations=[
            Operation(type=OperationType.ADD, item_id=item.id, item=item)
            for item in duplicate_items
        ],
    )
    print(result)
    assert len(result.groups) == 1
    assert len(result.groups[0].items) == 2

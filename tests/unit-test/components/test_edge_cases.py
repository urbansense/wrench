from unittest.mock import Mock, patch

import pytest

from wrench.components.cataloger import Cataloger
from wrench.components.grouper import Grouper
from wrench.components.harvester import Harvester
from wrench.components.metadatabuilder import MetadataBuilder
from wrench.models import CommonMetadata


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

    # Should propagate the error
    with pytest.raises(ValueError, match="Failed to group items"):
        await grouper_component.run([{"id": 1}])


@pytest.mark.asyncio
async def test_metadatabuilder_with_empty_inputs():
    """Test metadata builder with empty inputs."""

    class MinimalMockMetadataBuilder:
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
                endpoint_url="http://test-url.com/",
                source_type="mock-source",
                title=f"Empty Group {group.name}",
                description="Empty group",
                identifier=f"empty-group-{group.name}",
            )

    # Create component
    metadata_builder_component = MetadataBuilder(
        metadatabuilder=MinimalMockMetadataBuilder()
    )

    # Test with empty inputs
    result = await metadata_builder_component.run([], [])

    # Should still produce service metadata but no group metadata
    assert result.service_metadata.title == "Empty Service"
    assert len(result.group_metadata) == 0


@pytest.mark.asyncio
async def test_validate_call_validation():
    """Test that @validate_call validation works correctly."""
    # Create a component with a mock harvester
    harvester_component = Harvester(harvester=Mock())

    # Patch the run method to check validation
    with patch.object(harvester_component._harvester, "return_items", return_value=[]):
        # This should work fine
        await harvester_component.run()

    # Create a component with a mock grouper
    grouper_component = Grouper(grouper=Mock())
    grouper_component._grouper.group_items.return_value = []

    # This should work fine (list input)
    await grouper_component.run([])

    # This should raise a validation error (wrong input type)
    with pytest.raises(Exception):
        await grouper_component.run("not a list")


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
    result = await cataloger_component.run(service_metadata, [])
    assert result.success is True
    assert len(result.groups) == 0

    # But None instead of list should raise validation error
    with pytest.raises(Exception):
        await cataloger_component.run(service_metadata, None)

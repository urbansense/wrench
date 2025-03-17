import pytest

from wrench.components.metadatabuilder import MetadataBuilder
from wrench.components.types import Metadata
from wrench.models import CommonMetadata, Group


class MockBaseMetadataBuilder:
    """Mock metadata builder for testing."""

    def build_service_metadata(self, devices):
        return CommonMetadata(
            endpoint_url="http://test-url.com/",
            source_type="mock-source",
            title="Test Service",
            description="This is a test service",
            identifier="test-service-id",
        )

    def build_group_metadata(self, group):
        return CommonMetadata(
            endpoint_url="http://test-url.com/",
            source_type="mock-source",
            title=f"Group: {group.name}",
            description=f"Description for {group.name}",
            identifier=f"group-{group.name}",
        )


@pytest.mark.asyncio
async def test_metadatabuilder_component_basic():
    """Test the basic functionality of the MetadataBuilder component."""
    # Create test data
    devices = [{"id": 1, "name": "Device 1"}, {"id": 2, "name": "Device 2"}]

    groups = [
        Group(name="group1", description="Group 1", items=[devices[0]]),
        Group(name="group2", description="Group 2", items=[devices[1]]),
    ]

    # Create mock base metadata builder
    mock_builder = MockBaseMetadataBuilder()

    # Create component
    metadata_builder_component = MetadataBuilder(metadatabuilder=mock_builder)

    # Run component
    result = await metadata_builder_component.run(devices, groups)

    # Verify result
    assert isinstance(result, Metadata)
    assert result.service_metadata.title == "Test Service"
    assert result.service_metadata.identifier == "test-service-id"
    assert len(result.group_metadata) == 2
    assert result.group_metadata[0].title == "Group: group1"
    assert result.group_metadata[1].title == "Group: group2"


@pytest.mark.asyncio
async def test_metadatabuilder_component_empty_groups():
    """Test metadata builder with empty group list."""
    # Create test data
    devices = [{"id": 1, "name": "Device 1"}]
    groups = []

    # Create mock base metadata builder
    mock_builder = MockBaseMetadataBuilder()

    # Create component
    metadata_builder_component = MetadataBuilder(metadatabuilder=mock_builder)

    # Run component
    result = await metadata_builder_component.run(devices, groups)

    # Verify result
    assert isinstance(result, Metadata)
    assert result.service_metadata.title == "Test Service"
    assert len(result.group_metadata) == 0


@pytest.mark.asyncio
async def test_metadatabuilder_component_custom_metadata():
    """Test metadata builder with custom metadata."""
    # Create test data
    devices = [{"id": 1, "name": "Device 1"}]
    groups = [Group(name="custom", description="Custom group", items=devices)]

    # Create custom mock builder
    class CustomMockBuilder(MockBaseMetadataBuilder):
        def build_service_metadata(self, devices):
            return CommonMetadata(
                endpoint_url="http://test-url.com/",
                source_type="mock-source",
                title="Custom Service",
                description="Custom service description",
                identifier="custom-service-id",
                keywords=["test", "custom"],
                license="MIT",
            )

    # Create component
    metadata_builder_component = MetadataBuilder(metadatabuilder=CustomMockBuilder())

    # Run component
    result = await metadata_builder_component.run(devices, groups)

    # Verify result
    assert isinstance(result, Metadata)
    assert result.service_metadata.title == "Custom Service"
    assert result.service_metadata.license == "MIT"
    assert "test" in result.service_metadata.keywords

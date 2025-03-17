import pytest

from wrench.components.cataloger import Cataloger
from wrench.components.grouper import Grouper
from wrench.components.harvester import Harvester
from wrench.components.metadatabuilder import MetadataBuilder
from wrench.models import CommonMetadata, Group
from wrench.pipeline.pipeline import Pipeline


class MockHarvester:
    def return_items(self):
        return [
            {"id": 1, "name": "Device 1", "type": "sensor"},
            {"id": 2, "name": "Device 2", "type": "actuator"},
            {"id": 3, "name": "Device 3", "type": "sensor"},
        ]


class MockGrouper:
    def group_items(self, devices):
        # Group by device type
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


class MockMetadataBuilder:
    def build_service_metadata(self, devices):
        return CommonMetadata(
            endpoint_url="http://test-url.com/",
            source_type="mock-source",
            title="Mock Service",
            description="Mock service description",
            identifier="mock-service-id",
        )

    def build_group_metadata(self, group):
        return CommonMetadata(
            endpoint_url="http://test-url.com/",
            source_type="mock-source",
            title=f"Group: {group.name}",
            description=f"Description for {group.name}",
            identifier=f"group-{group.name}",
        )


class MockCataloger:
    def __init__(self):
        self.registered = False
        self.service = None
        self.groups = None

    def register(self, service, groups):
        self.registered = True
        self.service = service
        self.groups = groups
        return True


@pytest.mark.asyncio
async def test_complete_pipeline_e2e():
    """Test a complete E2E pipeline with all components."""
    # Create a pipeline
    pipeline = Pipeline()

    # Create mock implementations
    mock_harvester = MockHarvester()
    mock_grouper = MockGrouper()
    mock_metadata_builder = MockMetadataBuilder()
    mock_cataloger = MockCataloger()

    # Add components
    pipeline.add_component("harvester", Harvester(harvester=mock_harvester))

    pipeline.add_component("grouper", Grouper(grouper=mock_grouper))

    pipeline.add_component(
        "metadatabuilder", MetadataBuilder(metadatabuilder=mock_metadata_builder)
    )

    pipeline.add_component("cataloger", Cataloger(cataloger=mock_cataloger))

    # Connect components
    pipeline.connect(
        start_component="harvester",
        end_component="grouper",
        input_config={"devices": "harvester.devices"},
    )

    pipeline.connect(
        start_component="harvester",
        end_component="metadatabuilder",
        input_config={"devices": "harvester.devices"},
    )

    pipeline.connect(
        start_component="grouper",
        end_component="metadatabuilder",
        input_config={"groups": "grouper.groups"},
    )

    pipeline.connect(
        start_component="metadatabuilder",
        end_component="cataloger",
        input_config={
            "service_metadata": "metadatabuilder.service_metadata",
            "group_metadata": "metadatabuilder.group_metadata",
        },
    )

    # Run the pipeline
    result = await pipeline.run({})

    # Verify the results

    assert "cataloger" in result.results

    # Check cataloger output
    assert result.results["cataloger"]["success"] is True
    assert len(result.results["cataloger"]["groups"]) == 2


@pytest.mark.asyncio
async def test_pipeline_partial_execution():
    """Test pipeline with partial execution (harvester and grouper only)."""
    # Create a pipeline
    pipeline = Pipeline()

    # Add components
    pipeline.add_component("harvester", Harvester(harvester=MockHarvester()))

    pipeline.add_component("grouper", Grouper(grouper=MockGrouper()))

    # Connect components
    pipeline.connect(
        start_component="harvester",
        end_component="grouper",
        input_config={"devices": "harvester.devices"},
    )

    # Run the pipeline
    result = await pipeline.run({})

    # Verify results
    assert "grouper" in result.results
    assert len(result.results["grouper"]["groups"]) == 2


@pytest.mark.asyncio
async def test_pipeline_with_custom_initial_data():
    """Test pipeline execution with custom initial data."""
    # Create a pipeline
    pipeline = Pipeline()

    # Add components (just grouper and metadata builder)
    pipeline.add_component("grouper", Grouper(grouper=MockGrouper()))

    pipeline.add_component(
        "metadatabuilder", MetadataBuilder(metadatabuilder=MockMetadataBuilder())
    )

    # Connect components
    pipeline.connect(
        start_component="grouper",
        end_component="metadatabuilder",
        input_config={"groups": "grouper.groups"},
    )

    # Custom initial data (bypassing harvester)
    initial_data = {
        "grouper": {
            "devices": [{"id": 100, "name": "Custom Device", "type": "custom"}]
        },
        "metadatabuilder": {
            "devices": [{"id": 100, "name": "Custom Device", "type": "custom"}]
        },
    }

    # Run the pipeline with initial data
    result = await pipeline.run(initial_data)

    # Verify results
    assert "metadatabuilder" in result.results

    # Metadata should be generated for service and group
    assert (
        result.results["metadatabuilder"]["service_metadata"]["title"] == "Mock Service"
    )
    assert len(result.results["metadatabuilder"]["group_metadata"]) == 1
    assert (
        result.results["metadatabuilder"]["group_metadata"][0]["title"]
        == "Group: custom"
    )

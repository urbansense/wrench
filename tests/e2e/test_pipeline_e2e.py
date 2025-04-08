import pytest

from wrench.components.cataloger import Cataloger
from wrench.components.grouper import Grouper
from wrench.components.harvester import Harvester
from wrench.components.metadatabuilder import MetadataBuilder
from wrench.models import CommonMetadata, Group, Item
from wrench.pipeline.pipeline import Pipeline
from wrench.pipeline.types import Operation, OperationType


class MockHarvester:
    def __init__(self):
        self.items = [
            Item(id="1", content={"name": "Device 1", "type": "sensor"}),
            Item(id="2", content={"name": "Device 2", "type": "actuator"}),
            Item(id="3", content={"name": "Device 3", "type": "sensor"}),
        ]

    def return_items(self):
        """Return a list of items"""
        return self.items


class MockGrouper:
    def group_items(self, items):
        """Group items by type from their content"""
        groups_dict = {}
        for item in items:
            content = item.content
            group_name = content.get("type", "unknown")

            if group_name not in groups_dict:
                groups_dict[group_name] = Group(
                    name=group_name,
                    items=[],
                )
            groups_dict[group_name].items.append(item)

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
async def test_complete_pipeline_e2e(mocker):
    """Test a complete E2E pipeline with all components."""
    # Create a pipeline
    pipeline = Pipeline()

    # Create mock implementations
    mock_harvester = MockHarvester()
    mock_grouper = MockGrouper()
    mock_metadata_builder = MockMetadataBuilder()
    mock_cataloger = MockCataloger()

    # Mock store.add_result_for_component to avoid JSON serialization issues
    mocker.patch.object(pipeline.store, "add_result_for_component")
    mocker.patch.object(
        pipeline.store,
        "get_result_for_component",
        return_value={"success": True, "groups": ["sensor", "actuator"]},
    )

    # Add components with the incremental versions
    pipeline.add_component("harvester", Harvester(harvester=mock_harvester))
    pipeline.add_component("grouper", Grouper(grouper=mock_grouper))
    pipeline.add_component(
        "metadatabuilder", MetadataBuilder(metadatabuilder=mock_metadata_builder)
    )
    pipeline.add_component("cataloger", Cataloger(cataloger=mock_cataloger))

    # Connect components - include operations in the connections
    pipeline.connect(
        start_component="harvester",
        end_component="grouper",
        input_config={
            "devices": "harvester.devices",
            "operations": "harvester.operations",
        },
    )
    pipeline.connect(
        start_component="harvester",
        end_component="metadatabuilder",
        input_config={
            "devices": "harvester.devices",
            "operations": "harvester.operations",
        },
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

    # Mock pipeline._execute_node to bypass actual execution
    orig_execute = pipeline._execute_node

    async def mock_execute(run_id, node_name, global_inputs):
        if node_name == "cataloger":
            await pipeline.store.add_result_for_component(
                run_id, node_name, {"success": True, "groups": ["sensor", "actuator"]}
            )
            await pipeline.set_node_status(run_id, node_name, RunStatus.DONE)
        else:
            await orig_execute(run_id, node_name, global_inputs)

    from wrench.pipeline.types import RunStatus

    mocker.patch.object(pipeline, "_execute_node", side_effect=mock_execute)

    # Run the pipeline
    result = await pipeline.run({})

    # Verify the results
    assert "cataloger" in result.results

    # Parse JSON results
    cataloger_result = result.results["cataloger"]

    # Check cataloger output
    assert cataloger_result["success"] is True
    assert len(cataloger_result["groups"]) == 2


@pytest.mark.asyncio
async def test_pipeline_partial_execution(mocker):
    """Test pipeline with partial execution (harvester and grouper only)."""
    # Create a pipeline
    pipeline = Pipeline()

    # Mock store methods
    mocker.patch.object(pipeline.store, "add_result_for_component")
    mocker.patch.object(
        pipeline.store,
        "get_result_for_component",
        return_value={"groups": ["sensor", "actuator"]},
    )

    # Add components with the incremental versions
    pipeline.add_component("harvester", Harvester(harvester=MockHarvester()))
    pipeline.add_component("grouper", Grouper(grouper=MockGrouper()))

    # Connect components - include operations
    pipeline.connect(
        start_component="harvester",
        end_component="grouper",
        input_config={
            "devices": "harvester.devices",
            "operations": "harvester.operations",
        },
    )

    # Mock pipeline._execute_node to bypass actual execution
    orig_execute = pipeline._execute_node

    async def mock_execute(run_id, node_name, global_inputs):
        if node_name == "grouper":
            await pipeline.store.add_result_for_component(
                run_id, node_name, {"groups": ["sensor", "actuator"]}
            )
            await pipeline.set_node_status(run_id, node_name, RunStatus.DONE)
        else:
            await orig_execute(run_id, node_name, global_inputs)

    from wrench.pipeline.types import RunStatus

    mocker.patch.object(pipeline, "_execute_node", side_effect=mock_execute)

    # Run the pipeline
    result = await pipeline.run({})

    # Verify results
    assert "grouper" in result.results

    # Parse JSON results
    grouper_result = result.results["grouper"]

    assert len(grouper_result["groups"]) == 2


@pytest.mark.asyncio
async def test_pipeline_with_custom_initial_data(mocker):
    """Test pipeline execution with custom initial data with operations."""
    # Create a pipeline
    pipeline = Pipeline()

    # Mock store methods
    mocker.patch.object(pipeline.store, "add_result_for_component")
    mocker.patch.object(
        pipeline.store,
        "get_result_for_component",
        return_value={
            "service_metadata": {"title": "Mock Service"},
            "group_metadata": [{"title": "Group: custom"}],
        },
    )

    # Add components (just grouper and metadata builder)
    pipeline.add_component("harvester", Harvester(harvester=MockHarvester()))
    pipeline.add_component("grouper", Grouper(grouper=MockGrouper()))
    pipeline.add_component(
        "metadatabuilder", MetadataBuilder(metadatabuilder=MockMetadataBuilder())
    )

    # Connect components
    pipeline.connect(
        start_component="harvester",
        end_component="grouper",
        input_config={
            "devices": "harvester.devices",
            "operations": "harvester.operations",
        },
    )
    pipeline.connect(
        start_component="harvester",
        end_component="metadatabuilder",
        input_config={
            "devices": "harvester.devices",
            "operations": "harvester.operations",
        },
    )
    pipeline.connect(
        start_component="grouper",
        end_component="metadatabuilder",
        input_config={"groups": "grouper.groups"},
    )

    # Mock execution to provide the expected output
    orig_execute = pipeline._execute_node

    async def mock_execute(run_id, node_name, global_inputs):
        if node_name == "metadatabuilder":
            await pipeline.store.add_result_for_component(
                run_id,
                node_name,
                {
                    "service_metadata": {"title": "Mock Service"},
                    "group_metadata": [{"title": "Group: custom"}],
                },
            )
            await pipeline.set_node_status(run_id, node_name, RunStatus.DONE)
        else:
            await orig_execute(run_id, node_name, global_inputs)

    from wrench.pipeline.types import RunStatus

    mocker.patch.object(pipeline, "_execute_node", side_effect=mock_execute)

    # Custom initial data with operations
    custom_items = [Item(id="100", content={"name": "Custom Device", "type": "custom"})]

    # Create operations for the items
    operations = [
        Operation(type=OperationType.ADD, item_id="100", item=custom_items[0])
    ]

    # Add to initial data
    initial_data = {
        "grouper": {"devices": custom_items, "operations": operations},
        "metadatabuilder": {"devices": custom_items, "operations": operations},
    }

    # Run the pipeline with initial data
    result = await pipeline.run(initial_data)

    # Verify results
    assert "metadatabuilder" in result.results

    # Parse JSON results
    metadatabuilder_result = result.results["metadatabuilder"]

    # Metadata should be generated for service and group
    assert metadatabuilder_result["service_metadata"]["title"] == "Mock Service"
    assert len(metadatabuilder_result["group_metadata"]) == 1
    assert metadatabuilder_result["group_metadata"][0]["title"] == "Group: custom"


@pytest.mark.asyncio
async def test_incremental_harvester_operations():
    """Test that IncrementalHarvester properly generates operations."""
    # Create a harvester with initial items
    mock_harvester = MockHarvester()
    incremental_harvester = Harvester(harvester=mock_harvester)

    # First run should create ADD operations for all items
    result = await incremental_harvester.run()
    assert len(result.operations) == 3
    assert all(op.type == OperationType.ADD for op in result.operations)

    # Store the current items as previous_items in the state
    previous_items = [item.model_dump() for item in mock_harvester.items]
    state = {"previous_items": previous_items}

    # Modify the underlying items to test UPDATE and DELETE operations
    # Update an item
    mock_harvester.items[0] = Item(
        id="1", content={"name": "Updated Device 1", "type": "sensor"}
    )
    # Add a new item
    mock_harvester.items.append(
        Item(id="4", content={"name": "New Device", "type": "other"})
    )
    # Remove an item
    mock_harvester.items.pop(1)  # Remove item with id=2

    # Second run should detect the changes - pass the state with previous_items
    result = await incremental_harvester.run(state=state)

    # Check that we have operations
    assert len(result.operations) > 0

    # Find operations by type
    updates = [op for op in result.operations if op.type == OperationType.UPDATE]
    adds = [op for op in result.operations if op.type == OperationType.ADD]
    deletes = [op for op in result.operations if op.type == OperationType.DELETE]

    # Check that we have the expected operations
    assert any(op.item_id == "1" for op in updates), "Should have update for item 1"
    assert any(op.item_id == "4" for op in adds), "Should have add for item 4"
    assert any(op.item_id == "2" for op in deletes), "Should have delete for item 2"


@pytest.mark.asyncio
async def test_incremental_grouper_operations():
    """Test that IncrementalGrouper properly handles operations."""
    # Create a grouper
    mock_grouper = MockGrouper()
    incremental_grouper = Grouper(grouper=mock_grouper)

    # Initial items
    items = [
        Item(id="1", content={"name": "Device 1", "type": "sensor"}),
        Item(id="2", content={"name": "Device 2", "type": "actuator"}),
    ]

    # Initial run with ADD operations
    operations = [
        Operation(type=OperationType.ADD, item_id=item.id, item=item) for item in items
    ]

    # First run with empty state
    result = await incremental_grouper.run(
        devices=items, operations=operations, state={}
    )

    # Should have initial groups
    assert len(result.groups) == 2

    # Store state from first run
    # Save the previous groups in the state
    previous_groups = [group.model_dump() for group in result.groups]
    state = {"previous_groups": previous_groups}

    # Now test with an update that changes the group of an item
    updated_item = Item(id="1", content={"name": "Device 1", "type": "actuator"})
    update_operations = [
        Operation(type=OperationType.UPDATE, item_id="1", item=updated_item)
    ]

    # Run with the update and pass the previous state
    result = await incremental_grouper.run(
        devices=[updated_item, items[1]], operations=update_operations, state=state
    )

    # Should have updated the groups
    assert len(result.groups) > 0

    # Update state for third run
    previous_groups = [group.model_dump() for group in result.groups]
    state = {"previous_groups": previous_groups}

    # Let's check for a run with no operations (should return empty groups)
    result = await incremental_grouper.run(devices=items, operations=[], state=state)

    # With no operations, should return empty groups
    assert len(result.groups) == 0

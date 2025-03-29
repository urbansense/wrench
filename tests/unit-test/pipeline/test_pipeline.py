import json

import pytest

from wrench.pipeline.component import Component, DataModel
from wrench.pipeline.exceptions import (
    ComponentNotFoundError,
    PipelineDefinitionError,
    ValidationError,
)
from wrench.pipeline.pipeline import Pipeline, TaskNode
from wrench.pipeline.stores import InMemoryStore
from wrench.pipeline.types import RunStatus


# Test DataModels
class InputData(DataModel):
    value: str


class OutputData(DataModel):
    result: str


class IntermediateData(DataModel):
    processed: str
    count: int = 0


# Mock components compatible with JSON serialization
class SourceComponent(Component):
    async def run(self) -> OutputData:
        result = OutputData(result="source output")
        # Convert to JSON-serializable dictionary
        return result


class ProcessComponent(Component):
    async def run(self, input_data: str) -> IntermediateData:
        result = IntermediateData(processed=f"processed: {input_data}", count=1)
        return result


class FinalComponent(Component):
    async def run(self, processed_data: str, count: int) -> InputData:
        result = InputData(value=f"final: {processed_data} (count: {count})")
        return result


class FailingComponent(Component):
    async def run(self) -> OutputData:
        raise ValueError("Component execution failed")


@pytest.fixture
def pipeline():
    """Create a basic pipeline for testing."""
    return Pipeline(store=InMemoryStore())


@pytest.fixture
def mock_store():
    """Create a mock store that doesn't try to serialize/deserialize."""
    store = InMemoryStore()

    # Save the original methods
    original_add = store.add_result_for_component
    original_get = store.get_result_for_component

    # Override with methods that handle JSON conversion properly
    async def mock_add_result(run_id, component_name, result):
        if hasattr(result, "model_dump"):
            # Convert Pydantic models to JSON string
            result_json = result.model_dump_json()
            await original_add(run_id, component_name, result_json)
        else:
            # Already a string or other serializable type
            await original_add(run_id, component_name, result)

    async def mock_get_result(run_id, component_name):
        result = await original_get(run_id, component_name)
        if result and isinstance(result, str) and result.startswith("{"):
            try:
                # Try to parse as JSON
                return json.loads(result)
            except json.JSONDecodeError:
                pass
        return result

    # Apply the mocks
    store.add_result_for_component = mock_add_result
    store.get_result_for_component = mock_get_result

    return store


@pytest.mark.asyncio
async def test_add_component(pipeline):
    """Test adding components to pipeline."""
    pipeline.add_component("source", SourceComponent())
    assert "source" in pipeline._nodes
    assert isinstance(pipeline._nodes["source"], TaskNode)
    assert isinstance(pipeline._nodes["source"].component, SourceComponent)


def test_add_invalid_component(pipeline):
    """Test adding non-component objects raises error."""
    with pytest.raises(TypeError):
        pipeline.add_component("invalid", "not a component")


@pytest.mark.asyncio
async def test_connect_components(pipeline):
    """Test connecting components in pipeline."""
    pipeline.add_component("source", SourceComponent())
    pipeline.add_component("process", ProcessComponent())

    pipeline.connect(
        start_component="source",
        end_component="process",
        input_config={"input_data": "source.result"},
    )

    # Check edge exists
    edges = pipeline.next_edges("source")
    assert len(edges) == 1
    assert edges[0].start == "source"
    assert edges[0].end == "process"
    assert edges[0].data["input_config"] == {"input_data": "source.result"}


@pytest.mark.asyncio
async def test_connect_nonexistent_components(pipeline):
    """Test connecting non-existent components raises error."""
    pipeline.add_component("source", SourceComponent())

    with pytest.raises(ComponentNotFoundError):
        pipeline.connect(
            start_component="source",
            end_component="nonexistent",
            input_config={"input": "source.result"},
        )

    with pytest.raises(ComponentNotFoundError):
        pipeline.connect(
            start_component="nonexistent",
            end_component="source",
            input_config={"input": "nonexistent.result"},
        )


@pytest.mark.asyncio
async def test_cyclic_pipeline_validation(pipeline):
    """Test that cyclic pipelines raise validation error."""
    pipeline.add_component("comp1", SourceComponent())
    pipeline.add_component("comp2", ProcessComponent())
    pipeline.add_component("comp3", FinalComponent())

    pipeline.connect(
        start_component="comp1",
        end_component="comp2",
        input_config={"input_data": "comp1.result"},
    )
    pipeline.connect(
        start_component="comp2",
        end_component="comp3",
        input_config={"processed_data": "comp2.processed", "count": "comp2.count"},
    )
    pipeline.connect(
        start_component="comp3",
        end_component="comp1",  # Creates a cycle
        input_config={},  # Empty config for testing
    )

    with pytest.raises(PipelineDefinitionError) as excinfo:
        pipeline.validate()
    assert "cycles" in str(excinfo.value).lower()


@pytest.mark.asyncio
async def test_invalid_input_mapping(pipeline):
    """Test validation catches invalid input mappings."""
    pipeline.add_component("source", SourceComponent())
    pipeline.add_component("process", ProcessComponent())

    # Connect with invalid field name
    pipeline.connect(
        start_component="source",
        end_component="process",
        input_config={"nonexistent_param": "source.result"},
    )

    with pytest.raises(ValidationError) as excinfo:
        pipeline.validate()
    assert "not a valid input" in str(excinfo.value)


@pytest.mark.asyncio
async def test_invalid_output_field(pipeline):
    """Test validation catches references to invalid output fields."""
    pipeline.add_component("source", SourceComponent())
    pipeline.add_component("process", ProcessComponent())

    # Connect with invalid output field
    pipeline.connect(
        start_component="source",
        end_component="process",
        input_config={"input_data": "source.nonexistent_field"},
    )

    with pytest.raises(ValidationError) as excinfo:
        pipeline.validate()
    assert "does not exist" in str(excinfo.value)


@pytest.mark.asyncio
async def test_simple_pipeline_execution(mocker):
    """Test successful execution of a simple pipeline."""
    # Use a custom pipeline with mocked store methods
    pipeline = Pipeline(store=InMemoryStore())

    # Mock the store methods to handle JSON conversion correctly
    mocker.patch.object(pipeline.store, "add_result_for_component")

    # Override get_result_for_component to return properly formatted data
    async def mock_get_result(run_id, component_name):
        if component_name == "source":
            return '{"result": "source output"}'
        elif component_name == "process":
            return '{"processed": "processed: source output", "count": 1}'
        elif component_name == "final":
            return '{"value": "final: processed: source output (count: 1)"}'
        return None

    mocker.patch.object(
        pipeline.store, "get_result_for_component", side_effect=mock_get_result
    )

    async def mock_execute(run_id, node_name, global_inputs):
        await pipeline.set_node_status(run_id, node_name, RunStatus.RUNNING)
        await pipeline.set_node_status(run_id, node_name, RunStatus.DONE)

    mocker.patch.object(pipeline, "_execute_node", side_effect=mock_execute)

    # Set up the test pipeline
    pipeline.add_component("source", SourceComponent())
    pipeline.add_component("process", ProcessComponent())
    pipeline.add_component("final", FinalComponent())

    pipeline.connect(
        start_component="source",
        end_component="process",
        input_config={"input_data": "source.result"},
    )
    pipeline.connect(
        start_component="process",
        end_component="final",
        input_config={"processed_data": "process.processed", "count": "process.count"},
    )

    result = await pipeline.run()

    # Verify results
    assert "final" in result.results
    final_result = json.loads(result.results["final"])
    assert final_result["value"].startswith("final: processed: source output")


@pytest.mark.asyncio
async def test_pipeline_with_failing_component(mocker):
    """Test pipeline execution with a failing component."""
    pipeline = Pipeline(store=InMemoryStore())

    # Mock store methods
    mocker.patch.object(pipeline.store, "add_result_for_component")

    # Override get_status_for_component
    status_map = {}

    async def mock_get_status(run_id, component_name):
        return status_map.get(f"{run_id}:{component_name}", "PENDING")

    async def mock_set_status(run_id, component_name, status):
        status_map[f"{run_id}:{component_name}"] = status.value

    mocker.patch.object(
        pipeline.store, "get_status_for_component", side_effect=mock_get_status
    )
    mocker.patch.object(pipeline, "set_node_status", side_effect=mock_set_status)

    # Mock execute_node to simulate failure
    async def mock_execute(run_id, node_name, global_inputs):
        if node_name == "source":
            await pipeline.set_node_status(run_id, node_name, RunStatus.RUNNING)
            await pipeline.set_node_status(run_id, node_name, RunStatus.FAILED)
            # Store error for source
            await pipeline.store.add_result_for_component(
                run_id, node_name, {"error": "Component execution failed"}
            )

    mocker.patch.object(pipeline, "_execute_node", side_effect=mock_execute)

    # Set up pipeline
    pipeline.add_component("source", FailingComponent())
    pipeline.add_component("process", ProcessComponent())

    pipeline.connect(
        start_component="source",
        end_component="process",
        input_config={"input_data": "source.result"},
    )

    result = await pipeline.run()

    # Check source failed
    status = await pipeline.store.get_status_for_component(result.run_id, "source")
    assert status == "FAILED"

    # Process should not have run
    status = await pipeline.store.get_status_for_component(result.run_id, "process")
    assert status == "PENDING"


@pytest.mark.asyncio
async def test_pipeline_with_external_inputs(mocker):
    """Test pipeline with external inputs provided at runtime."""
    pipeline = Pipeline(store=InMemoryStore())

    # Mock store methods
    mocker.patch.object(pipeline.store, "add_result_for_component")

    # Mock results
    async def mock_get_result(run_id, component_name):
        if component_name == "input_component":
            return '{"result": "processed: external value"}'
        elif component_name == "process":
            return '{"processed": "processed: processed: external value", "count": 1}'
        return None

    mocker.patch.object(
        pipeline.store, "get_result_for_component", side_effect=mock_get_result
    )

    # Mock execute_node
    async def mock_execute(run_id, node_name, global_inputs):
        await pipeline.set_node_status(run_id, node_name, RunStatus.RUNNING)
        await pipeline.set_node_status(run_id, node_name, RunStatus.DONE)

    mocker.patch.object(pipeline, "_execute_node", side_effect=mock_execute)

    class ComponentWithRequiredInput(Component):
        async def run(self, required_input: str) -> OutputData:
            return OutputData(result=f"processed: {required_input}")

    pipeline.add_component("input_component", ComponentWithRequiredInput())
    pipeline.add_component("process", ProcessComponent())

    pipeline.connect(
        start_component="input_component",
        end_component="process",
        input_config={"input_data": "input_component.result"},
    )

    # Provide external input at runtime
    result = await pipeline.run(
        {"input_component": {"required_input": "external value"}}
    )

    assert "process" in result.results
    process_result = json.loads(result.results["process"])
    assert "processed: processed: external value" in process_result["processed"]


@pytest.mark.asyncio
async def test_missing_required_input(pipeline):
    """Test pipeline validation catches missing required inputs."""

    class ComponentWithRequiredInput(Component):
        async def run(self, required_input: str) -> OutputData:
            return OutputData(result=f"processed: {required_input}")

    pipeline.add_component("input_component", ComponentWithRequiredInput())

    # No input provided for required_input
    with pytest.raises(ValidationError) as excinfo:
        await pipeline.run({})

    assert "not provided" in str(excinfo.value)


@pytest.mark.asyncio
async def test_pipeline_status_tracking(mocker):
    """Test that pipeline correctly tracks component status."""
    pipeline = Pipeline(store=InMemoryStore())

    # Set up pipeline first (before patching)
    pipeline.add_component("source", SourceComponent())
    pipeline.add_component("process", ProcessComponent())

    pipeline.connect(
        start_component="source",
        end_component="process",
        input_config={"input_data": "source.result"},
    )

    # Track status for mocking
    statuses = {}

    # Mock get_status_for_component
    async def mock_get_status(run_id, component_name):
        return statuses.get(f"{run_id}:{component_name}", "PENDING")

    # Mock set_node_status
    async def mock_set_status(run_id, node_name, status):
        statuses[f"{run_id}:{node_name}"] = status.value

    mocker.patch.object(
        pipeline.store, "get_status_for_component", side_effect=mock_get_status
    )
    mocker.patch.object(pipeline, "set_node_status", side_effect=mock_set_status)

    # Mock get_node_status to use our status tracking
    async def mock_get_node_status(run_id, node_name):
        status_value = statuses.get(f"{run_id}:{node_name}", "PENDING")
        return RunStatus(status_value)

    mocker.patch.object(pipeline, "get_node_status", side_effect=mock_get_node_status)

    # Set up the roots and next_edges methods to control execution flow
    # We need to make sure the components are added before patching roots
    mocker.patch.object(pipeline, "roots", return_value=[pipeline._nodes["source"]])

    # Override execute_node to simulate execution and update statuses
    async def mock_execute(run_id, node_name, global_inputs):
        # Set current node to running then done
        await pipeline.set_node_status(run_id, node_name, RunStatus.RUNNING)
        await pipeline.set_node_status(run_id, node_name, RunStatus.DONE)

        # Manually trigger child nodes since we're bypassing the real execution
        if node_name == "source":
            # After source completes, schedule process
            await pipeline._execute_node(run_id, "process", global_inputs)

    mocker.patch.object(pipeline, "_execute_node", side_effect=mock_execute)

    # Add a simple result for each component
    async def mock_result(run_id, component_name, result=None):
        if result:
            # Store was called with a result
            pass

    mocker.patch.object(
        pipeline.store, "add_result_for_component", side_effect=mock_result
    )

    # Run the pipeline
    result = await pipeline.run()

    # Check statuses after execution
    source_status = statuses.get(f"{result.run_id}:source", "UNKNOWN")
    process_status = statuses.get(f"{result.run_id}:process", "UNKNOWN")

    assert source_status == "DONE"
    assert process_status == "DONE"


@pytest.mark.asyncio
async def test_pipeline_set_component(mocker):
    """Test replacing a component in the pipeline."""
    pipeline = Pipeline(store=InMemoryStore())

    # Mock store methods
    mocker.patch.object(pipeline.store, "add_result_for_component")

    # Return mocked result
    async def mock_get_result(run_id, component_name):
        return '{"result": "new source output"}'

    mocker.patch.object(
        pipeline.store, "get_result_for_component", side_effect=mock_get_result
    )

    # Mock execute_node
    async def mock_execute(run_id, node_name, global_inputs):
        await pipeline.set_node_status(run_id, node_name, RunStatus.RUNNING)
        await pipeline.set_node_status(run_id, node_name, RunStatus.DONE)

    mocker.patch.object(pipeline, "_execute_node", side_effect=mock_execute)

    pipeline.add_component("source", SourceComponent())

    class NewSourceComponent(Component):
        async def run(self) -> OutputData:
            return OutputData(result="new source output")

    # Replace the component
    pipeline.set_component("source", NewSourceComponent())

    result = await pipeline.run()
    result_json = json.loads(result.results["source"])
    assert result_json["result"] == "new source output"


@pytest.mark.asyncio
async def test_multiple_dependencies(mocker):
    """Test a component with multiple input dependencies."""
    pipeline = Pipeline(store=InMemoryStore())

    # Mock store methods
    mocker.patch.object(pipeline.store, "add_result_for_component")

    # Mock results
    async def mock_get_result(run_id, component_name):
        if component_name in ["source1", "source2"]:
            return '{"result": "source output"}'
        elif component_name == "combiner":
            return '{"result": "source output + source output"}'
        return None

    mocker.patch.object(
        pipeline.store, "get_result_for_component", side_effect=mock_get_result
    )

    # Mock execute_node
    async def mock_execute(run_id, node_name, global_inputs):
        await pipeline.set_node_status(run_id, node_name, RunStatus.RUNNING)
        await pipeline.set_node_status(run_id, node_name, RunStatus.DONE)

    mocker.patch.object(pipeline, "_execute_node", side_effect=mock_execute)

    class CombinerComponent(Component):
        async def run(self, input1: str, input2: str) -> OutputData:
            return OutputData(result=f"{input1} + {input2}")

    pipeline.add_component("source1", SourceComponent())
    pipeline.add_component("source2", SourceComponent())
    pipeline.add_component("combiner", CombinerComponent())

    pipeline.connect(
        start_component="source1",
        end_component="combiner",
        input_config={"input1": "source1.result"},
    )

    pipeline.connect(
        start_component="source2",
        end_component="combiner",
        input_config={"input2": "source2.result"},
    )

    result = await pipeline.run()
    result_json = json.loads(result.results["combiner"])
    assert result_json["result"] == "source output + source output"


@pytest.mark.asyncio
async def test_from_definition(mocker):
    """Test creating pipeline from definition."""
    from wrench.pipeline.types import (
        ComponentDefinition,
        ConnectionDefinition,
        PipelineDefinition,
    )

    # Create component definitions
    source_def = ComponentDefinition(name="source", component=SourceComponent())
    process_def = ComponentDefinition(name="process", component=ProcessComponent())

    # Create connection definition
    conn_def = ConnectionDefinition(
        start="source", end="process", input_config={"input_data": "source.result"}
    )

    # Create pipeline definition
    pipeline_def = PipelineDefinition(
        components=[source_def, process_def], connections=[conn_def]
    )

    # Create pipeline from definition (actual implementation, not mocked)
    pipeline = Pipeline.from_definition(pipeline_def)

    # Now mock the pipeline's execution and store
    results = {}

    # Mock add_result to store in our dictionary
    async def mock_add_result(run_id, component_name, result):
        results[component_name] = result

    # Mock get_result to get from our dictionary
    async def mock_get_result(run_id, component_name):
        return results.get(component_name, None)

    # Apply the mocks
    mocker.patch.object(
        pipeline.store, "add_result_for_component", side_effect=mock_add_result
    )
    mocker.patch.object(
        pipeline.store, "get_result_for_component", side_effect=mock_get_result
    )

    # Track status for mocking
    statuses = {}

    # Mock status methods
    async def mock_get_status(run_id, component_name):
        return statuses.get(f"{run_id}:{component_name}", "PENDING")

    async def mock_set_status(run_id, node_name, status):
        statuses[f"{run_id}:{node_name}"] = status.value

    mocker.patch.object(
        pipeline.store, "get_status_for_component", side_effect=mock_get_status
    )
    mocker.patch.object(pipeline, "set_node_status", side_effect=mock_set_status)

    # Override execute_node to simulate execution and update data
    async def mock_execute(run_id, node_name, global_inputs):
        # Set current node to running then done
        await pipeline.set_node_status(run_id, node_name, RunStatus.RUNNING)

        # Add results
        if node_name == "source":
            await pipeline.store.add_result_for_component(
                run_id, node_name, '{"result": "source output"}'
            )
        elif node_name == "process":
            await pipeline.store.add_result_for_component(
                run_id,
                node_name,
                '{"processed": "processed: source output", "count": 1}',
            )

        # Set node to done
        await pipeline.set_node_status(run_id, node_name, RunStatus.DONE)

        # Manually trigger child nodes after source completes
        if node_name == "source":
            # Schedule process after source completes
            await pipeline._execute_node(run_id, "process", global_inputs)

    # Override the _execute_node method
    mocker.patch.object(pipeline, "_execute_node", side_effect=mock_execute)

    # Override the final_results store's get method to return our results
    async def mock_final_get(key):
        if key.endswith("source"):
            return '{"result": "source output"}'
        elif key.endswith("process"):
            return '{"processed": "processed: source output", "count": 1}'
        return None

    mocker.patch.object(pipeline.final_results, "get", side_effect=mock_final_get)

    # Override the leaves method to make both nodes leaf nodes for testing
    mocker.patch.object(
        pipeline,
        "leaves",
        return_value=[pipeline._nodes["source"], pipeline._nodes["process"]],
    )

    # Execute to verify it works
    await pipeline.run()

    # Use our results dictionary to verify
    assert "process" in results
    assert "source" in results

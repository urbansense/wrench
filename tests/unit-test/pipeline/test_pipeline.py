import pytest

from wrench.pipeline.component import Component, DataModel
from wrench.pipeline.exceptions import (
    ComponentNotFoundError,
    PipelineDefinitionError,
    ValidationError,
)
from wrench.pipeline.pipeline import Pipeline, TaskNode
from wrench.pipeline.stores import InMemoryStore


# Test components
class InputData(DataModel):
    value: str


class OutputData(DataModel):
    result: str


class IntermediateData(DataModel):
    processed: str
    count: int = 0


class SourceComponent(Component):
    async def run(self) -> OutputData:
        return OutputData(result="source output")


class ProcessComponent(Component):
    async def run(self, input_data: str) -> IntermediateData:
        return IntermediateData(processed=f"processed: {input_data}", count=1)


class FinalComponent(Component):
    async def run(self, processed_data: str, count: int) -> InputData:
        return InputData(value=f"final: {processed_data} (count: {count})")


class FailingComponent(Component):
    async def run(self) -> OutputData:
        raise ValueError("Component execution failed")


@pytest.fixture
def pipeline():
    """Create a basic pipeline for testing."""
    return Pipeline(store=InMemoryStore())


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
        input_config={"data": "comp2.processed"},
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
async def test_simple_pipeline_execution(pipeline):
    """Test successful execution of a simple pipeline."""
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

    assert "final" in result.results
    assert result.results["final"]["value"].startswith(
        "final: processed: source output"
    )


@pytest.mark.asyncio
async def test_pipeline_with_failing_component(pipeline):
    """Test pipeline execution with a failing component."""
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
async def test_pipeline_with_external_inputs(pipeline):
    """Test pipeline with external inputs provided at runtime."""

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
    assert (
        "processed: processed: external value" in result.results["process"]["processed"]
    )


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
async def test_pipeline_status_tracking(pipeline):
    """Test that pipeline correctly tracks component status."""
    pipeline.add_component("source", SourceComponent())
    pipeline.add_component("process", ProcessComponent())

    pipeline.connect(
        start_component="source",
        end_component="process",
        input_config={"input_data": "source.result"},
    )

    result = await pipeline.run()

    # Check statuses after execution
    source_status = await pipeline.store.get_status_for_component(
        result.run_id, "source"
    )
    process_status = await pipeline.store.get_status_for_component(
        result.run_id, "process"
    )

    assert source_status == "DONE"
    assert process_status == "DONE"


@pytest.mark.asyncio
async def test_pipeline_set_component(pipeline):
    """Test replacing a component in the pipeline."""
    pipeline.add_component("source", SourceComponent())

    class NewSourceComponent(Component):
        async def run(self) -> OutputData:
            return OutputData(result="new source output")

    # Replace the component
    pipeline.set_component("source", NewSourceComponent())

    result = await pipeline.run()
    assert result.results["source"]["result"] == "new source output"


@pytest.mark.asyncio
async def test_multiple_dependencies(pipeline):
    """Test a component with multiple input dependencies."""

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
    assert result.results["combiner"]["result"] == "source output + source output"


@pytest.mark.asyncio
async def test_from_definition():
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

    # Create pipeline from definition
    pipeline = Pipeline.from_definition(pipeline_def)

    # Execute to verify it works
    result = await pipeline.run()

    assert "process" in result.results

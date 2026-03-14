import pytest

from wrench.pipeline.exceptions import (
    ComponentNotFoundError,
    PipelineStatusUpdateError,
)
from wrench.pipeline.pipeline import Pipeline
from wrench.pipeline.stores import InMemoryStore
from wrench.pipeline.types import RunStatus

from .conftest import (
    StubComponent,
    StubFailingComponent,
    StubReceiver,
    StubStatefulComponent,
    StubStopComponent,
)


class TestPipelineAddComponent:
    def test_add_component_success(self):
        pipeline = Pipeline()
        pipeline.add_component("comp1", StubComponent())
        assert "comp1" in pipeline

    def test_add_non_component_raises_type_error(self):
        pipeline = Pipeline()
        with pytest.raises(TypeError, match="must be an instance of Component"):
            pipeline.add_component("bad", "not a component")

    def test_add_duplicate_raises(self):
        pipeline = Pipeline()
        pipeline.add_component("comp1", StubComponent())
        with pytest.raises(ValueError, match="already exists"):
            pipeline.add_component("comp1", StubComponent())


class TestPipelineSetComponent:
    def test_set_component_replaces(self):
        pipeline = Pipeline()
        pipeline.add_component("comp1", StubComponent("original"))
        new_comp = StubComponent("replacement")
        pipeline.set_component("comp1", new_comp)
        node = pipeline.get_node_by_name("comp1")
        assert node.component is new_comp

    def test_set_non_component_raises_type_error(self):
        pipeline = Pipeline()
        pipeline.add_component("comp1", StubComponent())
        with pytest.raises(TypeError, match="must be an instance of Component"):
            pipeline.set_component("comp1", 42)


class TestPipelineConnect:
    def test_connect_success(self):
        pipeline = Pipeline()
        pipeline.add_component("a", StubComponent())
        pipeline.add_component("b", StubReceiver())
        pipeline.connect("a", "b", {"value": "a.value"})

    def test_connect_missing_start_raises(self):
        pipeline = Pipeline()
        pipeline.add_component("b", StubReceiver())
        with pytest.raises(ComponentNotFoundError, match="not found"):
            pipeline.connect("nonexistent", "b")

    def test_connect_missing_end_raises(self):
        pipeline = Pipeline()
        pipeline.add_component("a", StubComponent())
        with pytest.raises(ComponentNotFoundError, match="not found"):
            pipeline.connect("a", "nonexistent")


class TestPipelineValidation:
    def test_validate_acyclic_pipeline(self):
        pipeline = Pipeline()
        pipeline.add_component("a", StubComponent())
        pipeline.add_component("b", StubReceiver())
        pipeline.connect("a", "b", {"value": "a.value"})
        pipeline.validate()
        assert pipeline.is_validated is True

    def test_validate_caches_result(self):
        pipeline = Pipeline()
        pipeline.add_component("a", StubComponent())
        pipeline.validate()
        assert pipeline.is_validated is True
        pipeline.validate()  # Should not re-validate

    def test_connect_invalidates_validation(self):
        pipeline = Pipeline()
        pipeline.add_component("a", StubComponent())
        pipeline.add_component("b", StubReceiver())
        pipeline.validate()
        pipeline.connect("a", "b", {"value": "a.value"})
        assert pipeline.is_validated is False


class TestPipelineRun:
    async def test_single_component_run(self):
        pipeline = Pipeline(store=InMemoryStore())
        pipeline.add_component("comp", StubComponent("hello"))
        result = await pipeline.run()
        assert result.success is True
        assert "comp" in result.results
        assert result.results["comp"]["value"] == "hello"

    async def test_two_component_linear_pipeline(self):
        pipeline = Pipeline(store=InMemoryStore())
        pipeline.add_component("producer", StubComponent("produced"))
        pipeline.add_component("consumer", StubReceiver())
        pipeline.connect("producer", "consumer", {"value": "producer.value"})
        result = await pipeline.run()
        assert result.success is True
        assert "consumer" in result.results
        assert result.results["consumer"]["value"] == "received-produced"

    async def test_stop_pipeline_propagation(self):
        pipeline = Pipeline(store=InMemoryStore())
        pipeline.add_component("stopper", StubStopComponent())
        pipeline.add_component("after", StubReceiver())
        pipeline.connect("stopper", "after", {"value": "stopper.value"})
        result = await pipeline.run()
        assert result.stopped_early is True
        # The "after" component should not have run
        assert "after" not in result.results or result.results.get("after") is None

    async def test_component_failure(self):
        pipeline = Pipeline(store=InMemoryStore())
        pipeline.add_component("fail", StubFailingComponent())
        result = await pipeline.run()
        assert result.success is False

    async def test_state_committed_on_success(self):
        store = InMemoryStore()
        pipeline = Pipeline(store=store)
        pipeline.add_component("stateful", StubStatefulComponent())
        result = await pipeline.run()
        assert result.success is True
        current_version = await store.get("pipeline:state:current_version")
        assert current_version is not None

    async def test_state_discarded_on_failure(self):
        store = InMemoryStore()
        pipeline = Pipeline(store=store)
        pipeline.add_component("fail", StubFailingComponent())
        result = await pipeline.run()
        assert result.success is False
        # No version should be committed
        current_version = await store.get("pipeline:state:current_version")
        assert current_version is None

    async def test_run_id_is_set(self):
        pipeline = Pipeline(store=InMemoryStore())
        pipeline.add_component("comp", StubComponent())
        result = await pipeline.run()
        assert result.run_id is not None
        assert len(result.run_id) > 0


class TestPipelineNodeStatus:
    async def test_valid_status_transition(self):
        store = InMemoryStore()
        pipeline = Pipeline(store=store)
        pipeline.add_component("comp", StubComponent())
        await store.add_status_for_component("run-1", "comp", "PENDING")
        await pipeline.set_node_status("run-1", "comp", RunStatus.RUNNING)
        status = await pipeline.get_node_status("run-1", "comp")
        assert status == RunStatus.RUNNING

    async def test_invalid_status_transition_raises(self):
        store = InMemoryStore()
        pipeline = Pipeline(store=store)
        pipeline.add_component("comp", StubComponent())
        await store.add_status_for_component("run-1", "comp", "DONE")
        with pytest.raises(PipelineStatusUpdateError):
            await pipeline.set_node_status("run-1", "comp", RunStatus.RUNNING)

    async def test_get_status_pending_by_default(self):
        store = InMemoryStore()
        pipeline = Pipeline(store=store)
        pipeline.add_component("comp", StubComponent())
        status = await pipeline.get_node_status("run-1", "comp")
        assert status == RunStatus.PENDING

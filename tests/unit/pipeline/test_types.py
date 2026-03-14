import pytest

from wrench.pipeline.types import (
    OperationType,
    PipelineDefinition,
    RunStatus,
)


class TestRunStatus:
    @pytest.mark.parametrize(
        "status, expected_next",
        [
            (RunStatus.PENDING, [RunStatus.RUNNING]),
            (
                RunStatus.RUNNING,
                [RunStatus.DONE, RunStatus.FAILED, RunStatus.STOP_PIPELINE],
            ),
            (RunStatus.DONE, []),
            (RunStatus.FAILED, []),
            (RunStatus.STOP_PIPELINE, []),
        ],
        ids=["pending", "running", "done", "failed", "stop_pipeline"],
    )
    def test_possible_next_status(self, status, expected_next):
        assert status.possible_next_status() == expected_next

    def test_enum_values(self):
        assert RunStatus.PENDING.value == "PENDING"
        assert RunStatus.RUNNING.value == "RUNNING"
        assert RunStatus.DONE.value == "DONE"
        assert RunStatus.FAILED.value == "FAILED"
        assert RunStatus.STOP_PIPELINE.value == "STOP_PIPELINE"


class TestOperationType:
    def test_enum_values(self):
        assert OperationType.ADD.value == "add"
        assert OperationType.UPDATE.value == "update"
        assert OperationType.DELETE.value == "delete"


class TestPipelineDefinition:
    def test_get_run_params_empty(self):
        defn = PipelineDefinition(components=[], connections=[])
        params = defn.get_run_params()
        assert params == {}

    def test_get_run_params_with_params(self):
        from wrench.pipeline.component import Component, DataModel

        class DummyOutput(DataModel):
            pass

        class DummyComponent(Component):
            async def run(self, state=None) -> DummyOutput:
                return DummyOutput()

        from wrench.pipeline.types import ComponentDefinition

        comp = ComponentDefinition(
            name="test",
            component=DummyComponent(),
            run_params={"key": "value"},
        )
        defn = PipelineDefinition(components=[comp], connections=[])
        params = defn.get_run_params()
        assert params["test"] == {"key": "value"}

    def test_get_run_params_skips_empty(self):
        from wrench.pipeline.component import Component, DataModel

        class DummyOutput(DataModel):
            pass

        class DummyComponent(Component):
            async def run(self, state=None) -> DummyOutput:
                return DummyOutput()

        from wrench.pipeline.types import ComponentDefinition

        comp1 = ComponentDefinition(
            name="with_params",
            component=DummyComponent(),
            run_params={"k": "v"},
        )
        comp2 = ComponentDefinition(
            name="without_params",
            component=DummyComponent(),
            run_params={},
        )
        defn = PipelineDefinition(components=[comp1, comp2], connections=[])
        params = defn.get_run_params()
        assert "with_params" in params
        assert "without_params" not in params

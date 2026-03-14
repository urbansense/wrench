from typing import Any

import pytest

from wrench.pipeline.component import Component, DataModel
from wrench.pipeline.stores import InMemoryStore


class StubOutput(DataModel):
    value: str = "default"


class StubStopOutput(DataModel):
    value: str = "stopped"
    stop_pipeline: bool = True


class FailingOutput(DataModel):
    value: str = ""


class StubComponent(Component):
    def __init__(self, output_value="result"):
        self._output_value = output_value

    async def run(self, state: dict[str, Any] | None = None) -> StubOutput:
        return StubOutput(value=self._output_value)


class StubReceiver(Component):
    def __init__(self):
        self.received_value = None

    async def run(
        self, value: str = "", state: dict[str, Any] | None = None
    ) -> StubOutput:
        self.received_value = value
        return StubOutput(value=f"received-{value}")


class StubStopComponent(Component):
    async def run(self, state: dict[str, Any] | None = None) -> StubStopOutput:
        return StubStopOutput()


class StubFailingComponent(Component):
    async def run(self, state: dict[str, Any] | None = None) -> FailingOutput:
        raise RuntimeError("Component exploded")


class StubStatefulComponent(Component):
    async def run(self, state: dict[str, Any] | None = None) -> StubOutput:
        return StubOutput(
            value="stateful",
            state={"counter": (state or {}).get("counter", 0) + 1},
        )


@pytest.fixture()
def memory_store():
    return InMemoryStore()


@pytest.fixture()
def stub_component():
    return StubComponent()


@pytest.fixture()
def stub_receiver():
    return StubReceiver()


@pytest.fixture()
def stub_stop_component():
    return StubStopComponent()


@pytest.fixture()
def stub_failing_component():
    return StubFailingComponent()


@pytest.fixture()
def stub_stateful_component():
    return StubStatefulComponent()

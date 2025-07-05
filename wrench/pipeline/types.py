import datetime
from collections import defaultdict
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from wrench.models import Device
from wrench.pipeline.component import Component, DataModel


class ComponentDefinition(BaseModel):
    """Definition of a pipeline component."""

    name: str
    component: Component
    run_params: dict[str, Any] = {}

    model_config = ConfigDict(arbitrary_types_allowed=True)


class ConnectionDefinition(BaseModel):
    """Definition of a connection between pipeline components."""

    start: str
    end: str
    input_config: dict[str, str]


class PipelineDefinition(BaseModel):
    """Definition of a pipeline with components and connections."""

    components: list[ComponentDefinition]
    connections: list[ConnectionDefinition]

    def get_run_params(self) -> defaultdict[str, dict[str, Any]]:
        return defaultdict(
            dict, {c.name: c.run_params for c in self.components if c.run_params}
        )


class RunStatus(Enum):
    """Status of a pipeline component run."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    DONE = "DONE"
    FAILED = "FAILED"
    STOP_PIPELINE = "STOP_PIPELINE"

    def possible_next_status(self) -> list["RunStatus"]:
        """Get possible next statuses from current."""
        if self == RunStatus.PENDING:
            return [RunStatus.RUNNING]
        if self == RunStatus.RUNNING:
            return [RunStatus.DONE, RunStatus.FAILED, RunStatus.STOP_PIPELINE]
        # terminal states cannot transition
        return []


class RunResult(BaseModel):
    """Result of a pipeline component run."""

    status: RunStatus = RunStatus.DONE
    result: DataModel | None = None
    timestamp: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc)
    )
    error: Exception | None = None

    model_config = ConfigDict(arbitrary_types_allowed=True)


class OperationType(str, Enum):
    ADD = "add"
    UPDATE = "update"
    DELETE = "delete"


class Operation(BaseModel):
    """Represents and operation on a data item."""

    model_config = {"arbitrary_types_allowed": True}

    type: OperationType
    device: Device

from pydantic import ConfigDict

from wrench.models import CommonMetadata, Device, Group
from wrench.pipeline.component import DataModel
from wrench.pipeline.types import Operation


class Items[T: Device](DataModel):
    devices: list[T]
    operations: list[Operation] = []
    model_config = ConfigDict(arbitrary_types_allowed=True)


class Groups(DataModel):
    groups: list[Group]


class Metadata(DataModel):
    service_metadata: CommonMetadata | None
    group_metadata: list[CommonMetadata]

from typing import Sequence

from pydantic import ConfigDict

from wrench.models import CommonMetadata, Group, Item
from wrench.pipeline.component import DataModel
from wrench.pipeline.types import Operation


class Items[T: Item](DataModel):
    devices: Sequence[T]
    operations: list[Operation] = []
    model_config = ConfigDict(arbitrary_types_allowed=True)


class Groups(DataModel):
    groups: Sequence[Group]


class Metadata(DataModel):
    service_metadata: CommonMetadata | None
    group_metadata: list[CommonMetadata]

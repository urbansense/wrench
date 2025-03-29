from typing import Sequence

from pydantic import ConfigDict

from wrench.models import CommonMetadata, Group, Item
from wrench.pipeline.component import DataModel
from wrench.pipeline.types import Operation


class Items[T: Item](DataModel):
    devices: Sequence[T]
    operations: list[Operation] = []
    model_config = ConfigDict(arbitrary_types_allowed=True)

    def model_dump(self, **kwargs):
        result = super().model_dump(**kwargs)

        if hasattr(self, "devices") and self.devices:
            result["devices"] = []
            for device in self.devices:
                if hasattr(device, "model_dump"):
                    # Force include extra fields
                    device_dict = device.model_dump(by_alias=True, exclude_none=False)
                    result["devices"].append(device_dict)
                else:
                    result["devices"].append(device)

        return result


class Groups(DataModel):
    groups: Sequence[Group]


class Metadata(DataModel):
    service_metadata: CommonMetadata | None
    group_metadata: list[CommonMetadata]

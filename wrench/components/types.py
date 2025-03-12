from typing import Sequence

from wrench.models import Group
from wrench.pipeline.component import DataModel


class Items(DataModel):
    devices: Sequence[dict]


class Groups(DataModel):
    groups: Sequence[Group]

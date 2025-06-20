from functools import cached_property

from pydantic import BaseModel, PrivateAttr

from wrench.models import Device


class Topic(BaseModel):
    cluster_id: str
    name: str
    description: str
    parent_topics: list[str]
    keywords: list[str]

    def __hash__(self):
        """Use topic name as unique identifier for hashing."""
        return hash(self.name)

    def __eq__(self, other):
        """Topics are equal if their names as the same."""
        if not isinstance(other, Topic):
            return False
        return self.name == other.name

    def __repr__(self):
        return f"<Topic: {self.name}>"


class TopicList(BaseModel):
    topics: list[Topic]


class Cluster(BaseModel):
    cluster_id: str
    keywords: list[str]
    _devices: list[Device] | None = PrivateAttr(default=None)

    @cached_property
    def representative_devices(self) -> list[Device]:
        if self._devices is None:
            raise ValueError("run classifier before creating representative devices")
        unique_ds = set()
        repr_device = set()
        for d in self._devices:
            for ds in d.datastreams:
                if ds in unique_ds:
                    continue
                unique_ds.add(ds)
                repr_device.add(d)

        return list(repr_device)[:3]

    def __str__(self):
        return f"""Cluster_ID: {self.cluster_id}:
                    Keywords: {self.keywords}
                    Documents: {
            "\n\n".join(
                dev.to_string(
                    exclude=[
                        "id",
                        "locations",
                        "time_frame",
                        "properties",
                        "_raw_data",
                        "sensors",
                        "datastreams",
                    ]
                )
                for dev in self.representative_devices
            )
        }
                """

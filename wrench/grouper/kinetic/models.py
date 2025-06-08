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

    def __str__(self):
        return f"""Cluster_ID: {self.cluster_id}:
                    Keywords: {self.keywords}
                    Documents: {
            (
                "{name} {description} {properties}".format(
                    name=self._devices[0].name,
                    description=self._devices[0].description,
                    properties=str(self._devices[0].observed_properties),
                ),
            )
        }
                """

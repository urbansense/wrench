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
        return """Cluster_ID: {id}:
                    Keywords: {kw}
                    Documents: {sample_doc}
                """.format(
            id=self.cluster_id,
            kw=str(self.keywords),
            sample_doc="{name} {description} {properties}".format(
                name=self._devices[0].name,
                description=self._devices[0].description,
                properties=str(self._devices[0].observed_properties),
            ),
        )

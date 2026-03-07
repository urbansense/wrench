"""Tracer module for exporting KINETIC pipeline data to JSON."""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import networkx as nx

from .models import Cluster


@dataclass
class DocumentTrace:
    """Trace data for a single document."""

    doc_id: int
    text: str
    keywords: list[str]


@dataclass
class NetworkTrace:
    """Trace data for the co-occurrence network."""

    nodes: list[str]
    edges: list[dict[str, Any]]  # {"source": str, "target": str, "weight": int}
    partitions: dict[str, int]  # keyword -> community_id


@dataclass
class ClusterTrace:
    """Trace data for a cluster."""

    cluster_id: str
    keywords: list[str]
    document_ids: list[int] = field(default_factory=list)


@dataclass
class TopicTrace:
    """Trace data for a generated topic."""

    name: str
    description: str
    cluster_ids: list[str]
    keywords: list[str]
    parent_topics: list[str]


@dataclass
class KineticTrace:
    """Complete trace of a KINETIC pipeline run."""

    documents: list[DocumentTrace] = field(default_factory=list)
    network: NetworkTrace | None = None
    clusters: list[ClusterTrace] = field(default_factory=list)
    topics: list[TopicTrace] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert trace to dictionary."""
        return {
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "num_documents": len(self.documents),
                "num_clusters": len(self.clusters),
                "num_topics": len(self.topics),
                **self.metadata,
            },
            "documents": [
                {"doc_id": d.doc_id, "text": d.text, "keywords": d.keywords}
                for d in self.documents
            ],
            "cooccurrence_network": (
                {
                    "nodes": self.network.nodes,
                    "edges": self.network.edges,
                    "partitions": self.network.partitions,
                }
                if self.network
                else None
            ),
            "clusters": [
                {
                    "cluster_id": c.cluster_id,
                    "keywords": c.keywords,
                    "document_ids": c.document_ids,
                }
                for c in self.clusters
            ],
            "topics": [
                {
                    "name": t.name,
                    "description": t.description,
                    "cluster_ids": t.cluster_ids,
                    "keywords": t.keywords,
                    "parent_topics": t.parent_topics,
                }
                for t in self.topics
            ],
        }

    def to_json(self, indent: int = 2) -> str:
        """Convert trace to JSON string."""
        return json.dumps(
            self.to_dict(), indent=indent, ensure_ascii=False, default=_json_default
        )

    def save(self, path: str | Path) -> None:
        """Save trace to a JSON file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.to_json())


def _json_default(obj):
    """Handle non-JSON-serializable objects."""
    import numpy as np

    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, (np.integer, np.floating)):
        return obj.item()
    if isinstance(obj, np.bool_):
        return bool(obj)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


class KineticTracer:
    """Tracer for capturing KINETIC pipeline execution data."""

    def __init__(self):
        self.trace = KineticTrace()

    def trace_documents(self, docs: list[str], keywords_per_doc: list[list[str]]):
        """Record document texts and their extracted keywords."""
        self.trace.documents = [
            DocumentTrace(doc_id=i, text=doc, keywords=kws)
            for i, (doc, kws) in enumerate(zip(docs, keywords_per_doc))
        ]

    def trace_network(self, graph: nx.Graph, partition: dict[str, int]):
        """Record the co-occurrence network structure."""
        edges = [
            {"source": str(u), "target": str(v), "weight": int(data.get("weight", 1))}
            for u, v, data in graph.edges(data=True)
        ]
        # Convert partition values to native Python ints
        clean_partition = {str(k): int(v) for k, v in partition.items()}
        self.trace.network = NetworkTrace(
            nodes=[str(n) for n in graph.nodes()],
            edges=edges,
            partitions=clean_partition,
        )

    def trace_clusters(self, clusters: list[Cluster]):
        """Record cluster information."""
        self.trace.clusters = [
            ClusterTrace(cluster_id=c.cluster_id, keywords=c.keywords) for c in clusters
        ]

    def trace_topics(self, topics):
        """Record generated topics with their cluster mappings.

        Args:
            topics: List of Topic objects from the LLM topic generator.
        """
        self.trace.topics = [
            TopicTrace(
                name=t.name,
                description=t.description,
                cluster_ids=[t.cluster_id],
                keywords=t.keywords,
                parent_topics=list(t.parent_topics),
            )
            for t in topics
        ]

    def trace_classification(self, doc_ids: list):
        """Record which documents were classified into which clusters."""
        for cluster_trace, ids in zip(self.trace.clusters, doc_ids):
            cluster_trace.document_ids = list(ids)

    def set_metadata(self, **kwargs):
        """Set additional metadata for the trace."""
        self.trace.metadata.update(kwargs)

    def get_trace(self) -> KineticTrace:
        """Get the complete trace."""
        return self.trace

    def save(self, path: str | Path) -> None:
        """Save the trace to a JSON file."""
        self.trace.save(path)

    def reset(self):
        """Reset the tracer for a new run."""
        self.trace = KineticTrace()

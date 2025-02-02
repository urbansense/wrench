from typing import Any

import networkx as nx
from pydantic import BaseModel, Field


class LLMConfig(BaseModel):
    """Configuration for the LLM service"""

    host: str = Field(description="LLM service host URL")
    model: str = Field(description="Model to use for LLM enrichment")
    prompt: str = Field(
        default=None, description="Prompt to generate key terms for enrichment"
    )
    temperature: float = Field(
        default=0.1, description="Temperature for LLM generation"
    )


class EmbeddingConfig(BaseModel):
    """Configuration for the embedding service"""

    model_name: str = Field(
        default="all-mpnet-base-v2",
        description="Name of the sentence transformer model",
    )


class CorpusConfig(BaseModel):
    """Configuration for corpus enrichment"""

    phrase_extractor: str = Field(
        default="yake", description="Phrase extraction method (keybert or yake)"
    )
    top_n: int = Field(default=5, description="Number of top phrases to extract")


class CacheConfig(BaseModel):
    """Configuration for caching"""

    enabled: bool = Field(default=True, description="Whether to enable caching")
    directory: str = Field(
        default=".teleclass_cache", description="Directory for cache files"
    )


class TaxonomyMetadata(BaseModel):
    """Metadata about the taxonomy"""

    name: str = Field(default="", description="Name of the taxonomy")
    description: str = Field(
        default="", description="Description of the taxonomy's purpose"
    )


class TELEClassConfig(BaseModel):
    """Main configuration for TELEClass"""

    llm: LLMConfig
    embedding: EmbeddingConfig = Field(default_factory=EmbeddingConfig)
    corpus: CorpusConfig = Field(default_factory=CorpusConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)
    taxonomy_metadata: TaxonomyMetadata = Field(
        description="Metadata about the taxonomy"
    )
    taxonomy: list[dict[str, Any]] = Field(
        description="Taxonomy structure in hierarchical format"
    )

    def build_taxonomy_graph(self) -> nx.DiGraph:
        """
        Convert taxonomy configuration into a NetworkX DiGraph

        Args:
            config: TELEClass configuration containing taxonomy structure

        Returns:
            NetworkX DiGraph representing the taxonomy
        """
        G = nx.DiGraph()

        def add_nodes_recursive(parent: str, node_list: list[Any]):
            if not node_list:
                return

            for item in node_list:
                if isinstance(item, dict):
                    # Check if this is a node with metadata
                    if "name" in item and "description" in item:
                        node_name = item["name"]
                        description = item["description"]
                        children = item.get("children", [])
                    else:
                        # Traditional format with single key and children
                        node_name = next(iter(item.keys()))
                        description = ""
                        children = item[node_name]

                    # Add edge from parent to current node
                    G.add_edge(parent, node_name)

                    # Store node attributes
                    G.nodes[node_name]["description"] = description

                    # Recursively add children if they exist
                    if children:
                        add_nodes_recursive(node_name, children)
                elif isinstance(item, str):
                    # Handle leaf nodes (strings)
                    G.add_edge(parent, item)

        # Add root node
        root_name = "root"
        G.add_node(root_name)

        # Process the node hierarchy starting from root
        add_nodes_recursive(root_name, self.taxonomy)

        # Validate the graph
        if not nx.is_directed_acyclic_graph(G):
            raise ValueError("Taxonomy contains cycles, which are not allowed")

        if len(G.nodes()) < 2:
            raise ValueError("Taxonomy must contain at least one node besides root")

        # Get first level nodes (children of root)
        root_children = list(G.successors(root_name))

        # Remove the root node
        G.remove_node(root_name)

        # Update graph validation
        if len(root_children) < 1:
            raise ValueError("Taxonomy must contain at least one top-level node")

        return G

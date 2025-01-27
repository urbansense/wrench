from pathlib import Path
from typing import Any, Dict, List

import networkx as nx
import yaml
from ollama import Client
from pydantic import BaseModel, Field

from autoreg_metadata.classifier.teleclass.core.embeddings import EmbeddingService
from autoreg_metadata.classifier.teleclass.core.taxonomy_manager import TaxonomyManager
from autoreg_metadata.classifier.teleclass.core.teleclass import TELEClass
from autoreg_metadata.classifier.teleclass.enrichment.corpus import CorpusEnricher
from autoreg_metadata.classifier.teleclass.enrichment.llm import LLMEnricher


class LLMConfig(BaseModel):
    """Configuration for the LLM service"""
    host: str = Field(default="http://localhost:11434", description="LLM service host URL")
    model: str = Field(default="llama2:3b-instruct", description="Model to use for LLM enrichment")
    temperature: float = Field(default=0.1, description="Temperature for LLM generation")


class EmbeddingConfig(BaseModel):
    """Configuration for the embedding service"""
    model_name: str = Field(
        default="all-mpnet-base-v2", 
        description="Name of the sentence transformer model"
    )


class CorpusConfig(BaseModel):
    """Configuration for corpus enrichment"""
    phrase_extractor: str = Field(
        default="keybert",
        description="Phrase extraction method (keybert or yake)"
    )
    top_n: int = Field(default=5, description="Number of top phrases to extract")


class CacheConfig(BaseModel):
    """Configuration for caching"""
    enabled: bool = Field(default=True, description="Whether to enable caching")
    directory: str = Field(
        default=".teleclass_cache",
        description="Directory for cache files"
    )


class TaxonomyNode(BaseModel):
    """Represents a node in the taxonomy"""
    name: str
    children: List['TaxonomyNode'] = Field(default_factory=list)


class TELEClassConfig(BaseModel):
    """Main configuration for TELEClass"""
    llm: LLMConfig = Field(default_factory=LLMConfig)
    embedding: EmbeddingConfig = Field(default_factory=EmbeddingConfig)
    corpus: CorpusConfig = Field(default_factory=CorpusConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)
    taxonomy: Dict[str, List[Dict[str, Any]]] = Field(
        ...,
        description="Taxonomy structure in hierarchical format"
    )


def build_taxonomy_graph(taxonomy_dict: Dict[str, List[Dict[str, Any]]]) -> nx.DiGraph:
    """
    Convert taxonomy dictionary from YAML into a NetworkX DiGraph
    
    Args:
        taxonomy_dict: Dictionary representing taxonomy hierarchy
        
    Returns:
        NetworkX DiGraph representing the taxonomy
    """
    G = nx.DiGraph()
    
    def add_nodes_recursive(parent: str, children: List[Dict[str, Any]]):
        for child in children:
            for child_name, grandchildren in child.items():
                G.add_edge(parent, child_name)
                if grandchildren:
                    add_nodes_recursive(child_name, grandchildren)
    
    # Add root node and its children
    root_name = "root"
    G.add_node(root_name)
    for category in taxonomy_dict["taxonomy"]:
        for category_name, subcategories in category.items():
            G.add_edge(root_name, category_name)
            if subcategories:
                add_nodes_recursive(category_name, subcategories)
    
    return G
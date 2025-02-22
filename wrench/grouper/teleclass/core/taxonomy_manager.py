from typing import Any

import networkx as nx


class TaxonomyManager:
    """Manages taxonomy operations and caching."""

    @classmethod
    def from_config(cls, taxonomy: list[dict[str, Any]]) -> "TaxonomyManager":
        """Create from TELEClassConfig."""
        graph = cls._build_graph(taxonomy)
        return cls(graph)

    @staticmethod
    def _build_graph(taxonomy: list[dict]) -> nx.DiGraph:
        """
        Convert taxonomy configuration into a NetworkX DiGraph.

        Args:
            taxonomy: Taxonomy structure contained in TELEClass Config

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
                        try:
                            node_name = next(iter(item.keys()))
                            description = ""
                            children = item[node_name]
                        except (StopIteration, AttributeError) as e:
                            raise ValueError(
                                f"Invalid taxonomy node structure: {str(e)}"
                            ) from e

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
        add_nodes_recursive(root_name, taxonomy)

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

    def __init__(self, taxonomy: nx.DiGraph):
        """
        Initializes the TaxonomyManager with a given taxonomy graph.

        Args:
            taxonomy (nx.DiGraph): A directed graph representing the taxonomy.

        Attributes:
            taxonomy (nx.DiGraph): The directed graph representing the taxonomy.
            root_nodes (list): A list of root nodes in the taxonomy.
            max_depth (int): The maximum depth of the taxonomy.
        """
        self.taxonomy = taxonomy
        self.root_nodes = self._find_root_nodes()
        self.max_depth = self._calculate_max_depth()

    def _find_root_nodes(self) -> list[str]:
        """Find all root nodes in the taxonomy."""
        return [
            node for node in self.taxonomy.nodes() if self.taxonomy.in_degree(node) == 0
        ]

    def get_all_classes(self) -> list[str]:
        """Get all classes and their description if they exist in the taxonomy."""
        return list(self.taxonomy.nodes())

    def get_all_classes_with_description(self) -> dict[str, str]:
        """Get all classes including their descriptions in the taxonomy."""
        node_w_desc: dict[str, str] = {}
        for node in list(self.taxonomy.nodes()):
            if "description" in self.taxonomy.nodes[node]:
                node_w_desc[node] = self.taxonomy.nodes[node]["description"]
            else:
                node_w_desc[node] = ""

        return node_w_desc

    def _calculate_max_depth(self) -> int:
        """Calculate the maximum depth of the taxonomy."""
        return nx.dag_longest_path_length(self.taxonomy)

    def get_ancestors(self, node: str) -> set[str]:
        """Get all ancestors of a node."""
        return set(nx.ancestors(self.taxonomy, node))

    def get_parents(self, node: str) -> set[str]:
        """Get all parents of a node."""
        return set(self.taxonomy.predecessors(node))

    def get_siblings(self, node: str) -> set[str]:
        """Get siblings of a node across all parents."""
        siblings = set()
        for parent in self.taxonomy.predecessors(node):
            siblings.update(self.taxonomy.successors(parent))
        siblings.discard(node)
        return siblings

    def get_leaf_nodes(self) -> set[str]:
        """
        Find all leaf nodes (nodes with no children) in the taxonomy.

        Returns a set of node names that are leaves.
        """
        return {
            node
            for node in self.taxonomy.nodes()
            if self.taxonomy.out_degree(node) == 0
        }

    def get_all_paths(self) -> list[list[str]]:
        """
        Get all meaningful paths from level-1 nodes to leaf nodes in the taxonomy.

        A meaningful path starts from a non-root node (level-1) and goes to a leaf node.

        Returns:
            list of paths, where each path is a list of node names from level-1 to leaf.
        """
        # Get leaf nodes
        leaf_nodes = self.get_leaf_nodes()
        all_paths = []

        # For each leaf node, find all simple paths from root nodes
        for leaf in leaf_nodes:
            for root in self.root_nodes:
                # Find all simple paths from root to this leaf
                paths = list(nx.all_simple_paths(self.taxonomy, root, leaf))

                # For each path, extract the portion from level-1 to leaf
                for path in paths:
                    # Skip root node (index 0) to get path from level-1
                    meaningful_path = path[1:]  # Exclude root node
                    if meaningful_path:  # Check if path is not empty
                        all_paths.append(meaningful_path)

        # Remove duplicates while preserving order
        unique_paths = []
        seen = set()
        for path in all_paths:
            path_tuple = tuple(path)  # Convert to tuple for hashing
            if path_tuple not in seen:
                seen.add(path_tuple)
                unique_paths.append(path)

        return unique_paths

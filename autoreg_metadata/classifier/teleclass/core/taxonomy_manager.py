import networkx as nx


class TaxonomyManager:
    """Manages taxonomy operations and caching"""

    def __init__(self, taxonomy: nx.DiGraph):
        self.taxonomy = taxonomy
        self.root_nodes = self._find_root_nodes()
        self.max_depth = self._calculate_max_depth()

    def _find_root_nodes(self) -> list[str]:
        """Find all root nodes in the taxonomy"""
        return [node for node in self.taxonomy.nodes()
                if self.taxonomy.in_degree(node) == 0]

    def get_all_classes(self) -> list[str]:
        """Get all classes in the taxonomy"""
        return list(self.taxonomy.nodes())

    def _calculate_max_depth(self) -> int:
        """Calculate the maximum depth of the taxonomy"""
        return nx.dag_longest_path_length(self.taxonomy)

    def get_ancestors(self, node: str) -> set[str]:
        """Get all ancestors of a node"""
        return set(nx.ancestors(self.taxonomy, node))

    def get_parents(self, node: str) -> set[str]:
        """Get all parents of a node"""
        return set(self.taxonomy.predecessors(node))

    def get_siblings(self, node: str) -> set[str]:
        """Get siblings of a node across all parents"""
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
            node for node in self.taxonomy.nodes()
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

import pytest

from wrench.pipeline.pipeline_graph import PipelineEdge, PipelineGraph, PipelineNode


@pytest.fixture()
def graph():
    return PipelineGraph()


@pytest.fixture()
def node_a():
    return PipelineNode("a")


@pytest.fixture()
def node_b():
    return PipelineNode("b")


@pytest.fixture()
def node_c():
    return PipelineNode("c")


class TestPipelineNode:
    def test_is_root_when_no_parents(self, node_a):
        assert node_a.is_root() is True

    def test_is_not_root_when_has_parents(self, node_a):
        node_a.parents.append("other")
        assert node_a.is_root() is False

    def test_is_leaf_when_no_children(self, node_a):
        assert node_a.is_leaf() is True

    def test_is_not_leaf_when_has_children(self, node_a):
        node_a.children.append("other")
        assert node_a.is_leaf() is False


class TestPipelineGraphAddNode:
    def test_add_node_success(self, graph, node_a):
        graph.add_node(node_a)
        assert "a" in graph

    def test_add_duplicate_node_raises(self, graph, node_a):
        graph.add_node(node_a)
        with pytest.raises(ValueError, match="already exists"):
            graph.add_node(PipelineNode("a"))


class TestPipelineGraphSetNode:
    def test_set_node_replaces_existing(self, graph, node_a):
        graph.add_node(node_a)
        replacement = PipelineNode("a")
        graph.set_node(replacement)
        assert graph.get_node_by_name("a") is replacement

    def test_set_node_missing_raises(self, graph):
        with pytest.raises(ValueError, match="does not exist"):
            graph.set_node(PipelineNode("nonexistent"))

    def test_set_node_preserves_connections(self, graph, node_a, node_b):
        graph.add_node(node_a)
        graph.add_node(node_b)
        edge = PipelineEdge("a", "b", {})
        graph.add_edge(edge)

        replacement = PipelineNode("a")
        graph.set_node(replacement)
        assert replacement.children == ["b"]


class TestPipelineGraphAddEdge:
    def test_add_edge_success(self, graph, node_a, node_b):
        graph.add_node(node_a)
        graph.add_node(node_b)
        edge = PipelineEdge("a", "b", {})
        graph.add_edge(edge)
        assert "a" in node_b.parents
        assert "b" in node_a.children

    def test_add_edge_missing_start_raises(self, graph, node_b):
        graph.add_node(node_b)
        with pytest.raises(KeyError, match="does not exist"):
            graph.add_edge(PipelineEdge("nonexistent", "b", {}))

    def test_add_edge_missing_end_raises(self, graph, node_a):
        graph.add_node(node_a)
        with pytest.raises(KeyError, match="does not exist"):
            graph.add_edge(PipelineEdge("a", "nonexistent", {}))

    def test_add_duplicate_edge_raises(self, graph, node_a, node_b):
        graph.add_node(node_a)
        graph.add_node(node_b)
        graph.add_edge(PipelineEdge("a", "b", {}))
        with pytest.raises(ValueError, match="already connected"):
            graph.add_edge(PipelineEdge("a", "b", {}))


class TestPipelineGraphTraversal:
    def test_roots_returns_parentless_nodes(self, graph, node_a, node_b, node_c):
        graph.add_node(node_a)
        graph.add_node(node_b)
        graph.add_node(node_c)
        graph.add_edge(PipelineEdge("a", "b", {}))
        graph.add_edge(PipelineEdge("a", "c", {}))
        roots = graph.roots()
        assert len(roots) == 1
        assert roots[0].name == "a"

    def test_leaves_returns_childless_nodes(self, graph, node_a, node_b, node_c):
        graph.add_node(node_a)
        graph.add_node(node_b)
        graph.add_node(node_c)
        graph.add_edge(PipelineEdge("a", "b", {}))
        graph.add_edge(PipelineEdge("a", "c", {}))
        leaves = graph.leaves()
        leaf_names = {n.name for n in leaves}
        assert leaf_names == {"b", "c"}

    def test_next_edges(self, graph, node_a, node_b, node_c):
        graph.add_node(node_a)
        graph.add_node(node_b)
        graph.add_node(node_c)
        graph.add_edge(PipelineEdge("a", "b", {}))
        graph.add_edge(PipelineEdge("a", "c", {}))
        edges = graph.next_edges("a")
        assert len(edges) == 2
        ends = {e.end for e in edges}
        assert ends == {"b", "c"}

    def test_previous_edges(self, graph, node_a, node_b, node_c):
        graph.add_node(node_a)
        graph.add_node(node_b)
        graph.add_node(node_c)
        graph.add_edge(PipelineEdge("a", "c", {}))
        graph.add_edge(PipelineEdge("b", "c", {}))
        edges = graph.previous_edges("c")
        assert len(edges) == 2
        starts = {e.start for e in edges}
        assert starts == {"a", "b"}

    def test_next_edges_empty(self, graph, node_a):
        graph.add_node(node_a)
        assert graph.next_edges("a") == []

    def test_previous_edges_empty(self, graph, node_a):
        graph.add_node(node_a)
        assert graph.previous_edges("a") == []


class TestPipelineGraphContains:
    def test_contains_by_node_object(self, graph, node_a):
        graph.add_node(node_a)
        assert node_a in graph

    def test_contains_by_string(self, graph, node_a):
        graph.add_node(node_a)
        assert "a" in graph

    def test_not_contains(self, graph):
        assert "nonexistent" not in graph


class TestPipelineGraphCycleDetection:
    def test_linear_chain_not_cyclic(self, graph, node_a, node_b, node_c):
        graph.add_node(node_a)
        graph.add_node(node_b)
        graph.add_node(node_c)
        graph.add_edge(PipelineEdge("a", "b", {}))
        graph.add_edge(PipelineEdge("b", "c", {}))
        assert graph.is_cyclic() is False

    def test_diamond_not_cyclic(self, graph):
        for name in ["a", "b", "c", "d"]:
            graph.add_node(PipelineNode(name))
        graph.add_edge(PipelineEdge("a", "b", {}))
        graph.add_edge(PipelineEdge("a", "c", {}))
        graph.add_edge(PipelineEdge("b", "d", {}))
        graph.add_edge(PipelineEdge("c", "d", {}))
        assert graph.is_cyclic() is False

    def test_cycle_detected(self, graph, node_a, node_b):
        graph.add_node(node_a)
        graph.add_node(node_b)
        graph.add_edge(PipelineEdge("a", "b", {}))
        # Manually create cycle by bypassing validation
        graph._edges.append(PipelineEdge("b", "a", {}))
        graph._nodes["a"].parents.append("b")
        graph._nodes["b"].children.append("a")
        assert graph.is_cyclic() is True

    def test_single_node_not_cyclic(self, graph, node_a):
        graph.add_node(node_a)
        assert graph.is_cyclic() is False

    def test_empty_graph_not_cyclic(self, graph):
        assert graph.is_cyclic() is False

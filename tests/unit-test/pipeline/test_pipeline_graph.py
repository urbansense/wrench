import pytest

from wrench.pipeline.pipeline_graph import PipelineEdge, PipelineGraph, PipelineNode


class MockNode(PipelineNode):
    pass


class MockEdge(PipelineEdge):
    pass


@pytest.fixture
def graph():
    return PipelineGraph[MockNode, MockEdge]()


def test_add_node(graph):
    """Test adding nodes to the graph."""
    node = MockNode("test-node")
    graph.add_node(node)

    assert "test-node" in graph._nodes
    assert graph._nodes["test-node"] is node


def test_add_duplicate_node(graph):
    """Test adding a duplicate node raises an error."""
    node = MockNode("test-node")
    graph.add_node(node)

    with pytest.raises(ValueError):
        graph.add_node(MockNode("test-node"))


def test_set_node(graph):
    """Test replacing an existing node."""
    node1 = MockNode("test-node")
    graph.add_node(node1)

    # Add connections
    graph.add_node(MockNode("other-node"))
    graph.add_edge(MockEdge("test-node", "other-node", {}))

    # Replace the node
    node2 = MockNode("test-node")
    graph.set_node(node2)

    # Check node was replaced but connections preserved
    assert graph._nodes["test-node"] is node2
    assert "other-node" in graph._nodes["test-node"].children


def test_set_nonexistent_node(graph):
    """Test replacing a non-existent node raises an error."""
    with pytest.raises(ValueError):
        graph.set_node(MockNode("nonexistent"))


def test_add_edge(graph):
    """Test adding edges between nodes."""
    graph.add_node(MockNode("node1"))
    graph.add_node(MockNode("node2"))

    edge = MockEdge("node1", "node2", {"data": "test"})
    graph.add_edge(edge)

    assert edge in graph._edges
    assert "node2" in graph._nodes["node1"].children
    assert "node1" in graph._nodes["node2"].parents


def test_add_edge_nonexistent_node(graph):
    """Test adding an edge with non-existent nodes raises an error."""
    graph.add_node(MockNode("node1"))

    with pytest.raises(KeyError):
        graph.add_edge(MockEdge("node1", "nonexistent", {}))

    with pytest.raises(KeyError):
        graph.add_edge(MockEdge("nonexistent", "node1", {}))


def test_add_duplicate_edge(graph):
    """Test adding a duplicate edge raises an error."""
    graph.add_node(MockNode("node1"))
    graph.add_node(MockNode("node2"))

    graph.add_edge(MockEdge("node1", "node2", {}))

    with pytest.raises(ValueError):
        graph.add_edge(MockEdge("node1", "node2", {"different": "data"}))


def test_roots(graph):
    """Test identifying root nodes."""
    graph.add_node(MockNode("root1"))
    graph.add_node(MockNode("root2"))
    graph.add_node(MockNode("child"))

    graph.add_edge(MockEdge("root1", "child", {}))
    graph.add_edge(MockEdge("root2", "child", {}))

    roots = graph.roots()
    root_names = [node.name for node in roots]

    assert len(roots) == 2
    assert "root1" in root_names
    assert "root2" in root_names
    assert "child" not in root_names


def test_leaves(graph):
    """Test identifying leaf nodes."""
    graph.add_node(MockNode("root"))
    graph.add_node(MockNode("middle"))
    graph.add_node(MockNode("leaf1"))
    graph.add_node(MockNode("leaf2"))

    graph.add_edge(MockEdge("root", "middle", {}))
    graph.add_edge(MockEdge("middle", "leaf1", {}))
    graph.add_edge(MockEdge("middle", "leaf2", {}))

    leaves = graph.leaves()
    leaf_names = [node.name for node in leaves]

    assert len(leaves) == 2
    assert "leaf1" in leaf_names
    assert "leaf2" in leaf_names
    assert "root" not in leaf_names
    assert "middle" not in leaf_names


def test_next_edges(graph):
    """Test getting outgoing edges."""
    graph.add_node(MockNode("source"))
    graph.add_node(MockNode("target1"))
    graph.add_node(MockNode("target2"))

    edge1 = MockEdge("source", "target1", {})
    edge2 = MockEdge("source", "target2", {})

    graph.add_edge(edge1)
    graph.add_edge(edge2)

    next_edges = graph.next_edges("source")

    assert len(next_edges) == 2
    assert edge1 in next_edges
    assert edge2 in next_edges


def test_previous_edges(graph):
    """Test getting incoming edges."""
    graph.add_node(MockNode("source1"))
    graph.add_node(MockNode("source2"))
    graph.add_node(MockNode("target"))

    edge1 = MockEdge("source1", "target", {})
    edge2 = MockEdge("source2", "target", {})

    graph.add_edge(edge1)
    graph.add_edge(edge2)

    prev_edges = graph.previous_edges("target")

    assert len(prev_edges) == 2
    assert edge1 in prev_edges
    assert edge2 in prev_edges


def test_is_cyclic_no_cycle(graph):
    """Test cycle detection with no cycles."""
    graph.add_node(MockNode("A"))
    graph.add_node(MockNode("B"))
    graph.add_node(MockNode("C"))

from collections import defaultdict

import community as cd
import matplotlib.pyplot as plt
import networkx as nx

from .models import Cluster


def build_cooccurence_network(
    keywords_per_doc: list[list[str]], top_n=7
) -> list[Cluster]:
    """Builds a keyword co-occurrence network and visualizes it.

    The function identifies communities (clusters) of keywords and extracts the most
    central keywords from each community.

    Args:
        keywords_per_doc: A list of lists, where each inner list contains keywords
                          for a specific document.
        top_n: Number of most central keywords from the cluster. Defaults to 7

    Returns:
        A dictionary where keys are cluster identifiers (e.g., 'cluster_0') and
        values are lists of the top n most central keywords in that cluster.
    """
    G = nx.Graph()

    for kw_list in keywords_per_doc:
        for i, kw in enumerate(kw_list):
            for other in kw_list[i + 1 :]:
                if G.has_edge(kw, other):
                    G[kw][other]["weight"] += 1
                else:
                    G.add_edge(kw, other, weight=1)

    partition = cd.best_partition(G, weight="weight")

    comms = defaultdict(list)
    for node, comm_id in partition.items():
        comms[comm_id].append(node)

    essential = {}
    for comm_id, kws in comms.items():
        # compute weighted degree
        deg = {kw: G.degree(kw, weight="weight") for kw in kws}
        top = sorted(deg, key=deg.get, reverse=True)[:top_n]
        essential[f"cluster_{comm_id}"] = top

    visualize_cooccurence_network(G, partition)

    return [
        Cluster(cluster_id=id, keywords=keywords) for id, keywords in essential.items()
    ]


def visualize_cooccurence_network(G: nx.Graph, partition: dict):
    """
    Visualizes the cooccurence graph.

    Displays the detected partitions in the graph.

    Args:
        G (nx.Graph): Graph containing nodes of keywords.
        partition (dict): Partitioned nodes.
    """
    centrality = dict(G.degree(weight="weight"))

    # Generate positions for all nodes
    pos = nx.spring_layout(G, weight="weight", seed=42)

    # Extract community IDs and centrality values
    colors = [partition[node] for node in G.nodes()]
    # Adjust node sizes: ensure a minimum size and scale by centrality
    sizes = [max(100, centrality.get(node, 0) * 300) for node in G.nodes()]

    # Draw nodes
    nx.draw_networkx_nodes(G, pos, node_color=colors, node_size=sizes, cmap=plt.cm.Set3)

    # Draw edges
    nx.draw_networkx_edges(G, pos, alpha=0.5)

    # Draw labels
    nx.draw_networkx_labels(G, pos, font_size=6)

    # Display the plot
    plt.axis("off")
    plt.show()

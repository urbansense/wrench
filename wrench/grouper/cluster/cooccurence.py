from collections import defaultdict

import community as cd
import networkx as nx


def build_cooccurence_network(keywords_per_doc: list[list[str]]) -> dict[str, list]:
    """Builds a keyword co-occurrence network and visualizes it.

    The function identifies communities (clusters) of keywords and extracts the most
    central keywords from each community.

    Args:
        keywords_per_doc: A list of lists, where each inner list contains keywords
                          for a specific document.

    Returns:
        A dictionary where keys are cluster identifiers (e.g., 'cluster_0') and
        values are lists of the top 5 most central keywords in that cluster.
    """
    G = nx.Graph()

    for kw_list in keywords_per_doc:
        for i, u in enumerate(kw_list):
            for v in kw_list[i + 1 :]:
                if G.has_edge(u, v):
                    G[u][v]["weight"] += 1
                else:
                    G.add_edge(u, v, weight=1)

    partition = cd.best_partition(G, weight="weight")

    comms = defaultdict(list)
    for node, comm_id in partition.items():
        comms[comm_id].append(node)

    essential = {}
    for comm_id, kws in comms.items():
        # compute weighted degree
        deg = {kw: G.degree(kw, weight="weight") for kw in kws}
        # select top 7 (or whatever you need)
        top5 = sorted(deg, key=deg.get, reverse=True)[:7]
        essential[f"cluster_{comm_id}"] = top5

    return essential

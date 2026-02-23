"""Shared metric computation for clustering evaluation."""

from __future__ import annotations

import json

from rich.table import Table

from tools.core.console import console


def dicts_to_labels(
    true_dict: dict,
    pred_dict: dict,
    handle_missing: str = "skip",
) -> tuple[list, list[int], list[int]]:
    """Convert cluster dictionaries to label arrays for sklearn metrics.

    Args:
        true_dict: Ground truth mapping (cluster name -> item IDs).
        pred_dict: Predicted mapping (cluster name -> item IDs).
        handle_missing: How to handle items missing from one dataset
            ("skip", "error", or "assign_new_cluster").

    Returns:
        Tuple of (item_ids, true_labels, predicted_labels).
    """
    all_items = set()
    for items in true_dict.values():
        all_items.update(items)
    for items in pred_dict.values():
        all_items.update(items)

    all_items = sorted(list(all_items))

    # Create reverse mappings
    true_item_to_cluster = {}
    for cluster, items in true_dict.items():
        for item in items:
            true_item_to_cluster[item] = cluster

    pred_item_to_cluster = {}
    for cluster, items in pred_dict.items():
        for item in items:
            pred_item_to_cluster[item] = cluster

    # Handle missing items
    if handle_missing == "skip":
        all_items = [
            item
            for item in all_items
            if item in true_item_to_cluster and item in pred_item_to_cluster
        ]
    elif handle_missing == "assign_new_cluster":
        next_true_cluster = f"missing_true_{len(true_dict)}"
        next_pred_cluster = f"missing_pred_{len(pred_dict)}"

        for item in all_items:
            if item not in true_item_to_cluster:
                true_item_to_cluster[item] = next_true_cluster
            if item not in pred_item_to_cluster:
                pred_item_to_cluster[item] = next_pred_cluster

    # Create label mappings
    all_true_clusters = list(set(true_item_to_cluster.values()))
    all_pred_clusters = list(set(pred_item_to_cluster.values()))

    true_cluster_to_label = {cluster: i for i, cluster in enumerate(all_true_clusters)}
    pred_cluster_to_label = {cluster: i for i, cluster in enumerate(all_pred_clusters)}

    # Create label arrays
    x = all_items
    y_true = [true_cluster_to_label[true_item_to_cluster[item]] for item in all_items]
    y_pred = [pred_cluster_to_label[pred_item_to_cluster[item]] for item in all_items]

    return x, y_true, y_pred


def compute_clustering_metrics(ground_truth_path: str, results: dict) -> dict | None:
    """Compute clustering metrics against ground truth.

    Args:
        ground_truth_path: Path to ground truth JSON file.
        results: Predicted clustering (topic name -> device IDs).

    Returns:
        Dict of metric scores, or None if computation fails.
    """
    try:
        from sklearn.metrics import (
            homogeneity_completeness_v_measure,
            normalized_mutual_info_score,
        )

        with open(ground_truth_path) as f:
            gt_data = json.load(f)

        x, y_true, y_pred = dicts_to_labels(gt_data, results, "skip")

        nmi = normalized_mutual_info_score(y_true, y_pred)
        h, c, v = homogeneity_completeness_v_measure(y_true, y_pred)

        return {
            "nmi": float(nmi),
            "homogeneity": float(h),
            "completeness": float(c),
            "v_measure": float(v),
            "items_compared": len(x),
        }
    except Exception as e:
        console.print(f"[yellow]Could not compute metrics: {e}[/yellow]")
        return None


def display_metrics(metrics: dict) -> None:
    """Display clustering metrics in a Rich table."""
    table = Table(title="Clustering Metrics")
    table.add_column("Metric", style="bold cyan")
    table.add_column("Score", style="magenta", justify="right")
    table.add_row("NMI", f"{metrics['nmi']:.4f}")
    table.add_row("Homogeneity", f"{metrics['homogeneity']:.4f}")
    table.add_row("Completeness", f"{metrics['completeness']:.4f}")
    table.add_row("V-Measure", f"{metrics['v_measure']:.4f}")
    table.add_row("Items Compared", str(metrics["items_compared"]))
    console.print(table)

"""HTML report generation for experiments."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def generate_doc_scores_html(
    doc_details: list[dict], cluster_labels: list[str], exp_id: str
) -> str:
    """Generate a scrollable HTML table of per-document similarity scores.

    Args:
        doc_details: List of per-document score dicts from KINETIC.
        cluster_labels: Cluster label strings.
        exp_id: Experiment identifier (used in title and output path).

    Returns:
        Path to the generated HTML file.
    """
    n_clusters = len(doc_details[0].get("combined_sims", []))
    labels = [
        cluster_labels[c] if c < len(cluster_labels) else f"C{c}"
        for c in range(n_clusters)
    ]

    # Build header
    header_cells = "<th>Device</th><th>Assigned Topic</th>"
    for lbl in labels:
        header_cells += f"<th>{lbl}<br><small>emb | sub | comb</small></th>"

    # Build rows
    rows = []
    for d, entry in enumerate(doc_details):
        device_name = entry.get("device_name", f"doc_{d}")
        assigned_topic = entry.get("assigned_topic", "—")
        emb = entry.get("embedding_sims", [])
        sub = entry.get("substring_sims", [])
        comb = entry.get("combined_sims", [])

        # Highlight the column with the highest combined score
        best_col = max(range(len(comb)), key=lambda c: comb[c]) if comb else -1

        cells = f"<td class='device-name'>{device_name}</td>"
        cells += f"<td><b>{assigned_topic}</b></td>"
        for c in range(n_clusters):
            e = f"{emb[c]:.3f}" if c < len(emb) else "—"
            s = f"{sub[c]:.3f}" if c < len(sub) else "—"
            cb = f"{comb[c]:.3f}" if c < len(comb) else "—"
            style = ' class="assigned"' if c == best_col else ""
            cells += f"<td{style}>{e} | {s} | {cb}</td>"

        rows.append(f"<tr>{cells}</tr>")

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Document Scores — {exp_id}</title>
<style>
    body {{ font-family: Arial, sans-serif; margin: 20px; }}
    h2 {{ color: #333; }}
    .table-wrap {{
        max-height: 85vh;
        overflow: auto;
        border: 1px solid #ddd;
    }}
    table {{
        border-collapse: collapse;
        font-size: 13px;
        width: 100%;
    }}
    th {{
        background: #f5f5f5;
        position: sticky;
        top: 0;
        z-index: 1;
        border: 1px solid #ddd;
        padding: 8px 6px;
        text-align: center;
    }}
    td {{
        border: 1px solid #eee;
        padding: 4px 6px;
        text-align: center;
        white-space: nowrap;
    }}
    tr:hover {{ background: #f0f8ff; }}
    .assigned {{
        background: #d4edda;
        font-weight: bold;
    }}
    tr:hover .assigned {{ background: #b8dfc8; }}
    .device-name {{
        position: sticky;
        left: 0;
        background: #fff;
        z-index: 1;
        font-weight: bold;
        text-align: left;
        border-right: 2px solid #ccc;
        max-width: 200px;
        overflow: hidden;
        text-overflow: ellipsis;
        resize: horizontal;
    }}
    tr:hover .device-name {{ background: #f0f8ff; }}
    th:first-child {{
        position: sticky;
        left: 0;
        z-index: 2;
    }}
</style>
</head>
<body>
<h2>Per-Document Similarity Scores — {exp_id}</h2>
<p>{len(doc_details)} documents, {n_clusters} clusters</p>
<div class="table-wrap">
<table>
<thead><tr>{header_cells}</tr></thead>
<tbody>
{"".join(rows)}
</tbody>
</table>
</div>
</body>
</html>"""

    out_path = Path(".experiments") / exp_id / "doc_scores.html"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        f.write(html)
    return str(out_path)


def generate_comparison_report(
    experiments: list[dict[str, Any]],
    results_list: list[dict[str, list[str]]],
    output_path: str,
) -> str:
    """Generate an interactive HTML report comparing experiments.

    Args:
        experiments: List of experiment metadata dicts.
        results_list: List of results dicts (topic -> device IDs) per experiment.
        output_path: Path to write the HTML report.

    Returns:
        Path to the generated HTML file.
    """
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    num_experiments = len(experiments)
    exp_names = [
        e.get("name", e.get("id", f"exp_{i}")) for i, e in enumerate(experiments)
    ]

    sections: list[str] = []

    # --- Section 1: Metrics bar chart ---
    metrics_available = any(e.get("metrics") for e in experiments)
    if metrics_available:
        metric_keys = ["nmi", "homogeneity", "completeness", "v_measure"]
        metric_labels = ["NMI", "Homogeneity", "Completeness", "V-Measure"]
        fig_metrics = go.Figure()

        for i, exp in enumerate(experiments):
            metrics = exp.get("metrics", {})
            values = [metrics.get(k, 0) for k in metric_keys]
            fig_metrics.add_trace(go.Bar(name=exp_names[i], x=metric_labels, y=values))

        fig_metrics.update_layout(
            title="Clustering Metrics Comparison",
            barmode="group",
            yaxis_title="Score",
            yaxis_range=[0, 1],
        )
        sections.append(fig_metrics.to_html(full_html=False, include_plotlyjs=False))

    # --- Section 2: Config diff table ---
    config_html = _build_config_diff_table(experiments, exp_names)
    sections.append(config_html)

    # --- Section 3: Topic distribution ---
    fig_topics = go.Figure()
    for i, results in enumerate(results_list):
        topics = sorted(results.keys())
        sizes = [len(results[t]) for t in topics]
        fig_topics.add_trace(go.Bar(name=exp_names[i], x=topics, y=sizes))

    fig_topics.update_layout(
        title="Topic Size Distribution",
        barmode="group",
        xaxis_title="Topic",
        yaxis_title="Number of Devices",
        xaxis_tickangle=-45,
    )
    sections.append(fig_topics.to_html(full_html=False, include_plotlyjs=False))

    # --- Section 4: Similarity heatmaps ---
    for i, exp in enumerate(experiments):
        sim_scores = exp.get("similarity_scores", {})
        cosine_data = sim_scores.get("cluster_cosine_similarity", {})
        matrix = cosine_data.get("matrix")
        if matrix:
            fig_heat = go.Figure(
                data=go.Heatmap(
                    z=matrix,
                    colorscale="Viridis",
                    colorbar_title="Cosine Sim",
                )
            )
            fig_heat.update_layout(
                title=f"Cluster Cosine Similarity — {exp_names[i]}",
                xaxis_title="Cluster",
                yaxis_title="Cluster",
            )
            sections.append(fig_heat.to_html(full_html=False, include_plotlyjs=False))

    # --- Assemble full HTML ---
    html = _wrap_html(sections, exp_names)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        f.write(html)

    return output_path


def _build_config_diff_table(experiments: list[dict], exp_names: list[str]) -> str:
    """Build an HTML table highlighting config differences."""
    configs = [e.get("config", {}) for e in experiments]
    all_keys = sorted({k for c in configs for k in c})

    rows: list[str] = []
    for key in all_keys:
        values = [_format_value(c.get(key, "—")) for c in configs]
        is_diff = len(set(values)) > 1
        style = ' style="background-color: #fff3cd;"' if is_diff else ""

        cells = "".join(f"<td{style}>{v}</td>" for v in values)
        rows.append(f"<tr><td><strong>{key}</strong></td>{cells}</tr>")

    headers = "".join(f"<th>{name}</th>" for name in exp_names)
    return f"""
    <h3>Configuration Comparison</h3>
    <table border="1" cellpadding="6" cellspacing="0" style="border-collapse: collapse; width: 100%;">
        <tr><th>Parameter</th>{headers}</tr>
        {"".join(rows)}
    </table>
    """


def _format_value(value: Any) -> str:
    """Format a config value for display."""
    if isinstance(value, dict):
        return json.dumps(value, default=str)
    return str(value)


def _wrap_html(sections: list[str], exp_names: list[str]) -> str:
    """Wrap plot sections into a full standalone HTML page."""
    title = "Experiment Comparison: " + " vs ".join(exp_names)
    body = "\n<hr>\n".join(sections)
    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{title}</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        h1 {{ color: #333; }}
        h3 {{ color: #555; margin-top: 30px; }}
        table {{ margin: 10px 0; font-size: 14px; }}
        th {{ background-color: #f0f0f0; }}
        hr {{ border: none; border-top: 1px solid #ddd; margin: 30px 0; }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    {body}
</body>
</html>"""

"""Experiment tracking CLI commands."""

from __future__ import annotations

import webbrowser
from datetime import datetime
from pathlib import Path

import click
from rich.table import Table

from tools.core.console import console
from tools.core.experiment import ExperimentTracker


@click.group()
def experiment():
    """Run, track, and compare KINETIC experiments."""
    pass


# ---------------------------------------------------------------------------
# experiment run
# ---------------------------------------------------------------------------


@experiment.command()
@click.argument("source")
@click.option(
    "--name", "-n", default=None, help="Experiment name (auto-generated if omitted)"
)
@click.option("--embedding-model", "-em", default=None, help="Embeddings model name")
@click.option("--llm-model", default=None, help="LLM model name")
@click.option("--llm-base-url", default=None, help="LLM base URL")
@click.option("--llm-api-key", default=None, help="LLM API key")
@click.option(
    "--keyword-extractor",
    type=click.Choice(["keybert", "yake"]),
    default="keybert",
    help="Keyword extractor to use",
)
@click.option("--keybert-top-n", type=int, default=7, help="KeyBERT top_n")
@click.option("--keybert-use-mmr", is_flag=True, help="Enable MMR in KeyBERT")
@click.option("--keybert-diversity", type=float, default=0.5, help="KeyBERT diversity")
@click.option("--resolution", "-r", type=int, default=1, help="Louvain resolution")
@click.option(
    "--cooccurrence-top-n", type=int, default=7, help="Co-occurrence top-n keywords"
)
@click.option(
    "--ground-truth",
    "-gt",
    type=click.Path(exists=True),
    default=None,
    help="Path to ground truth JSON for auto-metrics",
)
@click.option("--lang", type=click.Choice(["de", "en"]), default="de", help="Language")
@click.option(
    "--env", "-e", type=click.Path(), default=None, help="Load env from .env file"
)
def run(
    source: str,
    name: str | None,
    embedding_model: str | None,
    llm_model: str | None,
    llm_base_url: str | None,
    llm_api_key: str | None,
    keyword_extractor: str,
    keybert_top_n: int,
    keybert_use_mmr: bool,
    keybert_diversity: float,
    resolution: int,
    cooccurrence_top_n: int,
    ground_truth: str | None,
    lang: str,
    env: str | None,
):
    """Run a KINETIC experiment on a cached data source.

    SOURCE: name of the data source (e.g. osnabrueck, hamburg)
    """
    if env:
        from dotenv import load_dotenv

        load_dotenv(env)

    from wrench.grouper.kinetic.kinetic import KINETIC

    from tools.core.cache import DataCache
    from tools.core.config import resolve_llm_config
    from tools.core.metrics import compute_clustering_metrics, display_metrics

    if name is None:
        name = f"{source}_r{resolution}_{datetime.now().strftime('%H%M%S')}"

    console.print(f"[bold blue]Running experiment:[/bold blue] {name}\n")

    # Load devices
    cache = DataCache()
    with console.status("[bold green]Loading cached devices..."):
        devices = cache.load_devices(source)
    console.print(f"[green]✓[/green] Loaded {len(devices)} devices from cache\n")

    # Build LLM config
    llm_cfg = resolve_llm_config(llm_base_url, llm_model, llm_api_key, embedding_model)

    console.print(f"[dim]LLM base_url:       {llm_cfg.base_url}[/dim]")
    console.print(f"[dim]LLM model:          {llm_cfg.model}[/dim]")
    console.print(
        f"[dim]Embedding model:    {llm_cfg.embedding_model or 'local (e5-large)'}[/dim]"
    )
    console.print(f"[dim]LLM api_key:        {llm_cfg.api_key[:8]}...[/dim]\n")

    # Instantiate KINETIC
    kinetic = KINETIC(
        llm_config=llm_cfg,
        embedder=None,
        lang=lang,
        resolution=resolution,
        enable_trace=True,
        cache_doc_embeddings=True,
    )

    # Run grouping
    with console.status("[bold green]Running KINETIC pipeline..."):
        groups = kinetic.group_devices(devices)

    console.print(f"[green]✓[/green] Generated {len(groups)} topics\n")

    # Build results dict
    results = {group.name: [str(d.id) for d in group.devices] for group in groups}

    # Config
    config = kinetic.get_config()

    # Similarity scores
    similarity_scores = kinetic.get_similarity_scores()

    # Metrics (if ground truth provided)
    metrics = None
    if ground_truth:
        metrics = compute_clustering_metrics(ground_truth, results)
        if metrics:
            display_metrics(metrics)

    # Save experiment
    tracker = ExperimentTracker()
    exp_dir = tracker.save_experiment(
        name=name,
        source=source,
        grouper="kinetic",
        results=results,
        config=config,
        metrics=metrics,
        similarity_scores=similarity_scores,
        trace=kinetic.last_trace,
    )

    console.print(f"[green]✓[/green] Experiment saved to [cyan]{exp_dir}[/cyan]")
    console.print(f"  ID: [bold]{exp_dir.name}[/bold]")


# ---------------------------------------------------------------------------
# experiment list
# ---------------------------------------------------------------------------


@experiment.command(name="list")
@click.option("--source", "-s", default=None, help="Filter by data source")
def list_experiments(source: str | None):
    """List all tracked experiments."""
    tracker = ExperimentTracker()
    experiments = tracker.list_experiments(source=source)

    if not experiments:
        console.print("[yellow]No experiments found.[/yellow]")
        return

    table = Table(title="Experiments")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Name", style="bold")
    table.add_column("Source")
    table.add_column("Timestamp")
    table.add_column("Embedding Model", max_width=30)
    table.add_column("LLM Model", max_width=25)
    table.add_column("Resolution", justify="right")
    table.add_column("Topics", justify="right")
    table.add_column("NMI", justify="right")
    table.add_column("V-Measure", justify="right")

    for exp in experiments:
        config = exp.get("config", {})
        metrics = exp.get("metrics", {})
        table.add_row(
            exp.get("id", ""),
            exp.get("name", ""),
            exp.get("source", ""),
            exp.get("timestamp", ""),
            str(config.get("embedding_model", "—")),
            str(config.get("llm_model", "—")),
            str(config.get("resolution", "—")),
            str(exp.get("num_topics", "—")),
            f"{metrics['nmi']:.4f}" if "nmi" in metrics else "—",
            f"{metrics['v_measure']:.4f}" if "v_measure" in metrics else "—",
        )

    console.print(table)


# ---------------------------------------------------------------------------
# experiment show
# ---------------------------------------------------------------------------


@experiment.command()
@click.argument("exp_id")
def show(exp_id: str):
    """Show details of a single experiment."""
    from tools.core.report import generate_doc_scores_html

    tracker = ExperimentTracker()

    try:
        metadata, results = tracker.get_experiment(exp_id)
    except FileNotFoundError:
        console.print(f"[red]Experiment {exp_id} not found.[/red]")
        return

    console.print(
        f"[bold blue]Experiment: {metadata.get('name', exp_id)}[/bold blue]\n"
    )

    # Basic info
    info_table = Table(show_header=False, box=None)
    info_table.add_column("Key", style="bold")
    info_table.add_column("Value", style="cyan")
    info_table.add_row("ID", exp_id)
    info_table.add_row("Source", metadata.get("source", "—"))
    info_table.add_row("Grouper", metadata.get("grouper", "—"))
    info_table.add_row("Timestamp", metadata.get("timestamp", "—"))
    info_table.add_row("Topics", str(metadata.get("num_topics", "—")))
    info_table.add_row("Devices", str(metadata.get("num_devices", "—")))
    console.print(info_table)

    # Config
    config = metadata.get("config", {})
    if config:
        console.print("\n[bold]Configuration:[/bold]")
        cfg_table = Table(show_header=False, box=None)
        cfg_table.add_column("Parameter", style="bold")
        cfg_table.add_column("Value", style="cyan")
        for key, value in config.items():
            cfg_table.add_row(key, str(value))
        console.print(cfg_table)

    # Metrics
    metrics = metadata.get("metrics", {})
    if metrics:
        console.print("\n[bold]Metrics:[/bold]")
        m_table = Table()
        m_table.add_column("Metric", style="bold cyan")
        m_table.add_column("Score", style="magenta", justify="right")
        for key, value in metrics.items():
            m_table.add_row(
                key, f"{value:.4f}" if isinstance(value, float) else str(value)
            )
        console.print(m_table)

    # Similarity scores
    sim_scores = metadata.get("similarity_scores", {})
    if sim_scores:
        cluster_labels = sim_scores.get("cluster_labels", [])

        # Per-document detail table → save as HTML
        doc_details = sim_scores.get("doc_details", [])
        if doc_details:
            html_path = generate_doc_scores_html(doc_details, cluster_labels, exp_id)
            console.print(
                f"\n[bold]Per-Document Scores:[/bold] {len(doc_details)} docs → "
                f"[cyan]{html_path}[/cyan]"
            )
            webbrowser.open(f"file://{Path(html_path).resolve()}")

    # Topics
    console.print("\n[bold]Topics:[/bold]")
    topic_table = Table()
    topic_table.add_column("Topic", style="cyan")
    topic_table.add_column("Devices", justify="right")
    for topic, device_ids in sorted(
        results.items(), key=lambda x: len(x[1]), reverse=True
    ):
        topic_table.add_row(topic, str(len(device_ids)))
    console.print(topic_table)


# ---------------------------------------------------------------------------
# experiment compare
# ---------------------------------------------------------------------------


@experiment.command()
@click.argument("exp_ids", nargs=-1, required=True)
@click.option(
    "--output", "-o", default=None, help="Output HTML path (default: auto-generated)"
)
@click.option("--open-browser", is_flag=True, help="Open report in browser")
def compare(exp_ids: tuple[str, ...], output: str | None, open_browser: bool):
    """Compare multiple experiments in an interactive HTML report.

    EXP_IDS: two or more experiment IDs to compare
    """
    if len(exp_ids) < 2:
        console.print("[red]Provide at least two experiment IDs to compare.[/red]")
        return

    tracker = ExperimentTracker()
    experiments = []
    results_list = []

    for eid in exp_ids:
        try:
            meta, results = tracker.get_experiment(eid)
            meta["id"] = eid
            experiments.append(meta)
            results_list.append(results)
        except FileNotFoundError:
            console.print(f"[red]Experiment {eid} not found, skipping.[/red]")

    if len(experiments) < 2:
        console.print("[red]Need at least two valid experiments to compare.[/red]")
        return

    if output is None:
        output = f".experiments/compare_{'_vs_'.join(e['id'][:12] for e in experiments)}.html"

    from tools.core.report import generate_comparison_report

    report_path = generate_comparison_report(experiments, results_list, output)
    console.print(f"[green]✓[/green] Report generated: [cyan]{report_path}[/cyan]")

    if open_browser:
        webbrowser.open(f"file://{Path(report_path).resolve()}")

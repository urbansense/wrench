"""Evaluation and metrics commands."""

from __future__ import annotations

import json

import click
from rich.console import Console
from rich.table import Table

from tools.fixtures.data_sources import get_source

console = Console()


@click.group()
def evaluate():
    """Evaluation and metrics for clustering results."""
    pass


@evaluate.command(name="create-ground-truth")
@click.argument("source")
@click.argument("output", type=click.Path())
@click.option(
    "--interactive",
    "-i",
    is_flag=True,
    help="Interactive mode to add custom rules",
)
def create_ground_truth(source: str, output: str, interactive: bool):
    """Create ground truth dataset from a data source.

    SOURCE: Name of the data source (hamburg, osnabrueck, muenchen)
    OUTPUT: Path to save the ground truth JSON file
    """
    from tools.core.ground_truth import GroundTruthBuilder
    from wrench.harvester.sensorthings import SensorThingsHarvester

    data_source = get_source(source)
    console.print(
        f"[bold blue]Creating ground truth for {data_source.title}[/bold blue]"
    )

    # Initialize harvester and builder
    harvester = SensorThingsHarvester(base_url=data_source.base_url)
    builder = GroundTruthBuilder(harvester)

    with console.status("[bold green]Fetching devices..."):
        devices = builder.fetch_devices()
    console.print(f"[green]✓[/green] Fetched {len(devices)} devices")

    # Apply predefined rules based on source
    console.print("\n[bold]Applying classification rules...[/bold]")

    if source == "hamburg":
        _apply_hamburg_rules(builder)
    elif source == "osnabrueck":
        _apply_osnabrueck_rules(builder)
    elif source == "muenchen":
        _apply_muenchen_rules(builder)

    # Show statistics
    stats = builder.get_statistics()
    _display_stats(stats)

    # Interactive mode
    if interactive:
        console.print(
            "\n[bold yellow]Interactive mode not yet implemented[/bold yellow]"
        )

    # Save ground truth
    builder.save(output)
    console.print(f"\n[green]✓[/green] Ground truth saved to {output}")


def _apply_hamburg_rules(builder: GroundTruthBuilder):
    """Apply Hamburg-specific classification rules."""
    rules = [
        ("Traffic Counting", ["Verkehrsmenge"]),
        ("Bicycle Rental Stations", ["Fahrradverleihsystem"]),
        ("Electric Vehicle Charging Stations", ["E-Ladestation"]),
        ("Renewable Energy Generation", ["Photovoltaik"]),
        ("Road Traffic Monitoring", ["Traffic Forecast"]),
    ]

    for category, keywords in rules:
        count = builder.add_keyword_rule(category, keywords)
        console.print(f"  {category}: {count} items")


def _apply_osnabrueck_rules(builder: GroundTruthBuilder):
    """Apply Osnabrück-specific classification rules."""
    # Keyword-based rules (checking 'keywords' field)
    keyword_rules = [
        ("Parking Status", ["Parkplatz"]),
        ("Groundwater Level Measurement", ["GWM"]),
        ("Electric Vehicle Charging", ["Ladestation"]),
        ("Soil Moisture and Temperature", ["Boden"]),
        ("Winter Road Conditions", ["Winterdienst"]),
        ("Weather Monitoring", ["Wetter"]),
    ]

    for category, keywords in keyword_rules:
        count = builder.add_keyword_rule(category, keywords, field="keywords")
        console.print(f"  {category}: {count} items")

    # Topic-based rules (checking 'topic' field in properties)
    topic_rules = [
        ("Traffic Volume Measurement", ["Verkehrszaehlung"]),
    ]

    for category, topics in topic_rules:
        count = builder.add_keyword_rule(category, topics, field="topic")
        console.print(f"  {category}: {count} items")

    # Name-based rules
    name_rules = [
        ("Cycling Event Statistics", ["Stadtradeln"]),
        ("Energy Consumption Monitoring", ["Tiny house"]),
    ]

    for category, patterns in name_rules:
        count = builder.add_name_contains_rule(category, patterns)
        console.print(f"  {category}: {count} items")


def _apply_muenchen_rules(builder: GroundTruthBuilder):
    """Apply München-specific classification rules."""
    # Name prefix rules
    prefix_rules = [
        ("Air Quality Monitoring", ["LfU"]),
        ("Traffic Signal Status", ["LSA"]),
        ("Traffic Flow Monitoring", ["Schleifen"]),
    ]

    for category, prefixes in prefix_rules:
        count = builder.add_name_prefix_rule(category, prefixes)
        console.print(f"  {category}: {count} items")


def _display_stats(stats: dict):
    """Display ground truth statistics."""
    console.print("\n[bold]Ground Truth Statistics:[/bold]")

    table = Table(show_header=False, box=None)
    table.add_column("Property", style="bold")
    table.add_column("Value", style="cyan")

    table.add_row("Total Devices", str(stats["total_devices"]))
    table.add_row("Assigned Devices", str(stats["assigned_devices"]))
    table.add_row("Unassigned Devices", str(stats["unassigned_devices"]))
    table.add_row("Categories", str(stats["categories"]))

    console.print(table)

    # Category distribution
    if stats["category_distribution"]:
        console.print("\n[bold]Category Distribution:[/bold]")
        dist_table = Table()
        dist_table.add_column("Category", style="cyan")
        dist_table.add_column("Count", style="magenta", justify="right")

        for cat, count in sorted(
            stats["category_distribution"].items(), key=lambda x: x[1], reverse=True
        ):
            dist_table.add_row(cat, str(count))

        console.print(dist_table)


@evaluate.command(name="metrics")
@click.argument("ground_truth", type=click.Path(exists=True))
@click.argument("results", type=click.Path(exists=True))
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Save metrics to JSON file",
)
@click.option(
    "--handle-missing",
    type=click.Choice(["skip", "error", "assign_new_cluster"]),
    default="skip",
    help="How to handle items missing from one of the datasets",
)
def compute_metrics(ground_truth: str, results: str, output: str, handle_missing: str):
    """Compute clustering metrics by comparing results to ground truth.

    GROUND_TRUTH: Path to ground truth JSON file
    RESULTS: Path to clustering results JSON file
    """
    from sklearn.metrics import (
        homogeneity_completeness_v_measure,
        normalized_mutual_info_score,
    )

    console.print("[bold blue]Computing Clustering Metrics[/bold blue]\n")

    # Load data
    with open(ground_truth) as f:
        gt_data = json.load(f)

    with open(results) as f:
        result_data = json.load(f)

    console.print(f"Ground truth categories: {len(gt_data)}")
    console.print(f"Result clusters: {len(result_data)}")

    # Convert to labels
    x, y_true, y_pred = _dicts_to_labels(gt_data, result_data, handle_missing)

    console.print(f"Comparing {len(x)} items\n")

    # Compute metrics
    nmi = normalized_mutual_info_score(y_true, y_pred)
    homogeneity, completeness, v_measure = homogeneity_completeness_v_measure(
        y_true, y_pred
    )

    # Display metrics
    table = Table(title="Clustering Metrics")
    table.add_column("Metric", style="bold cyan")
    table.add_column("Score", style="magenta", justify="right")

    table.add_row("Normalized Mutual Information", f"{nmi:.4f}")
    table.add_row("Homogeneity", f"{homogeneity:.4f}")
    table.add_row("Completeness", f"{completeness:.4f}")
    table.add_row("V-Measure", f"{v_measure:.4f}")

    console.print(table)

    # Save to file if requested
    if output:
        metrics = {
            "nmi": float(nmi),
            "homogeneity": float(homogeneity),
            "completeness": float(completeness),
            "v_measure": float(v_measure),
            "items_compared": len(x),
        }

        with open(output, "w") as f:
            json.dump(metrics, f, indent=2)

        console.print(f"\n[green]✓[/green] Metrics saved to {output}")


@evaluate.command(name="compare")
@click.argument("ground_truth", type=click.Path(exists=True))
@click.argument("results", type=click.Path(exists=True))
@click.option(
    "--detailed/--summary",
    default=False,
    help="Show detailed differences per category",
)
def compare_results(ground_truth: str, results: str, detailed: bool):
    """Compare clustering results to ground truth and show differences.

    GROUND_TRUTH: Path to ground truth JSON file
    RESULTS: Path to clustering results JSON file
    """
    with open(ground_truth) as f:
        gt_data = json.load(f)

    with open(results) as f:
        result_data = json.load(f)

    console.print("[bold blue]Comparing Results to Ground Truth[/bold blue]\n")

    differences = _compare_json_lists(gt_data, result_data)

    if not differences:
        console.print("[green]✓ Results match ground truth perfectly![/green]")
        return

    # Summary table
    table = Table(title="Comparison Summary")
    table.add_column("Category", style="cyan")
    table.add_column("Correct", style="green", justify="right")
    table.add_column("Misclassified", style="red", justify="right")
    table.add_column("Missing", style="yellow", justify="right")

    total_correct = 0
    total_wrong = 0

    for key, diff in sorted(differences.items()):
        correct = len(diff["common"])
        wrong_in_results = len(diff["only_in_json2"])
        missing_from_results = len(diff["only_in_json1"])

        total_correct += correct
        total_wrong += wrong_in_results

        table.add_row(
            key,
            str(correct),
            str(wrong_in_results),
            str(missing_from_results),
        )

    console.print(table)

    # Overall summary
    console.print("\n[bold]Overall:[/bold]")
    console.print(f"  Correctly classified: [green]{total_correct}[/green]")
    console.print(f"  Misclassified: [red]{total_wrong}[/red]")

    if total_correct + total_wrong > 0:
        accuracy = total_correct / (total_correct + total_wrong)
        console.print(f"  Accuracy: [cyan]{accuracy:.2%}[/cyan]")

    # Detailed view
    if detailed:
        console.print("\n[bold]Detailed Differences:[/bold]")
        for key, diff in sorted(differences.items()):
            if diff["only_in_json2"] or diff["only_in_json1"]:
                console.print(f"\n[cyan]{key}:[/cyan]")
                if diff["only_in_json2"]:
                    console.print(
                        f"  Incorrectly in results: {diff['only_in_json2'][:5]}..."
                    )
                if diff["only_in_json1"]:
                    console.print(
                        f"  Missing from results: {diff['only_in_json1'][:5]}..."
                    )


def _dicts_to_labels(true_dict, pred_dict, handle_missing="skip"):
    """Convert cluster dictionaries to label arrays for sklearn metrics."""
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
        valid_items = [
            item
            for item in all_items
            if item in true_item_to_cluster and item in pred_item_to_cluster
        ]
        all_items = valid_items
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


def _compare_json_lists(json1, json2):
    """Compare two clustering result JSONs and find differences."""
    all_keys = set(json1.keys()) | set(json2.keys())
    differences = {}

    for key in all_keys:
        list1 = set(json1.get(key, []))
        list2 = set(json2.get(key, []))

        if list1 != list2:
            differences[key] = {
                "only_in_json1": list(list1 - list2),
                "only_in_json2": list(list2 - list1),
                "common": list(list1 & list2),
            }

    return differences

"""Pipeline execution commands."""

import asyncio
from pathlib import Path

import click
from rich.console import Console

from tools.core.config_loader import ConfigLoader

console = Console()


@click.group()
def pipeline():
    """Run and test pipelines."""
    pass


@pipeline.command()
@click.argument("config_path", type=click.Path(exists=True))
@click.option(
    "--once",
    is_flag=True,
    help="Run pipeline once and exit (ignore scheduler)",
)
@click.option(
    "--save-results",
    "-s",
    type=click.Path(),
    help="Save results to JSON file",
)
def run(config_path: str, once: bool, save_results: str):
    """Run a pipeline from a configuration file.

    CONFIG_PATH: Path to pipeline configuration YAML file
    """
    console.print(f"[bold blue]Running pipeline from {config_path}[/bold blue]\n")

    try:
        from wrench.pipeline.config import PipelineRunner

        # Load configuration
        config_loader = ConfigLoader()
        config = config_loader.load_yaml(config_path)

        console.print("[bold]Configuration loaded:[/bold]")
        console.print(
            f"  Harvester: {list(config.get('harvester', {}).keys())[0] if config.get('harvester') else 'None'}"
        )
        console.print(
            f"  Grouper: {list(config.get('classifier', {}).keys())[0] if config.get('classifier') else 'None'}"
        )
        console.print(
            f"  Cataloger: {list(config.get('catalogger', {}).keys())[0] if config.get('catalogger') else 'None'}"
        )

        # Create pipeline runner
        pipeline_runner = PipelineRunner.from_config_file(config_path)

        # Run pipeline
        if once:
            console.print("\n[bold green]Running pipeline once...[/bold green]")
            result = asyncio.run(pipeline_runner.run())

            if result:
                console.print("\n[green]✓[/green] Pipeline completed successfully")
                console.print(
                    f"  Items processed: {len(result.items) if hasattr(result, 'items') else 'N/A'}"
                )
                console.print(
                    f"  Groups created: {len(result.groups) if hasattr(result, 'groups') else 'N/A'}"
                )

                if save_results and hasattr(result, "groups"):
                    import json

                    output = {
                        group.name: [str(item.id) for item in group.items]
                        for group in result.groups
                    }
                    Path(save_results).parent.mkdir(parents=True, exist_ok=True)
                    with open(save_results, "w") as f:
                        json.dump(output, f, indent=2)
                    console.print(f"\n[green]✓[/green] Results saved to {save_results}")
            else:
                console.print("[yellow]Pipeline returned no results[/yellow]")
        else:
            console.print("\n[bold green]Starting scheduled pipeline...[/bold green]")
            console.print("[dim]Press Ctrl+C to stop[/dim]\n")
            try:
                asyncio.run(pipeline_runner.run())
            except KeyboardInterrupt:
                console.print("\n[yellow]Pipeline stopped by user[/yellow]")

    except Exception as e:
        console.print(f"\n[red]Error running pipeline: {e}[/red]")
        raise


@pipeline.command()
@click.argument(
    "component_type",
    type=click.Choice(["harvester", "grouper", "cataloger", "metadataenricher"]),
)
@click.argument("config_path", type=click.Path(exists=True))
@click.option(
    "--limit",
    "-l",
    type=int,
    help="Limit number of items to process",
)
def test(component_type: str, config_path: str, limit: int):
    """Test a single component with its configuration.

    COMPONENT_TYPE: Type of component to test
    CONFIG_PATH: Path to component configuration file
    """
    console.print(
        f"[bold blue]Testing {component_type} with {config_path}[/bold blue]\n"
    )

    try:
        config_loader = ConfigLoader()
        config = config_loader.load_yaml(config_path)

        if component_type == "harvester":
            _test_harvester(config, limit)
        elif component_type == "grouper":
            _test_grouper(config, limit)
        elif component_type == "cataloger":
            _test_cataloger(config)
        elif component_type == "metadataenricher":
            _test_metadataenricher(config)

    except Exception as e:
        console.print(f"\n[red]Error testing component: {e}[/red]")
        raise


def _test_harvester(config: dict, limit: int | None):
    """Test a harvester configuration."""
    from wrench.harvester.sensorthings import SensorThingsHarvester

    console.print("[bold]Testing SensorThings Harvester[/bold]")

    harvester_config = {**config}
    if limit:
        harvester_config["default_limit"] = limit

    harvester = SensorThingsHarvester(**harvester_config)

    with console.status("[bold green]Fetching items..."):
        items = harvester.return_items()

    console.print(f"\n[green]✓[/green] Harvested {len(items)} items")

    if items:
        console.print("\n[bold]Sample items:[/bold]")
        for i, item in enumerate(items[:3], 1):
            console.print(f"{i}. [cyan]{item.name}[/cyan]")
            console.print(f"   Description: {item.description[:80]}...")
            console.print(f"   Sensors: {len(item.sensors)}")


def _test_grouper(config: dict, limit: int | None):
    """Test a grouper configuration."""
    console.print("[bold]Testing Grouper[/bold]")
    console.print(
        "[yellow]Grouper testing requires harvested data. Please run 'wrench-tools data fetch' first.[/yellow]"
    )

    # This would require loading cached data and running the grouper
    # Left as exercise for more complex implementation


def _test_cataloger(config: dict):
    """Test a cataloger configuration."""
    from wrench.cataloger.sddi import SDDICataloger

    console.print("[bold]Testing SDDI Cataloger[/bold]")

    cataloger = SDDICataloger(**config)

    try:
        # Test connection by listing packages
        packages = cataloger.ckan.action.package_list()
        console.print("\n[green]✓[/green] Connected to catalog successfully")
        console.print(f"  Total packages: {len(packages)}")
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to connect: {e}")


def _test_metadataenricher(config: dict):
    """Test a metadata enricher configuration."""
    console.print("[bold]Testing Metadata Enricher[/bold]")
    console.print("[yellow]Metadata enricher testing not yet implemented[/yellow]")


@pipeline.command(name="list-configs")
@click.option(
    "--component",
    "-c",
    type=click.Choice(["harvester", "grouper", "cataloger", "metadataenricher"]),
    help="Filter by component type",
)
def list_configs(component: str):
    """List available pipeline configuration files."""
    config_loader = ConfigLoader()
    configs = config_loader.list_configs(component)

    console.print("[bold]Available Configuration Files[/bold]\n")

    if not configs:
        console.print("[yellow]No configuration files found.[/yellow]")
        return

    for config_path in configs:
        console.print(f"[cyan]{config_path}[/cyan]")

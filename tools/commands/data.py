"""Data management commands."""

import click
from rich.console import Console
from rich.table import Table

from tools.core.cache import DataCache
from tools.fixtures.data_sources import KNOWN_SOURCES, get_source, list_sources

console = Console()


@click.group()
def data():
    """Manage test data and caching."""
    pass


@data.command()
@click.argument("source", type=click.Choice(list_sources()))
@click.option(
    "--limit",
    "-l",
    type=int,
    default=-1,
    help="Limit number of items to fetch (-1 for all)",
)
@click.option(
    "--embeddings/--no-embeddings",
    default=False,
    help="Also generate and cache embeddings",
)
@click.option(
    "--embedding-model",
    default="intfloat/multilingual-e5-large-instruct",
    help="Model to use for embeddings",
)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Force re-fetch even if cached data exists",
)
def fetch(source: str, limit: int, embeddings: bool, embedding_model: str, force: bool):
    """Fetch data from a SensorThings server and cache it.

    SOURCE: Name of the data source (hamburg, osnabrueck, muenchen)
    """
    cache = DataCache()
    data_source = get_source(source)

    console.print(f"[bold blue]Fetching data from {data_source.title}[/bold blue]")
    console.print(f"URL: {data_source.base_url}")

    # Check if already cached
    if not force and cache.has_cached(source, "devices"):
        console.print(
            f"[yellow]Devices already cached for '{source}'. Use --force to re-fetch.[/yellow]"
        )
        devices = cache.load_devices(source)
    else:
        with console.status(f"[bold green]Fetching devices from {source}..."):
            devices = cache.fetch_and_cache_devices(source, data_source.base_url, limit)
        console.print(f"[green]✓[/green] Fetched and cached {len(devices)} devices")

    # Generate embeddings if requested
    if embeddings:
        if not force and cache.has_cached(source, "embeddings"):
            console.print(
                f"[yellow]Embeddings already cached for '{source}'. Use --force to regenerate.[/yellow]"
            )
        else:
            console.print(
                f"[bold blue]Generating embeddings with {embedding_model}[/bold blue]"
            )
            emb = cache.generate_and_cache_embeddings(source, embedding_model)
            console.print(
                f"[green]✓[/green] Generated and cached embeddings with shape {emb.shape}"
            )

    # Show stats
    stats = cache.get_cache_stats(source)
    console.print("\n[bold]Cache Statistics:[/bold]")
    console.print(
        f"  Devices: {stats.get('device_count', 0)} ({stats.get('devices_size_mb', 0):.2f} MB)"
    )
    if stats.get("has_embeddings"):
        console.print(
            f"  Embeddings: {stats.get('embedding_shape')} ({stats.get('embeddings_size_mb', 0):.2f} MB)"
        )


@data.command()
def list():
    """List all cached data sources."""
    cache = DataCache()
    sources = cache.list_cached_sources()

    if not sources:
        console.print("[yellow]No cached data found.[/yellow]")
        console.print(
            "Run [bold]wrench-tools data fetch <source>[/bold] to cache data."
        )
        return

    table = Table(title="Cached Data Sources")
    table.add_column("Source", style="cyan")
    table.add_column("Devices", style="green")
    table.add_column("Embeddings", style="blue")
    table.add_column("Device Count", style="magenta")

    for source_name, available in sorted(sources.items()):
        stats = cache.get_cache_stats(source_name)
        table.add_row(
            source_name,
            "✓" if available["devices"] else "✗",
            "✓" if available["embeddings"] else "✗",
            str(stats.get("device_count", "N/A")),
        )

    console.print(table)


@data.command()
@click.argument("source", type=str)
def info(source: str):
    """Show detailed information about a cached data source.

    SOURCE: Name of the cached data source
    """
    cache = DataCache()

    if not cache.has_cached(source, "devices"):
        console.print(f"[red]No cached data found for source '{source}'[/red]")
        console.print(
            f"Available sources: {', '.join(cache.list_cached_sources().keys())}"
        )
        return

    stats = cache.get_cache_stats(source)

    console.print(f"\n[bold blue]Cache Information for '{source}'[/bold blue]\n")

    table = Table(show_header=False, box=None)
    table.add_column("Property", style="bold")
    table.add_column("Value")

    table.add_row("Source", stats["source"])
    table.add_row("Devices Cached", "Yes" if stats["has_devices"] else "No")

    if stats.get("device_count"):
        table.add_row("Device Count", str(stats["device_count"]))
        table.add_row("Devices Size", f"{stats['devices_size_mb']:.2f} MB")

    table.add_row("Embeddings Cached", "Yes" if stats["has_embeddings"] else "No")

    if stats.get("embedding_shape"):
        table.add_row("Embedding Shape", str(stats["embedding_shape"]))
        table.add_row("Embeddings Size", f"{stats['embeddings_size_mb']:.2f} MB")

    console.print(table)

    # Show sample devices
    if stats["has_devices"]:
        devices = cache.load_devices(source)
        console.print("\n[bold]Sample Devices (first 3):[/bold]\n")
        for i, device in enumerate(devices[:3]):
            console.print(f"{i + 1}. [cyan]{device.name}[/cyan]")
            console.print(f"   Description: {device.description[:100]}...")
            console.print(f"   Sensors: {len(device.sensors)}")


@data.command()
def sources():
    """Show available data sources."""
    console.print("[bold]Available SensorThings Data Sources:[/bold]\n")

    for name, src in KNOWN_SOURCES.items():
        console.print(f"[cyan]{name}[/cyan]")
        console.print(f"  Title: {src.title}")
        console.print(f"  URL: {src.base_url}")
        console.print(f"  Description: {src.description}\n")

"""SDDI/CKAN catalog management commands."""

import click
from ckanapi.errors import NotFound
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

console = Console()


@click.group()
def catalog():
    """Manage SDDI/CKAN catalog entries."""
    pass


@catalog.command()
@click.option(
    "--base-url",
    envvar="CKAN_BASE_URL",
    default="http://localhost:5000",
    help="CKAN base URL",
)
@click.option(
    "--api-key",
    envvar="CKAN_API_TOKEN",
    required=True,
    help="CKAN API token (or set CKAN_API_TOKEN env var)",
)
@click.option(
    "--pattern",
    "-p",
    help="Filter packages by name pattern",
)
def list(base_url: str, api_key: str, pattern: str):
    """List packages in the SDDI catalog."""
    from wrench.cataloger.sddi import SDDICataloger

    load_dotenv("test_script/.env")

    cataloger = SDDICataloger(base_url=base_url, api_key=api_key)

    try:
        with console.status("[bold green]Fetching catalog packages..."):
            # Use CKAN API to list packages
            packages = cataloger.ckan_server.call_action(action="package_list")

        if pattern:
            packages = [p for p in packages if pattern.lower() in p.lower()]

        console.print(f"\n[bold blue]Found {len(packages)} packages[/bold blue]\n")

        if not packages:
            console.print("[yellow]No packages found in catalog.[/yellow]")
            return

        # Display in groups of 50
        for i, package_name in enumerate(sorted(packages), 1):
            console.print(f"{i}. [cyan]{package_name}[/cyan]")

    except Exception as e:
        console.print(f"[red]Error listing packages: {e}[/red]")


@catalog.command()
@click.argument("package_id")
@click.option(
    "--base-url",
    envvar="CKAN_BASE_URL",
    default="http://localhost:5000",
    help="CKAN base URL",
)
@click.option(
    "--api-key",
    envvar="CKAN_API_TOKEN",
    required=True,
    help="CKAN API token",
)
def show(package_id: str, base_url: str, api_key: str):
    """Show details of a specific package.

    PACKAGE_ID: The package identifier
    """
    from wrench.cataloger.sddi import SDDICataloger

    load_dotenv("test_script/.env")

    cataloger = SDDICataloger(base_url=base_url, api_key=api_key)

    try:
        package = cataloger._get_package(package_id)

        console.print(f"\n[bold blue]Package: {package['name']}[/bold blue]\n")

        table = Table(show_header=False, box=None)
        table.add_column("Property", style="bold")
        table.add_column("Value")

        table.add_row("ID", package.get("id", "N/A"))
        table.add_row("Title", package.get("title", "N/A"))
        table.add_row("State", package.get("state", "N/A"))
        table.add_row("Private", str(package.get("private", False)))
        table.add_row("Owner Org", package.get("owner_org", "N/A"))
        table.add_row("Resources", str(len(package.get("resources", []))))

        console.print(table)

        if package.get("notes"):
            console.print("\n[bold]Description:[/bold]")
            console.print(
                package["notes"][:200] + "..."
                if len(package["notes"]) > 200
                else package["notes"]
            )

        if package.get("resources"):
            console.print("\n[bold]Resources:[/bold]")
            for i, resource in enumerate(package["resources"], 1):
                console.print(
                    f"{i}. {resource.get('name', 'Unnamed')} ({resource.get('format', 'N/A')})"
                )

    except NotFound:
        console.print(f"[red]Package '{package_id}' not found in catalog.[/red]")
    except Exception as e:
        console.print(f"[red]Error fetching package: {e}[/red]")


@catalog.command()
@click.argument("package_id")
@click.option(
    "--base-url",
    envvar="CKAN_BASE_URL",
    default="http://localhost:5000",
    help="CKAN base URL",
)
@click.option(
    "--api-key",
    envvar="CKAN_API_TOKEN",
    required=True,
    help="CKAN API token",
)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Skip confirmation prompt",
)
def delete(package_id: str, base_url: str, api_key: str, force: bool):
    """Delete a package from the catalog.

    PACKAGE_ID: The package identifier to delete
    """
    from wrench.cataloger.sddi import SDDICataloger

    load_dotenv("test_script/.env")

    if not force:
        if not click.confirm(f"Are you sure you want to delete '{package_id}'?"):
            console.print("[yellow]Deletion cancelled.[/yellow]")
            return

    cataloger = SDDICataloger(base_url=base_url, api_key=api_key)

    try:
        cataloger.delete_resource(package_id)
        console.print(f"[green]✓[/green] Deleted package '{package_id}'")
    except NotFound:
        console.print(f"[red]Package '{package_id}' not found.[/red]")
    except Exception as e:
        console.print(f"[red]Error deleting package: {e}[/red]")


@catalog.command(name="delete-batch")
@click.argument("package_file", type=click.Path(exists=True))
@click.option(
    "--base-url",
    envvar="CKAN_BASE_URL",
    default="http://localhost:5000",
    help="CKAN base URL",
)
@click.option(
    "--api-key",
    envvar="CKAN_API_TOKEN",
    required=True,
    help="CKAN API token",
)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Skip confirmation prompt",
)
def delete_batch(package_file: str, base_url: str, api_key: str, force: bool):
    """Delete multiple packages from a file (one package ID per line).

    PACKAGE_FILE: Path to file containing package IDs (one per line)
    """
    from wrench.cataloger.sddi import SDDICataloger

    load_dotenv("test_script/.env")

    with open(package_file) as f:
        package_ids = [
            line.strip() for line in f if line.strip() and not line.startswith("#")
        ]

    console.print(f"[bold]Found {len(package_ids)} packages to delete[/bold]")

    if not force:
        console.print("\nPackages to be deleted:")
        for pid in package_ids[:10]:
            console.print(f"  - {pid}")
        if len(package_ids) > 10:
            console.print(f"  ... and {len(package_ids) - 10} more")

        if not click.confirm(f"\nDelete all {len(package_ids)} packages?"):
            console.print("[yellow]Deletion cancelled.[/yellow]")
            return

    cataloger = SDDICataloger(base_url=base_url, api_key=api_key)

    success_count = 0
    error_count = 0

    with console.status("[bold green]Deleting packages...") as status:
        for i, package_id in enumerate(package_ids, 1):
            status.update(f"[bold green]Deleting {i}/{len(package_ids)}: {package_id}")
            try:
                cataloger.delete_resource(package_id)
                success_count += 1
            except NotFound:
                console.print(
                    f"[yellow]Package '{package_id}' not found, skipping[/yellow]"
                )
                error_count += 1
            except Exception as e:
                console.print(f"[red]Error deleting '{package_id}': {e}[/red]")
                error_count += 1

    console.print(f"\n[green]✓[/green] Deleted {success_count} packages")
    if error_count > 0:
        console.print(f"[yellow]⚠[/yellow] {error_count} packages had errors")


@catalog.command(name="clean-all")
@click.option(
    "--base-url",
    envvar="CKAN_BASE_URL",
    default="http://localhost:5000",
    help="CKAN base URL",
)
@click.option(
    "--api-key",
    envvar="CKAN_API_TOKEN",
    required=True,
    help="CKAN API token",
)
@click.option(
    "--pattern",
    "-p",
    help="Only delete packages matching pattern",
)
def clean_all(base_url: str, api_key: str, pattern: str):
    """Interactively clean all packages from the catalog.

    This is a destructive operation. Use with caution!
    """
    from wrench.cataloger.sddi import SDDICataloger

    load_dotenv("test_script/.env")

    cataloger = SDDICataloger(base_url=base_url, api_key=api_key)

    try:
        packages = cataloger.ckan.action.package_list()

        if pattern:
            packages = [p for p in packages if pattern.lower() in p.lower()]

        console.print(
            f"[bold red]WARNING: This will delete {len(packages)} packages![/bold red]"
        )

        if pattern:
            console.print(f"Filter pattern: '{pattern}'")

        console.print("\nFirst 10 packages to be deleted:")
        for p in packages[:10]:
            console.print(f"  - {p}")

        if len(packages) > 10:
            console.print(f"  ... and {len(packages) - 10} more")

        if not click.confirm(
            "\nAre you ABSOLUTELY SURE you want to delete all these packages?"
        ):
            console.print("[yellow]Operation cancelled.[/yellow]")
            return

        if not click.confirm("This cannot be undone. Continue?"):
            console.print("[yellow]Operation cancelled.[/yellow]")
            return

        success_count = 0
        error_count = 0

        with console.status("[bold green]Deleting packages...") as status:
            for i, package_id in enumerate(packages, 1):
                status.update(f"[bold green]Deleting {i}/{len(packages)}: {package_id}")
                try:
                    cataloger.delete_resource(package_id)
                    success_count += 1
                except Exception as e:
                    console.print(f"[red]Error deleting '{package_id}': {e}[/red]")
                    error_count += 1

        console.print(f"\n[green]✓[/green] Deleted {success_count} packages")
        if error_count > 0:
            console.print(f"[yellow]⚠[/yellow] {error_count} packages had errors")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")

#!/usr/bin/env python3
"""Main CLI entry point for wrench development tools."""

import click

from tools.commands.catalog import catalog
from tools.commands.data import data
from tools.commands.evaluate import evaluate
from tools.commands.pipeline import pipeline


@click.group()
@click.version_option(version="0.1.0", prog_name="wrench-tools")
def cli():
    """Wrench development and testing tools.

    A comprehensive CLI for managing test data, running evaluations,
    managing catalog entries, and executing pipelines.
    """
    pass


# Register command groups
cli.add_command(data)
cli.add_command(evaluate)
cli.add_command(catalog)
cli.add_command(pipeline)


if __name__ == "__main__":
    cli()

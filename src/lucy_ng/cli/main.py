"""Main CLI entry point for lucy-ng."""

import click

from lucy_ng import __version__


@click.group()
@click.version_option(version=__version__, prog_name="lucy")
def cli() -> None:
    """lucy-ng: AI-powered Computer-Assisted Structure Elucidation.

    A command-line interface for NMR processing and structure elucidation
    of organic natural products.
    """
    pass


# Command groups will be added in subsequent tasks

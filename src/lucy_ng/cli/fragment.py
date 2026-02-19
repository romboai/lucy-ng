"""CLI commands for fragment library management."""

from __future__ import annotations

from pathlib import Path

import click

from lucy_ng.fragments import FragmentDatabaseManager

DEFAULT_FRAGMENTS_DB = Path("data/reference/lucy-ng-fragments.db")


@click.group()
def fragment() -> None:
    """Fragment library management and search."""


@fragment.command()
@click.argument("db_path", type=click.Path(path_type=Path), default=DEFAULT_FRAGMENTS_DB)
def info(db_path: Path) -> None:
    """Show fragment database statistics.

    Display information about a fragment database including schema version,
    SSC count, bin size, and file size.

    Example:

        lucy fragment info data/reference/lucy-ng-fragments.db
    """
    if not db_path.exists():
        click.echo(
            f"Error: Fragment database not found: {db_path}\n"
            "Run 'lucy fragment build' to create it, or specify a path with"
            " 'lucy fragment info <path>'",
            err=True,
        )
        raise click.Abort()

    with FragmentDatabaseManager(db_path) as db:
        version = db.get_schema_version()
        if version != 7:
            click.echo(
                f"Warning: Expected schema version 7, found {version}."
                " This may not be a fragment database.",
                err=True,
            )

        ssc_count = db.get_ssc_count()
        bin_size = db.get_bin_size()
        file_size_mb = db_path.stat().st_size / 1_000_000

        click.echo(f"Fragment database: {db_path}")
        click.echo(f"  Schema version: {version}")
        click.echo(f"  SSC count: {ssc_count:,}")
        click.echo(f"  Bin size: {bin_size:.1f} ppm")
        click.echo(f"  File size: {file_size_mb:.1f} MB")

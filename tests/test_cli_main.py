"""Tests for CLI main module."""

from click.testing import CliRunner

from lucy_ng import __version__
from lucy_ng.cli import cli


class TestCLIMain:
    """Tests for CLI entry point."""

    def test_version(self) -> None:
        """Test --version returns correct version."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert __version__ in result.output

    def test_help(self) -> None:
        """Test --help shows usage info."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "lucy-ng" in result.output
        assert "Computer-Assisted Structure Elucidation" in result.output

    def test_no_args(self) -> None:
        """Test running with no arguments shows usage."""
        runner = CliRunner()
        result = runner.invoke(cli, [])
        # Click shows usage and exits with code 0 or 2 depending on config
        assert "Usage:" in result.output

    def test_invalid_command(self) -> None:
        """Test invalid command shows error."""
        runner = CliRunner()
        result = runner.invoke(cli, ["invalid-command"])
        assert result.exit_code != 0
        assert "No such command" in result.output

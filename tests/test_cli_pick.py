"""Tests for CLI pick commands."""

import json

from click.testing import CliRunner

from lucy_ng.cli.pick import pick


class TestPick1D:
    """Tests for lucy pick 1d command."""

    def test_pick_1d_text(self) -> None:
        """Test picking 1D peaks with text output."""
        runner = CliRunner()
        result = runner.invoke(pick, ["1d", "data/Ibuprofen/2"])  # 13C
        assert result.exit_code == 0
        assert "Found" in result.output
        assert "peaks" in result.output
        assert "ppm" in result.output

    def test_pick_1d_json(self) -> None:
        """Test picking 1D peaks with JSON output."""
        runner = CliRunner()
        result = runner.invoke(pick, ["1d", "data/Ibuprofen/2", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "count" in data
        assert "peaks" in data
        assert data["count"] > 0
        # Each peak should have ppm and intensity
        assert "ppm" in data["peaks"][0]
        assert "intensity" in data["peaks"][0]

    def test_pick_1d_with_threshold(self) -> None:
        """Test picking with explicit threshold."""
        runner = CliRunner()
        result = runner.invoke(pick, ["1d", "data/Ibuprofen/2", "-t", "0.1"])
        assert result.exit_code == 0
        assert "Found" in result.output


class TestPick2D:
    """Tests for lucy pick 2d command."""

    def test_pick_2d_text(self) -> None:
        """Test picking 2D peaks with text output."""
        runner = CliRunner()
        result = runner.invoke(pick, ["2d", "data/Ibuprofen/6"])  # HSQC
        assert result.exit_code == 0
        assert "Found" in result.output
        assert "HSQC" in result.output
        assert "F1:" in result.output
        assert "F2:" in result.output

    def test_pick_2d_json(self) -> None:
        """Test picking 2D peaks with JSON output."""
        runner = CliRunner()
        result = runner.invoke(pick, ["2d", "data/Ibuprofen/6", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["experiment_type"] == "HSQC"
        assert "count" in data
        assert "peaks" in data
        if data["count"] > 0:
            assert "f1_position" in data["peaks"][0]
            assert "f2_position" in data["peaks"][0]


class TestPickHSQC:
    """Tests for lucy pick hsqc command."""

    def test_pick_hsqc_text(self) -> None:
        """Test raw HSQC picking with text output."""
        runner = CliRunner()
        result = runner.invoke(
            pick, ["hsqc", "data/Ibuprofen/6"]
        )
        assert result.exit_code == 0
        assert "Found" in result.output
        assert "peaks" in result.output
        assert "HSQC" in result.output

    def test_pick_hsqc_json(self) -> None:
        """Test raw HSQC picking with JSON output."""
        runner = CliRunner()
        result = runner.invoke(
            pick, ["hsqc", "data/Ibuprofen/6", "--format", "json"]
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["experiment_type"] == "HSQC"
        assert "count" in data
        assert "peaks" in data
        if data["count"] > 0:
            assert "f1_position" in data["peaks"][0]
            assert "f2_position" in data["peaks"][0]
            assert "intensity" in data["peaks"][0]


class TestPickHMBC:
    """Tests for lucy pick hmbc command."""

    def test_pick_hmbc_text(self) -> None:
        """Test raw HMBC picking with text output."""
        runner = CliRunner()
        result = runner.invoke(
            pick, ["hmbc", "data/Ibuprofen/7"]
        )
        assert result.exit_code == 0
        assert "Found" in result.output
        assert "peaks" in result.output
        assert "HMBC" in result.output

    def test_pick_hmbc_json(self) -> None:
        """Test raw HMBC picking with JSON output."""
        runner = CliRunner()
        result = runner.invoke(
            pick,
            [
                "hmbc",
                "data/Ibuprofen/7",
                "--format",
                "json",
            ],
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["experiment_type"] == "HMBC"
        assert "count" in data
        assert "peaks" in data
        if data["count"] > 0:
            assert "f1_position" in data["peaks"][0]
            assert "f2_position" in data["peaks"][0]
            assert "intensity" in data["peaks"][0]

    def test_pick_hmbc_with_threshold(self) -> None:
        """Test raw HMBC picking with custom threshold."""
        runner = CliRunner()
        result = runner.invoke(
            pick,
            [
                "hmbc",
                "data/Ibuprofen/7",
                "-t",
                "0.1",
            ],
        )
        assert result.exit_code == 0
        assert "Found" in result.output

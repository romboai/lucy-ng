"""Tests for LSD runner."""

import pytest
from pathlib import Path
import tempfile

from lucy_ng.lsd.models import Hybridization, LSDAtom, LSDCorrelation, LSDProblem
from lucy_ng.lsd.runner import LSDRunner, LSDResult


class TestLSDResult:
    """Tests for LSDResult dataclass."""

    def test_create_success_result(self):
        """Test creating successful result."""
        result = LSDResult(
            success=True,
            solution_count=5,
            return_code=0,
        )
        assert result.success is True
        assert result.solution_count == 5

    def test_create_failure_result(self):
        """Test creating failure result."""
        result = LSDResult(
            success=False,
            solution_count=0,
            stderr="Error message",
            return_code=1,
        )
        assert result.success is False
        assert "Error" in result.stderr

    def test_summary_success(self):
        """Test summary for successful result."""
        result = LSDResult(success=True, solution_count=3, return_code=0)
        summary = result.summary()

        assert "Success" in summary
        assert "3" in summary

    def test_summary_failure(self):
        """Test summary for failed result."""
        result = LSDResult(
            success=False,
            solution_count=0,
            stderr="Parse error",
            return_code=1,
        )
        summary = result.summary()

        assert "Failed" in summary
        assert "Parse error" in summary


class TestLSDRunnerAvailability:
    """Tests for LSD availability checking."""

    def test_is_available_returns_bool(self):
        """Test that is_available returns a boolean."""
        result = LSDRunner.is_available()
        assert isinstance(result, bool)

    def test_find_lsd_returns_path_or_none(self):
        """Test that _find_lsd returns Path or None."""
        result = LSDRunner._find_lsd()
        assert result is None or isinstance(result, Path)


class TestLSDRunnerInit:
    """Tests for LSDRunner initialization."""

    def test_init_with_path(self):
        """Test initialization with explicit path."""
        runner = LSDRunner(lsd_path="/usr/local/bin/lsd")
        assert runner.lsd_path == Path("/usr/local/bin/lsd")

    def test_init_with_expanduser(self):
        """Test that ~ is expanded in path."""
        runner = LSDRunner(lsd_path="~/bin/lsd")
        assert "~" not in str(runner.lsd_path)

    def test_init_without_path(self):
        """Test initialization without path (auto-detect)."""
        runner = LSDRunner()
        # Should be None if not installed, or a Path if found
        assert runner.lsd_path is None or isinstance(runner.lsd_path, Path)


class TestLSDRunnerExecution:
    """Tests for LSD execution."""

    @pytest.fixture
    def simple_problem(self):
        """Create a simple LSD problem for testing."""
        problem = LSDProblem(name="test")
        problem.add_atom(LSDAtom(1, "C", Hybridization.SP2, 0))
        problem.add_atom(LSDAtom(2, "C", Hybridization.SP3, 2))
        problem.add_correlation(LSDCorrelation(1, 2, "HMBC"))
        return problem

    def test_run_without_lsd_raises(self, simple_problem):
        """Test that run raises if LSD not found."""
        # Create runner with non-existent path
        runner = LSDRunner(lsd_path="/nonexistent/lsd")
        runner.lsd_path = None  # Force no LSD

        with pytest.raises(FileNotFoundError, match="LSD executable not found"):
            runner.run(simple_problem)

    def test_run_file_not_found_raises(self):
        """Test that run_file raises for missing file."""
        runner = LSDRunner()
        if runner.lsd_path is None:
            pytest.skip("LSD not installed")

        with pytest.raises(FileNotFoundError, match="Input file not found"):
            runner.run_file("/nonexistent/file.lsd")

    @pytest.mark.skipif(
        not LSDRunner.is_available(),
        reason="LSD not installed"
    )
    def test_run_with_real_lsd(self, simple_problem):
        """Test running with real LSD (if available)."""
        runner = LSDRunner()
        result = runner.run(simple_problem, timeout=30)

        assert isinstance(result, LSDResult)
        # May or may not succeed depending on problem validity
        assert result.return_code is not None

    def test_count_solutions_from_files(self):
        """Test solution counting from output files."""
        runner = LSDRunner()

        # Test with mock file list
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            (tmpdir / "sol1.sol").write_text("solution 1")
            (tmpdir / "sol2.sol").write_text("solution 2")
            (tmpdir / "output.out").write_text("log")

            files = list(tmpdir.glob("*"))
            count = runner._count_solutions("", files)

            assert count == 2  # Two .sol files

    def test_count_solutions_from_stdout(self):
        """Test solution counting from stdout."""
        runner = LSDRunner()

        stdout = "Found 5 solutions in 0.1 seconds"
        count = runner._count_solutions(stdout, [])

        assert count == 5


class TestLSDRunnerFileHandling:
    """Tests for file handling."""

    def test_creates_temp_dir_if_none(self):
        """Test that temp directory is created if output_dir not specified."""
        problem = LSDProblem(name="test")
        problem.add_atom(LSDAtom(1, "C", Hybridization.SP3, 3))

        runner = LSDRunner()
        if runner.lsd_path is None:
            # Test just the input file writing part
            with tempfile.TemporaryDirectory() as tmpdir:
                from lucy_ng.lsd.generator import LSDInputGenerator
                output_path = Path(tmpdir) / "test.lsd"
                LSDInputGenerator.write_file(problem, output_path)
                assert output_path.exists()
        else:
            # Full test with LSD
            result = runner.run(problem)
            # Result should exist regardless of success
            assert isinstance(result, LSDResult)

    def test_uses_specified_output_dir(self):
        """Test that specified output directory is used."""
        problem = LSDProblem(name="test")
        problem.add_atom(LSDAtom(1, "C", Hybridization.SP3, 3))

        runner = LSDRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            if runner.lsd_path is None:
                # Just test file writing
                from lucy_ng.lsd.generator import LSDInputGenerator
                output_path = tmpdir / "test.lsd"
                LSDInputGenerator.write_file(problem, output_path)
                assert output_path.exists()
            else:
                result = runner.run(problem, output_dir=tmpdir, keep_files=True)
                assert result.output_dir == tmpdir
                assert (tmpdir / "test.lsd").exists()


class TestLSDRunnerMocked:
    """Tests with mocked subprocess for consistent behavior."""

    def test_timeout_handling(self, monkeypatch):
        """Test timeout is properly handled."""
        import subprocess

        def mock_run(*args, **kwargs):
            raise subprocess.TimeoutExpired(cmd="lsd", timeout=1)

        monkeypatch.setattr(subprocess, "run", mock_run)

        runner = LSDRunner(lsd_path="/bin/true")  # Use any existing executable
        problem = LSDProblem(name="test")
        problem.add_atom(LSDAtom(1, "C", Hybridization.SP3, 3))

        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.run(problem, output_dir=Path(tmpdir), timeout=1)

        assert result.success is False
        assert "timed out" in result.stderr

    def test_exception_handling(self, monkeypatch):
        """Test general exception handling."""
        import subprocess

        def mock_run(*args, **kwargs):
            raise OSError("Execution failed")

        monkeypatch.setattr(subprocess, "run", mock_run)

        runner = LSDRunner(lsd_path="/bin/true")
        problem = LSDProblem(name="test")
        problem.add_atom(LSDAtom(1, "C", Hybridization.SP3, 3))

        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.run(problem, output_dir=Path(tmpdir))

        assert result.success is False
        assert "Execution failed" in result.stderr

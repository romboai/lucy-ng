"""LSD (Logic for Structure Determination) runner."""

import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from lucy_ng.lsd.generator import LSDInputGenerator
from lucy_ng.lsd.models import LSDProblem


@dataclass
class LSDResult:
    """Result from LSD execution.

    Attributes:
        success: Whether LSD completed successfully
        solution_count: Number of solutions found
        solutions: List of solution file contents
        output_files: Paths to generated output files
        stdout: Standard output from LSD
        stderr: Standard error from LSD
        return_code: Process return code
        input_file: Path to the input file used
        output_dir: Directory containing output files
    """

    success: bool
    solution_count: int
    solutions: list[str] = field(default_factory=list)
    output_files: list[Path] = field(default_factory=list)
    stdout: str = ""
    stderr: str = ""
    return_code: int = 0
    input_file: Path | None = None
    output_dir: Path | None = None

    def summary(self) -> str:
        """Return a summary of the result."""
        status = "Success" if self.success else "Failed"
        lines = [
            f"LSD Result: {status}",
            f"  Solutions found: {self.solution_count}",
            f"  Return code: {self.return_code}",
        ]
        if self.output_files:
            lines.append(f"  Output files: {len(self.output_files)}")
        if self.stderr and not self.success:
            lines.append(f"  Error: {self.stderr[:200]}")
        return "\n".join(lines)


class LSDRunner:
    """Execute LSD solver.

    Manages execution of the LSD program as a subprocess,
    handling input file creation and output file parsing.
    """

    # Common locations to search for LSD
    SEARCH_PATHS = [
        "/usr/local/bin/lsd",
        "/usr/bin/lsd",
        "~/.local/bin/lsd",
        "~/LSD/lsd",
        "~/PyLSD/LSD/lsd",
    ]

    def __init__(self, lsd_path: str | Path | None = None):
        """Initialize with path to LSD executable.

        Args:
            lsd_path: Path to LSD executable. If None, will search
                     in PATH and common locations.
        """
        if lsd_path:
            self.lsd_path = Path(lsd_path).expanduser()
        else:
            self.lsd_path = self._find_lsd()

    def run(
        self,
        problem: LSDProblem,
        output_dir: Path | None = None,
        timeout: int = 60,
        keep_files: bool = False,
    ) -> LSDResult:
        """Run LSD on problem and return results.

        Args:
            problem: LSD problem to solve
            output_dir: Directory for output files. If None, uses temp dir.
            timeout: Maximum execution time in seconds
            keep_files: If True, don't clean up temp files

        Returns:
            LSDResult with solution information

        Raises:
            FileNotFoundError: If LSD executable not found
            RuntimeError: If LSD execution fails critically
        """
        if self.lsd_path is None:
            raise FileNotFoundError(
                "LSD executable not found. Install LSD or provide path."
            )

        # Create output directory
        if output_dir:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            cleanup = False
        else:
            output_dir = Path(tempfile.mkdtemp(prefix="lsd_"))
            cleanup = not keep_files

        try:
            # Write input file
            input_file = output_dir / f"{problem.name}.lsd"
            LSDInputGenerator.write_file(problem, input_file)

            # Run LSD
            result = self._execute_lsd(input_file, output_dir, timeout)
            result.input_file = input_file
            result.output_dir = output_dir

            return result

        finally:
            if cleanup and output_dir.exists():
                shutil.rmtree(output_dir, ignore_errors=True)

    def run_file(
        self,
        input_file: Path | str,
        output_dir: Path | None = None,
        timeout: int = 60,
    ) -> LSDResult:
        """Run LSD on an existing input file.

        Args:
            input_file: Path to LSD input file
            output_dir: Directory for output files
            timeout: Maximum execution time in seconds

        Returns:
            LSDResult with solution information
        """
        if self.lsd_path is None:
            raise FileNotFoundError(
                "LSD executable not found. Install LSD or provide path."
            )

        input_file = Path(input_file)
        if not input_file.exists():
            raise FileNotFoundError(f"Input file not found: {input_file}")

        if output_dir is None:
            output_dir = input_file.parent

        result = self._execute_lsd(input_file, output_dir, timeout)
        result.input_file = input_file
        result.output_dir = output_dir

        return result

    def _execute_lsd(
        self,
        input_file: Path,
        output_dir: Path,
        timeout: int,
    ) -> LSDResult:
        """Execute LSD subprocess.

        Args:
            input_file: Path to input file
            output_dir: Working directory
            timeout: Timeout in seconds

        Returns:
            LSDResult with execution information
        """
        try:
            # LSD command: lsd < input.lsd
            proc = subprocess.run(
                [str(self.lsd_path)],
                input=input_file.read_text(),
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=output_dir,
            )

            # Find output files
            output_files = list(output_dir.glob("*.sol")) + list(output_dir.glob("*.out"))

            # Count solutions from output
            solution_count = self._count_solutions(proc.stdout, output_files)

            # Read solution contents
            solutions = []
            for sol_file in sorted(output_dir.glob("*.sol")):
                solutions.append(sol_file.read_text())

            return LSDResult(
                success=proc.returncode == 0,
                solution_count=solution_count,
                solutions=solutions,
                output_files=output_files,
                stdout=proc.stdout,
                stderr=proc.stderr,
                return_code=proc.returncode,
            )

        except subprocess.TimeoutExpired:
            return LSDResult(
                success=False,
                solution_count=0,
                stderr=f"LSD execution timed out after {timeout} seconds",
                return_code=-1,
            )

        except Exception as e:
            return LSDResult(
                success=False,
                solution_count=0,
                stderr=str(e),
                return_code=-1,
            )

    def _count_solutions(self, stdout: str, output_files: list[Path]) -> int:
        """Count number of solutions from LSD output.

        Args:
            stdout: LSD standard output
            output_files: List of output files

        Returns:
            Number of solutions found
        """
        # Try to parse from stdout
        for line in stdout.split("\n"):
            if "solution" in line.lower():
                # Try to extract number
                import re
                match = re.search(r"(\d+)\s+solution", line.lower())
                if match:
                    return int(match.group(1))

        # Fallback: count .sol files
        sol_files = [f for f in output_files if f.suffix == ".sol"]
        return len(sol_files)

    @classmethod
    def _find_lsd(cls) -> Path | None:
        """Try to find LSD executable.

        Returns:
            Path to LSD executable, or None if not found
        """
        # Check PATH first
        lsd_in_path = shutil.which("lsd")
        if lsd_in_path:
            return Path(lsd_in_path)

        # Check common locations
        for path_str in cls.SEARCH_PATHS:
            path = Path(path_str).expanduser()
            if path.exists() and path.is_file():
                return path

        return None

    @classmethod
    def is_available(cls) -> bool:
        """Check if LSD is available on the system.

        Returns:
            True if LSD executable is found
        """
        return cls._find_lsd() is not None

    @classmethod
    def get_version(cls) -> str | None:
        """Get LSD version if available.

        Returns:
            Version string, or None if not available
        """
        lsd_path = cls._find_lsd()
        if lsd_path is None:
            return None

        try:
            # Try running lsd --version or similar
            result = subprocess.run(
                [str(lsd_path), "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass

        return "unknown"

"""Parser for LSD output files."""

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class LSDSolution:
    """Single solution from LSD.

    Represents one possible molecular structure found by LSD/outlsd.

    Attributes:
        index: Solution number (1-based)
        smiles: SMILES string for the structure
    """

    index: int
    smiles: str

    def summary(self) -> str:
        """Return a summary of the solution."""
        return f"Solution {self.index}: {self.smiles}"


class LSDOutputParser:
    """Parse LSD/outlsd output files.

    The primary input for ranking is a SMILES file produced by outlsd,
    containing one SMILES string per line.
    """

    @staticmethod
    def parse_smiles_file(smiles_path: Path | str) -> list[LSDSolution]:
        """Parse a SMILES file with one SMILES per line.

        This is the standard output format from outlsd. Each line contains
        one SMILES string representing an LSD solution.

        Args:
            smiles_path: Path to SMILES file (e.g., outlsd.out)

        Returns:
            List of LSDSolution objects, indexed 1, 2, 3, ...
        """
        smiles_path = Path(smiles_path)
        if not smiles_path.exists():
            raise FileNotFoundError(f"SMILES file not found: {smiles_path}")

        content = smiles_path.read_text()
        solutions = []

        for line in content.strip().split("\n"):
            line = line.strip()
            # Skip comments and empty lines
            if not line or line.startswith("#") or line.startswith(";"):
                continue
            # Basic SMILES validation: contains letters and possibly brackets, numbers, etc.
            if re.match(r"^[A-Za-z0-9@\[\]\(\)=#\-\+\\/\.]+$", line):
                solutions.append(
                    LSDSolution(index=len(solutions) + 1, smiles=line)
                )

        return solutions

    @staticmethod
    def parse_summary_output(output: str) -> dict:
        """Parse LSD summary output for statistics.

        Args:
            output: LSD stdout content

        Returns:
            Dictionary with parsed statistics
        """
        stats = {
            "solution_count": 0,
            "execution_time": None,
            "status": "unknown",
        }

        # Look for solution count
        count_match = re.search(r"(\d+)\s+solution", output.lower())
        if count_match:
            stats["solution_count"] = int(count_match.group(1))

        # Look for timing information
        time_match = re.search(r"(\d+\.?\d*)\s*(sec|second|ms)", output.lower())
        if time_match:
            stats["execution_time"] = float(time_match.group(1))

        # Determine status
        if "error" in output.lower():
            stats["status"] = "error"
        elif "no solution" in output.lower():
            stats["status"] = "no_solution"
        elif stats["solution_count"] > 0:
            stats["status"] = "success"

        return stats

    @staticmethod
    def solutions_to_smiles_list(solutions: list[LSDSolution]) -> list[str]:
        """Extract SMILES strings from solutions.

        Args:
            solutions: List of parsed solutions

        Returns:
            List of SMILES strings
        """
        return [s.smiles for s in solutions]

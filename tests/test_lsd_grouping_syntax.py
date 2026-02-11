"""Tests for LSD parenthesized syntax for signal grouping.

This module validates that LSD accepts parenthesized atom lists in HMBC constraints
for combinatorial exploration of close chemical shifts (e.g., HMBC (2 3) 8).

The tests confirm that the output format from signal grouping analysis can be used
directly in LSD input files to enable automatic permutation of assignments.
"""

import shutil
import tempfile
from pathlib import Path

import pytest


class TestLSDParenthesizedSyntax:
    """Test LSD parenthesized atom list syntax for HMBC constraints.

    Tests validate that:
    1. LSD accepts HMBC (2 3) 8 syntax for 2-way combinatorial exchange
    2. LSD accepts HMBC (2 3 4) 8 syntax for 3-way combinatorial exchange
    3. LSD produces solutions (not errors) when parenthesized lists are used
    4. Parenthesized syntax produces >= solutions vs fixed assignment
    """

    @pytest.fixture
    def lsd_available(self):
        """Check if LSD binary is available."""
        return shutil.which("LSD") is not None

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for LSD files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def _write_lsd_file(self, filepath: Path, content: str) -> None:
        """Write LSD file with given content."""
        filepath.write_text(content)

    def _run_lsd(self, lsd_file: Path, timeout: int = 30) -> tuple[bool, int, str]:
        """Run LSD on given file.

        Returns:
            (success, solution_count, stderr)
        """
        import subprocess

        try:
            result = subprocess.run(
                ["LSD", str(lsd_file)],
                cwd=lsd_file.parent,
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            # LSD writes solution count to stderr (not stdout)
            stderr = result.stderr

            # Check for solution files (.sol) created in working directory
            sol_files = list(lsd_file.parent.glob("*.sol"))
            solution_count = len(sol_files)

            # Success if solutions were generated
            success = solution_count > 0

            return success, solution_count, stderr

        except subprocess.TimeoutExpired:
            return False, 0, "LSD timed out"
        except Exception as e:
            return False, 0, str(e)

    @pytest.mark.skipif(
        shutil.which("LSD") is None,
        reason="LSD not installed - cannot validate parenthesized syntax"
    )
    def test_lsd_accepts_2way_parenthesized_hmbc(self, temp_dir):
        """Test that LSD accepts HMBC (2 3) 8 syntax for 2-way grouping.

        This tests the case where two carbon shifts are close (within 0.25 ppm)
        and have compatible multiplicities. LSD should try both permutations:
        - Carbon 2 → Proton 8
        - Carbon 3 → Proton 8

        Example: Ibuprofen C4/C5 at 44.90/45.03 ppm (both CH2).
        """
        # Create simple molecule: propanol C3H8O
        # 3 carbons + 1 oxygen
        # Carbons 2 and 3 are "close" in this test (simulated grouping)

        lsd_content = """; Test case: 2-way parenthesized HMBC
; Propanol with C2/C3 grouped (simulated close shifts)

; Carbons
MULT 1 C 3 0   ; CH3
MULT 2 C 2 0   ; CH2 (close to C3)
MULT 3 C 2 0   ; CH2 (close to C2)

; Oxygen
MULT 4 O 1 0   ; OH

; HSQC (carbons with protons)
HSQC 1 1
HSQC 2 2
HSQC 3 3

; HMBC with parenthesized syntax - C1 sees C2 or C3
HMBC (2 3) 1

; HMBC - C3 sees C1
HMBC 3 1
"""

        lsd_file = temp_dir / "test_2way.lsd"
        self._write_lsd_file(lsd_file, lsd_content)

        success, solution_count, stderr = self._run_lsd(lsd_file)

        assert success, f"LSD failed with parenthesized syntax. stderr: {stderr}"
        assert solution_count > 0, "Expected solutions with 2-way parenthesized HMBC"

    @pytest.mark.skipif(
        shutil.which("LSD") is None,
        reason="LSD not installed - cannot validate parenthesized syntax"
    )
    def test_lsd_accepts_3way_parenthesized_hmbc(self, temp_dir):
        """Test that LSD accepts HMBC (2 3 4) 8 syntax for 3-way grouping.

        This tests the case where three carbon shifts are all close (all within
        0.25 ppm of each other) and have compatible multiplicities.

        LSD should try all three permutations when exploring structure space.
        """
        # Create simple molecule: butanol C4H10O
        # 4 carbons + 1 oxygen
        # Carbons 2, 3, 4 are "close" (simulated grouping)

        lsd_content = """; Test case: 3-way parenthesized HMBC
; Butanol with C2/C3/C4 grouped (simulated close shifts)

; Carbons
MULT 1 C 3 0   ; CH3
MULT 2 C 2 0   ; CH2 (close to C3/C4)
MULT 3 C 2 0   ; CH2 (close to C2/C4)
MULT 4 C 2 0   ; CH2 (close to C2/C3)

; Oxygen
MULT 5 O 1 0   ; OH

; HSQC
HSQC 1 1
HSQC 2 2
HSQC 3 3
HSQC 4 4

; HMBC with 3-way parenthesized syntax
HMBC (2 3 4) 1

; HMBC - C4 sees C1
HMBC 4 1
"""

        lsd_file = temp_dir / "test_3way.lsd"
        self._write_lsd_file(lsd_file, lsd_content)

        success, solution_count, stderr = self._run_lsd(lsd_file)

        assert success, f"LSD failed with 3-way parenthesized syntax. stderr: {stderr}"
        assert solution_count > 0, "Expected solutions with 3-way parenthesized HMBC"

    @pytest.mark.skipif(
        shutil.which("LSD") is None,
        reason="LSD not installed - cannot validate parenthesized syntax"
    )
    def test_parenthesized_produces_more_solutions_than_fixed(self, temp_dir):
        """Test that parenthesized syntax explores more permutations.

        Validates that HMBC (2 3) 8 produces >= solutions compared to HMBC 2 8
        because it allows combinatorial exploration of both assignments.

        This is the key benefit of signal grouping - it enables LSD to find
        solutions that would be missed with rigid assignments.
        """
        # Fixed assignment: C1 sees C2 only
        lsd_fixed = """; Test case: Fixed assignment (baseline)

MULT 1 C 3 0
MULT 2 C 2 0
MULT 3 C 2 0
MULT 4 O 1 0

HSQC 1 1
HSQC 2 2
HSQC 3 3

; Fixed HMBC - C2 to H1 only
HMBC 2 1
HMBC 3 1
"""

        # Parenthesized: C1 sees C2 OR C3
        lsd_grouped = """; Test case: Grouped assignment (combinatorial)

MULT 1 C 3 0
MULT 2 C 2 0
MULT 3 C 2 0
MULT 4 O 1 0

HSQC 1 1
HSQC 2 2
HSQC 3 3

; Parenthesized HMBC - C2 or C3 to H1
HMBC (2 3) 1
HMBC 3 1
"""

        # Run fixed assignment
        lsd_fixed_file = temp_dir / "test_fixed.lsd"
        self._write_lsd_file(lsd_fixed_file, lsd_fixed)
        success_fixed, count_fixed, stderr_fixed = self._run_lsd(lsd_fixed_file)

        # Run grouped assignment
        lsd_grouped_file = temp_dir / "test_grouped.lsd"
        self._write_lsd_file(lsd_grouped_file, lsd_grouped)
        success_grouped, count_grouped, stderr_grouped = self._run_lsd(lsd_grouped_file)

        # Both should succeed
        assert success_fixed, f"Fixed assignment failed: {stderr_fixed}"
        assert success_grouped, f"Grouped assignment failed: {stderr_grouped}"

        # Grouped should produce >= solutions (explores more permutations)
        assert count_grouped >= count_fixed, (
            f"Expected grouped syntax to produce >= solutions. "
            f"Fixed: {count_fixed}, Grouped: {count_grouped}"
        )

    @pytest.mark.skipif(
        shutil.which("LSD") is None,
        reason="LSD not installed - cannot validate parenthesized syntax"
    )
    def test_parenthesized_syntax_not_causing_errors(self, temp_dir):
        """Test that parenthesized syntax doesn't cause LSD parsing errors.

        This validates that the syntax is correctly recognized by LSD's parser
        and doesn't produce syntax error messages in stderr.
        """
        lsd_content = """; Test case: Syntax validation

MULT 1 C 3 0
MULT 2 C 2 0
MULT 3 C 2 0

HSQC 1 1
HSQC 2 2
HSQC 3 3

; Parenthesized HMBC
HMBC (2 3) 1
"""

        lsd_file = temp_dir / "test_syntax.lsd"
        self._write_lsd_file(lsd_file, lsd_content)

        success, solution_count, stderr = self._run_lsd(lsd_file)

        # Check for syntax error indicators
        error_indicators = [
            "syntax error",
            "parse error",
            "invalid syntax",
            "unexpected token",
            "unrecognized command",
        ]

        stderr_lower = stderr.lower()
        for indicator in error_indicators:
            assert indicator not in stderr_lower, (
                f"LSD reported syntax error with parenthesized HMBC. "
                f"stderr: {stderr}"
            )

        # Should produce solutions
        assert success, "LSD should succeed with valid parenthesized syntax"
        assert solution_count > 0, "Should generate at least one solution"


class TestGroupingSyntaxDocumentation:
    """Tests documenting the syntax and pitfalls of signal grouping."""

    def test_documents_false_positive_risk(self):
        """Document that grouping close shifts with different multiplicities
        creates false positive risk.

        This test serves as documentation that multiplicity-aware grouping is
        critical. Grouping CH2 with CH creates combinatorial explosion where
        most permutations are chemically invalid.

        Example from Sherlock analysis:
        - C4 (CH2) at 44.90 ppm
        - C5 (CH) at 45.03 ppm
        - Difference: 0.13 ppm (within 0.25 ppm tolerance)

        Grouping these creates 2x search space but only 1/2 permutations
        are correct. This is why grouping MUST check multiplicity compatibility.
        """
        warning = """
        CRITICAL: Signal grouping must be multiplicity-aware to prevent false positives.

        Rules for multiplicity compatibility:
        1. Same multiplicity (both CH2) → COMPATIBLE, safe to group
        2. Both ambiguous (CH/CH3) → COMPATIBLE, safe to group
        3. Different definite multiplicities (CH2 vs CH) → INCOMPATIBLE, do NOT group
        4. One or both unknown → CONSERVATIVE, allow grouping but warn user

        Tolerance: 0.25 ppm (validated by Sherlock ibuprofen case)

        LSD parenthesized syntax enables combinatorial exploration:
        - HMBC (2 3) 8 → LSD tries both C2-H8 and C3-H8 correlations
        - HMBC (2 3 4) 8 → LSD tries C2-H8, C3-H8, and C4-H8

        The grouping algorithm (Plan 37-01) handles multiplicity filtering.
        This test validates that LSD understands the output format.
        """

        # This test always passes - it exists for documentation
        assert True, warning

    def test_documents_tolerance_rationale(self):
        """Document the 0.25 ppm tolerance value and its origin.

        Source: Sherlock CASE system (Wenk PhD thesis)

        Ibuprofen case:
        - C4: 44.90 ppm (CH2)
        - C5: 45.03 ppm (CH2)
        - Difference: 0.13 ppm

        Without grouping these two shifts, the candidate list was EMPTY.
        With 0.25 ppm tolerance grouping, ibuprofen was solved.

        This tolerance is conservative enough to avoid false positives while
        being permissive enough to handle realistic NMR resolution limits.
        """
        tolerance_info = """
        Signal grouping tolerance: 0.25 ppm

        Rationale:
        - NMR 13C resolution: typically 0.1-0.2 ppm at 100 MHz
        - Chemical shift prediction error: typically ±2-3 ppm
        - Close shifts in real molecules: 0.1-0.3 ppm difference common

        Ibuprofen validation:
        - C4/C5 at 44.90/45.03 ppm (Δ = 0.13 ppm)
        - Both CH2 (multiplicity compatible)
        - Grouping these was REQUIRED to solve structure

        Recommendation: Hardcode 0.25 ppm in Phase 37, make configurable if needed.
        """

        # This test always passes - it exists for documentation
        assert True, tolerance_info

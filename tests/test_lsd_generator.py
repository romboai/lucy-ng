"""Tests for LSD input file generator."""

import pytest
from pathlib import Path
import tempfile

from lucy_ng import BrukerReader, DEPTGuidedPicker, Peak1D, Peak2D, PeakList1D, PeakList2D
from lucy_ng.lsd.models import Hybridization, LSDAtom, LSDCorrelation, LSDProblem
from lucy_ng.lsd.generator import LSDInputGenerator


class TestLSDInputGeneratorBasic:
    """Basic tests for LSD input generation."""

    def test_generate_empty_problem(self):
        """Test generating input for empty problem."""
        problem = LSDProblem(name="empty")
        content = LSDInputGenerator.generate(problem)

        assert "; LSD input file: empty" in content
        assert "EXIT" in content

    def test_generate_with_atoms(self):
        """Test generating MULT lines."""
        problem = LSDProblem(name="test")
        problem.add_atom(LSDAtom(1, "C", Hybridization.SP2, 0))
        problem.add_atom(LSDAtom(2, "C", Hybridization.SP3, 2))
        problem.add_atom(LSDAtom(3, "C", Hybridization.SP3, 3))

        content = LSDInputGenerator.generate(problem)

        assert "MULT 1 C 2 0" in content
        assert "MULT 2 C 3 2" in content
        assert "MULT 3 C 3 3" in content

    def test_generate_with_molecular_formula(self):
        """Test molecular formula in header."""
        problem = LSDProblem(name="ibuprofen", molecular_formula="C13H18O2")
        content = LSDInputGenerator.generate(problem)

        assert "; Molecular formula: C13H18O2" in content

    def test_generate_with_chemical_shifts(self):
        """Test SHIX lines for chemical shifts."""
        problem = LSDProblem()
        problem.add_atom(LSDAtom(1, "C", Hybridization.SP2, 0, carbon_shift=129.5))
        problem.add_atom(LSDAtom(2, "C", Hybridization.SP3, 2, carbon_shift=45.0))

        content = LSDInputGenerator.generate(problem)

        assert "SHIX 1 129.50" in content
        assert "SHIX 2 45.00" in content

    def test_generate_hsqc_correlations(self):
        """Test HSQC correlation lines."""
        problem = LSDProblem()
        problem.add_atom(LSDAtom(1, "C", Hybridization.SP3, 1))
        problem.add_correlation(LSDCorrelation(1, 1, "HSQC"))

        content = LSDInputGenerator.generate(problem)

        assert "HSQC 1 1" in content
        assert "; Direct C-H correlations" in content

    def test_generate_hmbc_correlations(self):
        """Test HMBC correlation lines with bond distances."""
        problem = LSDProblem()
        problem.add_atom(LSDAtom(1, "C", Hybridization.SP2, 0))
        problem.add_atom(LSDAtom(2, "C", Hybridization.SP3, 2))
        problem.add_correlation(LSDCorrelation(1, 2, "HMBC", min_bonds=2, max_bonds=3))

        content = LSDInputGenerator.generate(problem)

        # LSD HMBC uses 2 parameters; bond distance defaults to 2-3
        assert "HMBC 1 2" in content
        assert "; Long-range C-H correlations" in content

    def test_generate_cosy_correlations(self):
        """Test COSY correlation lines."""
        problem = LSDProblem()
        problem.add_atom(LSDAtom(1, "C", Hybridization.SP3, 1))
        problem.add_atom(LSDAtom(2, "C", Hybridization.SP3, 2))
        problem.add_correlation(LSDCorrelation(1, 2, "COSY"))

        content = LSDInputGenerator.generate(problem)

        assert "COSY 1 2" in content
        assert "; H-H correlations" in content

    def test_atoms_sorted_by_index(self):
        """Test that atoms are output in index order."""
        problem = LSDProblem()
        problem.add_atom(LSDAtom(3, "C", Hybridization.SP3, 3))
        problem.add_atom(LSDAtom(1, "C", Hybridization.SP2, 0))
        problem.add_atom(LSDAtom(2, "C", Hybridization.SP3, 2))

        content = LSDInputGenerator.generate(problem)
        lines = content.split("\n")
        mult_lines = [l for l in lines if l.startswith("MULT")]

        assert mult_lines[0] == "MULT 1 C 2 0"
        assert mult_lines[1] == "MULT 2 C 3 2"
        assert mult_lines[2] == "MULT 3 C 3 3"


class TestLSDInputGeneratorFile:
    """Tests for file writing."""

    def test_write_file(self):
        """Test writing LSD input to file."""
        problem = LSDProblem(name="test")
        problem.add_atom(LSDAtom(1, "C", Hybridization.SP2, 0))

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.lsd"
            result_path = LSDInputGenerator.write_file(problem, output_path)

            assert result_path.exists()
            content = result_path.read_text()
            assert "MULT 1 C 2 0" in content


class TestLSDInputGeneratorFromPeakData:
    """Tests for building problems from peak data."""

    def test_from_carbon_peaks_only(self):
        """Test building problem from 13C peaks only."""
        carbon_peaks = PeakList1D(
            peaks=[
                Peak1D(position=129.5, intensity=1000.0),
                Peak1D(position=45.0, intensity=800.0),
                Peak1D(position=22.5, intensity=600.0),
            ],
            nucleus="13C",
        )

        problem = LSDInputGenerator.from_peak_data(
            carbon_peaks=carbon_peaks,
            name="test",
        )

        assert len(problem.atoms) == 3
        # Sorted by ppm descending, so 129.5 is index 1
        assert problem.get_atom_by_index(1).carbon_shift == 129.5
        assert problem.get_atom_by_index(2).carbon_shift == 45.0
        assert problem.get_atom_by_index(3).carbon_shift == 22.5

    def test_from_peaks_with_hsqc(self):
        """Test building problem with HSQC correlations."""
        carbon_peaks = PeakList1D(
            peaks=[
                Peak1D(position=129.5, intensity=1000.0),
                Peak1D(position=45.0, intensity=800.0),
            ],
            nucleus="13C",
        )

        hsqc_peaks = PeakList2D(
            peaks=[
                Peak2D(f1_position=129.5, f2_position=7.2, intensity=100.0),
                Peak2D(f1_position=45.0, f2_position=2.5, intensity=100.0),
            ],
            f1_nucleus="13C",
            f2_nucleus="1H",
            experiment_type="HSQC",
        )

        problem = LSDInputGenerator.from_peak_data(
            carbon_peaks=carbon_peaks,
            hsqc_peaks=hsqc_peaks,
        )

        # Should have 2 HSQC correlations
        hsqc_corrs = [c for c in problem.correlations if c.correlation_type == "HSQC"]
        assert len(hsqc_corrs) == 2

    def test_from_peaks_no_duplicate_hsqc(self):
        """Test that duplicate HSQC peaks don't create duplicate correlations."""
        carbon_peaks = PeakList1D(
            peaks=[Peak1D(position=129.5, intensity=1000.0)],
            nucleus="13C",
        )

        hsqc_peaks = PeakList2D(
            peaks=[
                Peak2D(f1_position=129.5, f2_position=7.2, intensity=100.0),
                Peak2D(f1_position=129.5, f2_position=7.2, intensity=90.0),  # Duplicate
            ],
            f1_nucleus="13C",
            f2_nucleus="1H",
            experiment_type="HSQC",
        )

        problem = LSDInputGenerator.from_peak_data(
            carbon_peaks=carbon_peaks,
            hsqc_peaks=hsqc_peaks,
        )

        hsqc_corrs = [c for c in problem.correlations if c.correlation_type == "HSQC"]
        assert len(hsqc_corrs) == 1  # Should deduplicate

    def test_from_peaks_with_molecular_formula(self):
        """Test molecular formula is preserved."""
        carbon_peaks = PeakList1D(
            peaks=[Peak1D(position=129.5, intensity=1000.0)],
            nucleus="13C",
        )

        problem = LSDInputGenerator.from_peak_data(
            carbon_peaks=carbon_peaks,
            molecular_formula="C13H18O2",
        )

        assert problem.molecular_formula == "C13H18O2"


class TestLSDInputGeneratorIntegration:
    """Integration tests with real Ibuprofen data."""

    @pytest.fixture
    def ibuprofen_dept_result(self):
        """Load Ibuprofen DEPT-guided result."""
        hsqc = BrukerReader.read_2d("data/Ibuprofen/6")
        dept = BrukerReader.read_1d("data/Ibuprofen/3")
        return DEPTGuidedPicker.pick_hsqc_peaks(hsqc, dept)

    def test_from_dept_result(self, ibuprofen_dept_result):
        """Test building LSD problem from DEPT result."""
        problem = LSDInputGenerator.from_dept_result(
            dept_result=ibuprofen_dept_result,
            molecular_formula="C13H18O2",
            name="ibuprofen",
        )

        # Should have atoms from DEPT peaks
        assert len(problem.atoms) >= 7  # At least 7 protonated carbons
        assert problem.molecular_formula == "C13H18O2"
        assert problem.name == "ibuprofen"

    def test_from_dept_result_has_multiplicities(self, ibuprofen_dept_result):
        """Test that DEPT multiplicities are used for H count."""
        problem = LSDInputGenerator.from_dept_result(
            dept_result=ibuprofen_dept_result,
        )

        # Check that some atoms have hydrogen counts set
        h_counts = [a.hydrogen_count for a in problem.atoms]
        assert any(h > 0 for h in h_counts), "Should have atoms with hydrogens"

    def test_from_dept_result_generates_valid_lsd(self, ibuprofen_dept_result):
        """Test that generated LSD file is syntactically valid."""
        problem = LSDInputGenerator.from_dept_result(
            dept_result=ibuprofen_dept_result,
            molecular_formula="C13H18O2",
        )

        content = LSDInputGenerator.generate(problem)

        # Check basic structure
        assert content.startswith(";")  # Comment header
        assert "MULT" in content
        assert "EXIT" in content

        # Check all MULT lines are valid
        for line in content.split("\n"):
            if line.startswith("MULT"):
                parts = line.split()
                assert len(parts) >= 5  # MULT idx elem hyb hcount
                assert parts[1].isdigit()  # Index
                assert parts[2] in ("C", "N", "O", "S", "P")  # Element
                assert parts[3] in ("1", "2", "3")  # Hybridization
                assert parts[4].isdigit()  # H count

    def test_full_workflow_output(self, ibuprofen_dept_result):
        """Test complete workflow and print output for inspection."""
        problem = LSDInputGenerator.from_dept_result(
            dept_result=ibuprofen_dept_result,
            molecular_formula="C13H18O2",
            name="ibuprofen",
        )

        content = LSDInputGenerator.generate(problem)

        # Just verify it generates without error and has expected sections
        assert "; LSD input file: ibuprofen" in content
        assert "; Molecular formula: C13H18O2" in content
        assert "MULT" in content
        assert "HSQC" in content or len(problem.correlations) == 0
        assert "EXIT" in content

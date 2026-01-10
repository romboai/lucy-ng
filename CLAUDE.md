# lucy-ng

AI-agent powered Computer-Assisted Structure Elucidation for organic natural products.

## Quick Reference

```bash
# Run tests
pytest

# Run tests with coverage
pytest --cov=lucy_ng

# Type checking
mypy src/lucy_ng

# Linting
ruff check src tests

# Build package
hatch build
```

## Project Structure

```
src/lucy_ng/
├── models/          # Pydantic v2 data models (Spectrum1D, Spectrum2D, Peak1D, etc.)
├── readers/         # NMR file readers (BrukerReader)
├── processing/      # Peak picking, signal processing
├── dereplication/   # Database matching (NMRShiftDBLoader, SpectrumMatcher)
├── solvers/         # LSD/pyLSD integration (future)
└── __init__.py      # Public API exports

tests/               # pytest tests
data/                # Test NMR datasets (Bruker format)
.planning/           # GSD planning files (PROJECT.md, ROADMAP.md, STATE.md)
```

## Technology Stack

- **Python 3.10+** - minimum version
- **Pydantic v2** - data models with validation
- **nmrglue** - Bruker NMR file parsing
- **NumPy/SciPy** - numerical processing
- **RDKit** - SD file parsing for reference databases
- **hatch** - build system
- **pytest** - testing
- **ruff** - linting
- **mypy** - type checking (strict mode)

## Code Conventions

- Type hints on all functions
- Docstrings with Args/Returns/Raises sections
- Static methods for readers (e.g., `BrukerReader.read_1d()`)
- Helper functions prefixed with `_` for private use
- Line length: 100 characters
- Imports: standard library, third-party, local (isort order)

## NMR Data

Test data is Bruker format in `data/` directory:
- `data/Ibuprofen/` - 1D (1H, 13C) and 2D (COSY, HSQC, HMBC)
- `data/4-Hydroxy-3-Iodo-biphenyl/` - includes NOESY
- Processed data read from `pdata/1/` subdirectory

## Key Patterns

### Reading NMR data
```python
from lucy_ng import BrukerReader, Spectrum1D

spectrum: Spectrum1D = BrukerReader.read_1d("data/Ibuprofen/10")
```

### Models are Pydantic
```python
from lucy_ng.models import Peak1D

peak = Peak1D(ppm=45.2, intensity=1.0e6, assignment="C-1")
```

## Peak Picking

### HSQC: Use DEPT-Guided Picker (Preferred)

For HSQC peak picking, **always use `DEPTGuidedPicker`** instead of raw `PeakPicker2D`. This ensures:
- Only peaks corresponding to real protonated carbons are returned
- Noise peaks are filtered out by requiring DEPT correspondence
- Carbon multiplicity (CH, CH2, CH3) is extracted from DEPT signs
- Adaptive thresholding finds weak signals without picking noise

```python
from lucy_ng import BrukerReader
from lucy_ng.processing import DEPTGuidedPicker

hsqc = BrukerReader.read_2d("data/Ibuprofen/6")      # HSQC
dept135 = BrukerReader.read_1d("data/Ibuprofen/3")   # DEPT-135
dept90 = BrukerReader.read_1d("data/Ibuprofen/4")    # DEPT-90 (optional)

# With DEPT-90 for full CH/CH3 disambiguation
result = DEPTGuidedPicker.pick_hsqc_peaks_with_dept90(hsqc, dept135, dept90)

# Or with DEPT-135 only (CH and CH3 remain ambiguous as "CH/CH3")
result = DEPTGuidedPicker.pick_hsqc_peaks(hsqc, dept135)

print(result.summary())
# Access: result.peaks, result.carbon_multiplicities, result.all_carbons_found
```

**Note on symmetry**: Equivalent carbons (e.g., ortho/meta in para-substituted benzene) appear as single signals. The observed signal count may be less than the molecular formula carbon count.

### HMBC: Use Guided Picker (Preferred)

For HMBC peak picking, **use `HMBCGuidedPicker`** to filter noise by requiring:
1. Carbon (F1) must match a known carbon from 13C or DEPT spectrum
2. Proton (F2) must match a known proton from HSQC

```python
from lucy_ng import BrukerReader
from lucy_ng.processing import HMBCGuidedPicker

hmbc = BrukerReader.read_2d("data/Ibuprofen/7")
c13 = BrukerReader.read_1d("data/Ibuprofen/2")
hsqc = BrukerReader.read_2d("data/Ibuprofen/6")
dept135 = BrukerReader.read_1d("data/Ibuprofen/3")  # optional

result = HMBCGuidedPicker.pick_hmbc_peaks_from_spectra(
    hmbc=hmbc,
    carbon_spectrum=c13,
    hsqc=hsqc,
    dept135=dept135,  # optional, adds extra carbon positions
)

print(result.summary())
# Access: result.peaks, result.validated_count, result.rejected_count
```

### Other 2D Spectra (COSY, etc.)

For COSY and other 2D spectra, use `PeakPicker2D`:
```python
from lucy_ng.processing import PeakPicker2D

cosy = BrukerReader.read_2d("data/Ibuprofen/5")
peaks = PeakPicker2D.pick_peaks(cosy, threshold=0.05)
```

## Planning

This project uses GSD (Get Shit Done) workflow. Planning files in `.planning/`:
- `STATE.md` - current position and session context
- `ROADMAP.md` - milestone and phase overview
- `PROJECT.md` - vision, requirements, constraints
- `phases/` - detailed phase plans and summaries

Use `/gsd:resume-work` to restore context at session start.

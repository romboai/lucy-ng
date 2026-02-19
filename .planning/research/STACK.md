# Technology Stack: Fragment Library and SSC Search

**Project:** lucy-ng
**Milestone:** v5.0 Fragment Library (SSC extraction, fingerprint indexing, spectral search)
**Researched:** 2026-02-19
**Confidence:** HIGH

---

## Context: What Already Exists

The existing stack (do not re-evaluate these):

| Component | Version | Status |
|-----------|---------|--------|
| Python | 3.10+ | Locked |
| RDKit | 2025.9.4 | Installed, in use |
| NumPy | 2.2.1 | Installed, in use |
| SciPy | 1.17.0 | Installed, in use |
| Pydantic v2 | 2.12.5 | Installed, in use |
| Click | 8.1.8 | Installed, in use |
| SQLite | stdlib | In use (schema v6, 928K compounds) |
| tqdm | 4.67.3 | Installed, in use |
| hosegen | git | Installed, in use |

The fragment library milestone adds capabilities on top of this stack. **No existing dependencies are changed or removed.**

---

## New Capabilities Required

The fragment library milestone needs to:

1. **Extract SSCs** — enumerate atom-environment fragments from 928K compounds, pair each fragment with its observed 13C subspectrum
2. **Build fingerprints** — encode each SSC's subspectrum as a 256-bit bitset (2 ppm bins)
3. **Index fingerprints** — store 24M+ SSC records in SQLite with binary fingerprints for fast retrieval
4. **Screen fragments** — match experimental spectrum against SSC library via Boolean AND bitset pre-screening
5. **Fine matching** — score surviving SSCs by DEV/AVGDEV spectral deviation
6. **Convert to LSD constraints** — translate matching fragments to DEFF/FEXP goodlist commands

---

## Recommended Stack Additions

### Core: No New Python Dependencies

**Finding:** All required operations are achievable with the existing stack. No new `pip install` required.

| Operation | Implementation | Why No New Dependency |
|-----------|---------------|----------------------|
| Fragment extraction (atom environments) | `rdkit.Chem.FindAtomEnvironmentOfRadiusN` + `PathToSubmol` | Already in RDKit 2025.9.4 |
| Bitset fingerprints (256-bit) | `numpy.ndarray` of `uint8[32]` with bitwise ops | NumPy 2.2.1 supports vectorized bitwise AND |
| SSC storage | SQLite BLOB column for fingerprint bytes | Existing schema extension |
| Bitset screening | `numpy.bitwise_and` on (N, 32) array | Vectorized, no extra lib needed |
| DEFF fragment file generation | Python string formatting + file I/O | No new dependency |
| Parallel extraction pipeline | `concurrent.futures.ProcessPoolExecutor` | Python stdlib |

**Confidence:** HIGH — RDKit 2025.9.4 includes `FindAtomEnvironmentOfRadiusN`, `PathToSubmol`, `MolToSmiles`, all verified in official docs. NumPy 2.2.1 bitwise operations confirmed in official NumPy documentation.

---

### Schema Extension: SQLite Fragment Library Tables

The existing SQLite database (schema v6) gets two new tables. Schema version bumps to v7.

#### Table: `ssc_fragments`

Stores the substructure side of each SSC — the atom-environment subgraph as SMILES.

```sql
CREATE TABLE ssc_fragments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    compound_id INTEGER NOT NULL,     -- FK to compounds.id
    center_atom_idx INTEGER NOT NULL, -- atom index in parent compound
    radius INTEGER NOT NULL,          -- sphere radius (1-4)
    fragment_smiles TEXT NOT NULL,    -- canonical SMILES of fragment (no explicit H)
    atom_count INTEGER NOT NULL,      -- number of heavy atoms in fragment
    FOREIGN KEY (compound_id) REFERENCES compounds(id) ON DELETE CASCADE
);

CREATE INDEX idx_ssc_fragments_smiles ON ssc_fragments(fragment_smiles);
CREATE INDEX idx_ssc_fragments_compound ON ssc_fragments(compound_id);
```

**Rationale:** `fragment_smiles` as the lookup key allows deduplication — identical substructures from different compounds map to the same fragment. Indexing on SMILES enables grouping all SSCs by substructure.

#### Table: `ssc_spectra`

Stores the subspectrum side — the observed 13C shifts for each SSC, plus the 256-bit bitset fingerprint for fast screening.

```sql
CREATE TABLE ssc_spectra (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fragment_id INTEGER NOT NULL,     -- FK to ssc_fragments.id
    shift_ppm REAL NOT NULL,          -- 13C shift for this carbon in the fragment
    fingerprint BLOB NOT NULL,        -- 32 bytes = 256 bits, 2 ppm bins, 0-511 ppm
    signal_count INTEGER NOT NULL,    -- number of 13C signals in this subspectrum
    FOREIGN KEY (fragment_id) REFERENCES ssc_fragments(id) ON DELETE CASCADE
);

CREATE INDEX idx_ssc_spectra_fragment ON ssc_spectra(fragment_id);
```

**Alternative design considered:** Single denormalized `ssc` table with all shifts comma-joined. Rejected because normalized schema enables:
- Efficient per-signal queries for DEV/AVGDEV scoring
- Easier schema migration if more spectral dimensions added (multiplicity, 1H shifts)
- Standard relational integrity

**Fingerprint encoding:** 256 bits = 32 bytes stored as BLOB. Each bit corresponds to a 2 ppm bin covering the 13C range 0-511 ppm (256 bins x 2 ppm/bin). Bit N is set if the subspectrum has a signal within bin N. Construction: `bin_idx = int(shift_ppm / 2.0); fingerprint[bin_idx // 8] |= (1 << (bin_idx % 8))`.

**Confidence:** HIGH — 256-bit / 2 ppm bin design is from Sherlock paper (PMC9920390), confirmed: "each fragment has a bit string representation to indicate whether a given chemical shift in the assigned subspectrum exists."

---

## Implementation Patterns

### Pattern 1: Fragment Extraction (SSC Construction)

**Tool:** `rdkit.Chem.FindAtomEnvironmentOfRadiusN` + `Chem.PathToSubmol`

```python
from rdkit import Chem

def extract_ssc_for_atom(mol: Chem.Mol, atom_idx: int, radius: int) -> str | None:
    """Extract atom-environment fragment SMILES at given radius."""
    env = Chem.FindAtomEnvironmentOfRadiusN(mol, radius, atom_idx)
    if not env:
        return None
    amap: dict[int, int] = {}
    submol = Chem.PathToSubmol(mol, env, atomMap=amap)
    if atom_idx not in amap:
        return None
    return Chem.MolToSmiles(submol, rootedAtAtom=amap[atom_idx], canonical=True)
```

**Why this approach over BRICS or other fragmentation:** BRICS breaks retrosynthetic bonds to produce synthetically accessible fragments. SSC extraction needs atom-environment spheres centered on each NMR-observed carbon — structurally correlated with HOSE codes, not synthetic accessibility. `FindAtomEnvironmentOfRadiusN` produces exactly the radius-N neighborhood needed.

**Key constraint:** Use molecules WITHOUT explicit hydrogens (same rule as HOSE code generation — see CLAUDE.md "Critical Architecture Decisions"). Consistent with existing database generation.

### Pattern 2: Bitset Fingerprint Construction

**Tool:** NumPy uint8 array, 32 bytes = 256 bits

```python
import numpy as np

def shifts_to_fingerprint(shifts: list[float]) -> bytes:
    """Encode list of 13C shifts as 256-bit fingerprint (2 ppm bins)."""
    fp = np.zeros(32, dtype=np.uint8)
    for shift in shifts:
        if 0.0 <= shift < 512.0:
            bin_idx = int(shift / 2.0)   # bin 0 = 0-2 ppm, bin 255 = 510-512 ppm
            fp[bin_idx // 8] |= np.uint8(1 << (bin_idx % 8))
    return fp.tobytes()

def fingerprint_matches_query(fragment_fp: bytes, query_fp: bytes) -> bool:
    """Boolean AND screening: all fragment bits must be set in query."""
    fp_array = np.frombuffer(fragment_fp, dtype=np.uint8)
    q_array = np.frombuffer(query_fp, dtype=np.uint8)
    # Fragment is candidate if ALL its set bits are present in query
    return bool(np.all((fp_array & q_array) == fp_array))
```

**Vectorized screening over all SSCs:**

```python
def screen_fragments(db_fingerprints: np.ndarray, query_fp: bytes) -> np.ndarray:
    """
    Vectorized Boolean AND screening.
    db_fingerprints: shape (N, 32) uint8 — all N SSC fingerprints loaded into memory
    query_fp: 32 bytes — experimental spectrum fingerprint
    Returns: boolean mask of candidates that pass screening
    """
    q_array = np.frombuffer(query_fp, dtype=np.uint8)  # shape (32,)
    # Broadcasting: for each row, check (row & query) == row
    screened = (db_fingerprints & q_array) == db_fingerprints  # (N, 32) bool
    return screened.all(axis=1)  # (N,) bool — True means candidate passed
```

**Memory estimate:** 24.5M SSCs x 32 bytes = 784 MB for in-memory screening array. Acceptable for a one-time `lucy fragment build` operation; for `lucy fragment search`, load only SSCs matching atom count <= query carbon count first to reduce the array size, then screen.

**Confidence:** HIGH — NumPy 2.2.1 bitwise operations on uint8 arrays verified in official NumPy documentation. Vectorized broadcasting pattern is standard NumPy practice.

### Pattern 3: Fine Matching (DEV/AVGDEV)

After Boolean AND screening eliminates non-candidates, score survivors by spectral deviation.

**DEV threshold (default: 3.0 ppm):** Maximum allowed deviation for any individual signal.
**AVGDEV threshold (default: 2.0 ppm):** Average deviation across all matched signals.

```python
def fine_match_ssc(fragment_shifts: list[float], query_shifts: list[float],
                   dev_threshold: float = 3.0, avgdev_threshold: float = 2.0) -> float | None:
    """
    Match fragment subspectrum against query spectrum.
    Returns AVGDEV if within thresholds, None if rejected.
    """
    deviations = []
    for frag_shift in fragment_shifts:
        # Find closest query shift
        closest_dev = min(abs(frag_shift - q) for q in query_shifts)
        if closest_dev > dev_threshold:
            return None  # Individual signal exceeds DEV threshold
        deviations.append(closest_dev)
    avg_dev = sum(deviations) / len(deviations)
    if avg_dev > avgdev_threshold:
        return None
    return avg_dev
```

**Source:** DEV/AVGDEV thresholds from Sherlock paper examples (PMC9920390): "DEV: 3 ppm, AVGDEV: 2 ppm" as working defaults. These match the +/- 2 ppm detection window used throughout existing detection code.

### Pattern 4: DEFF/FEXP LSD Constraint Generation

LSD uses external fragment files. `DEFF` maps a fragment number to a file path. `FEXP` combines fragments with Boolean logic. Confirmed from LSD manual (nuzillard.github.io/LSD/MANUAL_ENG.html).

```
; LSD goodlist fragment constraints
DEFF F1 "fragments/frag_001.lsd"
DEFF F2 "fragments/frag_002.lsd"
FEXP "F1 AND F2"
```

Fragment files use standard LSD atom notation. For each matching SSC, the fragment substructure is serialized as an LSD atom definition using the existing MULT/BOND notation the lsd-engineer agent already knows.

**Implementation strategy:** Generate fragment files alongside the main LSD file in the iteration directory. The `lucy fragment search` command outputs both the fragment files and the DEFF/FEXP lines to add to the LSD input.

**Confidence:** MEDIUM — DEFF/FEXP syntax confirmed from LSD manual. Fragment file format (atom notation inside fragment files) requires verification against LSD manual appendix or test case before implementation.

---

## Extraction Pipeline Architecture

### Build Pipeline (`lucy fragment build`)

One-time operation to populate `ssc_fragments` and `ssc_spectra` tables from existing 928K compounds.

**Verified prerequisite:** Database query confirms 23,994,980 of 24,063,169 shifts (99.7%) have `atom_index` populated. All 928,443 compounds have at least one indexed shift. SSC extraction from the full database is feasible without any data gaps.

**Approach:** Batch processing with `concurrent.futures.ProcessPoolExecutor`

```
Stage 1: Read compounds from SQLite (id, smiles, shifts with atom_index)
  | 928K compounds, 23.9M atom-indexed shifts
Stage 2: [Parallel, 8 workers] For each compound:
  a. Parse SMILES -> RDKit Mol (no explicit H)
  b. For each carbon atom with known shift, extract fragment at radii 1-4
  c. Build subspectrum: collect all shifts for atoms within the fragment
  d. Compute 256-bit fingerprint from subspectrum shifts
  e. Yield (compound_id, atom_idx, radius, fragment_smiles, shift_ppm, fingerprint)
  | ~24M SSC records
Stage 3: Deduplicate fragment_smiles (group SSCs by substructure)
  | N unique fragments
Stage 4: Batch INSERT to SQLite (executemany, 10K rows/batch)
  | Populated ssc_fragments + ssc_spectra tables
```

**Parallelism:** Use `ProcessPoolExecutor` (not `ThreadPoolExecutor`) because RDKit SMILES parsing and fragment extraction are CPU-bound. `tqdm` already used in existing pipeline (stats_generator.py) — same pattern applies here.

**Estimated runtime:** Existing HOSE stats generation processes 928K compounds in ~8 hours single-threaded. Parallel SSC extraction with 8 workers should complete in 2-3 hours. Acceptable for one-time build.

**Radius strategy:** Extract radii 1-4 (not 1-6). Reasoning: radius 5-6 fragments are large enough that few compounds in the query will contain them — low search utility, high storage cost. This matches Sherlock's fragment library design (Wenk thesis confirms maximum radius was empirically tuned).

**Confidence:** MEDIUM for radius cutoff — inferred from Sherlock's 24.5M SSC count. With 928K compounds x ~7 carbons/compound x 4 radii ~ 26M raw SSCs before deduplication, landing at Sherlock's 24.5M is plausible. Exact radius cutoff should be validated empirically.

### Search Pipeline (`lucy fragment search`)

Per-compound search during CASE workflow.

```
Input: experimental 13C shifts (list), molecular formula
  |
Step 1: Build query fingerprint from experimental shifts (256-bit)
Step 2: Load candidate SSCs from SQLite
  - Filter by atom_count <= compound carbon count (smaller fragments only)
  - Load fingerprint BLOBs into numpy array (N, 32)
Step 3: Vectorized Boolean AND pre-screening
  - Result: candidates where (fragment_fp & query_fp) == fragment_fp
Step 4: Load full subspectrum shifts for surviving candidates
Step 5: Fine matching (DEV/AVGDEV) for each candidate
Step 6: Rank survivors by AVGDEV ascending
Step 7: Select top-K matching fragments (default K=5)
Step 8: Generate DEFF fragment files + FEXP expression
Output: fragment files + LSD constraint lines
```

---

## What NOT to Add

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| FPSim2 | HDF5-based tool for Tanimoto similarity search. Overkill for Boolean AND screening; adds HDF5 dependency, changes storage format from SQLite. The SSC screening is Boolean AND (containment), not Tanimoto. | NumPy bitwise AND over SQLite-loaded arrays |
| h5py / HDF5 | Separate binary storage for fingerprints adds complexity without benefit at 24M record scale. SQLite BLOB is sufficient and keeps single-file database architecture. | SQLite BLOB column in existing database |
| BRICS fragmentation | Breaks retrosynthetic bonds. SSC extraction needs atom-environment spheres (radius-N neighborhoods), not synthetically motivated cuts. | `FindAtomEnvironmentOfRadiusN` + `PathToSubmol` |
| scikit-fingerprints | General fingerprint library (Morgan, ECFP, etc.). SSC fingerprints are custom spectral bitsets (2 ppm bins), not molecular topological fingerprints. RDKit is already available. | Custom bitset construction with NumPy |
| rdSubstructLibrary | Designed for SMARTS-based substructure screening of molecule libraries. The SSC search is spectral-match screening (not substructure queries). The library adds complexity without fitting the use case. | Direct SQLite queries + numpy bitset screening |
| PostgreSQL or MongoDB | Sherlock uses these (MongoDB for SSC fragments, PostgreSQL for compounds). Lucy-ng is a single-user CLI tool. SQLite handles 24M+ rows efficiently with proper indexing. | SQLite with schema extension |
| Numba / Cython | Premature optimization. NumPy vectorized bitwise AND on (N, 32) arrays is already SIMD-accelerated in numpy 2.2+. Profile first before adding compilation dependencies. | NumPy 2.2.1 vectorized bitwise ops |

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Fragment extraction | `FindAtomEnvironmentOfRadiusN` | BRICS decomposition | BRICS produces retrosynthetic fragments, not NMR-correlated atom environments. Wrong semantic for SSC. |
| Fingerprint storage | SQLite BLOB (32 bytes per SSC) | HDF5 + FPSim2 | Adds h5py dependency, breaks single-file database architecture. SQLite BLOB performs well for sub-100MB fingerprint loads. |
| Bitset screening | NumPy uint8 array bitwise AND | Python integer `&` operator | Python int bitwise AND is 100x slower than vectorized NumPy for N=24M records. NumPy avoids per-row Python overhead. |
| Fine matching | AVGDEV over all fragment signals | Cosine similarity | AVGDEV is domain-appropriate (NMR shift comparison), interpretable, and matches Sherlock's validated approach. Cosine requires normalization that loses shift-position meaning. |
| Parallelism | `ProcessPoolExecutor` (stdlib) | `joblib`, `ray`, `dask` | Build pipeline is embarrassingly parallel with no inter-worker state. stdlib `ProcessPoolExecutor` + tqdm is sufficient. No extra dependencies. |
| Fragment file format for DEFF | LSD atom notation files | SMILES-only | DEFF requires LSD-format fragment files. SMILES is insufficient — LSD needs MULT/BOND notation to define atom types and connectivity. |

---

## Version Compatibility

| Component | Required Version | Installed | Notes |
|-----------|-----------------|-----------|-------|
| RDKit | >=2023.09 | 2025.9.4 | `FindAtomEnvironmentOfRadiusN` stable since 2021. `PathToSubmol` stable. |
| NumPy | >=1.24 | 2.2.1 | Bitwise ops on uint8 arrays stable since 1.x. NumPy 2.x is backward compatible. |
| Python | >=3.10 | project requirement | `ProcessPoolExecutor` available since 3.2. |
| SQLite | >=3.31 | system | BLOB support available since SQLite 1.0. No version concern. |

---

## Installation

No new packages required. The fragment library milestone uses only the existing lucy-ng dependencies.

```bash
# Verify existing stack covers all needs
python3 -c "from rdkit.Chem import FindAtomEnvironmentOfRadiusN, PathToSubmol; print('RDKit OK')"
python3 -c "import numpy as np; fp = np.zeros(32, dtype=np.uint8); print('NumPy OK')"
python3 -c "from concurrent.futures import ProcessPoolExecutor; print('ProcessPoolExecutor OK')"

# All three should print OK with existing installation
```

---

## Sources

**PRIMARY SOURCES (HIGH confidence):**
- [RDKit 2025.09.5 rdFingerprintGenerator docs](https://www.rdkit.org/docs/source/rdkit.Chem.rdFingerprintGenerator.html) — fingerprint generation API verified
- [RDKit Getting Started in Python](https://www.rdkit.org/docs/GettingStartedInPython.html) — `FindAtomEnvironmentOfRadiusN`, `PathToSubmol` usage pattern confirmed
- [NumPy 2.4 Manual: packbits](https://numpy.org/doc/stable/reference/generated/numpy.packbits.html) — bitset encoding approach verified
- [LSD Manual (nuzillard.github.io)](https://nuzillard.github.io/LSD/MANUAL_ENG.html) — DEFF/FEXP syntax confirmed: `DEFF F_n_ <path>`, `FEXP "F1 AND F2"` pattern
- [RDKit rdSubstructLibrary docs](https://www.rdkit.org/docs/source/rdkit.Chem.rdSubstructLibrary.html) — evaluated and rejected for this use case (spectral match, not SMARTS search)
- lucy-ng SQLite database query — atom_index coverage: 99.7% (23,994,980 / 24,063,169 shifts), all 928,443 compounds covered

**SECONDARY SOURCES (MEDIUM confidence):**
- [Sherlock PMC paper (PMC9920390)](https://pmc.ncbi.nlm.nih.gov/articles/PMC9920390/) — 256-bit fingerprint bitstring confirmed: "each fragment has a bit string representation to indicate whether a given chemical shift in the assigned subspectrum exists... screened via a bit string comparison where all set bits of a fragment have to be present in the query bitset"
- [background/sherlock-analysis.md](/Users/steinbeck/Dropbox/develop/lucy-ng/background/sherlock-analysis.md) — 24.5M SSC count, 256-bit/2ppm fingerprint, DEV/AVGDEV thresholds (3 ppm DEV, 2 ppm AVGDEV), DEFF/FEXP application
- [FPSim2 docs (chembl.github.io)](https://chembl.github.io/FPSim2/) — evaluated and rejected for this use case
- [RDKit BRICS tutorial (greglandrum.github.io)](https://greglandrum.github.io/rdkit-blog/posts/2025-08-15-BRICS-tutorial.html) — evaluated and rejected for this use case

---

## Open Questions Requiring Validation

1. **Fragment file format for DEFF:** The LSD manual describes `DEFF F_n_ <path>` where the file contains a fragment definition. The exact internal format of these fragment files (how MULT/BOND notation is used inside a fragment file vs. the main LSD input) needs verification against LSD manual appendix or test cases before implementing `lucy fragment generate-lsd`. This is the highest-risk open question — get it wrong and DEFF files will be syntactically invalid.

2. **Radius cutoff empirics:** Radius 1-4 is inferred from SSC count math (928K x ~7 carbons/compound x 4 radii ~ 26M before dedup). Should be validated by building a small-scale fragment library (1% sample of compounds) at radii 1-6 and checking hit rates and storage overhead. Radii 5-6 may add too few useful fragments to justify the storage cost.

---

*Stack research for: Fragment library (SSC extraction, bitset fingerprinting, spectral search)*
*Researched: 2026-02-19*
*Confidence: HIGH for core implementation choices. MEDIUM for Sherlock-specific design parameters (radius cutoff, threshold values) and DEFF fragment file internal format.*

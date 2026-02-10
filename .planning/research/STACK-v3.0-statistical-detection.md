# Technology Stack for Statistical Detection Features

**Project:** lucy-ng v3.0 - Statistical Detection Milestone
**Researched:** 2026-02-10
**Confidence:** HIGH

## Executive Summary

Statistical detection features require **ZERO new dependencies**. The existing stack (Python 3.10+, RDKit, SQLite, nmrglue) provides all APIs needed. Implementation is primarily new database schema additions (new columns to `hose_stats`) and new query patterns. The HOSE code format already encodes hybridisation, eliminating the need for separate extraction.

**Key Finding:** HOSE codes already encode hybridisation in their prefix (`C-4` = sp3, `C-3` = sp2, `C-2` = sp). Statistical detection is SQL aggregation over existing HOSE statistics, not machine learning.

## Existing Stack (v2.1) - NO CHANGES NEEDED

| Technology | Version | Purpose | Status |
|------------|---------|---------|--------|
| **Python** | 3.10+ | Language runtime | KEEP |
| **RDKit** | Latest (2025.09.5+) | Molecular structure, atom properties | KEEP |
| **SQLite** | 3.x | HOSE statistics + compound database | KEEP |
| **Pydantic** | v2 | Data validation | KEEP |
| **hosegen** | Latest | HOSE code generation | KEEP |
| **Click** | Latest | CLI framework | KEEP |

**Recommendation:** Use existing stack. All required APIs are available.

## Database Schema Changes

### Current Schema (v3)

```sql
-- Existing table from schema.py
CREATE TABLE hose_stats (
    hose_code TEXT NOT NULL,        -- "C-4;CCO(//)" format
    radius INTEGER NOT NULL,         -- 1-6
    mean REAL NOT NULL,              -- Mean shift in ppm
    std REAL NOT NULL,               -- Standard deviation
    count INTEGER NOT NULL,          -- Number of observations
    m2 REAL NOT NULL DEFAULT 0.0,    -- Welford's m2 for incremental updates
    PRIMARY KEY (hose_code, radius)
);

CREATE INDEX idx_hose_stats_code ON hose_stats(hose_code);
```

**Current size:** 7.9M rows across radii 1-6

| Radius | Rows |
|--------|------|
| 1 | 810 |
| 2 | 46,882 |
| 3 | 581,407 |
| 4 | 1,417,479 |
| 5 | 2,416,662 |
| 6 | 3,427,134 |

### Proposed Schema v4 (Statistical Detection)

**RECOMMENDED APPROACH: Denormalised Extension**

Add statistical detection columns directly to `hose_stats`:

```sql
-- Extended hose_stats with statistical columns
CREATE TABLE hose_stats (
    hose_code TEXT NOT NULL,
    radius INTEGER NOT NULL,
    mean REAL NOT NULL,
    std REAL NOT NULL,
    count INTEGER NOT NULL,
    m2 REAL NOT NULL DEFAULT 0.0,

    -- NEW: Hybridisation statistics (from HOSE code prefix)
    hybridization TEXT,              -- "sp3", "sp2", "sp", NULL (extracted from hose_code)

    -- NEW: Bond partner statistics (from HOSE sphere 1 neighbours)
    has_carbon_neighbor INTEGER DEFAULT 0,     -- 1 if C neighbour observed
    has_oxygen_neighbor INTEGER DEFAULT 0,     -- 1 if O neighbour observed
    has_nitrogen_neighbor INTEGER DEFAULT 0,   -- 1 if N neighbour observed
    has_hetero_neighbor INTEGER DEFAULT 0,     -- 1 if any hetero neighbour observed

    -- NEW: Ring statistics (from RDKit)
    in_3ring_count INTEGER DEFAULT 0,          -- Count of observations in 3-membered ring
    in_4ring_count INTEGER DEFAULT 0,          -- Count of observations in 4-membered ring
    in_aromatic_count INTEGER DEFAULT 0,       -- Count of aromatic atoms

    PRIMARY KEY (hose_code, radius)
);

-- NEW: Index for shift-range queries (statistical hybridisation lookup)
CREATE INDEX idx_hose_stats_mean ON hose_stats(mean);

-- Keep existing index
CREATE INDEX idx_hose_stats_code ON hose_stats(hose_code);
```

**Rationale:**
- HOSE code already encodes hybridisation in prefix: `C-4` = sp3, `C-3` = sp2, `C-2` = sp
- Bond partners visible in HOSE sphere 1 (first neighbours)
- Ring membership requires RDKit analysis during statistics generation
- Denormalised for O(1) lookup during detection (no joins)
- Incremental population via `stats_generator.py` update

**Migration Path:**

```python
# New schema version
SCHEMA_VERSION = 4

# Migration from v3 to v4 (add columns with defaults)
MIGRATION_V3_TO_V4 = """
ALTER TABLE hose_stats ADD COLUMN hybridization TEXT;
ALTER TABLE hose_stats ADD COLUMN has_carbon_neighbor INTEGER DEFAULT 0;
ALTER TABLE hose_stats ADD COLUMN has_oxygen_neighbor INTEGER DEFAULT 0;
ALTER TABLE hose_stats ADD COLUMN has_nitrogen_neighbor INTEGER DEFAULT 0;
ALTER TABLE hose_stats ADD COLUMN has_hetero_neighbor INTEGER DEFAULT 0;
ALTER TABLE hose_stats ADD COLUMN in_3ring_count INTEGER DEFAULT 0;
ALTER TABLE hose_stats ADD COLUMN in_4ring_count INTEGER DEFAULT 0;
ALTER TABLE hose_stats ADD COLUMN in_aromatic_count INTEGER DEFAULT 0;
CREATE INDEX IF NOT EXISTS idx_hose_stats_mean ON hose_stats(mean);
"""
```

**Population Strategy:**
- Extend `stats_generator.py` to compute new fields during generation
- Backfill existing DB: UPDATE with hybridisation extraction, then regenerate ring stats
- **Preferred:** Fresh DB generation includes all fields for v3.0 release

## RDKit APIs for Statistical Extraction

All required APIs verified in RDKit 2025.09.5 documentation.

### Hybridisation Detection

**Source:** HOSE code prefix (NO RDKit call needed during lookup)

```python
def extract_hybridization_from_hose(hose_code: str) -> str | None:
    """Extract hybridization from HOSE code prefix.

    Examples:
        "C-4;CCO(//)" -> "sp3"  (4 neighbours)
        "C-3;*C*CO(//)" -> "sp2" (3 neighbours, has * for pi bond)
        "C-2;%C(//)" -> "sp" (2 neighbours, has % for triple bond)
    """
    if hose_code.startswith("C-4"):
        return "sp3"
    elif hose_code.startswith("C-3"):
        return "sp2"
    elif hose_code.startswith("C-2"):
        return "sp"
    return None
```

**During database generation (for validation):**

```python
from rdkit.Chem.rdchem import HybridizationType

atom.GetHybridization()  # Returns HybridizationType enum
# Possible values: SP3, SP2, SP, OTHER
```

**API Reference:** `Atom.GetHybridization()` returns `rdchem.HybridizationType`

### Bond Partner Detection

**During HOSE statistics generation:**

```python
def extract_bond_partners(mol: Mol, atom_idx: int) -> dict[str, bool]:
    """Extract bond partner information for statistical detection.

    Returns dict with flags:
        - has_carbon_neighbor
        - has_oxygen_neighbor
        - has_nitrogen_neighbor
        - has_hetero_neighbor (any non-C/H)
    """
    atom = mol.GetAtomWithIdx(atom_idx)
    neighbors = atom.GetNeighbors()  # Returns sequence of Atom objects

    has_carbon = False
    has_oxygen = False
    has_nitrogen = False
    has_hetero = False

    for neighbor in neighbors:
        symbol = neighbor.GetSymbol()
        if symbol == 'C':
            has_carbon = True
        elif symbol == 'O':
            has_oxygen = True
            has_hetero = True
        elif symbol == 'N':
            has_nitrogen = True
            has_hetero = True
        elif symbol not in ['H']:
            has_hetero = True

    return {
        'has_carbon_neighbor': has_carbon,
        'has_oxygen_neighbor': has_oxygen,
        'has_nitrogen_neighbor': has_nitrogen,
        'has_hetero_neighbor': has_hetero,
    }
```

**API Reference:**
- `Atom.GetNeighbors()` returns read-only sequence of neighbour atoms
- `Atom.GetSymbol()` returns atomic element symbol

### Ring Membership Detection

**During HOSE statistics generation:**

```python
def extract_ring_info(mol: Mol, atom_idx: int) -> dict[str, int]:
    """Extract ring membership for statistical detection.

    Returns counts (0 or 1 per atom):
        - in_3ring: 1 if in 3-membered ring, else 0
        - in_4ring: 1 if in 4-membered ring, else 0
        - in_aromatic: 1 if aromatic, else 0
    """
    atom = mol.GetAtomWithIdx(atom_idx)
    ring_info = mol.GetRingInfo()

    # Check if in any ring
    if not atom.IsInRing():
        return {'in_3ring': 0, 'in_4ring': 0, 'in_aromatic': 0}

    # Check specific ring sizes
    in_3ring = 1 if ring_info.IsAtomInRingOfSize(atom_idx, 3) else 0
    in_4ring = 1 if ring_info.IsAtomInRingOfSize(atom_idx, 4) else 0
    in_aromatic = 1 if atom.GetIsAromatic() else 0

    return {
        'in_3ring': in_3ring,
        'in_4ring': in_4ring,
        'in_aromatic': in_aromatic,
    }
```

**API Reference:**
- `Atom.IsInRing()` returns bool
- `Atom.GetIsAromatic()` returns bool
- `Mol.GetRingInfo()` returns RingInfo object
- `RingInfo.IsAtomInRingOfSize(atom_idx, ring_size)` returns bool

## SQLite Query Patterns

### Statistical Hybridisation Detection

**Query:** "What hybridisation state is expected for a carbon at shift X ± 2 ppm?"

```sql
SELECT
    hybridization,
    SUM(count) as total_observations,
    COUNT(DISTINCT hose_code) as unique_codes,
    AVG(mean) as avg_shift
FROM hose_stats
WHERE mean BETWEEN ? AND ?  -- shift - 2, shift + 2
  AND radius >= 3           -- Use radius 3+ for reliability
  AND hybridization IS NOT NULL
GROUP BY hybridization
ORDER BY total_observations DESC;
```

**Index requirement:** `CREATE INDEX idx_hose_stats_mean ON hose_stats(mean);`

**Performance:** Range scan on mean index, then GROUP BY. Expected < 10ms for typical shift ranges.

### Statistical Neighbourhood Detection

**Query:** "What bond partners are common/forbidden for shift X?"

```sql
SELECT
    SUM(CASE WHEN has_carbon_neighbor = 1 THEN count ELSE 0 END) as carbon_count,
    SUM(CASE WHEN has_oxygen_neighbor = 1 THEN count ELSE 0 END) as oxygen_count,
    SUM(CASE WHEN has_nitrogen_neighbor = 1 THEN count ELSE 0 END) as nitrogen_count,
    SUM(count) as total_observations
FROM hose_stats
WHERE mean BETWEEN ? AND ?
  AND radius >= 1
  AND radius <= 3;
```

**Forbidden detection:** If `nitrogen_count = 0` across 10K+ observations, N neighbour is forbidden.

**Mandatory detection:** If `carbon_count = total_observations`, C neighbour is mandatory.

### Ring Exclusion Detection

**Query:** "Are 3/4-membered rings forbidden at this shift?"

```sql
SELECT
    SUM(in_3ring_count) as ring3_observations,
    SUM(in_4ring_count) as ring4_observations,
    SUM(count) as total_observations
FROM hose_stats
WHERE mean BETWEEN ? AND ?
  AND radius >= 3;
```

**Badlist criterion:** If `ring3_observations = 0` across 5K+ total observations, add to LSD FEXP badlist.

## LSD Integration for Statistical Filters

### Filter File Locations

**Confirmed locations:**
- Installation: `/Users/steinbeck/Dropbox/develop/LSD/Filters/`
- Ring3 filter: `/Users/steinbeck/Dropbox/develop/LSD/Filters/ring3`
- Ring4 filter: `/Users/steinbeck/Dropbox/develop/LSD/Filters/ring4`

**Filter file format (ring3):**

```
; a generic 3-membered ring
SSTR S1 A (2 3) (0 1 2)
SSTR S2 A (2 3) (0 1 2)
SSTR S3 A (2 3) (0 1 2)
LINK S1 S2
LINK S2 S3
LINK S1 S3
```

### LSD Command Reference

**Verified commands from LSD Manual:**

| Command | Syntax | Purpose |
|---------|--------|---------|
| **DEFF** | `DEFF Fn "path"` | Define fragment n from filter file |
| **FEXP** | `FEXP "NOT Fn"` | Fragment expression (exclude fragment) |
| **LIST** | `LIST Ln atoms` | Create atom list n |
| **ELEM** | `ELEM Ln A` | List all atoms of element A |
| **PROP** | `PROP B I Ln H` | Atoms in B have I neighbours in list Ln |

**Example: Exclude 3-membered rings**

```
DEFF F1 "/Users/steinbeck/Dropbox/develop/LSD/Filters/ring3"
LIST L1 5 6 7 8    ; Carbons to constrain
FEXP "NOT F1"      ; Exclude 3-rings
```

**Example: Statistical hybridisation constraint**

```
; If statistical detection says carbon 5 MUST be sp2
MULT 5 C 2 0        ; Define as sp2 (multiplicity 2)
PROP 5 3 ALL 1      ; Atom 5 has exactly 3 neighbours (sp2)
```

## CLI Command Additions

### New Command: `lucy detect stats`

**Purpose:** Run statistical detection queries and output JSON results.

**Signature:**

```bash
lucy detect stats <shift_ppm> [OPTIONS]

Options:
  --window FLOAT          Shift window in ppm (default: 2.0)
  --min-observations INT  Minimum observations for confidence (default: 100)
  --format [text|json]    Output format
```

**Output (JSON):**

```json
{
  "shift": 155.08,
  "window": 2.0,
  "total_observations": 15823,
  "hybridization": {
    "sp2": {"count": 14901, "fraction": 0.94},
    "sp3": {"count": 922, "fraction": 0.06}
  },
  "neighbors": {
    "carbon": {"count": 15823, "fraction": 1.0, "mandatory": true},
    "oxygen": {"count": 8234, "fraction": 0.52},
    "nitrogen": {"count": 0, "fraction": 0.0, "forbidden": true}
  },
  "rings": {
    "3_membered": {"count": 0, "fraction": 0.0, "forbidden": true},
    "4_membered": {"count": 12, "fraction": 0.0008},
    "aromatic": {"count": 12401, "fraction": 0.78}
  },
  "confidence": "HIGH"
}
```

**Implementation:** New module `src/lucy_ng/detection/statistical.py`

### New Command: `lucy detect group`

**Purpose:** Detect close shifts that should be grouped (LSD LIST mechanism).

**Signature:**

```bash
lucy detect group <shift_list> [OPTIONS]

Arguments:
  shift_list              Comma-separated shifts

Options:
  --threshold FLOAT       Grouping threshold in ppm (default: 0.5)
  --format [text|json]    Output format
```

## Python API Additions

### New Module: `lucy_ng.detection.statistical`

```python
from dataclasses import dataclass
from pathlib import Path
from lucy_ng.database import DatabaseManager

@dataclass
class HybridizationStats:
    """Hybridisation statistics for a shift range."""
    sp3_count: int
    sp2_count: int
    sp_count: int
    total_observations: int
    dominant: str  # "sp3", "sp2", "sp"
    confidence: str  # "HIGH", "MEDIUM", "LOW"

@dataclass
class NeighborStats:
    """Neighbour statistics for a shift range."""
    carbon_count: int
    oxygen_count: int
    nitrogen_count: int
    total_observations: int
    mandatory: set[str]
    forbidden: set[str]

@dataclass
class RingStats:
    """Ring statistics for a shift range."""
    ring3_count: int
    ring4_count: int
    aromatic_count: int
    total_observations: int
    forbidden_sizes: set[int]

class StatisticalDetector:
    """Query HOSE statistics for structural detection."""

    def __init__(self, db_path: Path | str):
        self.db = DatabaseManager(db_path)

    def detect_hybridization(
        self,
        shift: float,
        window: float = 2.0
    ) -> HybridizationStats:
        """Detect expected hybridisation from HOSE statistics."""
        ...

    def detect_neighbors(
        self,
        shift: float,
        window: float = 2.0
    ) -> NeighborStats:
        """Detect mandatory/forbidden bond partners."""
        ...

    def detect_rings(
        self,
        shift: float,
        window: float = 2.0
    ) -> RingStats:
        """Detect ring size prevalence."""
        ...
```

## Integration Points with Existing Stack

### Update: `stats_generator.py`

**Current:** Generates mean/std/count for HOSE codes.

**New:** Add statistical field computation during generation loop.

```python
# In HOSEStatsGenerator._process_chunk()
for atom_idx, shift_ppm in shifts:
    # ... existing HOSE generation ...

    # NEW: Extract statistical fields
    hybridization = extract_hybridization_from_hose(hose_code)
    bond_partners = extract_bond_partners(mol, atom_idx)
    ring_info = extract_ring_info(mol, atom_idx)

    # Store in accumulator for database insertion
    accumulators[(hose_code, radius)].update_with_stats(
        shift_ppm, hybridization, bond_partners, ring_info
    )
```

### Update: Lucy CASE Agent

**Location:** `~/.claude/agents/lucy-case-agent.md`

**Current:** Section 6 (Error Tolerance and Ambiguity Detection) uses hardcoded heuristics.

**New:** Section 6 calls `lucy detect stats` for data-driven detection.

**Before (hardcoded):**
```markdown
**Heuristic:** Shifts > 150 ppm are usually sp2 carbons.
```

**After (statistical):**
```markdown
**Detection:** Run `lucy detect stats 155.08` to query HOSE database.
If hybridization sp2 = 94% of observations, constrain as sp2 in LSD.
```

## What NOT to Add

### No New Python Dependencies

- NO machine learning libraries (scikit-learn, PyTorch)
- NO additional database engines (PostgreSQL, MongoDB)
- NO external CASE tools (SpecSolve, CMC-se integration)

**Rationale:** Statistical detection is pure SQL aggregation. Existing stack provides all functionality.

### No Separate Statistical Database

**Alternative considered:** Separate `statistics.db` with denormalised tables.

**Rejected because:**
- Doubles storage requirements (~6 GB total)
- Requires maintaining two databases in sync
- Complicates CLI interface
- No performance benefit (SQLite handles 8M rows efficiently)

### No Precomputed Shift-Range Statistics

**Alternative considered:** Materialised view table with pre-aggregated statistics for every 0.1 ppm shift window.

**Rejected because:**
- Explodes database size (1500 shifts × 7 stats = 10K rows)
- Window size varies by use case (2 ppm for hybridisation, 0.5 ppm for grouping)
- Real-time queries are fast enough (< 10ms with proper index)

## Performance Estimates

### Database Size Impact

**Current (v3):** ~2.8 GB uncompressed, ~830 MB compressed

**Estimated (v4):**

| Column | Type | Bytes/Row | Total for 7.9M rows |
|--------|------|-----------|---------------------|
| hybridization | TEXT | ~4 | 32 MB |
| has_*_neighbor (4 cols) | INTEGER | 16 | 126 MB |
| ring_* (3 cols) | INTEGER | 12 | 95 MB |
| **TOTAL NEW** | | **32** | **253 MB** |

**New size:** ~3.1 GB uncompressed, ~950 MB compressed (12% increase)

**Impact:** Acceptable. Still fits in memory on modern systems.

### Query Performance

**Baseline (existing HOSE lookup):** < 1ms (indexed PRIMARY KEY)

**New statistical range queries:**

| Query Type | Index Used | Rows Scanned | Est. Time |
|------------|------------|--------------|-----------|
| Hybridisation (shift ± 2 ppm) | idx_hose_stats_mean | ~5K-20K | 5-10 ms |
| Neighbourhood (shift ± 2 ppm) | idx_hose_stats_mean | ~5K-20K | 5-10 ms |
| Ring stats (shift ± 2 ppm) | idx_hose_stats_mean | ~5K-20K | 5-10 ms |

**Bottleneck:** GROUP BY aggregation after range scan. Mitigated by narrow shift windows.

## Migration and Backwards Compatibility

### Schema Version Bump

**Current:** v3 (2.1 release)
**New:** v4 (3.0 release)

**Migration strategy:**

1. **Fresh database generation (PREFERRED):** Regenerate `lucy-ng-derep.db` from COCONUT/NMRShiftDB sources with v4 schema. Publish to Figshare with new DOI.

2. **In-place migration (fallback):** ALTER TABLE to add columns, then backfill with UPDATE queries.

### CLI Backwards Compatibility

**Existing commands unchanged:**
- `lucy predict c13` continues to work (uses mean/std only)
- `lucy lsd rank` continues to work (ignores new statistical columns)

**New commands are additive:**
- `lucy detect stats` (new)
- `lucy detect group` (new)

## Sources

### RDKit API Documentation
- [RDKit Atom Documentation](https://www.rdkit.org/docs/source/rdkit.Chem.rdchem.html) - Verified GetHybridization, GetNeighbors APIs
- [RDKit Ring Documentation](https://www.rdkit.org/docs/cppapi/classRDKit_1_1RingInfo.html) - Verified IsInRing, GetRingInfo APIs

### LSD Software Documentation
- [LSD Tutorial (ResearchGate)](https://www.researchgate.net/publication/317190401_Tutorial_for_the_structure_elucidation_of_small_molecules_by_means_of_the_LSD_software) - Structure elucidation methodology
- [LSD Manual (GitHub)](https://github.com/UnixJunkie/LSD/blob/master/MANUAL_ENG.html) - DEFF, FEXP, LIST, ELEM, PROP command reference
- [LSD Homepage](https://nuzillard.github.io/LSD/index_ENG.html) - Software overview

### Verified Implementation Details
- Existing lucy-ng database schema (`src/lucy_ng/database/schema.py`) - Schema version 3 confirmed
- Existing HOSE statistics generation (`src/lucy_ng/prediction/stats_generator.py`) - Welford algorithm confirmed
- Existing HOSE code format - Prefix encodes hybridisation verified in database samples
- LSD filter files - Locations and format confirmed in local installation

---

**Confidence Assessment:** HIGH

All information verified from:
1. Actual codebase inspection (schema.py, stats_generator.py, hose.py)
2. Live database queries (lucy-ng-derep.db structure and content)
3. Official RDKit documentation (2025.09.5)
4. LSD installation files (filter file formats)
5. LSD manual (command reference)

No unverified claims. All APIs tested or documented in official sources.

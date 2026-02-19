# Architecture Research: Fragment Library Integration

**Domain:** SSC fragment library integration into existing lucy-ng CASE system
**Researched:** 2026-02-19
**Confidence:** HIGH (existing codebase examined, Sherlock thesis analysed, architecture derived from code patterns)

---

## Executive Summary

The fragment library is a new subsystem that slots between two existing systems: the database (which already holds 928K compounds with 13C shifts) and the LSD workflow (which already consumes DEFF/FEXP goodlist constraints). The integration adds three new components — an extraction pipeline, a search service, and a CLI command group — plus schema v7 database tables. The agent workflow change is minimal: lsd-engineer calls one new CLI command before writing each LSD file iteration, then injects the returned DEFF commands.

The key architectural insight is that the fragment library reuses all existing infrastructure: the compound/shift data already in SQLite, the HOSECodeGenerator already in `prediction/hose.py`, the resumable chunked processing pattern already in `stats_generator.py`, and the CLI command group pattern already in `cli/database.py` and `cli/detect.py`. No new dependencies are required.

---

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          CASE Agent Workflow                            │
│  ┌──────────────┐    ┌────────────────┐    ┌──────────────────────────┐ │
│  │ nmr-chemist  │    │  lsd-engineer  │    │    solution-analyst       │ │
│  │ (picks peaks)│    │ (builds LSD)   │    │   (ranks solutions)       │ │
│  └──────┬───────┘    └───────┬────────┘    └──────────────────────────┘ │
│         │                   │                                           │
│         │  shifts[]         │  lucy fragment search --shifts "..." ──►  │
│         └──────────────────►│                                           │
│                             │  ◄── DEFF commands (goodlist fragments)   │
└─────────────────────────────┼───────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     Fragment Search Service                             │
│                    (NEW: lucy_ng/fragments/)                            │
│  ┌─────────────────┐    ┌──────────────────┐    ┌────────────────────┐  │
│  │ FingerprintIndex│    │  SSCSearcher     │    │  DEFFFormatter     │  │
│  │  (bitset AND)   │───►│  (fine matching) │───►│ (LSD injection)    │  │
│  └─────────────────┘    └──────────────────┘    └────────────────────┘  │
└─────────────────────────┬───────────────────────────────────────────────┘
                          │  SQLite queries (ssc, ssc_bitset tables)
                          ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    SQLite Database (schema v7)                          │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐  │
│  │  compounds  │  │  c13_shifts  │  │     ssc      │  │ ssc_bitset  │  │
│  │  (928K)     │  │  (existing)  │  │  (NEW 24M+)  │  │  (NEW 24M+) │  │
│  └──────┬──────┘  └──────┬───────┘  └──────────────┘  └─────────────┘  │
│         └────────────────┘                                              │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐                    │
│  │  hose_stats │  │bond_pair_stat│  │  operation_  │                    │
│  │  (existing) │  │  (existing)  │  │  checkpoint  │                    │
│  └─────────────┘  └──────────────┘  └──────────────┘                    │
└─────────────────────────────────────────────────────────────────────────┘
                          ▲
                          │  SSC extraction (one-time, resumable)
┌─────────────────────────┴───────────────────────────────────────────────┐
│                    SSC Extraction Pipeline                              │
│                 (NEW: lucy_ng/fragments/extractor.py)                   │
│  For each compound: iterate atoms → BFS sphere expansion →             │
│  deduplicate → store substructure SMILES + subspectrum shifts +        │
│  256-bit fingerprint (2 ppm bins)                                       │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Component Responsibilities

| Component | Responsibility | Location |
|-----------|----------------|----------|
| **SSC Extractor** | Iterate all 928K compounds, BFS sphere fragmentation, deduplication, fingerprint generation, DB write | `lucy_ng/fragments/extractor.py` (NEW) |
| **SSC Model** | Pydantic model for substructure-subspectrum correlation record | `lucy_ng/fragments/models.py` (NEW) |
| **Fragment Searcher** | Bitset pre-screen then fine spectral matching against SSC table | `lucy_ng/fragments/searcher.py` (NEW) |
| **DEFF Formatter** | Convert matched SSCs to LSD DEFF/FEXP command strings | `lucy_ng/fragments/lsd_formatter.py` (NEW) |
| **Fragment CLI** | `lucy fragment search`, `lucy fragment build`, `lucy fragment info` | `lucy_ng/cli/fragment.py` (NEW) |
| **Schema v7** | `ssc` and `ssc_bitset` tables, `migrate_v6_to_v7()` | `lucy_ng/database/schema.py` (MODIFIED) |
| **DatabaseManager** | `insert_ssc_batch()`, `search_ssc_by_bitset()`, query methods | `lucy_ng/database/manager.py` (MODIFIED) |
| **lsd-engineer agent** | Call `lucy fragment search` before writing each LSD iteration, inject DEFF output | `~/.claude/agents/lucy-lsd-engineer.md` (MODIFIED) |

---

## New Database Tables (Schema v7)

### Table: `ssc`

Stores each substructure-subspectrum correlation. One row per unique fragment extracted from the compound database.

```sql
CREATE TABLE IF NOT EXISTS ssc (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    smiles TEXT NOT NULL,            -- Substructure SMILES (R = open site, e.g. "CC(R)=O")
    atom_count INTEGER NOT NULL,     -- Heavy atom count including R groups (for ranking)
    shift_list TEXT NOT NULL,        -- JSON array of float shifts: "[45.1, 130.2, ...]"
    avg_shift REAL NOT NULL,         -- Mean shift of subspectrum (for range filtering)
    min_shift REAL NOT NULL,         -- Min shift (for range filtering)
    max_shift REAL NOT NULL          -- Max shift (for range filtering)
)
```

**Index on atom_count** (for size-ranked result ordering) and **index on avg_shift** (for optional range pre-filter).

### Table: `ssc_bitset`

Stores the 256-bit fingerprint for each SSC. Separate table avoids loading large blobs in text queries.

```sql
CREATE TABLE IF NOT EXISTS ssc_bitset (
    ssc_id INTEGER PRIMARY KEY,
    bitset BLOB NOT NULL,            -- 32 bytes = 256 bits, one bit per 2 ppm bin
    FOREIGN KEY (ssc_id) REFERENCES ssc(id) ON DELETE CASCADE
)
```

**Rationale for separate table:** Bitset blobs (32 bytes each) accessed only during pre-screening. Keeping them separate from text data avoids inflating the `ssc` table row size and allows the pre-screening query to be index-friendly.

**Storage estimate:** 24M SSCs × (32 bytes bitset + ~120 bytes ssc row) ≈ 3.6 GB additional. Total database grows from ~2.8 GB to ~6.4 GB. This is acceptable for the performance gain.

### Migration Function: `migrate_v6_to_v7()`

Follows existing pattern in `schema.py`. Creates both tables, updates `schema_meta` version to 7.

---

## New Python Modules

### `lucy_ng/fragments/__init__.py`

Exports `SSCExtractor`, `FragmentSearcher`, `SSCRecord`.

### `lucy_ng/fragments/models.py`

```python
class SSCRecord(BaseModel):
    """A substructure-subspectrum correlation record."""
    id: int | None = None
    smiles: str                  # Substructure SMILES with R open sites
    atom_count: int              # Heavy atoms including R (for ranking)
    shift_list: list[float]      # Subspectrum shifts
    avg_shift: float
    min_shift: float
    max_shift: float
    bitset: bytes | None = None  # 32-byte fingerprint (only when loaded)
```

### `lucy_ng/fragments/extractor.py`

BFS sphere fragmentation over all compounds. Follows the `ResumableHOSEStatsGenerator` pattern exactly: chunked processing, checkpoint/resume, Welford accumulators replaced by SSC deduplication via SMILES.

**Algorithm (from Sherlock thesis section 3.1.4.2.3):**

1. For each compound in DB, parse SMILES to RDKit mol
2. For each non-hydrogen atom as starting point:
   a. BFS up to 3 spheres (or 1 sphere for ring systems)
   b. Bond-preserving rules: keep if (a) connects heteroatoms, (b) bond order > 1, or (c) C adjacent to 2+ heteroatoms
   c. Replace cut bonds' atoms with R pseudo-atom
   d. Preserve associated 13C shifts for atoms remaining in substructure
3. Deduplicate by canonical SMILES within the compound
4. Compute 256-bit fingerprint: bins of 2 ppm over 0-512 ppm range, expand each set bit ±1 for tolerance
5. Store SSCRecord to database

**Key difference from HOSE stats generator:** SSC extractor deduplicates by SMILES globally (same substructure from different compounds merges to best-avg-deviation entry). HOSE stats accumulates numerically. This means SSC extraction must check-before-insert, not upsert-accumulate.

**Checkpoint pattern:** Uses `operation_checkpoint` table already in schema. Keys: `ssc_last_compound_id`, `ssc_compounds_processed`, `ssc_sscs_extracted`.

### `lucy_ng/fragments/searcher.py`

```python
class FragmentSearcher:
    """Search SSC database for fragments matching experimental spectrum."""

    def __init__(self, db_path: Path | str): ...

    def search(
        self,
        experimental_shifts: list[float],
        max_avg_deviation: float = 3.0,     # Sherlock default
        max_results: int = 20,
        min_atom_count: int = 3,            # Skip trivial single-atom fragments
    ) -> list[SSCMatch]: ...
```

**Two-phase search (follows Sherlock exactly):**

Phase 1 — Bitset pre-screen:
1. Build query bitset from experimental_shifts (256 bits, 2 ppm bins, expand ±1 bit)
2. Load all `ssc_bitset` rows (32 bytes each = 768 MB for 24M SSCs)
3. Filter: `(query_bitset AND ssc_bitset) == ssc_bitset` (all SSC bits must be in query)

**Note on memory:** 24M × 32 bytes = 768 MB bitsets in RAM during search. This is a design decision point. Three options:
- Load all bitsets at search time (~768 MB, fast, acceptable for desktop CASE use)
- Chunked scan with batch SQL reads (lower peak RAM, slower)
- Store bitsets as 4×uint64 columns for SQL bitwise AND (most efficient, requires schema adjustment)

**Recommendation:** Start with chunked SQL scan (Option B) using `SELECT ssc_id, bitset FROM ssc_bitset` in batches of 100K rows. At 24M rows, this is ~240 batches. Fast enough for per-iteration use (SSC search runs once per LSD iteration, not in a hot loop).

Phase 2 — Fine matching:
1. For surviving candidates, load full SSCRecord (smiles, shift_list)
2. Compute signal-signal pairs using Hungarian matching or greedy nearest-neighbour
3. Filter: avg_deviation <= max_avg_deviation
4. Filter: hybridisation check (if experimental shift known sp2, SSC shift must be sp2 compatible)
5. Deduplicate by canonical SMILES (keep lowest avg_deviation per structure)
6. Rank by (atom_count DESC, avg_deviation ASC)

### `lucy_ng/fragments/lsd_formatter.py`

Converts `SSCMatch` results to LSD-injectable DEFF/FEXP command strings.

**LSD DEFF/FEXP format (from Sherlock section 3.1.4.2.3 and Wenk thesis appendix A4):**

```
; Fragment goodlist (from fragment search)
DEFF F1 '/path/to/fragment1.mol'
DEFF F2 '/path/to/fragment2.mol'
FEXP 'F1 OR F2 OR ...'
```

Each matched SSC must be written as a MOL file in LSD's expected format, then referenced via DEFF. Alternatively, since lucy-ng uses LSD directly (not pyLSD), the SSTR/LINK syntax can be embedded inline:

```
; Fragment 1: CC(R)=O (acetyl, avg_dev=1.2 ppm, 3 heavy atoms)
DEFF F1 'goodlist_fragment_1.lsd'
```

Where `goodlist_fragment_1.lsd` contains the SSTR/LINK definition:
```
SSTR S1 C (3) (3)    ; sp3 C, 3H (CH3)
SSTR S2 C (2) (0)    ; sp2 C, 0H (carbonyl)
SSTR S3 O (2) (0)    ; sp2 O
LINK S1 S2
LINK S2 S3
```

**Formatter responsibility:** Given a matched SMILES like `CC(R)=O`, convert to SSTR/LINK format, write to temp file in iteration dir, return DEFF reference strings.

**Alternative (simpler):** Write fragment SMILES to a file and use pyLSD-compatible SMILES-based DEFF. Needs LSD version check. Defer to implementation phase.

---

## New CLI Command Group

### `lucy fragment` (NEW command group)

Added to `cli/main.py` alongside existing `read`, `pick`, `analyze`, `dereplicate`, `predict`, `detect`, `lsd`, `database`.

```python
# cli/fragment.py

@click.group()
def fragment() -> None:
    """Fragment library management and search."""

@fragment.command("build")
@click.option("--db", required=True, type=click.Path(), help="Database path")
@click.option("--chunk-size", default=10000, type=int)
@click.option("--log-file", type=click.Path())
@click.option("--resume/--fresh", default=True)
def fragment_build(db, chunk_size, log_file, resume): ...
# Runs SSCExtractor over all compounds, populates ssc + ssc_bitset tables

@fragment.command("search")
@click.option("--db", required=True, type=click.Path(), help="Database path")
@click.option("--shifts", required=True, type=str, help="Comma-separated ppm values")
@click.option("--max-deviation", default=3.0, type=float)
@click.option("--max-results", default=10, type=int)
@click.option("--format", "output_format", type=click.Choice(["text", "json"]), default="json")
def fragment_search(db, shifts, max_deviation, max_results, output_format): ...
# Agent-facing command. Returns DEFF commands + matched fragment summary

@fragment.command("info")
@click.option("--db", required=True, type=click.Path(), help="Database path")
def fragment_info(db): ...
# Shows SSC count, coverage statistics
```

**Agent-facing output (json format):**

```json
{
  "query_shifts": [45.03, 44.90, 129.38, 127.26, 141.2, 135.1, 180.56, 30.1, 22.5, 18.2],
  "fragments_found": 3,
  "deff_commands": [
    "DEFF F1 'analysis/iteration_03/fragment_1.lsd'",
    "DEFF F2 'analysis/iteration_03/fragment_2.lsd'",
    "DEFF F3 'analysis/iteration_03/fragment_3.lsd'"
  ],
  "fexp_command": "FEXP 'F1 OR F2 OR F3'",
  "fragment_files_written": [
    "analysis/iteration_03/fragment_1.lsd",
    "analysis/iteration_03/fragment_2.lsd",
    "analysis/iteration_03/fragment_3.lsd"
  ],
  "fragments": [
    {
      "rank": 1,
      "smiles": "c1ccccc1CC(R)R",
      "atom_count": 10,
      "avg_deviation": 0.83,
      "matched_shifts": [129.38, 127.26, 141.2, 135.1, 45.03]
    }
  ]
}
```

The agent reads `deff_commands` and `fexp_command` and injects them directly into the LSD file. The fragment `.lsd` files are written by the CLI into the current iteration directory so they are available at LSD run time.

---

## Data Flow: Extraction to Search to LSD Injection

### Phase A: One-Time Extraction (Pre-Processing)

```
lucy fragment build --db data/reference/lucy-ng-derep.db

    DatabaseManager.iter_compounds_with_shifts()
        ↓
    For each compound (928K total):
        HOSECodeGenerator.prepare_mol(smiles)  [reuse existing]
            ↓
        SSCExtractor._fragment_molecule(mol, shifts)
            ↓ BFS sphere expansion (Sherlock algorithm)
            ↓ bond-preserving cuts
            ↓ R-atom substitution at cut bonds
            ↓ deduplicate within compound by canonical SMILES
            ↓
        For each unique fragment:
            Compute 256-bit fingerprint (2 ppm bins from shift_list)
            Expand ±1 bit for tolerance
            ↓
        Check global SMILES deduplication
        If new: INSERT INTO ssc + ssc_bitset
        If known: UPDATE avg_deviation if new one is lower
            ↓
    Checkpoint every 10K compounds
    Resume-safe via operation_checkpoint table

Result: ~24M rows in ssc + ssc_bitset (estimate from Sherlock: 24.5M)
Build time: estimate 4-8h (similar to HOSE stats regeneration)
```

### Phase B: Per-Iteration Search (During CASE Run)

```
lsd-engineer calls:
lucy fragment search --db data/reference/lucy-ng-derep.db \
    --shifts "45.03,44.90,129.38,127.26,141.2,135.1,180.56,30.1,22.5,18.2" \
    --format json

    FragmentSearcher.search(experimental_shifts)
        ↓
    Phase 1: Bitset pre-screen
        Build query bitset from experimental_shifts
        Expand ±1 bin for tolerance
        SELECT ssc_id, bitset FROM ssc_bitset (batch scan, 100K/batch)
        Keep: (query_bitset AND ssc_bitset) == ssc_bitset
        → ~1000-5000 candidates pass pre-screen (estimate)
        ↓
    Phase 2: Fine matching
        For each candidate: load SSCRecord
        Compute shift distances (greedy nearest-neighbour)
        Filter: avg_deviation <= max_avg_deviation (3.0 ppm)
        Filter: hybridisation compatibility
        Deduplicate by canonical SMILES
        Rank: atom_count DESC, avg_deviation ASC
        → 3-15 final fragments (estimate)
        ↓
    DEFFFormatter.format(fragments, output_dir="analysis/iteration_03/")
        Write fragment_1.lsd, fragment_2.lsd, ... (SSTR/LINK format)
        Return DEFF + FEXP command strings
        ↓
    JSON output to stdout

lsd-engineer reads JSON:
    Appends DEFF + FEXP commands to iteration_NN/compound.lsd
    before MULT section (LSD requires DEFF before structural commands)
```

### Phase C: LSD Execution With Fragment Goodlist

```
compound.lsd contains:
    ; Fragment goodlist (from lucy fragment search)
    DEFF F1 'analysis/iteration_03/fragment_1.lsd'
    DEFF F2 'analysis/iteration_03/fragment_2.lsd'
    FEXP 'F1 OR F2'

    ; Atom definitions
    MULT 1 C 2 0    ; carbonyl
    ...
    HSQC 2 2
    ...
    HMBC 1 2
    ...

lucy lsd run compound.lsd
    ↓ LSD enforces: each solution must contain F1 OR F2 as substructure
    ↓ Solution count drops dramatically (Sherlock: 336→1 for Allantofuranone)
```

---

## Integration Points

### Modified Components

| Component | Change | Why |
|-----------|--------|-----|
| `database/schema.py` | Add `CREATE_SSC_TABLE`, `CREATE_SSC_BITSET_TABLE`, `migrate_v6_to_v7()`, update `SCHEMA_VERSION = 7` | New storage |
| `database/manager.py` | Add `insert_ssc_batch()`, `get_ssc_count()`, `iter_ssc_bitsets()`, `get_ssc_by_id()` | New query patterns |
| `cli/main.py` | Import and register `fragment` command group | CLI wiring |
| `~/.claude/agents/lucy-lsd-engineer.md` | Add fragment search step before each LSD file write | Agent workflow |

### New Components (No Existing Code Modified Except Above)

| Component | Depends On |
|-----------|------------|
| `lucy_ng/fragments/__init__.py` | (none — top of new module) |
| `lucy_ng/fragments/models.py` | `pydantic`, existing `CompoundRecord` pattern |
| `lucy_ng/fragments/extractor.py` | `HOSECodeGenerator` (reuse), `DatabaseManager` (existing), `operation_checkpoint` pattern (existing) |
| `lucy_ng/fragments/searcher.py` | `DatabaseManager`, `SSCRecord` |
| `lucy_ng/fragments/lsd_formatter.py` | `SSCMatch` model (new), RDKit for SMILES canonicalization |
| `lucy_ng/cli/fragment.py` | `FragmentSearcher`, `SSCExtractor`, Click (existing) |

---

## Agent Workflow Changes

### Modified: lsd-engineer workflow

**Current workflow (v4.0):**
1. Read previous iteration LSD file (if exists)
2. Copy forward all constraints from inventory
3. Add new HMBC batch from nmr-chemist assignments
4. Write iteration_NN/compound.lsd
5. Send to devils-advocate for validation
6. Run `lucy lsd run compound.lsd`

**New workflow (v5.0+):**
1. Read previous iteration LSD file (if exists)
2. Copy forward all constraints from inventory
3. Add new HMBC batch from nmr-chemist assignments
4. **NEW: Run fragment search**
   ```bash
   lucy fragment search --db data/reference/lucy-ng-derep.db \
       --shifts "<comma-separated experimental 13C shifts>" \
       --format json
   ```
5. **NEW: If fragments found: prepend DEFF/FEXP to LSD file (BEFORE MULT)**
   ```
   ; Fragment goodlist (iteration 03)
   DEFF F1 'analysis/iteration_03/fragment_1.lsd'
   FEXP 'F1'
   ```
6. Write iteration_NN/compound.lsd (with or without fragments)
7. Send to devils-advocate for validation
8. Run `lucy lsd run compound.lsd`

**Fragment search trigger:** Run at every iteration, not just when solution count is high. If no fragments are found, skip DEFF/FEXP injection — LSD file is unchanged. Fragment search adds <30 seconds per iteration (scan 24M bitsets at 100K/batch).

**Constraint inventory tracking:** Add fragment section to the constraint inventory header:
```
; FRAGMENT GOODLIST: 2 fragments (avg_dev=1.2 ppm, atom_count>=6)
;   F1: c1ccccc1CC(R)R (benzylmethylene, 10 atoms, dev=0.83)
;   F2: CC(=O)O (acetate, 4 atoms, dev=1.45)
```

### Not Modified: other agents

- nmr-chemist: no change (provides shifts, does not touch fragments)
- solution-analyst: no change (benefits automatically from reduced solution count)
- devils-advocate: add fragment file existence check to pre-run validation
  - "DEFF F1 referenced but analysis/iteration_03/fragment_1.lsd not found → fail"
  - Add fragment count to validation output: "DEFF: 2 fragments written"

---

## Suggested Build Order

Dependencies drive this order. Each step is independently testable.

### Step 1: Schema v7 and DatabaseManager extensions

**Files:** `database/schema.py`, `database/manager.py`
**What:** Add `ssc` and `ssc_bitset` tables. Add `insert_ssc_batch()`, `get_ssc_count()`, `iter_ssc_bitsets(batch_size)`, `get_ssc_by_id(ids)` to manager.
**Why first:** Everything else depends on storage.
**Test:** Create schema v7 database, insert 100 test SSC rows, query back, verify migration from v6.

### Step 2: SSC models

**Files:** `fragments/models.py`, `fragments/__init__.py`
**What:** `SSCRecord`, `SSCMatch` Pydantic models.
**Why:** Needed by both extractor and searcher before either is built.
**Test:** Instantiate models with test data, verify field validation.

### Step 3: SSC Extractor (pipeline, no CLI)

**Files:** `fragments/extractor.py`
**What:** BFS fragmentation algorithm, fingerprint generation, DB write. Resumable with checkpoint.
**Why third:** Most complex component. Build and test on 1K compounds before scale.
**Test:** Run on 1000 compounds from test DB. Verify fragment count reasonable (expect ~50-100 per compound = 50K-100K total from 1K compounds). Verify SMILES deduplication works. Verify fingerprints are 32 bytes each.

### Step 4: Fragment Searcher

**Files:** `fragments/searcher.py`
**What:** Bitset pre-screen then fine matching. Returns ranked SSCMatch list.
**Why fourth:** Depends on Step 3 having populated SSC table with test data.
**Test:** Search Ibuprofen shifts against 100K test SSCs. Verify aromatic ring fragments appear in top 5. Verify avg_deviation filter works.

### Step 5: DEFF Formatter

**Files:** `fragments/lsd_formatter.py`
**What:** Convert SSCMatch to SSTR/LINK format files + DEFF/FEXP command strings.
**Why fifth:** Depends on searcher output format.
**Test:** Format known fragment SMILES to SSTR/LINK. Verify output is valid LSD fragment syntax (manually check against Sherlock appendix A4 format).

### Step 6: CLI command group

**Files:** `cli/fragment.py`, `cli/main.py`
**What:** `lucy fragment build`, `lucy fragment search`, `lucy fragment info` commands.
**Why sixth:** Wraps Steps 3-5. CLI is the agent interface.
**Test:** `lucy fragment build --db test.db --limit 1000` completes. `lucy fragment search --shifts "45.0,130.0" --format json` returns valid JSON. Verify DEFF files written to current dir.

### Step 7: Full extraction run

**What:** Run `lucy fragment build` on full 928K compound database. Estimated 4-8h.
**Why seventh:** Must complete before agent integration is useful.
**Test:** `lucy fragment info` shows ~24M SSCs. Search Ibuprofen shifts returns aromatic ring fragment in top 3.

### Step 8: Agent integration

**Files:** `~/.claude/agents/lucy-lsd-engineer.md`
**What:** Add fragment search step and DEFF injection to lsd-engineer workflow.
**Why last:** Agent integration is meaningless without search infrastructure.
**Test:** Full CASE run on Ibuprofen. Verify fragment search runs, DEFF lines appear in compound.lsd, solution count lower than without fragments.

---

## Architectural Patterns to Follow

### Pattern 1: Resumable Chunked Processing

The SSCExtractor must follow `ResumableHOSEStatsGenerator` exactly:
- `operation_checkpoint` table for progress state
- `--resume/--fresh` CLI flags
- Log file support for nohup detached operation
- Progress reporting every chunk

**Why:** Full extraction over 928K compounds will take hours. A crash at 90% must not require restarting from zero.

### Pattern 2: Context Manager for DB Access

All new DB-accessing classes must follow:
```python
class FragmentSearcher:
    def __enter__(self) -> FragmentSearcher: ...
    def __exit__(self, ...) -> None: self.close()
```

Same as `StatisticalDetector` and `DatabaseQueryService`. Ensures connection cleanup.

### Pattern 3: Thin CLI, Logic in Module

CLI functions contain no business logic. They call module functions and format output. This is the existing pattern across all CLI files. `fragment_search()` calls `FragmentSearcher.search()`, formats result, writes to stdout.

### Pattern 4: JSON as Agent Interface

All agent-facing CLI commands output `--format json`. The agent reads stdout, parses JSON, uses specific fields. Never rely on text parsing of human-readable output. The `deff_commands` and `fexp_command` fields are the exact strings to inject into the LSD file.

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Load All Bitsets Into RAM at Import Time

**What people do:** Pre-load 24M × 32-byte bitsets (768 MB) at module initialization for fast search.

**Why wrong:** Makes the `lucy` CLI unusable for commands that don't need fragment search (every command would spend seconds loading bitsets on startup).

**Do this instead:** Load bitsets lazily inside `FragmentSearcher.search()`, in batches during the scan. The search happens once per LSD iteration, not in a tight loop.

### Anti-Pattern 2: Deduplicate SSCs In-Memory During Extraction

**What people do:** Build a dict of all seen SMILES in memory, filter before insert.

**Why wrong:** At 24M SSCs, the deduplication dict would consume 10+ GB of RAM.

**Do this instead:** Use SQLite's `INSERT OR IGNORE` with a UNIQUE constraint on `(smiles)` for global deduplication. Check-before-insert within a compound (per-compound deduplication can be in-memory because a single compound generates at most ~100 fragments).

### Anti-Pattern 3: Store Bitsets as TEXT (hex-encoded)

**What people do:** Store bitset as hex string `"0xFF3A..."` for readability.

**Why wrong:** 64-character hex string per SSC costs 64 bytes vs 32 bytes for BLOB. Bitwise AND in Python requires decode+int conversion per row.

**Do this instead:** Store as `BLOB NOT NULL` (32 bytes). Python `bytes` supports direct bitwise operations via `bytearray`.

### Anti-Pattern 4: Inject DEFF After MULT Commands

**What people do:** Append DEFF/FEXP at the end of the LSD file for convenience.

**Why wrong:** LSD requires fragment definitions (DEFF) to appear before structural commands (MULT). Wrong order causes LSD parse error.

**Do this instead:** lsd-engineer writes DEFF/FEXP as the first non-comment section of compound.lsd, before all MULT commands.

### Anti-Pattern 5: Run Fragment Search After LSD (For Next Iteration)

**What people do:** Run fragment search on current solutions to find matching fragments for the next iteration's goodlist.

**Why wrong:** Fragment search is against the reference database, not against current solutions. Running it after LSD adds latency without benefit — same shifts, same result.

**Do this instead:** Run fragment search at the START of each iteration before writing the LSD file. The experimental shifts from nmr-chemist are stable; fragment results are deterministic per shift set.

---

## Scalability Considerations

| Concern | Current | After SSC Integration |
|---------|---------|----------------------|
| DB size | ~2.8 GB | ~6.4 GB (+3.6 GB for SSC tables) |
| Search time | N/A | ~10-60s per iteration (bitset scan over 24M rows) |
| Memory during search | N/A | ~50-100 MB (batch loading of bitsets) |
| Extraction time | N/A | ~4-8h one-time (comparable to HOSE regen) |

**If search time is too slow:** Consider PostgreSQL BIT type with bitwise AND index support, or store bitsets as 4 × uint64 columns for SQL-level AND. SQLite doesn't support bitwise operations in WHERE clause efficiently, so the scan-and-compare-in-Python approach is the baseline.

**If DB size is a problem:** Fragment table can be stored in a separate file (`lucy-ng-fragments.db`). CLI accepts `--fragment-db` separately from `--db`. This keeps the main derep DB at current size for users who don't need fragment search.

---

## Sources

- `src/lucy_ng/database/schema.py` — v6 schema, migration pattern
- `src/lucy_ng/database/manager.py` — query and insert patterns
- `src/lucy_ng/prediction/stats_generator.py` — `ResumableHOSEStatsGenerator` pattern for chunked extraction
- `src/lucy_ng/detection/detector.py` — context manager pattern for DB access
- `src/lucy_ng/cli/database.py`, `src/lucy_ng/cli/detect.py`, `src/lucy_ng/cli/lsd.py` — CLI structure patterns
- `background/wenk-thesis.txt` lines 1835-1950 — SSC extraction algorithm
- `background/wenk-thesis.txt` lines 2115-2250 — DEFF/FEXP injection, LSD command reference
- `background/sherlock-analysis.md` — gap analysis, impact statistics (24.5M SSCs, 34/40 single-solution)
- `~/.claude/agents/lucy-lsd-engineer.md` — current lsd-engineer workflow for modification point

---

*Architecture research for: Fragment Library Integration into lucy-ng CASE System*
*Researched: 2026-02-19*

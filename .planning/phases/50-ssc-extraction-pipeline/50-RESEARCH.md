# Phase 50: SSC Extraction Pipeline - Research

**Researched:** 2026-02-19
**Domain:** BFS sphere fragmentation, SQLite batch extraction, checkpointing, fingerprint validation
**Confidence:** HIGH — all prior milestone research confirmed against live codebase; Phase 49 output fully inspected

---

## Summary

Phase 50 builds the SSC extraction pipeline: a resumable batch process that iterates all 928K compounds in the main database and writes substructure-subspectrum correlations (SSCs) into a separate `lucy-ng-fragments.db`. The Phase 49 output (schema v7, `FragmentDatabaseManager`, `SSCRecord`/`SSCMatch` models, `lucy fragment info` CLI stub) is completely in place and tested. Phase 50 adds the algorithmic core: the `SSCExtractor` class, the `lucy fragment build` CLI command, checkpoint/resume logic, and a sample-mode that validates the 2 ppm bin size before committing to the full 24M+ extraction.

The primary pattern to follow is `ResumableHOSEStatsGenerator` in `src/lucy_ng/prediction/stats_generator.py`. The checkpoint infrastructure in `DatabaseManager` (set/get/clear_checkpoint, `iter_compounds_with_shifts_from`) is already tested and proven. The key difference from HOSE stats: SSC extraction deduplicates by canonical SMILES at insert time (SQLite `UNIQUE(smiles)` + `INSERT OR IGNORE`) rather than accumulating statistics numerically.

A critical architectural gap exists: `FragmentDatabaseManager` (Phase 49) has no checkpoint methods. The extractor must either add checkpoint methods to `FragmentDatabaseManager`, or write checkpoint keys directly using `db.connection`. The former is cleaner and follows the pattern; the latter avoids touching Phase 49 output.

**Primary recommendation:** Implement `SSCExtractor` in `lucy_ng/fragments/extractor.py` following `ResumableHOSEStatsGenerator` exactly (chunk processing, checkpoint after each chunk, `--resume/--fresh` flags). Validate 2 ppm bin size on a 1K compound sample (`--sample N`) before full run. Add `build` command to the existing `fragment` CLI group.

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| FRAG-02 | SSC extraction pipeline extracts substructure-subspectrum correlations from 928K compounds using BFS sphere fragmentation with bond-preservation rules | Algorithmic spec confirmed from FEATURES.md + ARCHITECTURE.md; RDKit `FindAtomEnvironmentOfRadiusN` + `PathToSubmol` confirmed in STACK.md. Bond-preservation rules documented. |
| FRAG-03 | Extraction pipeline supports checkpointing and resume for multi-hour runs | Checkpoint pattern confirmed in `stats_generator.py` (ResumableHOSEStatsGenerator). `FragmentDatabaseManager` needs checkpoint methods added (gap found in Phase 49). |
| FRAG-04 | Fingerprint bin size (2 ppm) validated on 1K compound sample before full extraction | Validation approach documented in PITFALLS.md. Self-search recall >99% is the acceptance criterion. `--sample N` flag required on `lucy fragment build`. |
</phase_requirements>

---

## What Phase 49 Built (Inputs to Phase 50)

Understanding what already exists is critical — Phase 50 must not re-implement Phase 49 work.

### Already Exists and Tested

| File | What It Provides | Status |
|------|-----------------|--------|
| `src/lucy_ng/fragments/schema.py` | `FRAGMENT_SCHEMA_STATEMENTS`, schema v7 DDL, `CREATE_SSC_TABLE` (UNIQUE smiles), `CREATE_SSC_BITSET_TABLE`, atom_count index | Complete |
| `src/lucy_ng/fragments/models.py` | `SSCRecord` (with JSON field_validator), `SSCMatch` | Complete |
| `src/lucy_ng/fragments/db.py` | `FragmentDatabaseManager`: context manager, `create_tables()`, `insert_ssc_batch()` (with INSERT OR IGNORE deduplication and bitset), `get_ssc_count()`, `iter_ssc_bitsets()`, `get_ssc_by_id()` | Complete |
| `src/lucy_ng/fragments/__init__.py` | Exports `FragmentDatabaseManager`, `SSCRecord`, `SSCMatch` | Complete |
| `src/lucy_ng/cli/fragment.py` | `fragment` Click group + `info` subcommand | Partial — `build` command missing |
| `tests/test_fragment_db.py` | Full test coverage for Phase 49 | Complete |

### Critical Gap: No Checkpoint Support in FragmentDatabaseManager

`FragmentDatabaseManager` has no `set_checkpoint()`, `get_checkpoint()`, or `clear_checkpoint()` methods. The `schema_meta` table exists (used for `schema_version` and `bin_size`) but the fragment DB does not have an `operation_checkpoint` table.

**Decision for Phase 50:** Add an `operation_checkpoint` table and checkpoint methods to `FragmentDatabaseManager`. This is the clean solution. The `schema_meta` table could be abused as a checkpoint store (it's just key/value pairs), but adding a dedicated table matches the main DB pattern and is semantically correct.

**Alternative (no new table):** Use `schema_meta` for checkpoint keys (`ssc_last_compound_id`, `ssc_compounds_processed`). This avoids adding a new table and reuses `db.connection.execute("INSERT OR REPLACE INTO schema_meta ...")`. Simpler but conflates metadata with process state.

**Recommendation:** Use `schema_meta` for checkpoint storage (simplest, no new table, no Phase 49 output modified). Prefix keys with `checkpoint_` to distinguish from schema metadata. The planner should make the final call.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| RDKit | 2025.9.4 (installed) | Fragment extraction via BFS sphere expansion | `FindAtomEnvironmentOfRadiusN` + `PathToSubmol` confirmed API for radius-N atom environments |
| NumPy | 2.2.1 (installed) | 256-bit fingerprint encoding and bitwise operations | `uint8[32]` arrays with vectorized bitwise AND; `packbits`/`frombuffer` for encoding |
| SQLite (stdlib) | System | Fragment database storage, `INSERT OR IGNORE` deduplication | Already in use; UNIQUE constraint on `smiles` handles global deduplication |
| tqdm | 4.67.3 (installed) | Progress bar for multi-hour extraction | Already used in `stats_generator.py` for identical pattern |
| Click | 8.1.8 (installed) | CLI command group extension | `fragment build` follows same pattern as `database build` |
| Pydantic v2 | 2.12.5 (installed) | `SSCRecord` model (Phase 49 output) | Already in place |

### No New Dependencies

All required operations are achievable with the existing stack. No `pip install` required. Confirmed in STACK.md research.

---

## Architecture Patterns

### Recommended Module Structure

```
src/lucy_ng/fragments/          # Phase 49: all complete
├── __init__.py                 # Exports SSCRecord, SSCMatch, FragmentDatabaseManager
├── schema.py                   # Schema v7 DDL (Phase 49)
├── models.py                   # SSCRecord, SSCMatch Pydantic models (Phase 49)
├── db.py                       # FragmentDatabaseManager (Phase 49, needs checkpoint methods)
└── extractor.py                # NEW (Phase 50): SSCExtractor — BFS fragmentation + pipeline

src/lucy_ng/cli/
└── fragment.py                 # EXTEND (Phase 50): add `build` command to existing group
```

### Pattern 1: BFS Sphere Fragmentation (The Core Algorithm)

**Source:** `background/wenk-thesis.txt` §3.1.4.2.3; FEATURES.md bond-preservation rules

**Algorithm for each compound:**

```python
from rdkit import Chem
from rdkit.Chem import AllChem

def extract_fragments_for_compound(
    smiles: str,
    atom_shifts: list[tuple[int, float]],  # (atom_index, shift_ppm)
) -> list[SSCRecord]:
    """Extract all unique SSC fragments from one compound."""
    mol = Chem.MolFromSmiles(smiles)  # NO AddHs() — implicit H only
    if mol is None:
        return []

    # Standardize aromaticity BEFORE any fragmentation
    Chem.SetAromaticity(mol, Chem.AromaticityModel.AROMATICITY_MDL)

    # Build atom_index -> shift_ppm mapping (only atoms with known shifts)
    shift_map: dict[int, float] = {
        idx: ppm for (idx, ppm) in atom_shifts if idx is not None
    }
    if not shift_map:
        return []

    # Detect ring systems for ring-centered fragments
    ring_info = mol.GetRingInfo()
    ring_atom_sets: list[frozenset[int]] = [
        frozenset(ring) for ring in ring_info.AtomRings()
        if len(ring) <= 6  # Max ring size = 6 per Wenk thesis
    ]

    seen_smiles: set[str] = set()
    fragments: list[SSCRecord] = []

    # Atom-centered fragments: radius 1-3 from each atom with a known shift
    for atom_idx, center_shift in shift_map.items():
        for radius in range(1, 4):  # Max radius = 3 per Wenk thesis
            frag_smiles, frag_shifts = _extract_atom_environment(
                mol, atom_idx, radius, shift_map
            )
            if frag_smiles and frag_smiles not in seen_smiles and len(frag_shifts) > 0:
                seen_smiles.add(frag_smiles)
                fragments.append(_build_ssc_record(frag_smiles, frag_shifts))

    # Ring-centered fragments: radius 1 from ring systems containing atoms with shifts
    for ring_atoms in ring_atom_sets:
        if not (ring_atoms & set(shift_map.keys())):
            continue  # Skip rings with no known shifts
        frag_smiles, frag_shifts = _extract_ring_environment(
            mol, ring_atoms, radius=1, shift_map=shift_map
        )
        if frag_smiles and frag_smiles not in seen_smiles and len(frag_shifts) > 0:
            seen_smiles.add(frag_smiles)
            fragments.append(_build_ssc_record(frag_smiles, frag_shifts))

    return fragments
```

**Key constraint:** Work with implicit H only (no `Chem.AddHs()`). This matches the HOSE code generation policy in CLAUDE.md "Critical Architecture Decisions."

### Pattern 2: RDKit Fragment Extraction API

**Source:** STACK.md, verified against RDKit 2025.9.4 docs

```python
from rdkit import Chem

def _extract_atom_environment(
    mol: Chem.Mol,
    atom_idx: int,
    radius: int,
    shift_map: dict[int, float],
) -> tuple[str | None, list[float]]:
    """Extract BFS atom environment at given radius. Returns (canonical_smiles, shifts)."""
    env = Chem.FindAtomEnvironmentOfRadiusN(mol, radius, atom_idx)
    if not env:
        return None, []

    amap: dict[int, int] = {}
    submol = Chem.PathToSubmol(mol, env, atomMap=amap)
    if atom_idx not in amap:
        return None, []

    # Collect shifts for all atoms in the fragment that have known shifts
    frag_shifts = [
        shift_map[orig_idx]
        for orig_idx in amap
        if orig_idx in shift_map
    ]
    if not frag_shifts:
        return None, []

    canonical = Chem.MolToSmiles(submol, canonical=True)
    return canonical, frag_shifts
```

**Note on `PathToSubmol`:** The `atomMap` dict maps original atom indices to fragment atom indices. The fragment SMILES may include implicit attachment points (open valences become explicit if `dummyLabels=True` is used). For SSC storage, canonical SMILES without dummy labels is sufficient — the SMILES uniquely identifies the substructure.

**Note on ring system fragments:** Ring atoms form a single connected subgraph. Use `Chem.PathToSubmol` with all ring bonds included (from `mol.GetBondBetweenAtoms` for ring atom pairs), then expand by radius 1 using the same BFS.

### Pattern 3: 256-bit Fingerprint Generation

**Source:** STACK.md code example, confirmed against Sherlock PMC9920390

```python
import numpy as np

def shifts_to_fingerprint(shifts: list[float], bin_ppm: float = 2.0) -> bytes:
    """Encode subspectrum shifts as 256-bit fingerprint (32 bytes).

    Bin N covers [N*bin_ppm, (N+1)*bin_ppm) ppm.
    Range: 0-511 ppm with bin_ppm=2.0 gives 256 bins.
    """
    fp = np.zeros(32, dtype=np.uint8)
    for shift in shifts:
        if 0.0 <= shift < 512.0:
            bin_idx = int(shift / bin_ppm)  # 0..255
            byte_pos = bin_idx // 8
            bit_pos = bin_idx % 8
            fp[byte_pos] |= np.uint8(1 << bit_pos)
    return fp.tobytes()

def build_query_fingerprint_with_tolerance(
    shifts: list[float],
    bin_ppm: float = 2.0,
) -> bytes:
    """Build query fingerprint with ±1 bin tolerance expansion.

    Used at SEARCH time (Phase 51), not at extraction time.
    At extraction, store the exact fingerprint without expansion.
    """
    fp = np.zeros(32, dtype=np.uint8)
    for shift in shifts:
        if 0.0 <= shift < 512.0:
            bin_idx = int(shift / bin_ppm)
            for b in [bin_idx - 1, bin_idx, bin_idx + 1]:
                if 0 <= b <= 255:
                    fp[b // 8] |= np.uint8(1 << (b % 8))
    return fp.tobytes()
```

**Storage:** 32 bytes per SSC as SQLite BLOB. At 24M SSCs: 24M × 32 = 768 MB for bitsets alone.

### Pattern 4: Checkpoint/Resume (from ResumableHOSEStatsGenerator)

**Source:** `src/lucy_ng/prediction/stats_generator.py` lines 580-840

The `ResumableHOSEStatsGenerator.run()` method establishes the checkpoint pattern:

1. On `--fresh`: clear checkpoint keys AND delete existing SSC data, then start from compound_id=0
2. On `--resume`: load `ssc_last_compound_id` from checkpoint; start iteration from `id > last_id`
3. On normal start (no checkpoint exists): start from 0
4. After each chunk: `db.set_checkpoint("ssc_last_compound_id", str(last_compound_id))`
5. Commit SSC batch to DB, then commit checkpoint — ORDER MATTERS: commit SSCs first

**Checkpoint keys to use in schema_meta:**

```python
CHECKPOINT_KEY_LAST_COMPOUND_ID = "checkpoint_ssc_last_compound_id"
CHECKPOINT_KEY_COMPOUNDS_PROCESSED = "checkpoint_ssc_compounds_processed"
CHECKPOINT_KEY_COMPOUNDS_SKIPPED = "checkpoint_ssc_compounds_skipped"
CHECKPOINT_KEY_SSCS_EXTRACTED = "checkpoint_ssc_sscs_extracted"
```

**Checkpoint storage options:**

Option A — Add checkpoint table to fragment DB (clean, new table):
```sql
CREATE TABLE IF NOT EXISTS operation_checkpoint (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
)
```
Then add `set_checkpoint(key, value)`, `get_checkpoint(key)`, `clear_checkpoint(key)` to `FragmentDatabaseManager`.

Option B — Reuse `schema_meta` (simpler, no new table):
```python
# Use schema_meta with checkpoint_ prefix for all checkpoint keys
db.connection.execute(
    "INSERT OR REPLACE INTO schema_meta (key, value) VALUES (?, ?)",
    ("checkpoint_ssc_last_compound_id", str(compound_id))
)
```

**Recommendation:** Option B is simpler and avoids modifying Phase 49 output. Use `schema_meta` with `checkpoint_` prefix. The planner should decide based on code cleanliness preference.

### Pattern 5: Chunk Processing Loop

```python
class SSCExtractor:
    """Resumable SSC extraction pipeline."""

    def __init__(
        self,
        compound_db: DatabaseManager,
        fragment_db: FragmentDatabaseManager,
    ) -> None:
        self.compound_db = compound_db
        self.fragment_db = fragment_db

    def run(
        self,
        chunk_size: int = 1000,
        sample: int | None = None,
        resume: bool = True,
        fresh: bool = False,
        log_file: Path | str | None = None,
    ) -> SSCExtractionResult:
        """Run extraction pipeline."""

        if fresh:
            # Clear SSC table + checkpoint keys
            self._clear_data()
            start_id = 0
        elif resume:
            # Load last checkpoint
            start_id = int(
                self._get_checkpoint("checkpoint_ssc_last_compound_id") or "0"
            )
        else:
            start_id = 0

        max_compounds = sample  # None = process all

        compounds_processed = 0
        compounds_skipped = 0
        sscs_extracted = 0
        last_id = start_id

        for compound_id, smiles, shifts in self.compound_db.iter_compounds_with_shifts_from(
            start_id=start_id, batch_size=100
        ):
            if max_compounds and compounds_processed >= max_compounds:
                break

            # Filter: only compounds with atom-indexed shifts
            indexed_shifts = [(idx, ppm) for (idx, ppm) in shifts if idx is not None]
            if not indexed_shifts:
                compounds_skipped += 1
                print(f"SKIPPED: compound_id={compound_id} (no atom-indexed shifts)", file=sys.stderr)
                last_id = compound_id
                continue

            # Extract fragments
            fragments = extract_fragments_for_compound(smiles, indexed_shifts)

            # Batch insert (INSERT OR IGNORE deduplication)
            if fragments:
                inserted, skipped = self.fragment_db.insert_ssc_batch(fragments)
                sscs_extracted += inserted

            compounds_processed += 1
            last_id = compound_id

            # Checkpoint every chunk_size compounds
            if compounds_processed % chunk_size == 0:
                self._save_checkpoint(last_id, compounds_processed, compounds_skipped, sscs_extracted)

        # Final checkpoint
        self._save_checkpoint(last_id, compounds_processed, compounds_skipped, sscs_extracted)

        return SSCExtractionResult(
            compounds_processed=compounds_processed,
            compounds_skipped=compounds_skipped,
            sscs_extracted=sscs_extracted,
        )
```

### Pattern 6: CLI Build Command

**Source:** Existing `cli/database.py` `build` command and `cli/fragment.py` `info` command

```python
@fragment.command()
@click.argument("compound_db", type=click.Path(exists=True, path_type=Path))
@click.argument("fragment_db", type=click.Path(path_type=Path))
@click.option("--chunk-size", default=1000, type=int, show_default=True)
@click.option("--sample", type=int, default=None,
              help="Process only N compounds (for validation)")
@click.option("--resume/--fresh", default=True,
              help="Resume from checkpoint (default) or restart from scratch")
@click.option("--log-file", type=click.Path(path_type=Path), default=None,
              help="Write progress to log file (for nohup operation)")
def build(
    compound_db: Path,
    fragment_db: Path,
    chunk_size: int,
    sample: int | None,
    resume: bool,
    log_file: Path | None,
) -> None:
    """Build fragment (SSC) database from compound database.

    COMPOUND_DB: Path to lucy-ng-derep.db (source of 928K compounds).
    FRAGMENT_DB: Path to lucy-ng-fragments.db (output, created if not exists).

    Example (sample mode, bin size validation):

        lucy fragment build data/reference/lucy-ng-derep.db data/reference/lucy-ng-fragments.db --sample 1000

    Example (full run, resumable):

        nohup lucy fragment build data/reference/lucy-ng-derep.db data/reference/lucy-ng-fragments.db --log-file fragment.log &
    """
    ...
```

**Note on CLI signature:** The architecture docs show `--db` options, but the Phase 49 `info` command uses a positional argument. Follow the positional pattern for consistency within the fragment group. The planner should confirm.

### Anti-Patterns to Avoid

- **Anti-Pattern 1: Load all SSC bitsets into memory at import time.** Load lazily inside `search()` calls. (Phase 51 concern, but do not set a bad precedent in extractor.)
- **Anti-Pattern 2: In-memory global SMILES deduplication dict.** At 24M SSCs, this would consume 10+ GB. Use `INSERT OR IGNORE` with `UNIQUE(smiles)` constraint — already in place from Phase 49.
- **Anti-Pattern 3: Skip aromaticity standardization.** `Chem.SetAromaticity(mol, Chem.AromaticityModel.AROMATICITY_MDL)` must be called on every mol before fragmentation. Without it, aromatic SMILES from different sources produce inconsistent fragments.
- **Anti-Pattern 4: Store bitsets as hex text.** Phase 49 schema already uses BLOB. Keep it BLOB (32 bytes not 64 hex chars).
- **Anti-Pattern 5: Commit checkpoint before SSC batch.** If process dies between checkpoint commit and SSC commit, resume will skip already-checkpointed compounds without their SSCs. Commit SSC batch FIRST, then checkpoint.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| BFS atom environment extraction | Custom BFS traversal | `Chem.FindAtomEnvironmentOfRadiusN` + `Chem.PathToSubmol` | Already in RDKit 2025.9.4; handles ring systems, aromaticity, bond types |
| Bitset encoding | Custom bit manipulation | `numpy.uint8` array, 32 bytes | Vectorized, SIMD-accelerated in NumPy 2.2+; identical pattern for Phase 51 search |
| Global SMILES deduplication | In-memory set or dict | SQLite `UNIQUE(smiles)` + `INSERT OR IGNORE` | Already in Phase 49 schema; handles 24M rows without memory pressure |
| Resumable pipeline | Custom checkpoint file | `schema_meta` table (already exists in fragment DB) | Pattern proven by `operation_checkpoint` in compound DB |
| Canonical SMILES | Molecule fingerprinting | `Chem.MolToSmiles(canonical=True)` | RDKit canonical SMILES is deterministic across identical molecules |
| Parallel extraction | Custom multiprocessing | Start single-threaded; SQLite is single-writer anyway | `ProcessPoolExecutor` complicates checkpointing without performance gain due to write serialization |

---

## Common Pitfalls

### Pitfall 1: No Aromaticity Standardization Before Fragmentation

**What goes wrong:** COCONUT SMILES use aromatic notation (`c1ccccc1`), NMRShiftDB may use Kekulé (`C1=CC=CC=C1`). When `FindAtomEnvironmentOfRadiusN` is applied, the fragment SMILES depends on the input representation. Same chemical substructure stored as two different SMILES → fails deduplication, double-inserts.

**Why it happens:** RDKit's default `MolFromSmiles` with `sanitize=True` does perception, but aromaticity model varies by SMILES source. Without explicit `SetAromaticity` with a fixed model, canonical output can still differ.

**How to avoid:**
```python
mol = Chem.MolFromSmiles(smiles)  # implicit H, no AddHs
Chem.SetAromaticity(mol, Chem.AromaticityModel.AROMATICITY_MDL)
canonical = Chem.MolToSmiles(mol, canonical=True)
```
Apply before generating ANY fragment. This is documented as "Pitfall 3" in PITFALLS.md.

**Warning signs:** Self-search recall < 99% for aromatic compounds. Fragment count unexpectedly low for aromatic-rich databases.

**Verification:** After extraction from 1K sample, run self-search on 100 aromatic compounds (benzene ring in SMILES). All should find at least one matching SSC.

---

### Pitfall 2: Bin Size Is Unrecoverable — Validate Before Full Run

**What goes wrong:** The fingerprint bin size (2 ppm) is baked into every row's bitset BLOB at extraction time. Changing it requires re-extracting all 24M+ SSCs. Choosing the wrong value (too fine or too coarse) causes recall failures or search inefficiency.

**Why it happens:** Looks like a search-time parameter; it is actually a storage-time parameter.

**How to avoid:**
1. Run `lucy fragment build --sample 1000` on 1K compounds first
2. Run self-search on 100 sampled compounds: for each, search its own shifts against the fragment DB
3. Verify recall > 99%: the compound's own SSCs must appear in results
4. Only proceed to full run if recall criterion passes
5. The bin size is recorded in `schema_meta` key `bin_size` (already written by `create_tables()` in Phase 49). On full run, verify it matches.

**Warning signs:** Recall < 95% in sample mode self-search. Bin size not recorded in `schema_meta`.

**Verification criterion (from success criteria):** `lucy fragment build --sample 1000` completes AND self-search recall >99% on 100 sampled compounds.

---

### Pitfall 3: Missing Atom-Indexed Shifts — Silent Skip Required

**What goes wrong:** NMRShiftDB compounds often have shifts without `atom_index` mapping. Only COCONUT compounds have consistent atom-indexed shifts. Compounds with `atom_index IS NULL` on all shifts cannot yield valid SSCs (can't know which carbon has which shift → can't assign shifts to fragment atoms).

**How to avoid:**
- Filter early: skip compounds where ALL shifts lack `atom_index`
- Log to stderr: `SKIPPED: compound_id={id} (no atom-indexed shifts)` — this is required by the success criteria
- Do not silently ignore; log count for diagnostic purposes
- Expected: ~30-40% of compounds skipped (NMRShiftDB coverage)

**Warning signs:** Total SSC count much lower than ~24M (Sherlock's baseline). Check stderr skip log.

---

### Pitfall 4: Checkpoint-Before-Data Commit Order

**What goes wrong:** If checkpoint is committed before SSC batch, and the process dies between the two commits, resume will skip the compounds that were checkpointed but whose SSCs were never written. Result: missing SSCs with no duplicate protection.

**How to avoid:** Always commit SSC batch FIRST:
```python
# Correct order:
inserted, skipped = self.fragment_db.insert_ssc_batch(batch)  # commit inside batch insert
self._save_checkpoint(last_id, ...)  # commit checkpoint after
```
`insert_ssc_batch` in Phase 49 already commits internally every `batch_size` records.

---

### Pitfall 5: `--fresh` Does Not Clear Fragment DB by Default

**What goes wrong:** `--fresh` must clear ALL existing SSC data (truncate `ssc` and `ssc_bitset` tables) AND reset checkpoint keys. If only checkpoint is cleared but SSC data remains, resume will re-insert duplicates (which `INSERT OR IGNORE` handles, but wastes time) and the count will look inflated.

**How to avoid:**
```python
if fresh:
    db.connection.execute("DELETE FROM ssc_bitset")
    db.connection.execute("DELETE FROM ssc")
    db.connection.commit()
    # Clear checkpoint keys
    for key in CHECKPOINT_KEYS:
        db.connection.execute(
            "DELETE FROM schema_meta WHERE key = ?", (key,)
        )
    db.connection.commit()
```
This also resets the AUTOINCREMENT sequence (SQLite doesn't reset sequences on DELETE, but IDs will just continue from last value — irrelevant for correctness).

---

### Pitfall 6: `iter_compounds_with_shifts_from` Yields All Shifts Including Unindexed

**What goes wrong:** `DatabaseManager.iter_compounds_with_shifts_from()` returns `list[tuple[int | None, float]]` — atom_index can be None. The extractor receives these and must filter them out before passing to the fragmentation algorithm.

**Confirmed in source:**
```python
# manager.py line 1145
shifts = [(r["atom_index"], r["shift_ppm"]) for r in shift_cursor.fetchall()]
```
atom_index is nullable. Filter in the extractor: `indexed = [(idx, ppm) for idx, ppm in shifts if idx is not None]`.

---

## Code Examples

### Self-Search Recall Validation (Sample Mode)

```python
def validate_self_search(
    compound_db: DatabaseManager,
    fragment_db: FragmentDatabaseManager,
    sample_size: int = 100,
) -> float:
    """Validate bin size: search each compound's own shifts, expect its SSCs appear."""
    from lucy_ng.fragments.fingerprint import shifts_to_fingerprint  # Phase 50 output

    recall_hits = 0
    total = 0

    for compound_id, smiles, shifts in compound_db.iter_compounds_with_shifts(batch_size=100):
        if total >= sample_size:
            break
        indexed_shifts = [ppm for idx, ppm in shifts if idx is not None]
        if not indexed_shifts:
            continue

        # Build query fingerprint
        query_fp = shifts_to_fingerprint(indexed_shifts)  # no tolerance expansion for self-search

        # Bitset pre-screening
        candidates = []
        for ssc_id, bitset in fragment_db.iter_ssc_bitsets():
            fp_arr = np.frombuffer(bitset, dtype=np.uint8)
            q_arr = np.frombuffer(query_fp, dtype=np.uint8)
            if np.all((fp_arr & q_arr) == fp_arr):
                candidates.append(ssc_id)

        # A self-search hit means at least one SSC was found
        if candidates:
            recall_hits += 1
        total += 1

    return recall_hits / total if total > 0 else 0.0
```

### Fingerprint Utility Module

```python
# src/lucy_ng/fragments/fingerprint.py  (NEW, small utility)

import numpy as np

BIN_SIZE_PPM = 2.0
FINGERPRINT_BITS = 256
FINGERPRINT_BYTES = 32  # 256 / 8


def shifts_to_fingerprint(shifts: list[float], bin_ppm: float = BIN_SIZE_PPM) -> bytes:
    """Encode 13C shifts as a 256-bit fingerprint (32 bytes)."""
    fp = np.zeros(FINGERPRINT_BYTES, dtype=np.uint8)
    for shift in shifts:
        if 0.0 <= shift < 512.0:
            bin_idx = int(shift / bin_ppm)
            fp[bin_idx // 8] |= np.uint8(1 << (bin_idx % 8))
    return fp.tobytes()
```

This utility is shared between Phase 50 (extractor writes fingerprints) and Phase 51 (searcher reads and compares them). Define it once in `fragments/fingerprint.py`.

### SSCExtractionResult Dataclass

```python
from dataclasses import dataclass

@dataclass
class SSCExtractionResult:
    """Result summary from SSC extraction run."""
    compounds_processed: int
    compounds_skipped: int  # Missing atom-indexed shifts
    sscs_extracted: int     # New SSCs inserted (dedup applied)
    sscs_duplicate: int     # SSCs skipped due to SMILES deduplication
    start_compound_id: int  # Checkpoint value at start of this run
    end_compound_id: int    # Last compound_id processed
```

---

## Build Order

Dependencies drive this order. Each step is independently testable.

### Step 1: Fingerprint Utility (`fragments/fingerprint.py`)

**What:** `shifts_to_fingerprint(shifts, bin_ppm=2.0) -> bytes`. 32 bytes.
**Why first:** Both extractor (write) and searcher (read) depend on this. Define once.
**Test:** Ethanol shifts [18.1, 57.5] → 32-byte bitset. Bit 9 set (18 ppm, bin 9). Bit 28 set (57 ppm, bin 28).

### Step 2: Core BFS Fragmentation (`fragments/extractor.py` — algorithm only)

**What:** `extract_fragments_for_compound(smiles, atom_shifts) -> list[SSCRecord]` — no DB, no CLI, pure algorithm.
**Why:** Testable without database. Validate fragment count and SMILES output on known molecules (ibuprofen, ethanol, benzene).
**Test:** Ibuprofen SMILES + known shifts → fragments include aromatic ring fragment. Benzene → ring fragment with 6 carbons.

### Step 3: `SSCExtractor` class with checkpoint/resume

**What:** Full `SSCExtractor.run()` with chunk loop, `--resume`, `--fresh`, skip logging.
**Test:** Run on 10 compounds from test DB, verify fragments inserted. Kill halfway, resume, verify no duplicates and SSC count is correct.

### Step 4: `lucy fragment build` CLI command

**What:** Add `build` command to `src/lucy_ng/cli/fragment.py`. Calls `SSCExtractor.run()`.
**Test:** `lucy fragment build test.db frag.db --sample 10` completes. `lucy fragment info frag.db` shows SSC count > 0.

### Step 5: Sample mode + self-search recall validation

**What:** `lucy fragment build --sample 1000` runs, then CLI runs self-search on 100 sampled compounds, reports recall percentage.
**Test:** On 1K compound sample, recall > 99%.

### Step 6: Full run (manual, not CI)

**What:** `lucy fragment build data/reference/lucy-ng-derep.db data/reference/lucy-ng-fragments.db`
**Test:** `lucy fragment info` reports SSC count in millions. Interrupt at 10% and resume without duplicates.

---

## Open Questions

1. **Checkpoint storage: schema_meta vs new operation_checkpoint table**
   - What we know: `schema_meta` is a simple key/value store already in the fragment DB. Main compound DB has a separate `operation_checkpoint` table.
   - What's unclear: Is it acceptable to mix metadata (schema_version, bin_size) with process state (checkpoint keys) in `schema_meta`?
   - Recommendation: Use `schema_meta` with `checkpoint_` prefix for Phase 50 (minimal change); planner decides based on cleanliness preference.

2. **Maximum fragment radius: 3 or 4?**
   - What we know: Wenk thesis says max radius 3 for atom-centered. STACK.md research assumes radius 4 for a ~26M SSC count. FEATURES.md says radius 3.
   - What's unclear: Exact radius cutoff to reproduce Sherlock's ~24.5M count.
   - Recommendation: Use radius 3 (documented in Wenk thesis) and measure actual SSC count. Adjust to 4 if count is too low (< 15M).

3. **Ring-centered fragment: include full ring or ring + 1 sphere?**
   - What we know: Wenk thesis says "ring system with max sphere 1" for ring-centered starting points.
   - What's unclear: Does "ring + sphere 1" mean just the ring atoms, or ring atoms + their direct non-ring neighbors?
   - Recommendation: Include ring atoms + all bonds connecting to immediate neighbors (sphere 1). This includes the substituents directly attached to the ring, which is the chemically meaningful context.

4. **CLI signature: positional arguments or `--db` options?**
   - Phase 49 `info` uses a positional argument. Architecture docs use `--db` options.
   - Recommendation: Follow Phase 49 `info` pattern (positional) for consistency within the `fragment` group.

5. **WAL mode during extraction**
   - What we know: SQLite WAL mode improves write throughput for batch inserts.
   - Recommendation: Enable WAL mode in `FragmentDatabaseManager._connect()` for extraction (`PRAGMA journal_mode=WAL`). Already used in other SQLite-heavy tools. Phase 51 search benefits from concurrent reads.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Sherlock uses MongoDB for SSC storage | lucy-ng uses SQLite BLOB | Design decision (v5.0) | Single-file deployment, no separate server |
| Python integer for 256-bit bitset | NumPy uint8[32] array | Design decision (v5.0) | Vectorized screening in Phase 51 |
| Resume by restarting from scratch | Checkpoint via operation_checkpoint/schema_meta | Established in v3.0 for HOSE stats | 10h run survives crash at 90% |

---

## Sources

### Primary (HIGH confidence)

- `/Users/steinbeck/Dropbox/develop/lucy-ng/src/lucy_ng/fragments/db.py` — Phase 49 FragmentDatabaseManager, exact API confirmed
- `/Users/steinbeck/Dropbox/develop/lucy-ng/src/lucy_ng/fragments/models.py` — SSCRecord, SSCMatch exact fields confirmed
- `/Users/steinbeck/Dropbox/develop/lucy-ng/src/lucy_ng/fragments/schema.py` — Schema v7 DDL, UNIQUE(smiles) constraint confirmed
- `/Users/steinbeck/Dropbox/develop/lucy-ng/src/lucy_ng/fragments/__init__.py` — Public API confirmed
- `/Users/steinbeck/Dropbox/develop/lucy-ng/src/lucy_ng/cli/fragment.py` — Existing CLI stub (only `info`, no `build`)
- `/Users/steinbeck/Dropbox/develop/lucy-ng/src/lucy_ng/prediction/stats_generator.py` — ResumableHOSEStatsGenerator pattern, checkpoint keys, chunk loop
- `/Users/steinbeck/Dropbox/develop/lucy-ng/src/lucy_ng/database/manager.py` — `iter_compounds_with_shifts_from`, `set_checkpoint`, `get_checkpoint`, `clear_checkpoint` — confirmed patterns to follow
- `/Users/steinbeck/Dropbox/develop/lucy-ng/tests/test_fragment_db.py` — Phase 49 test coverage; confirms what's tested vs what needs new tests
- `/Users/steinbeck/Dropbox/develop/lucy-ng/.planning/research/ARCHITECTURE.md` — SSC extractor algorithm, component responsibilities, build order
- `/Users/steinbeck/Dropbox/develop/lucy-ng/.planning/research/FEATURES.md` — Bond-preservation rules, Wenk thesis parameters, search algorithm parameters table
- `/Users/steinbeck/Dropbox/develop/lucy-ng/.planning/research/PITFALLS.md` — 7 critical pitfalls with prevention and recovery strategies
- `/Users/steinbeck/Dropbox/develop/lucy-ng/.planning/research/STACK.md` — RDKit API confirmation, NumPy bitset pattern, no new dependencies

### Secondary (MEDIUM confidence)

- `background/sherlock-analysis.md` — 24.5M SSC count reference (Sherlock baseline); impact statistics
- Wenk thesis (via FEATURES.md synthesis) — Algorithm parameters: radius 3, ring max size 6, bin size 2 ppm, DEV 2 ppm, AVGDEV 1 ppm

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries confirmed installed, APIs confirmed in docs
- Architecture: HIGH — Phase 49 output inspected live, patterns confirmed from stats_generator.py
- Pitfalls: HIGH — extracted from project's own research files, confirmed against live code
- Build order: HIGH — dependencies are clear from inspection of Phase 49 outputs
- Open questions: MEDIUM — documented for planner decision; do not block planning

**Research date:** 2026-02-19
**Valid until:** 2026-03-19 (stable domain — RDKit and SQLite APIs don't change frequently)

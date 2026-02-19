# Pitfalls Research: Fragment Library for CASE

**Domain:** Adding SSC-based fragment library to existing 928K-compound CASE system
**Researched:** 2026-02-19
**Confidence:** MEDIUM-HIGH (Sherlock thesis analysis + project source code + architecture review)

---

## Critical Pitfalls

Mistakes that require rewrites, corrupt the database, or silently produce wrong structures.

### Pitfall 1: SSC Extraction Takes 10-20+ Hours — No Checkpointing Built In

**What goes wrong:**
SSC extraction from 928K compounds involves generating RDKit substructures for every carbon atom in every compound. Sherlock extracted 24.5M SSCs from 892K compounds. At comparable scale, this is a multi-hour job (HOSE stats regeneration for lucy-ng took 8h39m for 7.9M entries — SSC extraction is similar or worse because substructure enumeration involves graph traversal per atom per compound, not just HOSE lookups). If the process fails at hour 7 with no checkpoint, you restart from zero.

**Why it happens:**
SSC extraction is a one-time pipeline step, so developers underestimate its duration and write a simple for-loop without checkpointing. The existing HOSE stats generator already has this exact pitfall pattern — the checkpoint infrastructure (`operation_checkpoint` table, `CHECKPOINT_KEY_LAST_COMPOUND_ID`) was added after experiencing restart pain.

**How to avoid:**
Reuse the existing checkpoint pattern from `stats_generator.py`. The `operation_checkpoint` table and `set_checkpoint`/`get_checkpoint` methods already exist in `DatabaseManager`. Implement SSC extraction with:
1. Batch processing in groups of 1000 compounds
2. Checkpoint after every batch: `db.set_checkpoint("ssc_last_compound_id", str(compound_id))`
3. Resume with `iter_compounds_with_shifts_from(start_id=last_checkpoint)`
4. Validate checkpoint resume by verifying SSC count at restart matches expected from prior run

**Warning signs:**
- Extraction script has no progress bar and no checkpoint saves
- Extraction takes > 30 minutes on a test run without any intermediate commits
- No `ssc_last_compound_id` key in `operation_checkpoint` table during a run
- Log shows "processed N compounds" but no intermediate database inserts

**Phase to address:**
SSC Extraction Pipeline phase — must be the first deliverable tested. Run on 10K compound sample first to measure per-compound cost and project total time before committing to full 928K run.

---

### Pitfall 2: Fingerprint Bin Size Determines the Quality of Every Search — Wrong Value Is Unrecoverable

**What goes wrong:**
Sherlock uses 256-bit fingerprints with 2 ppm bins. The bit at position N is set if any carbon in the SSC has a shift in the range [N×2, (N+1)×2] ppm. This 2 ppm bin is a calibrated choice: too small (0.5 ppm) → fingerprints too sparse, AND operations return too few candidates → over-filters; too large (5 ppm) → fingerprints too dense, AND operations return too many candidates → no pre-screening benefit. The fingerprint bin size is baked into every row of the SSC table at extraction time. Changing it requires re-extracting all 24.5M+ SSCs.

**Why it happens:**
The bin size looks like a tunable parameter that can be changed at search time. It is not — it determines how the bitsets are computed at storage time. A developer implementing this for the first time may choose "something reasonable" and proceed, discovering only after full extraction that the search recall is unacceptable.

**How to avoid:**
Validate the bin size on a sample BEFORE full extraction:
1. Extract SSCs from 1K compounds with each candidate bin size (0.5, 1.0, 2.0, 5.0 ppm)
2. For each bin size, run fragment search on 5 known compounds from the Sherlock test set
3. Measure recall (does the correct fragment appear in the candidate set?) and precision (fraction of candidates that survive fine matching)
4. Accept 2 ppm only if: recall > 99% and candidates-per-search < 1000
5. Commit bin size to `schema_meta` table before extraction: `db.set_checkpoint("ssc_fingerprint_bin_ppm", "2.0")`

**Warning signs:**
- Bin size selected based on intuition, not empirical validation
- Fragment search returns 0 candidates for known-matching fragments (too-small bin)
- Fragment search returns > 5000 candidates requiring fine matching (too-large bin)
- Bin size not recorded anywhere in the database

**Phase to address:**
SSC Extraction Pipeline phase — validate bin size on sample before full run. This is a BLOCKING decision. Nothing else can proceed until bin size is confirmed.

---

### Pitfall 3: RDKit Substructure Enumeration Produces Invalid SSCs from Aromatic Systems

**What goes wrong:**
RDKit's ring system handling with aromatic SMILES produces ambiguous substructures. A benzene ring fragment may be enumerated as `c1ccccc1` (aromatic) or `C1=CC=CC=C1` (Kekulé). These do NOT match via RDKit's `HasSubstructMatch` if one is aromatic and the other Kekulé. Result: SSC stored as aromatic, query substructure is Kekulé → false negative. In Sherlock (Java/CDK), aromaticity perception is explicit. In RDKit (Python), it depends on `SanitizeMol` call order.

**Why it happens:**
SMILES from the compound database may be stored in either aromatic or Kekulé form depending on source (COCONUT uses aromatic notation, NMRShiftDB may not). When generating substructures via RDKit, the output form depends on which sanitization path is taken. Inconsistency between storage and query time causes lookup failures.

**How to avoid:**
Standardize ALL molecules before SSC extraction using a single aromaticity model:
```python
from rdkit import Chem
from rdkit.Chem import MolFromSmiles

# CORRECT: explicit aromaticity perception with canonical SMILES output
def standardize_mol(smiles: str) -> str | None:
    mol = MolFromSmiles(smiles)
    if mol is None:
        return None
    Chem.SetAromaticity(mol, Chem.AromaticityModel.AROMATICITY_MDL)
    return Chem.MolToSmiles(mol)  # canonical, consistent aromaticity
```
Apply the same standardization at query time (when building the query fragment from the experimental spectrum data). The molecule representation at storage time MUST match query time exactly.

**Warning signs:**
- SSC search on a compound using its own spectrum returns 0 matches (self-search should always match)
- Fragment search performance is asymmetric: aromatic compounds get 0 candidates, aliphatic compounds work
- Recall drops sharply for compounds containing aromatic rings

**Phase to address:**
SSC Extraction Pipeline phase — implement standardization before any extraction. Add a self-search test to the extraction validation suite: for 100 randomly sampled compounds, verify that searching with their own spectrum finds at least one matching SSC.

---

### Pitfall 4: DEFF/FEXP Goodlist Semantics Are Opposite to DEFF NOT Badlist — Agent Will Conflate Them

**What goes wrong:**
LSD's DEFF NOT badlist EXCLUDES structures containing the pattern. LSD's DEFF/FEXP goodlist REQUIRES that at least one solution contains the fragment. These are fundamentally different semantics. The agent (lsd-engineer) already knows DEFF NOT from v3.0/v4.0. When adding fragment goodlist support, the agent may:
- Write DEFF (goodlist) when it should write DEFF NOT (badlist), eliminating all solutions instead of filtering bad ones
- Apply DEFF goodlist constraints too aggressively, requiring multiple fragments simultaneously when LSD only requires each fragment to match at least ONE solution
- Mix goodlist and badlist DEFF commands in a way LSD doesn't support

**Why it happens:**
Both use the `DEFF` command root in LSD. The distinction is DEFF (fragment must be present in result) vs DEFF NOT (fragment must not be present). When the agent is given new knowledge about goodlist fragments, it is easy to confuse the constraint polarity, especially since both use similar SMILES pattern notation.

**How to avoid:**
In the agent knowledge update, use EXPLICIT semantic labeling with worked examples:
```
; DEFF NOT = BADLIST (exclusion filter)
DEFF NOT C1CC1    ; EXCLUDES all solutions containing cyclopropane

; DEFF = GOODLIST (inclusion requirement)
; This pattern must appear in at LEAST ONE solution
DEFF Cc1ccccc1    ; At least one solution must contain methylbenzene substructure
```
Teach the agent: "DEFF goodlist reduces solution count by REQUIRING structural features. Use only when fragment search confidence is HIGH (fine matching score < threshold). NEVER mix goodlist with badlist in same file unless you understand LSD's precedence."

The CLI command `lucy fragment search` should output the LSD command syntax explicitly, not just the SMILES pattern, to remove any ambiguity.

**Warning signs:**
- Zero solutions after fragment injection (goodlist applied when badlist was intended)
- Solution count unchanged after fragment injection (badlist applied when goodlist was intended)
- Agent writes DEFF commands but solution count goes UP (impossible — constraint is wrong)
- CASE-PROGRESS.md shows "fragment injected" but constraint is not verified against LSD docs

**Phase to address:**
Agent Integration phase — lsd-engineer knowledge update must include explicit DEFF vs DEFF NOT semantic tests. Add a verification step: run LSD on a minimal test case with known fragment before adding to compound workflow.

---

### Pitfall 5: Fragment Constraint Conflicts with HMBC-Derived Constraints — Over-Constraining Eliminates Correct Structure

**What goes wrong:**
HMBC correlations define connectivity constraints (which carbon connects to which proton). Fragment goodlist constraints define substructural requirements (which bonding pattern must exist). These can conflict: an HMBC constraint requires C5-H12 (3-bond path through 6-membered ring), but the fragment goodlist requires a 5-membered ring substructure. LSD must satisfy BOTH, but the correct ibuprofen-like structure satisfies neither fragment (it has a 6-membered ring). Result: correct structure eliminated, only wrong structures survive.

This is the ibuprofen failure mode inverted: v4.0 excluded correct structures via over-constraining with HMBC 4J couplings. Fragment constraints can do the same, especially if:
- Fragment was matched by spectral similarity but has wrong topology
- Fine matching threshold is too permissive (matches fragments that are spectrally similar but structurally wrong)
- Multiple fragments are injected simultaneously (each fragment correct individually, but impossible to satisfy all simultaneously)

**Why it happens:**
Fragment search is a pre-filter, not a definitive structural assignment. The fine matching step catches most false positives, but not all. When two correct fragments (e.g., "aromatic ring with methyl" and "carboxylic acid group") are each individually valid but their combined injection conflicts with HMBC constraints (say the HMBC forces them to be adjacent in a way the fragments don't permit), zero solutions emerge.

**How to avoid:**
Inject ONE fragment at a time and measure solution count change:
1. Baseline: N solutions without fragment
2. Inject fragment A: M solutions (if M = 0, fragment A conflicts with HMBC constraints — discard)
3. Inject fragment B: P solutions (if P = 0, B conflicts — discard)
4. Never inject two fragments simultaneously unless each was validated individually

Implement a fragment injection protocol in the agent:
```
For each candidate fragment (sorted by fine matching score, best first):
  1. Write LSD file with existing constraints + this fragment
  2. Run LSD
  3. If solutions > 0: keep fragment, move to next
  4. If solutions = 0: discard fragment, log conflict
  5. If final solution count = original (no improvement): report "no helpful fragments found"
```

**Warning signs:**
- Zero solutions immediately after fragment injection (first indication of conflict)
- Fragment confidence reported as HIGH but solution count drops to 0
- Agent injects 3+ fragments simultaneously without individual validation
- Fine matching threshold is > 5 ppm (too permissive)

**Phase to address:**
Agent Integration phase — define sequential injection protocol in lsd-engineer knowledge. The CLI command must support dry-run mode: `lucy fragment search --dry-run` outputs candidate fragments without injecting, allowing manual review before agent commits.

---

### Pitfall 6: Database Schema Migration from v6 — New Tables Must Not Break Existing Operations

**What goes wrong:**
The current database schema is at v6 with tables: `compounds`, `shifts`, `hose_stats`, `bond_pair_stats`, `schema_meta`, `operation_checkpoint`. Adding SSC tables (v7+) must NOT change the behavior of existing queries (dereplication, prediction, statistical detection). The migration risk is:
1. Accidentally changing an index that existing queries depend on
2. WAL mode conflicts: if SSC table is extremely large (24.5M+ rows), enabling WAL for write performance during extraction may affect read performance for concurrent prediction queries
3. SQLite file size limits: at 24.5M SSC rows × ~100 bytes per row ≈ 2.5 GB, added to existing 2.8 GB database = 5+ GB. SQLite supports this, but macOS Dropbox sync will choke on a 5 GB file that changes frequently.

**Why it happens:**
SSC extraction is the first time the database grows by an order of magnitude (2.8 GB → 5+ GB). The existing migration chain (v3 → v4 → v5 → v6) only added columns and a small table. Adding 24.5M rows is qualitatively different.

**How to avoid:**
1. Add SSC tables in a **separate database file** (`lucy-ng-fragments.db`) rather than `lucy-ng-derep.db`. This keeps the existing 2.8 GB database unchanged, avoids Dropbox sync issues, and allows separate backup/distribution.
2. CLI commands take `--fragments-db path` alongside existing `--database path`
3. Migration to separate file approach: no code migration needed (new file is new feature, not a schema change to existing file)
4. If single-file architecture is chosen, increment SCHEMA_VERSION to 7 and follow existing migration pattern exactly (see `migrate_v5_to_v6` as template)

**Warning signs:**
- SSC extraction writes to existing `lucy-ng-derep.db` and file grows > 5 GB
- Dereplication queries (formula lookup) are slower after extraction (index contention)
- Prediction accuracy changes after migration (wrong assumption: should be identical)
- Dropbox reports sync conflict on 5 GB database file during extraction

**Phase to address:**
Database Schema phase — FIRST decision to make before any extraction code is written. The separate-file approach is strongly recommended for this project. Commit to it early.

---

### Pitfall 7: Fine Matching Is O(N) per Search Over Candidate SSCs — Query Performance Degrades at Scale

**What goes wrong:**
Pre-screening with bitset fingerprints reduces candidates from 24.5M to (hopefully) < 1000. Fine matching then computes DEV and AVGDEV for each candidate. If bitset pre-screening is ineffective (wrong bin size, low bit density), fine matching must process 10,000+ candidates per search. At 1ms per candidate × 10,000 candidates = 10 seconds per fragment search call. The agent runs fragment search at the start of each CASE iteration — 10 iterations × 10 seconds = 100 seconds just for fragment search.

**Why it happens:**
Bitset pre-screening effectiveness depends on the input spectrum's fingerprint density. A spectrum with only 6 carbons (C6 formula) has a sparse fingerprint — few bits set — so the AND operation rejects few candidates. This is the correct behavior in principle (sparse spectra have more matching fragments) but can be slow.

**How to avoid:**
1. Implement bitset pre-screening using Python's built-in bitwise AND on integer bitmasks (256-bit = 4 × 64-bit integers). SQLite's BLOB storage is efficient for this.
2. Set a hard candidate limit: if bitset pre-screening yields > 2000 candidates, skip fine matching and return "no confident fragments" rather than spending 2+ seconds.
3. Add result caching: same `(formula, shifts_fingerprint)` query should cache results across iterations (shifts don't change, only HMBC constraints grow).
4. Benchmark on a real compound before agent integration: measure pre-screening candidate count and fine matching time for 5 known-structure compounds.

**Warning signs:**
- Fragment search takes > 3 seconds per call on an M1 Mac
- Pre-screening candidate count consistently > 5000 per search
- Agent iteration time increases by 30+ seconds after fragment search integration
- Candidate count doesn't decrease when shifts fingerprint is dense (many carbons)

**Phase to address:**
Fragment Search Engine phase — implement bitset pre-screening, measure candidate counts, add hard limit before exposing CLI command to agent.

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Store SSCs in existing `lucy-ng-derep.db` | Single database, simpler code | 5+ GB file, Dropbox sync issues, index contention with existing queries | Never — use separate `lucy-ng-fragments.db` |
| Skip bitset pre-screening (direct fine matching) | Simpler implementation, 1 algorithm instead of 2 | Fine matching 24.5M SSCs takes minutes per search | Never — bitset pre-screening is mandatory for < 1 second response |
| Inject all matching fragments simultaneously | Simpler agent logic (one LSD run) | Conflicting fragments eliminate correct structure; 0 solutions with no diagnostic | Never — always inject sequentially with solution count check |
| Use 5 ppm fine matching threshold (loose) | More fragments pass → fewer missed positives | Too many false positives; incorrect fragments constrain wrong structures | Acceptable only in initial discovery run, not in production |
| Hard-code bin size (don't record in schema_meta) | Faster implementation | Bin size mismatch if database is regenerated with different tooling | Never — always record extraction parameters in schema_meta |
| Skip self-search validation after extraction | Faster pipeline | Silent correctness failure — SSC table looks populated but matches nothing | Never — self-search is a 5-minute test that prevents days of debugging |
| No checkpoint in SSC extraction | Simpler code | 10+ hour restart on any failure | Never — extraction MUST be resumable |

## Integration Gotchas

Common mistakes when connecting SSC search to the existing CASE system.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| DEFF goodlist syntax | Write DEFF with pattern in same format as DEFF NOT | DEFF (goodlist) and DEFF NOT (badlist) have opposite semantics — test each on a minimal LSD file before agent integration |
| Fragment search CLI → agent | Agent receives SMILES pattern and writes DEFF command manually | CLI outputs the exact LSD command line ready to paste — removes agent interpretation error risk |
| Fragment injection timing | Run fragment search before writing LSD file (no HMBC context) | Run fragment search AFTER HMBC constraints are established (iteration 2+), so fragment-HMBC conflict can be detected |
| Fine matching DEV threshold | Copy Sherlock's 10 ppm DEV threshold without validation | 10 ppm is for ranking (lenient); fragment search needs tighter threshold (3-5 ppm) to avoid false positives |
| SSC extraction vs. HOSE extraction | Use same `iter_compounds_with_shifts` method | SSC extraction needs SMILES to build substructure graph, not just shifts — use `iter_compounds_with_shifts` but also retrieve SMILES |
| SQLite WAL mode during extraction | Enable WAL for write performance, leave enabled for reads | WAL is correct for extraction; switch back to DELETE journal mode for query-heavy CASE operations to avoid WAL file accumulation |

## Performance Traps

Patterns that work at small scale but fail at 24.5M SSC scale.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Linear scan of SSC table (no fingerprint index) | Fragment search takes 30+ seconds per call | Index on `ssc_fingerprint_blob` with partial match using SQLite BLOB prefix operations | At > 100K SSC rows |
| Fine matching all candidates without limit | Search time proportional to spectrum size (more carbons = more candidates = slower) | Hard candidate limit of 2000 after bitset pre-screening | Always for large databases |
| Parallel writes to SQLite during multi-threaded extraction | Database corruption or lock timeout errors | SQLite supports WAL for concurrent readers, but single writer only — serialize writes to one thread | With any parallelism during SSC insertion |
| Loading full SSC table into memory for bitset ops | OOM on machines with < 8 GB RAM when searching 24.5M SSCs | Stream-process candidates using SQL BLOB comparison — never load full table | At > 5M SSC rows |
| Fragment search at every CASE iteration | 10 iterations × search time = cumulative overhead | Cache results (fingerprint → fragment list) — shifts are fixed once picked | If shifts change between iterations (they shouldn't, but validate) |
| RDKit substructure matching in Python for 24.5M SSCs | Fine matching takes 10+ seconds per search | Pre-compute bitset fingerprints in database; fine matching only on < 2000 candidates | At > 1M SSC candidates after bitset filter |

## Data Quality Pitfalls

SSC-specific data quality issues that produce wrong fragments.

### DQ Pitfall 1: Missing Atom-to-Shift Mapping in Source Data

**What goes wrong:**
SSC extraction requires knowing which specific carbon atom (by index) has which experimental shift. In COCONUT, the `CNMR_SHIFTS` field maps atom index to shift. In NMRShiftDB, the mapping is in the assignment records. Some compounds in the database have shift data but no atom-to-shift mapping — only a list of shifts without atom assignments. These compounds CANNOT yield valid SSCs (you don't know which carbon atom has which shift).

**How to avoid:**
Filter compounds at the start of SSC extraction: only process compounds where `atom_index IS NOT NULL` for all shifts. Approximately 30-40% of compounds may lack atom mapping (NMRShiftDB is inconsistently assigned). This reduces the effective compound count but avoids generating invalid SSCs.

**Detection:** Log the skipped compound count: if > 60% of compounds are skipped for missing atom mapping, the shift data is worse than expected and the fragment library will be smaller than Sherlock's (Sherlock reports 24.5M from 892K compounds — if lucy-ng gets 10M from 928K, atom mapping coverage is likely the cause).

### DQ Pitfall 2: Hydrogen Count Mismatch Between SMILES and Atom Mapping

**What goes wrong:**
SMILES may have explicit hydrogens in some atoms but not others (mixed representation). When generating HOSE-based substructures, the hydrogen count affects the substructure graph. The shifts table stores `hydrogen_count` per atom, but this was populated from the source database's annotation, not from RDKit's hydrogen count. If a quaternary carbon in SMILES has `hydrogen_count=0` in the shifts table but RDKit computes `hydrogen_count=1` (due to valence inference), the SSC will be generated with wrong hydrogen annotation.

**How to avoid:**
Override hydrogen counts from RDKit, not from the database: `atom.GetTotalNumHs()` is authoritative. Only use the database's `hydrogen_count` as a sanity check (if they differ by more than 1, flag the compound for manual review).

## "Looks Done But Isn't" Checklist

Critical checks that indicate the fragment library is genuinely functional vs. appearing to work.

- [ ] **SSC Extraction Completeness:** `SELECT COUNT(*) FROM ssc` returns a number close to 24.5M (Sherlock's count), not < 1M. If count is low, check: compounds skipped due to missing atom mapping? Extraction terminated early without checkpoint?
- [ ] **Self-Search Validation:** For 100 randomly sampled compounds, searching with their own spectrum finds their own SSCs in the candidate set. If self-search fails, fingerprint generation is inconsistent between storage and query.
- [ ] **Bin Size Recorded:** `SELECT value FROM schema_meta WHERE key = 'ssc_fingerprint_bin_ppm'` returns a value. If missing, bin size may differ between extraction and search.
- [ ] **Goodlist Semantics Tested:** A known fragment injected as DEFF (goodlist) REDUCES solution count vs baseline. If count is unchanged or increases, DEFF syntax is wrong.
- [ ] **Sequential Injection Protocol:** Agent code injects one fragment at a time and checks solution count before next. If agent injects all fragments in one LSD file, over-constraining risk is unmitigated.
- [ ] **Conflict Detection:** When fragment conflicts with HMBC constraints (0 solutions), agent logs the conflict and moves on rather than halting. If agent halts on 0 solutions after fragment injection, it's conflating fragment conflict with LSD failure.
- [ ] **Fine Matching Time:** `lucy fragment search --shifts "..." --formula C13H18O2` completes in < 2 seconds on M1 Mac. If slower, pre-screening is not working.
- [ ] **Separate Database File:** SSC data lives in `lucy-ng-fragments.db`, not in `lucy-ng-derep.db`. Existing operations (dereplication, prediction) work identically without `--fragments-db` flag.

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Extraction failed at hour 7 without checkpoint | HIGH — restart from zero | 1. Add checkpoint code, 2. Delete partial SSC table, 3. Restart with checkpoint. Prevention is cheap; recovery is expensive. |
| Wrong bin size — must re-extract | HIGH — full re-extraction | 1. Drop SSC table, 2. Update bin size in schema_meta, 3. Re-extract with correct bin size. Takes 10+ hours. |
| DEFF goodlist applied as badlist | LOW — fix agent knowledge | 1. Identify all LSD files with wrong DEFF usage, 2. Update agent lsd-engineer.md with correct semantics + worked example, 3. Re-run affected compounds |
| Fragment conflicts with HMBC — 0 solutions | LOW — discard fragment | 1. CLI output already indicates conflict, 2. Agent skips fragment per sequential injection protocol, 3. No rewrite needed |
| SSC table in wrong database file | MEDIUM — data migration | 1. Create new separate database file, 2. Copy SSC table: `INSERT INTO fragments.ssc SELECT * FROM derep.ssc`, 3. Update CLI to use separate file |
| Fine matching too slow | MEDIUM — add caching and limits | 1. Add hard candidate limit (2000), 2. Add result cache keyed on (formula_normalized, shifts_fingerprint), 3. Benchmark improvement |
| Substructure aromaticity mismatch | MEDIUM — standardize and re-extract | 1. Identify aromatic compounds with 0 self-search recall, 2. Add standardization step to extraction, 3. Re-extract affected compounds (may be < 30% of total) |

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| No checkpoint in SSC extraction | SSC Extraction Pipeline | Run extraction to 10K compounds, kill process, verify restart from checkpoint continues correctly |
| Wrong fingerprint bin size | SSC Extraction Pipeline (pre-extraction validation) | Self-search recall > 99% on 100-compound sample at chosen bin size |
| Aromatic substructure mismatch | SSC Extraction Pipeline (standardization) | Self-search on aromatic compounds (benzene, naphthalene rings) returns SSC matches |
| DEFF goodlist vs. badlist confusion | Agent Integration | Smoke test: inject known fragment as DEFF, verify solution count decreases; inject as DEFF NOT, verify different compounds filtered |
| Fragment-HMBC conflict | Agent Integration (sequential injection protocol) | Run CASE on compound with known conflicting fragment; verify agent detects 0-solution conflict and discards fragment without halting |
| Database size and migration | Database Schema | SSC data in separate file; existing `lucy dereplicate c13` and `lucy predict c13` work without change |
| Fine matching performance | Fragment Search Engine | `lucy fragment search` < 2 seconds for any compound in Sherlock test set on M1 Mac |
| Missing atom mapping | SSC Extraction Pipeline (filtering) | Log shows skipped compound count; total SSC count within 50% of Sherlock's 24.5M |
| Simultaneous fragment injection | Agent Integration | CASE-PROGRESS.md shows one-fragment-at-a-time injection with solution counts after each |

---

## Sources

### Primary: Sherlock System Analysis
- `/Users/steinbeck/Dropbox/develop/lucy-ng/background/sherlock-analysis.md` — SSC extraction details, 24.5M count, bitset fingerprint design, DEFF/FEXP injection mechanism, impact on solution counts
- Wenk thesis (via sherlock-analysis.md): 256-bit fingerprints, 2 ppm bins, DEV/AVGDEV thresholds, compound processing scale

### Primary: lucy-ng Source Code
- `/Users/steinbeck/Dropbox/develop/lucy-ng/src/lucy_ng/database/schema.py` — v6 schema, existing migration pattern, checkpoint table
- `/Users/steinbeck/Dropbox/develop/lucy-ng/src/lucy_ng/database/manager.py` — `iter_compounds_with_shifts`, `set_checkpoint`, migration methods
- `/Users/steinbeck/Dropbox/develop/lucy-ng/src/lucy_ng/prediction/stats_generator.py` — checkpoint pattern, Welford accumulator, HOSE extraction timing (8h39m reference)
- `/Users/steinbeck/Dropbox/develop/lucy-ng/src/lucy_ng/prediction/hose.py` — `HOSECodeGenerator`, no explicit H policy

### Primary: Project Memory
- `MEMORY.md` — v4.0 UAT findings (ibuprofen failure, 4J HMBC), v3.0 constraint-loss bugs, HOSE regeneration timing

### Supporting: Domain Knowledge
- RDKit documentation: aromaticity models, `SetAromaticity`, `MolToSmiles` canonicalization (training data, MEDIUM confidence)
- SQLite documentation: WAL mode, BLOB storage, file size limits (training data, HIGH confidence for SQLite fundamentals)
- Sherlock GitHub repository (casekit library): SSC extraction implementation reference — MEDIUM confidence (code not directly inspected, inferred from thesis)

---
*Pitfalls research for: Fragment library and SSC search addition to lucy-ng CASE system*
*Researched: 2026-02-19*

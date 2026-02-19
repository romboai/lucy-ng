# Project Research Summary

**Project:** lucy-ng — v5.0 Fragment Library and SSC Search
**Domain:** Substructure-subspectrum correlation (SSC) fragment library for autonomous CASE
**Researched:** 2026-02-19
**Confidence:** HIGH (primary source: Wenk PhD thesis + existing codebase direct inspection)

## Executive Summary

The v5.0 milestone adds a Sherlock-style SSC fragment library to lucy-ng's autonomous CASE workflow. The core idea is well-established and algorithmically validated: extract 24.5M substructure-subspectrum correlations (SSCs) from the existing 928K-compound database, encode each as a 256-bit bitset fingerprint, and enable fast Boolean AND pre-screening during CASE runs to identify which known substructures are consistent with an experimental spectrum. The best-matching fragment is injected as an LSD DEFF/FEXP goodlist constraint, forcing every generated structure to contain that substructure. In Sherlock's validated results, this reduces 34/40 test cases to a single solution after applying the first fragment. This is the highest-leverage missing capability in lucy-ng today.

The recommended approach requires no new Python dependencies — all needed functionality is available in the existing stack (RDKit 2025.9.4, NumPy 2.2.1, SQLite, ProcessPoolExecutor from stdlib). The critical implementation choices are: separate database file (`lucy-ng-fragments.db`) to avoid inflating the existing 2.8 GB compound database, resumable checkpointed extraction to survive multi-hour pipeline runs, 2 ppm bin size validated empirically before full extraction (baked into every stored fingerprint, unrecoverable if wrong), and batch SQLite scanning for bitset pre-screening rather than loading 768 MB into memory at module startup. The fragment library and the 4J detection problem (from v4.0 UAT) are complementary, not competing: fragments can only select among structurally valid solutions — if the correct structure is excluded by wrong HMBC constraints, no fragment constraint can restore it.

The top implementation risk is extraction pipeline reliability. The existing HOSE stats generator took 8h39m for 7.9M entries; SSC extraction will be comparable or longer at 24M entries. A crash at hour 7 without checkpointing requires a full restart. The second major risk is DEFF goodlist vs. DEFF NOT badlist semantic confusion — the lsd-engineer agent already knows DEFF NOT (badlist), and conflating the two semantics produces wrong results with no error signal (either zero solutions or no constraint effect). Both risks have clear prevention strategies that must be built into the first deliverable.

## Key Findings

### Recommended Stack

No new Python dependencies are required. The fragment library milestone is buildable entirely from existing installed packages: RDKit 2025.9.4 (`FindAtomEnvironmentOfRadiusN`, `PathToSubmol`), NumPy 2.2.1 (vectorized uint8 bitwise AND), SQLite BLOB storage, and stdlib `concurrent.futures.ProcessPoolExecutor` for parallel extraction. The existing database schema (v6) is extended to v7 with two new tables. The SSC data should live in a separate `lucy-ng-fragments.db` file to keep the main compound database at its current 2.8 GB size.

The only medium-confidence architectural decision is separate vs. single database file. Research firmly recommends a separate file: the existing database lives on Dropbox, macOS sync will choke on a 5+ GB file that changes during extraction, and index contention during insertion could slow dereplication and prediction queries. This decision must be made before any extraction code is written.

**Core technologies:**
- RDKit 2025.9.4: fragment extraction via `FindAtomEnvironmentOfRadiusN` + `PathToSubmol` — already installed, correct API for atom-environment spheres (not BRICS, which produces retrosynthetic fragments)
- NumPy 2.2.1: 256-bit fingerprint bitset storage and vectorized AND screening — 32-byte uint8 arrays, SIMD-accelerated in NumPy 2.x, no FPSim2 or h5py needed
- SQLite BLOB: fingerprint storage at 32 bytes per SSC — single-file architecture, no external service; SSC data in separate `lucy-ng-fragments.db`
- ProcessPoolExecutor (stdlib): parallel extraction over 928K compounds — CPU-bound RDKit work, no joblib/ray/dask needed

### Expected Features

The MVP (v5.0 core) is the end-to-end path from offline extraction to agent-usable fragment constraints. Every item in the P1 list is a hard dependency — missing any one means the feature does not function at all.

**Must have (table stakes, v5.0 launch):**
- SSC extraction pipeline with checkpointing — without the library, nothing else works; extraction must survive multi-hour interruption
- 256-bit fingerprint per SSC (2 ppm bins, validated before full extraction) with Boolean AND pre-screening — without pre-screening, fine-matching 24M SSCs per CASE run is computationally infeasible
- Fine spectral matching (DEV 2 ppm, AVGDEV 1 ppm) with multiplicity and equivalence match — pre-screening has too many false positives; fine match selects genuinely useful fragments
- CLI: `lucy fragment search --shifts "..." --format json` — agent-accessible interface; lsd-engineer reads JSON and injects DEFF commands directly
- LSD goodlist file generation (SSTR/LINK format in fragment .lsd files) — fragment only useful if expressible in LSD syntax
- Agent integration in lsd-engineer — fragment search runs before each LSD write iteration; DEFF/FEXP injected before MULT commands; sequential single-fragment injection with solution-count validation
- Multi-compound UAT on at least 5 compounds from Sherlock test set — validates that solution count reduction matches Sherlock's expected pattern

**Should have (v5.x, after validation):**
- Multi-fragment sequential injection (inject second fragment if first still yields >5 solutions)
- Fragment search statistics in CLI output (diagnostic for threshold tuning)
- Formula-aware pre-screening (filter SSC by atom composition against query formula for speed)
- Fragment display in CASE-PROGRESS.md (transparency for chemist review)
- Resumable extraction checkpoint in CLI (--resume/--fresh flags; add if extraction is interrupted)

**Defer (v5.2+):**
- Fragment size filter (min 4 heavy atoms) — fine matching likely handles this implicitly via AVGDEV
- Custom user-uploaded fragments — high complexity, low value
- Fragment database regeneration when compound DB updates — only needed on rare compound DB updates

### Architecture Approach

The fragment library is a new subsystem that slots cleanly between two existing systems: the SQLite compound database (source of SSC data) and the LSD CASE workflow (consumer of DEFF/FEXP constraints). The integration is additive — no existing code paths are broken. The new `lucy_ng/fragments/` module follows all established patterns: thin CLI calling module logic, context manager for DB access, resumable chunked processing (clone of `ResumableHOSEStatsGenerator`), JSON output format for agent consumption. The lsd-engineer agent gains one new step: run `lucy fragment search` before writing each LSD iteration file, prepend DEFF/FEXP output before the MULT section.

**Major components:**
1. **SSC Extractor** (`fragments/extractor.py`) — BFS sphere fragmentation over all 928K compounds, aromaticity-standardized SMILES deduplication, 256-bit fingerprint generation, checkpoint/resume via existing `operation_checkpoint` table; follows `ResumableHOSEStatsGenerator` pattern exactly
2. **Fragment Searcher** (`fragments/searcher.py`) — batched bitset pre-screening (100K rows/batch from SQLite, avoiding 768 MB RAM load at startup), fine spectral matching (DEV/AVGDEV + multiplicity + equivalence), result ranking by atom_count DESC then AVGDEV ASC
3. **DEFF Formatter** (`fragments/lsd_formatter.py`) — converts matched SSC SMILES (with R group open sites) to SSTR/LINK format files; generates DEFF/FEXP command strings ready for direct injection; writes fragment files to current iteration directory
4. **Fragment CLI** (`cli/fragment.py`) — `lucy fragment build`, `lucy fragment search`, `lucy fragment info` commands; JSON output is the complete agent interface including exact LSD command strings
5. **Schema v7** (`database/schema.py`) — `ssc` and `ssc_bitset` tables in separate `lucy-ng-fragments.db`, migration function following existing v6 pattern; bin size recorded in `schema_meta` before extraction starts
6. **lsd-engineer agent update** — adds fragment search step at start of each LSD write iteration; adds DEFF/FEXP to constraint inventory; sequential injection protocol (one fragment at a time, discard if zero solutions); devils-advocate checks fragment file existence pre-run

### Critical Pitfalls

1. **No checkpointing in SSC extraction** — 24M SSC extraction will run 4-8 hours; a crash without checkpointing requires a full restart from zero. Prevention: reuse `operation_checkpoint` table and `set_checkpoint`/`get_checkpoint` from existing `DatabaseManager`; batch in groups of 1000 compounds; validate resume by checking SSC count matches prior progress.

2. **Wrong fingerprint bin size baked into all stored fingerprints** — bin size (2 ppm recommended from Sherlock thesis) is computed at extraction time and stored in every SSC row; changing it requires full re-extraction at 4-8 hours cost. Prevention: validate 2 ppm on a 1K compound sample across 5 known structures before full extraction; confirm recall >99% and candidates-per-search <1000; record bin size in `schema_meta` before starting full extraction.

3. **DEFF goodlist vs. DEFF NOT badlist semantic confusion** — lsd-engineer agent already knows DEFF NOT (badlist). Adding goodlist support creates a conflation risk with no error message distinguishing the outcomes: wrong goodlist semantics produces zero solutions or no constraint effect. Prevention: explicit worked examples in agent knowledge; CLI outputs exact LSD command strings, not just SMILES; smoke test goodlist semantics on minimal LSD case before agent integration.

4. **Fragment constraint conflicts with HMBC constraints eliminating correct structure** — a valid fragment may individually match spectral data but be topologically incompatible with HMBC-derived constraints, producing zero solutions. Prevention: inject one fragment at a time, run LSD after each, discard any fragment that yields zero solutions; never inject 3+ fragments simultaneously; agent logs conflict and continues rather than halting.

5. **RDKit aromatic substructure mismatch between extraction and query** — SMILES in the compound database may be stored in aromatic or Kekulé form; RDKit's aromaticity perception depends on sanitization path. Inconsistency between storage and query time causes false negatives for aromatic compounds. Prevention: standardize all molecules through one explicit aromaticity model (`SetAromaticity` with `AROMATICITY_MDL`) at both extraction and query time; validate with self-search test (100 compounds, their own spectrum must find their own SSCs in results).

## Implications for Roadmap

Based on combined research, the phase structure is strongly constrained by hard dependencies. Phase 1 and Phase 2 must complete in sequence before any subsequent phase can be meaningfully tested. The extraction pipeline is the first hard blocker; the DEFF formatter's fragment file format is the highest-risk unresolved question.

### Phase 1: Database Schema and Extraction Infrastructure

**Rationale:** Everything downstream depends on storage. Schema must exist before extraction can write data; extraction infrastructure must exist before the search engine has anything to query. This phase also forces the critical architectural decision (separate file vs. same database) before any code is written, at minimum cost.
**Delivers:** Schema v7 (`ssc` and `ssc_bitset` tables in `lucy-ng-fragments.db`); `DatabaseManager` query methods (`insert_ssc_batch`, `get_ssc_count`, `iter_ssc_bitsets`, `get_ssc_by_id`); `SSCRecord`/`SSCMatch` Pydantic models; validated schema migration; separate database file confirmed working with existing `lucy dereplicate` and `lucy predict` commands
**Addresses:** Fragment database schema (table stakes #7), pitfalls #1 (checkpointing table exists) and #6 (database migration/separation)
**Avoids:** Schema changes breaking existing dereplication and prediction queries; Dropbox sync issues from 5+ GB single file

### Phase 2: SSC Extraction Pipeline

**Rationale:** The fragment library is the foundation of all search functionality. Without 24M+ extracted SSCs, fragment search returns nothing and agent integration is untestable. This is the largest single phase and the highest-risk due to multi-hour runtime. Sample validation must precede full extraction.
**Delivers:** `SSCExtractor` with BFS sphere fragmentation, bond-preserving rules (Sherlock algorithm: preserve heteroatom-heteroatom bonds, bond order >1, C adjacent to 2+ heteroatoms, complete ring systems), aromaticity standardization, deduplication by canonical SMILES, 256-bit fingerprint generation (2 ppm bins, bin size validated and recorded in schema_meta); `lucy fragment build` CLI command with `--resume`/`--fresh` flags; `lucy fragment info` for validation; approximately 24M SSC records
**Addresses:** Table stakes #1-3 (SSC extraction, deduplication, fingerprints), pitfall #2 (bin size validation before full run), pitfall #5 (aromaticity standardization)
**Avoids:** Re-extraction by validating fingerprint bin size on 1K sample first; self-search validation on 100 compounds (including aromatic compounds) before committing to full 928K run

**Research flag:** Run on 1K compound sample first, measure per-compound cost, project full runtime, then commit to full run. Do not start full extraction until sample run passes self-search test (>99% recall on 100 sampled compounds) and bin size is confirmed. Log skipped compound count (compounds without atom-indexed shifts) — if >60% skipped, effective SSC count will be significantly below Sherlock's 24.5M.

### Phase 3: Fragment Search Engine

**Rationale:** With the SSC table populated, the search engine can be built and validated in isolation before agent integration. This separation makes debugging much easier — search correctness issues are isolated from agent behavior issues.
**Delivers:** `FragmentSearcher` with batched bitset pre-screening (100K rows/batch, avoiding full RAM load) and fine spectral matching (DEV/AVGDEV + multiplicity + equivalence match); result ranking; CLI `lucy fragment search` command with JSON output including `deff_commands` and `fexp_command` fields as exact strings for agent injection; performance benchmarks (target: <2 seconds on M1 Mac with hard 2000-candidate limit after pre-screening)
**Addresses:** Table stakes #2 (bitset pre-screening), #3 (fine matching), #4 (CLI), pitfall #7 (query performance)
**Avoids:** Anti-pattern of loading 768 MB bitsets at module import time; validates pre-screening effectiveness on Ibuprofen and 4 other test compounds (search on own shifts must find plausible fragments) before agent integration

### Phase 4: DEFF Formatter and LSD Integration

**Rationale:** The DEFF formatter is the highest-risk single component because the exact LSD fragment file format (SSTR/LINK notation inside a DEFF-referenced file) requires direct validation against LSD manual appendix before implementation. A wrong format produces syntactically invalid DEFF files with no helpful error message from LSD. This phase must validate LSD syntax independently before agent integration depends on it.
**Delivers:** `DEFFFormatter` converting SSC SMILES with R groups to SSTR/LINK format files; `lucy fragment to-lsd` CLI command; validated DEFF/FEXP syntax confirmed with working LSD smoke test (inject known fragment, verify solution count decreases); fragment .lsd files written to iteration directory
**Addresses:** Table stakes #5 (LSD goodlist file generation), pitfall #4 (DEFF vs DEFF NOT semantics)
**Avoids:** Anti-pattern of injecting DEFF after MULT commands (must appear first in LSD file); validates goodlist semantics with minimal LSD test case before any agent workflow integration

**Research flag:** DEFF fragment file internal format (SSTR/LINK notation inside the referenced .lsd file) is listed as MEDIUM confidence in research. Needs direct LSD manual appendix A4 verification or working test case before writing the formatter. This is the one unresolved open question that could require significant rework if the format differs from assumed SSTR/LINK structure.

### Phase 5: Agent Integration

**Rationale:** Agent integration is the final step and has no meaning until phases 1-4 deliver a working search pipeline with validated LSD syntax. The lsd-engineer workflow change is minimal in code (one new step before each LSD write) but high-risk in semantics (DEFF vs DEFF NOT confusion, sequential injection protocol). Integration must include explicit semantic tests before going to UAT.
**Delivers:** Updated `lucy-lsd-engineer.md` agent with fragment search step, sequential injection protocol (one fragment at a time; discard if 0 solutions; log conflict and continue), DEFF/FEXP constraint inventory tracking in LSD file header, devils-advocate fragment file existence check pre-run; CASE-PROGRESS.md showing fragment search results per iteration
**Addresses:** Table stakes #6 (agent integration), pitfall #4 (DEFF semantics with worked examples and smoke test), pitfall #5 (conflict detection and discard protocol)
**Avoids:** Simultaneous multi-fragment injection without individual validation; agent halting on 0-solution fragment conflict instead of discarding and continuing to next fragment

### Phase 6: Multi-Compound UAT

**Rationale:** Single-compound testing during development is insufficient to validate the fragment library's impact. The Sherlock paper claims 34/40 cases reduce to single solution after first fragment — lucy-ng needs comparable validation. UAT must test ibuprofen plus 4+ other compounds from Sherlock's test set. Note: ibuprofen may not benefit if the 4J HMBC problem (excluded correct structure) persists from v4.0.
**Delivers:** UAT results on 5+ compounds with solution counts before and after fragment injection; confirmation that fragment search finds structurally plausible fragments for each compound; identification of any remaining failure modes (4J problem compounds vs. fragment-limitation compounds); go/no-go for v5.0 release
**Addresses:** Table stakes #7 (multi-compound UAT)

### Phase Ordering Rationale

- Phase 1 before Phase 2: storage schema must exist before extraction writes data
- Phase 2 before Phase 3: SSC table must be populated before search engine is testable
- Phases 3 and 4 can run in parallel: search engine and DEFF formatter are independent modules; both depend only on the `SSCMatch` Pydantic model from Phase 1
- Phase 5 must wait for Phase 4: agent integration needs the complete CLI pipeline (search + formatter) to be validated with real LSD smoke tests
- Phase 6 must wait for Phase 5: full end-to-end pipeline before UAT is meaningful

### Research Flags

Phases needing deeper research during planning:
- **Phase 2 (Extraction):** Validate 2 ppm bin size empirically on a 1K compound sample before committing to full 24M extraction. This is an unrecoverable decision if wrong.
- **Phase 4 (DEFF Formatter):** LSD fragment file internal format (SSTR/LINK notation) is MEDIUM confidence. Needs LSD manual appendix A4 verification or working test case before implementing serialization. The fragment search pipeline works without this — only the LSD injection step requires it.

Phases with standard patterns (no additional research needed):
- **Phase 1 (Schema):** Follows existing `migrate_v5_to_v6` pattern exactly. Standard SQLite schema migration. Two new tables, one new foreign key, one migration function.
- **Phase 3 (Search Engine):** Bitset AND pre-screening and DEV/AVGDEV fine matching are fully specified in the Wenk thesis. All algorithm parameters are from primary sources with HIGH confidence.
- **Phase 5 (Agent Integration):** lsd-engineer workflow change is a minimal addition to an existing documented workflow. Semantic validation (DEFF vs DEFF NOT) requires a smoke test but not research.
- **Phase 6 (UAT):** Execution and measurement, not research.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All dependencies verified against official docs; no new packages required; `FindAtomEnvironmentOfRadiusN`, `PathToSubmol`, NumPy bitwise ops all confirmed in official documentation for installed versions |
| Features | HIGH | Primary source is Wenk PhD thesis with full algorithmic specification; all algorithm parameters (bin size, thresholds, sphere radius, bond-preservation rules, fragment ranking) sourced directly from thesis |
| Architecture | HIGH | Existing codebase directly inspected for all integration points (schema.py, manager.py, stats_generator.py, cli/*.py); patterns confirmed working in production; data flow matches established patterns throughout |
| Pitfalls | MEDIUM-HIGH | Extraction pitfalls derived from existing HOSE stats generator experience (same code patterns, same runtime characteristics); DEFF semantic pitfall derived from agent behavior patterns observed in v3.0/v4.0 UAT; DEFF fragment file format is the one MEDIUM-confidence pitfall |

**Overall confidence:** HIGH

### Gaps to Address

- **DEFF fragment file internal format (SSTR/LINK notation):** Confirmed at MEDIUM confidence from Sherlock thesis description. Exact LSD syntax for atom definitions inside a DEFF-referenced .lsd fragment file must be validated against LSD manual or working test case before implementing `DEFFFormatter`. If the format differs from assumed SSTR/LINK, the formatter implementation must change. Handle at start of Phase 4 — this is the highest-risk open question.

- **Fingerprint bin size validation:** 2 ppm is from Sherlock thesis and is strongly recommended, but must be validated empirically on a 1K compound sample before full extraction. If recall at 2 ppm is unexpectedly low (due to COCONUT vs NMRShiftDB spectrum quality differences), bin size needs adjustment. Handle at start of Phase 2 before committing full 24M extraction.

- **Effective SSC count from lucy-ng database:** Sherlock extracted 24.5M SSCs from 892K compounds. Lucy-ng has 928K compounds but only 99.7% have atom-indexed shifts. Compounds without atom mapping (estimated 30-40% from NMRShiftDB inconsistencies) cannot yield valid SSCs. Final SSC count may be noticeably below 24.5M. This affects search effectiveness but does not change the implementation approach. Log skipped compound count during extraction for post-hoc diagnosis.

- **4J HMBC interaction with fragment constraints (ibuprofen):** The v4.0 UAT shows ibuprofen's correct structure may not appear in the LSD solution set at all (excluded by 4J HMBC constraints interpreted as 3J). Fragment constraints cannot recover a correct structure that was never generated. Fragment library (v5.0) and 4J detection (future milestone) must be treated as complementary. UAT should test non-4J compounds first to validate fragment library impact independently.

## Sources

### Primary (HIGH confidence)
- Wenk, M. (2023). PhD Thesis, Friedrich-Schiller-Universitat Jena — full algorithmic specification for SSC extraction, bond-preservation rules, fingerprint design (256 bits, 2 ppm bins), DEV/AVGDEV thresholds, fragment ranking rules, and impact statistics (34/40 single solution result); the authoritative source for all algorithm parameters
- `background/sherlock-analysis.md` — project-specific synthesis of Sherlock SSC design and impact on lucy-ng (24.5M SSC count, DEFF/FEXP injection mechanism)
- `src/lucy_ng/database/schema.py` — v6 schema confirmed; migration pattern for v7 extension
- `src/lucy_ng/database/manager.py` — `iter_compounds_with_shifts`, `set_checkpoint`, `get_checkpoint` methods confirmed present
- `src/lucy_ng/prediction/stats_generator.py` — `ResumableHOSEStatsGenerator` checkpoint pattern; HOSE regen timing (8h39m reference) used to project SSC extraction time
- RDKit 2025.09.5 docs — `FindAtomEnvironmentOfRadiusN`, `PathToSubmol` usage pattern confirmed; `rdSubstructLibrary` evaluated and rejected
- NumPy 2.4 Manual — `packbits`, uint8 bitwise operations confirmed
- LSD Manual (nuzillard.github.io) — `DEFF`/`FEXP` syntax confirmed: `DEFF F_n_ <path>`, `FEXP "F1 AND F2"` pattern
- Lucy-ng SQLite database live query — atom_index coverage: 99.7% (23,994,980 / 24,063,169 shifts), all 928,443 compounds present

### Secondary (MEDIUM confidence)
- Sherlock PMC paper (PMC9920390) — 256-bit bitstring fingerprint description: "each fragment has a bit string representation... screened via a bit string comparison where all set bits of a fragment have to be present in the query bitset"
- Sherlock GitHub (casekit library, michaelwenk/casekit) — Java SSC extraction implementation reference; not directly inspected, inferred from thesis
- `~/.claude/agents/lucy-lsd-engineer.md` — current lsd-engineer workflow; v3.0/v4.0 UAT findings on DEFF NOT badlist behavior

### Tertiary (LOW confidence, explicitly rejected for this use case)
- FPSim2 — HDF5-based Tanimoto similarity tool; wrong semantic (containment not similarity) and adds HDF5 dependency
- rdSubstructLibrary — SMARTS-based substructure screening; wrong semantic (spectral match not SMARTS query)
- BRICS fragmentation — retrosynthetic cuts; wrong semantic (need atom-environment spheres)

---
*Research completed: 2026-02-19*
*Ready for roadmap: yes*
*Next step: gsd-roadmapper agent uses this SUMMARY.md to structure v5.0 milestone roadmap*

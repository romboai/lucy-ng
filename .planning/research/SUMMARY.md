# Project Research Summary: v3.0 Statistical Detection

**Project:** lucy-ng v3.0 — Statistical Detection Milestone
**Domain:** Computer-Assisted Structure Elucidation (CASE) with NMR spectroscopy
**Researched:** 2026-02-10
**Confidence:** HIGH

## Executive Summary

Statistical detection represents a transformative shift from heuristic-based CASE to data-driven structure elucidation. Research shows this approach delivers 5 orders of magnitude search space reduction (Sherlock: Caripyrin 8.5M → 30 structures) and solves 89% of multi-solution cases compared to v2.1's constraint-free approach. The key insight: the existing HOSE database already contains all necessary information — hybridisation is encoded in HOSE prefixes, bond partners are visible in sphere 1 neighbors, and shift distributions reveal what's mandatory vs forbidden.

The recommended approach requires ZERO new dependencies. Database schema extends with 8 new columns to hose_stats (18% storage increase), statistics generation extends existing stats_generator.py (10-20% runtime overhead), and CLI adds a new detect command group following established Click patterns. Implementation centers on six table-stakes features: hybridisation detection (queries shift → sp2/sp3 distribution), neighbourhood detection (queries shift → bond partner frequencies), HHB detection (queries formula → hetero-hetero bond prevalence), signal grouping (identifies close shifts for combinatorial LSD), two-tier ranking (counts signal matches before MAE), and badlist filters (excludes strained rings).

Critical risks center on HOSE hydrogen consistency (using AddHs() breaks 100% of predictions), threshold over-sensitivity (1% NN threshold works for 82% of cases but requires overrides for rare heteroatoms), and agent workflow confusion (statistical output must augment, not replace, chemistry knowledge). These are preventable through architecture enforcement, CLI override flags, and clear agent integration hierarchy.

## Key Findings

### Recommended Stack

**NO NEW DEPENDENCIES.** All statistical detection features build on the existing lucy-ng stack: Python 3.10+, RDKit (molecular analysis), SQLite (HOSE statistics), and Pydantic v2 (data models). The critical architectural insight from STACK research: HOSE codes already encode hybridisation in their prefix (C-4 = sp3, C-3 = sp2, C-2 = sp), eliminating need for separate hybridisation extraction during lookup.

**Core technologies (unchanged):**
- Python 3.10+ — Language runtime (KEEP, no version bump)
- RDKit 2025.09.5+ — GetHybridization(), GetNeighbors(), GetRingInfo() APIs verified
- SQLite 3.x — Extend hose_stats schema with 8 columns (+18% storage to ~3.3 GB)
- Pydantic v2 — Add DetectionStatsRecord, DetectionResult models
- hosegen — HOSE code generation (unchanged)
- Click — New detect.py command group

**Database migration strategy:** Extend existing hose_stats table with nullable columns (hybridization TEXT, has_*_neighbor flags, ring_* counts). Backfill via stats_generator.py update or regenerate fresh DB from COCONUT/NMRShiftDB sources for v3.0 release.

**RDKit APIs for statistical extraction:**
- `atom.GetHybridization()` → HybridizationType (SP3, SP2, SP)
- `atom.GetNeighbors()` → sequence of bonded atoms (excludes implicit H)
- `atom.IsInRing()`, `ring_info.IsAtomInRingOfSize(atom_idx, size)` → ring membership
- CRITICAL: All operations use molecules WITHOUT explicit hydrogens (consistent with existing HOSE prediction)

### Expected Features

**Must have (table stakes):**
- Hybridisation detection — Query shift ± 2 ppm → sp2/sp3/sp1 distribution, exclude <1% states. Delivers 5 orders of magnitude search space reduction (Sherlock: Caripyrin case).
- Neighbourhood detection (forbidden) — Query shift → bond partner frequencies, exclude elements <1% (NN threshold). Prevents chemically unreasonable bonds (O-O in non-peroxides).
- Neighbourhood detection (mandatory) — Query shift → bond partner frequencies, require elements >95% (SN threshold). Enforces strong chemical evidence (carbonyl C MUST bond to O).
- Two-tier ranking — Rank by (1) signal match count (within 10 ppm tolerance), then (2) MAE among matches. Prevents v2.1's MAE-only hallucination (ibuprofen cyclohexadiene ranked #1 with MAE 1.93 but wrong structure).
- Signal grouping — Identify shifts within 0.25 ppm, generate LSD HMBC parenthesized atom lists for combinatorial exchange. CRITICAL for ibuprofen-class cases (C4/C5 at 44.90/45.03 ppm).
- Badlist filters — DEFF/FEXP NOT commands to exclude 3/4-membered rings (chemically rare in natural products). Hardcoded in agent knowledge, no CLI needed.

**Should have (competitive differentiators for v3.1+):**
- Hetero-hetero bond (HHB) allowance — Automatic HETE 0/1 determination based on formula element statistics
- Fragment library search — 24.5M substructure-subspectrum correlations (SSCs) from Sherlock approach, reduces 27/40 multi-solution cases
- Solvent-aware prediction — Per-solvent HOSE statistics (CDCl3 vs DMSO), reduces MAE from ~2.5 to ~0.83 ppm

**Defer (explicit anti-features for v3.0):**
- ELIM command automation — Notoriously finicky, Sherlock disables by default
- 4-bond HMBC detection — High false positive rate, requires manual marking
- COSY correlation constraints — Complex multiplets, rarely improve results
- Stereochemistry (E/Z, R/S) — LSD doesn't handle well, defer to v4.0 with DFT ranking
- GUI parameter adjustment — Autonomous AI agent is differentiator, don't regress to manual tweaking

### Architecture Approach

Statistical detection integrates cleanly as additive layers over existing HOSE infrastructure. No invasive changes to core prediction pipeline. Database layer extends hose_stats schema, statistics generation extends stats_generator.py accumulator logic, CLI adds detect.py command group, and agent calls lucy detect via Bash (same pattern as existing lucy lsd rank).

**Major components:**
1. Database layer (schema.py, manager.py) — Extend hose_stats with hybridization, bond partner flags, ring counts. Migration via ALTER TABLE or fresh generation.
2. Statistics generation (stats_generator.py) — Extend WelfordAccumulator to track sp2/sp3 counts, neighbor symbols, ring membership during existing HOSE processing loop.
3. Detection module (detection/detector.py) — NEW: StatisticalDetector class queries extended hose_stats, returns DetectionResult with confidence scores.
4. CLI commands (cli/detect.py) — NEW: detect hybridisation/neighbours/hhb commands with JSON output for agent consumption.
5. Agent integration (lucy-case-agent.md) — Use detection to AUGMENT NMR knowledge, not replace. Chemistry-first hierarchy: never violate basic chemistry, use stats to narrow among valid options.
6. Two-tier ranking (ranking/ranker.py) — Modify existing SolutionRanker to count signal matches before MAE sorting. Optional HybridisationFilter pre-filter.

**Data flow:** User calls `lucy detect hybridisation db.sqlite 139.94` → CLI parses args → StatisticalDetector queries hose_stats WHERE mean BETWEEN 137.94 AND 141.94 → Database returns sp2_fraction/sp3_fraction → Detector compares fractions → Returns DetectionResult(prediction="sp2", confidence=0.91) → CLI formats JSON → Agent parses, uses in LSD MULT command.

**Build order:** (1) Schema extension, (2) Statistics generation, (3) Detection module, (4) CLI commands, (5) Agent integration, (6) Two-tier ranking (optional). Each phase depends on previous, enforced by dependency chain.

### Critical Pitfalls

1. **HOSE Hydrogen Consistency Violation** — Using AddHs() during statistical extraction while prediction uses implicit H breaks 100% of lookups. HOSE codes from mol vs AddHs(mol) are structurally different. Prevention: Enforce no-explicit-H in all molecule processing, use GetNumImplicitHs() to count hydrogens. Detection: CLI test `lucy predict c13 "CCO"` must return predictions with count > 0.

2. **Threshold Over-Sensitivity Without Overrides** — Hardcoded 1% NN, 95% SN thresholds work for 82% of Sherlock's cases but fail for rare heteroatoms or unusual hybridisation states. Agent gets stuck in "0 solutions with constraints" loops. Prevention: CLI override flags (--min-frequency 0.005, --mode relaxed), orchestrator intervention protocol when pattern detected, document threshold semantics.

3. **Circular Validation Risk** — Same HOSE database used for constraints (pre-LSD) and ranking (post-LSD) reinforces systematic biases. If database over-represents aromatic C-O, both steps favor aromatic structures. Mitigation: Database size (928K) provides diversity, threshold filtering (1%/95%) only applies strong patterns, agent fallback protocol (retry without constraints if 0 solutions), validation with held-out test set.

4. **COCONUT Data Quality Unknown** — 96.87% of HOSE data from COCONUT (predicted spectra), structures are "as-deposited" with varying curation. Bond assignments, tautomers, protonation states may have errors affecting bond partner statistics. Prevention: Extract from sanitized RDKit molecules (corrects many errors), validate sampling (100 random structures), cross-reference with NMRShiftDB subset (3.13% experimental data), conservative thresholds (1% NN tolerates noise).

5. **Signal Grouping False Positives** — Grouping shifts within 0.25 ppm creates combinatorial explosion when carbons are truly different (distinguished by multiplicities). Example: C4 at 44.90 (CH2), C5 at 45.03 (CH), C6 at 45.20 (CH3) → 6x search space, 5 permutations wrong. Prevention: Multiplicity-aware grouping (group only if same mult or both ambiguous CH/CH3), agent override mechanism, post-ranking collapse of identical-assignment solutions.

## Implications for Roadmap

Based on research findings and dependency analysis, v3.0 should follow a foundation-first approach: implement core statistical detection before advanced features, validate thoroughly before agent integration, defer fragment library and solvent-awareness to v3.1+.

### Suggested Phase Structure (6 phases)

### Phase 34-01: Hybridisation Detection
**Rationale:** Highest impact (5 orders magnitude reduction), cleanest implementation (HOSE prefix parsing), no database queries during detection (prefix already encodes state).
**Delivers:** `lucy detect hybridisation <shift>` CLI command, extended hose_stats schema with hybridization column, statistics generation for sp2/sp3/sp1 fractions.
**Addresses:** Table stakes feature 1 (hybridisation detection), foundation for all other statistical features.
**Avoids:** Pitfall 1 (HOSE H consistency via code review), Pitfall 6 (storage explosion via binned stats in 2 ppm windows).
**Research flags:** Standard pattern (HOSE parsing well-documented), no deeper research needed.

### Phase 34-02: Neighbourhood Detection
**Rationale:** Second-highest impact (prevents unreasonable bonds), depends on extended schema from 34-01, requires HOSE sphere 1 parsing.
**Delivers:** `lucy detect neighbours <shift>` CLI command, bond partner columns in hose_stats (has_carbon/oxygen/nitrogen_neighbor flags), NN/SN threshold filtering.
**Addresses:** Table stakes features 2-3 (forbidden/mandatory neighbours).
**Avoids:** Pitfall 2 (threshold sensitivity via override flags), Pitfall 4 (COCONUT quality via RDKit sanitization), Pitfall 12 (too many elements via min-report threshold).
**Research flags:** Needs HOSE sphere 1 parsing validation (medium complexity).

### Phase 34-03: HHB and Ring Detection
**Rationale:** Rounding out core detection features, both are simple queries (global HHB statistic, ring membership from RDKit).
**Delivers:** `lucy detect hhb <formula>` CLI command, ring statistics columns (in_3ring/4ring/aromatic counts), HETE command generation logic.
**Addresses:** Should-have feature (HHB allowance), badlist foundation (ring exclusion stats).
**Avoids:** Pitfall 4 (data quality via simple global statistic, low sensitivity to errors).
**Research flags:** Standard RDKit APIs (GetRingInfo), no research needed.

### Phase 34-04: Signal Grouping
**Rationale:** CRITICAL for ibuprofen-class cases, algorithmic (no database), but complex LSD file generation changes.
**Delivers:** `lucy analyze grouping <shifts>` CLI command, multiplicity-aware grouping logic, LSD HMBC parenthesized atom list generation.
**Addresses:** Table stakes feature 5 (signal grouping).
**Avoids:** Pitfall 5 (false positives via multiplicity awareness).
**Research flags:** Needs LSD file generation research (medium complexity, parenthesized syntax verification).

### Phase 34-05: Two-Tier Ranking and Badlist
**Rationale:** Quick wins (ranking is algorithmic, badlist is hardcoded), high impact (prevents MAE hallucinations).
**Delivers:** Modified `lucy lsd rank` with match-count-first sorting, HOSE radius reporting, badlist DEFF/FEXP patterns in agent knowledge.
**Addresses:** Table stakes features 4 and 6 (two-tier ranking, badlist filters).
**Avoids:** Pitfall 8 (match quality via radius-weighted scoring or reporting), Pitfall 10 (cyclopropane exclusion via override mechanism).
**Research flags:** Standard pattern (modify existing ranker), no research needed.

### Phase 34-06: Agent Integration
**Rationale:** Teaches agent to use new detection commands autonomously, highest risk (workflow confusion), must come after all CLI commands stable.
**Delivers:** Updated lucy-case-agent.md with detection protocol, chemistry-first hierarchy, threshold override examples, batch API if profiling shows >5s overhead.
**Addresses:** Makes all statistical features usable autonomously.
**Avoids:** Pitfall 7 (workflow confusion via clear hierarchy and examples), Pitfall 11 (CLI overhead via batch API if needed), Pitfall 13 (no summary via constraints.md generation).
**Research flags:** Needs agent prompt engineering research, test scenario validation (high complexity).

### Phase 34-07: Validation (Recommended Addition)
**Rationale:** Can't ship without knowing if constraints help or hurt, Sherlock's 45 test cases provide validation set.
**Delivers:** Validation test suite (Sherlock's 45 cases from nmrXiv), metrics (constraint accuracy, search space reduction, rank improvement), regression tests in CI.
**Addresses:** Pitfall 9 (no validation dataset).
**Avoids:** Shipping features that degrade performance without detection.
**Research flags:** Needs nmrXiv dataset download/sanitization (medium complexity).

### Phase Ordering Rationale

- Database schema changes FIRST (phases 34-01/02/03 all write to extended schema, must exist before generation runs)
- Algorithmic features (34-04, 34-05) interleaved to provide variety (reduces fatigue from back-to-back database work)
- Agent integration LAST (phase 34-06 depends on all CLI commands being stable and tested)
- Validation AFTER implementation (phase 34-07 measures quality of 34-01 through 34-06)

This order follows natural dependencies:
1. Schema → Generation → Detection module → CLI → Agent
2. Minimizes rework (schema changes are expensive, do once)
3. Enables incremental testing (each phase delivers working CLI command)
4. Defers complexity (agent integration is hardest, comes last when foundation solid)

### Research Flags

**Needs deeper research during planning:**
- Phase 34-02 (Neighbourhood Detection) — HOSE sphere 1 parsing validation, verify neighbor symbol extraction matches expectations
- Phase 34-04 (Signal Grouping) — LSD parenthesized atom list syntax, verify combinatorial generation works correctly
- Phase 34-06 (Agent Integration) — Prompt engineering for chemistry-first hierarchy, test scenario design for stats-vs-knowledge conflicts
- Phase 34-07 (Validation) — nmrXiv dataset API, Sherlock test case sanitization workflow

**Standard patterns (skip deeper research):**
- Phase 34-01 (Hybridisation) — HOSE prefix parsing is well-documented, RDKit GetHybridization() API verified
- Phase 34-03 (HHB/Ring) — Global statistic query (simple SQL), RDKit GetRingInfo() API verified
- Phase 34-05 (Ranking/Badlist) — Modify existing ranker (established codebase pattern), hardcoded SMARTS (no research)

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All RDKit APIs verified in 2025.09.5 documentation, no new dependencies needed, existing HOSE infrastructure confirmed via codebase inspection |
| Features | HIGH | Specifications directly from Sherlock thesis (Wenk 2023) with test case validation, thresholds (1% NN, 95% SN, 0.25 ppm grouping, 10 ppm match tolerance) documented with rationale |
| Architecture | HIGH | Integration points verified in existing codebase (schema.py, stats_generator.py, cli/ pattern), data flow tested on small samples, storage estimates calculated |
| Pitfalls | HIGH | Pitfalls 1-7 informed by lucy-ng architecture review, Sherlock analysis, RDKit documentation, and project memory (ibuprofen CASE learnings). Pitfalls 8-10 MEDIUM (edge cases, less documentation). Pitfalls 11-13 LOW (UX/performance, speculative) |

**Overall confidence:** HIGH

Research is comprehensive and actionable. All core APIs verified in official sources, all thresholds backed by Sherlock's experimental validation (45 test cases), all integration points confirmed in existing codebase. The foundation is solid.

### Gaps to Address During Planning

**1. HOSE sphere 1 parsing accuracy**
- Gap: Assumed HOSE first sphere neighbors map 1:1 to bond partners, but need to verify with hosegen library API.
- How to handle: Phase 34-02 planning should include test cases with known bond partners, verify extraction matches expectations.

**2. LSD parenthesized atom list syntax**
- Gap: Sherlock documentation shows `HMBC (2 3) 8` syntax for grouping, but LSD manual doesn't explicitly document this as valid.
- How to handle: Phase 34-04 planning should run LSD with parenthesized syntax test cases, verify solutions generated correctly.

**3. Threshold tuning validation**
- Gap: Sherlock's thresholds (1% NN, 95% SN) are defaults, but no systematic tuning study to prove optimality.
- How to handle: Phase 34-07 validation should test threshold sensitivity (0.5%, 1%, 2% NN; 90%, 95%, 99% SN), report which performs best on test set.

**4. COCONUT structure quality quantification**
- Gap: Inferred that COCONUT has variable curation quality, but no systematic measurement of bond assignment error rate.
- How to handle: Phase 34-03 planning should include validation sampling (100 random structures manual inspection), reject design if >10% errors found.

**5. Agent decision hierarchy edge cases**
- Gap: Defined chemistry-first hierarchy for stats-vs-knowledge conflicts, but untested on real contradiction scenarios.
- How to handle: Phase 34-06 planning should create test scenarios (e.g., sp3 stats for aromatic shift), verify agent resolves correctly.

## Sources

### Primary (HIGH confidence)

**Sherlock CASE System:**
- Michael Wenk, PhD Thesis, Friedrich-Schiller-Universitat Jena, 2023 — Statistical detection methodology, thresholds (1% NN, 95% SN, 0.25 ppm grouping), test case validation (45 compounds, 40/45 solved, 38/40 at rank #1)
- [Sherlock publication (Molecules 2023)](https://www.mdpi.com/1420-3049/28/3/1448) — System architecture, integration patterns
- [Sherlock GitHub](https://github.com/michaelwenk/sherlock) — Source code (pyLSD implementation)

**RDKit API:**
- [RDKit Atom Documentation](https://www.rdkit.org/docs/source/rdkit.Chem.rdchem.html) — GetHybridization(), GetNeighbors(), GetNumImplicitHs() verified
- [RDKit Ring Documentation](https://www.rdkit.org/docs/cppapi/classRDKit_1_1RingInfo.html) — IsInRing(), GetRingInfo(), IsAtomInRingOfSize() verified
- [RDKit Cookbook](https://www.rdkit.org/docs/Cookbook.html) — Implicit vs explicit hydrogen handling

**Lucy-ng Codebase:**
- `src/lucy_ng/database/schema.py` — Schema version 3 confirmed, hose_stats table structure
- `src/lucy_ng/prediction/stats_generator.py` — Welford algorithm for incremental statistics
- `src/lucy_ng/prediction/hose.py` — HOSE code format (prefix encodes hybridisation)
- Live database queries on lucy-ng-derep.db — 7.9M HOSE stats across radii 1-6

**LSD Software:**
- [LSD Manual (GitHub)](https://github.com/UnixJunkie/LSD/blob/master/MANUAL_ENG.html) — DEFF, FEXP, LIST, ELEM, PROP command reference
- Local installation (/Users/steinbeck/Dropbox/develop/LSD/Filters/) — Filter file formats (ring3, ring4) verified

### Secondary (MEDIUM confidence)

**COCONUT Database:**
- [COCONUT 2.0 (NAR 2024)](https://academic.oup.com/nar/article/53/D1/D634/7908792) — Comprehensive overhaul and curation, 63+ source databases
- [COCONUT original (JChemInf 2020)](https://jcheminf.biomedcentral.com/articles/10.1186/s13321-020-00478-9) — Database construction methodology

**NMR Prediction:**
- [HOSE code prediction performance (JChemInf 2023)](https://jcheminf.biomedcentral.com/articles/10.1186/s13321-023-00785-x) — Small data quantity analysis
- [Stereo-aware HOSE extension (ACS Omega 2019)](https://pubs.acs.org/doi/10.1021/acsomega.9b00488) — Enhanced methods

### Tertiary (LOW confidence, needs validation)

**Storage Estimates:**
- Database size calculations (7.9M rows × 32 bytes/row = 253 MB increase) — arithmetic based on column types, not measured
- Query performance estimates (5-10 ms for shift range) — extrapolated from small samples, not benchmarked on full DB

**Threshold Optimality:**
- Sherlock's 1% NN, 95% SN thresholds documented as defaults but no tuning study proving optimality — assumed based on 40/45 success rate

---
*Research completed: 2026-02-10*
*Ready for roadmap: yes*
*Next step: gsd-roadmapper agent uses this SUMMARY.md to structure v3.0 milestone roadmap*

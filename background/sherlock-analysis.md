# Sherlock CASE System: Deep Analysis Report

**Source:** Michael Wenk, PhD Thesis, Friedrich-Schiller-Universitat Jena, 2023
**Initial analysis:** 2026-02-10
**Updated:** 2026-02-19 (post v4.0 gap closure assessment)
**Purpose:** Strategic reference for lucy-ng milestone planning

---

## 1. System Overview

Sherlock is an open-source, web-based CASE system built on a microservice architecture (Docker, Java/CDK backend, React frontend). It uses pyLSD/LSD for structure generation and a knowledge base of 892,841 compounds (COCONUT + NMRShiftDB).

**Performance:** 40/45 test cases solved (88.9%), 38/40 at rank #1, mean prediction deviation 0.83 ppm. Largest solved: Cucurbitacin E (C32H44O8, 40 heavy atoms, 2 seconds).

---

## 2. Component-by-Component Comparison (Post v4.0)

### 2.1 Knowledge Base

| Feature | Sherlock | lucy-ng | Status |
|---------|----------|---------|--------|
| Compound count | 892,841 (COCONUT + NMRShiftDB) | 928,443 | Comparable |
| HOSE code entries | ~6.3M (stereo-enhanced, explicit H) | 7.9M (standard, no explicit H) | Different approach |
| Fragment library (SSCs) | **24.5M** substructure-subspectrum correlations | **None** | **OPEN GAP** |
| Solvent tracking | Per-solvent statistics (CDCl3, DMSO, etc.) | None | Open gap |
| Storage | MongoDB + PostgreSQL | SQLite | Architectural difference |

### 2.2 Statistical Detection (Pre-LSD Constraint Generation)

| Feature | Sherlock | lucy-ng | Status |
|---------|----------|---------|--------|
| Hybridisation detection | Automatic from KB (sp1/sp2/sp3 frequencies per shift) | `lucy detect hybridisation` — v3.0 | **CLOSED** |
| Neighbourhood detection | Automatic (forbidden < 1%, mandatory > 95%) | `lucy detect neighbours` — v3.0 | **CLOSED** |
| Hetero-hetero bond allowance | Automatic (1% threshold on bond pair statistics) | `lucy detect hhb` — v3.0 | **CLOSED** |
| Signal grouping | Automatic (0.25 ppm tolerance for 13C, 0.02 ppm for 1H) | `lucy analyze grouping` — v3.0 | **CLOSED** |
| Combinatorial atom exchange | Automatic in HMBC/COSY (first axis) | Agent writes parenthesized notation — v3.0/v4.0 | **CLOSED** |

### 2.3 Structure Generation

| Feature | Sherlock | lucy-ng | Status |
|---------|----------|---------|--------|
| Engine | pyLSD (Python wrapper) -> LSD (C) | LSD directly | Minor difference |
| MULT commands | Auto-generated from detection | Agent writes from detection results | Comparable |
| HSQC before HMBC | Enforced | Agent knows this rule | Comparable |
| BOND commands | From mandatory neighbours + detection | Agent writes from detection | Comparable |
| LIST/PROP commands | Auto-generated from neighbourhood stats | Agent writes from detection | Comparable |
| ELIM | Disabled by default, manual activation | Disabled by default | Same |
| 4-bond HMBC | Supported (manual marking) | Supported (manual) | Same limitation |
| HETE command | Auto-generated from HHB detection | Agent writes from `lucy detect hhb` | **CLOSED** |
| Goodlist fragments (DEFF/FEXP) | From fragment search | **None** | **OPEN GAP** |
| Badlist filters | 3/4-membered ring filters | DEFF NOT via agent — v3.0 | **CLOSED** |
| COSY correlations | Used in LSD commands | **Not used** | **OPEN GAP** |
| Combinatorial pyLSD files | Multiple files for atom exchange | Single file with parenthesized notation | Minor gap |
| Maximum runtime | 3 hours (configurable) | No timeout | Minor gap |

### 2.4 Fragment Search

| Feature | Sherlock | lucy-ng | Status |
|---------|----------|---------|--------|
| Fragment library size | 24.5M SSCs | **None** | **OPEN GAP** |
| Pre-screening | Bitset fingerprints (256-bit, 2 ppm bins) | N/A | **OPEN GAP** |
| Fine matching | Spectral comparison with DEV/AVGDEV | N/A | **OPEN GAP** |
| Fragment application | As DEFF/FEXP goodlist constraints | N/A | **OPEN GAP** |
| Impact | Reduced 27/40 multi-solution cases; 34/40 to single solution | N/A | **OPEN GAP** |

### 2.5 Spectral Prediction & Ranking

| Feature | Sherlock | lucy-ng | Status |
|---------|----------|---------|--------|
| HOSE code type | Stereo-enhanced (Kuhn et al.), explicit H | Standard, no explicit H | Different approach |
| Max sphere | 6 | 6 | Same |
| Fallback strategy | 6 -> 5 -> 4 -> ... -> 1 | Same | Same |
| Prediction method | Mean of medians per solvent group | Mean of all values | Minor gap |
| Ranking criterion #1 | Number of matching signals | Match count (descending) — v3.0 | **CLOSED** |
| Ranking criterion #2 | Average deviation | MAE (ascending) — v3.0 | **CLOSED** |
| Aromatic ring sanity check | None | Post-ranking verification — v4.0 | **lucy-ng advantage** |
| Mean deviation achieved | 0.83 ppm (40 cases) | ~2.5 ppm (limited testing) | Performance gap |

### 2.6 Constraint Persistence & Quality

| Feature | Sherlock | lucy-ng | Status |
|---------|----------|---------|--------|
| Constraint tracking | Implicit (auto-generated each run) | JSON inventory in LSD headers — v4.0 | **CLOSED** |
| Pre-run validation | None | Devils-advocate gate — v4.0 | **lucy-ng advantage** |
| Peer review | None (single system) | 5-agent team with real-time feedback — v4.0 | **lucy-ng advantage** |
| Aromatic ring awareness | None | nmr-chemist flags, solution-analyst verifies — v4.0 | **lucy-ng advantage** |

### 2.7 User Interface & Workflow

| Feature | Sherlock | lucy-ng | Status |
|---------|----------|---------|--------|
| Interface | Web-based (NMRium for spectrum display) | CLI + AI agent | Architectural difference |
| Spectrum processing | NMRium (manual peak picking) | Automated CLI peak pickers | **lucy-ng advantage** |
| Peak assignment | Manual/semi-automatic | Automated by AI agent | **lucy-ng advantage** |
| MCD visualization | Interactive graph | None | UI gap (not critical) |
| Parameter adjustment | GUI controls | Agent decides autonomously | **lucy-ng advantage** |
| Unattended operation | No (requires human interaction) | Yes (fully autonomous) | **lucy-ng advantage** |

---

## 3. Gap Status Summary (Post v4.0)

### CLOSED Gaps

| Gap | Closed In | How |
|-----|-----------|-----|
| Statistical detection (hybridisation) | v3.0 | `lucy detect hybridisation` queries 7.9M HOSE stats |
| Statistical detection (neighbours) | v3.0 | `lucy detect neighbours` with forbidden/mandatory thresholds |
| Statistical detection (HHB) | v3.0 | `lucy detect hhb` from bond_pair_stats table |
| Signal grouping + combinatorial exchange | v3.0 | `lucy analyze grouping` + parenthesized LSD notation |
| Two-tier ranking | v3.0 | Match count primary, MAE secondary |
| Badlist filters (strained rings) | v3.0 | DEFF NOT 3/4-membered ring exclusion in agent knowledge |
| Constraint persistence across iterations | v4.0 | JSON inventory in LSD headers, DA reconciliation |
| Agent constraint-loss bugs (5 bugs) | v4.0 | Team architecture with lsd-engineer + devils-advocate |

### OPEN Gaps (Prioritized)

#### Priority 1: Fragment Library (highest impact, largest effort)

**What Sherlock does:** Maintains 24.5M substructure-subspectrum correlations (SSCs). For each LSD solution set, searches for fragments matching the experimental spectrum using:
1. Fast bitset pre-screening (256-bit fingerprints, 2 ppm bins, Boolean AND)
2. Fine spectral matching (DEV/AVGDEV thresholds)

Matching fragments are injected as DEFF/FEXP goodlist constraints, dramatically reducing solution counts.

**Impact:** Reduced 27/40 multi-solution cases. Cases like Allantofuranone went from 336 solutions to 1 with a single fragment. Overall, 34/40 cases converged to a single solution after fragment application. This is what transforms Sherlock from "reasonable CASE system" to "34/40 single-solution system."

**Implementation path:**
1. Build SSC extraction pipeline from existing 928K compound database
2. Create 256-bit bitset fingerprint index (2 ppm bins)
3. Add CLI command: `lucy fragment search --shifts "..." --formula C13H18O2`
4. Convert matching fragments to DEFF/FEXP commands for LSD input
5. Integrate into lsd-engineer agent workflow

**Effort:** High (likely a full milestone). Requires new database tables, extraction pipeline, fingerprint indexing, search algorithm, CLI commands, and agent integration.

#### Priority 2: Statistical 4J HMBC Coupling Detection

**Not in Sherlock either** (supports manual 4J marking only), but v4.0 UAT proved this is essential for aromatic compounds.

**Problem:** Three W-pathway 4J couplings through ibuprofen's para-disubstituted ring silently excluded the correct structure. Unlike 7J/8J correlations (which cause zero solutions and are caught), 4J correlations produce wrong structures that satisfy the constraint as 3J — they silently exclude the correct answer.

**Implementation path:**
1. Build database of 4-bond coupling probabilities per atom-type pair and chemical shift range
2. Flag HMBC correlations where 4J probability exceeds threshold
3. Agent marks suspect correlations for optional inclusion/exclusion
4. Especially important for aromatic compounds with benzylic substituents

**Effort:** Medium. Requires analysis of coupling path statistics from compound database, new CLI command, agent integration.

#### Priority 3: COSY Correlation Integration

**What Sherlock does:** Uses COSY correlations in LSD commands (3-4 bond H-H correlations). The thesis appendix A4 shows Sherlock's ibuprofen LSD file includes 10 COSY commands providing independent connectivity confirmation.

**What lucy-ng does:** Can read and pick COSY spectra but doesn't use them in LSD constraint generation.

**Implementation path:**
1. Extend lsd-engineer knowledge with COSY command syntax
2. NMR-chemist includes COSY peaks in setup message
3. Agent writes COSY commands in LSD file

**Effort:** Low-medium. Infrastructure exists (peak picking works), needs agent knowledge update and workflow integration.

#### Priority 4: NP-Likeness Scoring

**Thesis mention:** Ertl NP-likeness score (ref 135, 136) for solution filtering.

**Implementation path:** RDKit has `NaturalProductLikeness` built in. Add as post-ranking filter to deprioritize non-NP-like solutions.

**Effort:** Low. Minimal engineering, cheap quality win.

#### Priority 5: Solvent-Aware Prediction

**What Sherlock does:** Tracks per-solvent statistics and computes mean-of-medians per solvent group. May contribute to Sherlock's 0.83 ppm mean deviation vs lucy-ng's ~2.5 ppm.

**Implementation path:** Add solvent column to HOSE stats table, regenerate database with solvent tracking, query by solvent when known.

**Effort:** Medium. Schema change + full database regeneration (~8h).

---

## 4. Ibuprofen Case Comparison

| Metric | Sherlock | lucy-ng v3.0 | lucy-ng v4.0 |
|--------|----------|--------------|--------------|
| Formula | C13H18O2 | C13H18O2 | C13H18O2 |
| Solutions (no fragment) | 2 | 8 (wrong topology) | 7 (wrong topology) |
| Solutions (with fragment) | 1 | N/A | N/A |
| Correct structure found? | **YES** | **NO** | **NO** |
| Rank | #1 | #1 (hallucinated) | N/A (all wrong) |
| Average deviation | 0.28 ppm | 1.93 ppm (wrong structure) | N/A |
| COSY used? | Yes (10 commands) | No | No |
| Signal grouping | Automatic (C4/C5) | Detected, not applied | Applied (parenthesized notation) |
| Constraint persistence | N/A (single run) | Lost across iterations | **Maintained** (inventory) |
| Aromatic ring check | None | None | **Detected mismatch** |
| 4J HMBC handling | Manual marking | Not detected | Not detected |

**Root cause of lucy-ng failure (both versions):** 3 W-pathway 4J HMBC couplings through the aromatic ring enforce wrong connectivity, excluding the correct structure. Fragment library and 4J detection would both address this.

**v4.0 improvements confirmed:** Constraint inventory maintained across all 5 iterations, DA caught SYME drop, O-forbidden detection applied, conflicting long-range correlations identified and removed. The team architecture works — the remaining problem is missing features (fragment library, 4J detection), not agent bugs.

---

## 5. Caripyrin: Constraint Impact Demonstration

From ~29 billion isomers to 5 candidates:

| Constraint Layer | Structures |
|-----------------|-----------|
| Molecular formula only (C10H11NO3) | 29,286,225,214 |
| + NMR correlations + multiplicities | 8,528,288 |
| + No hetero-hetero bonds | 1,607,593 |
| + Hybridisations | 30 |
| + Forbidden/mandatory neighbours | 10 |
| + First fragment | 5 |

Lucy-ng v3.0+ has the detection pipeline (hybridisation + neighbours + HHB) that provides the 5-orders-of-magnitude reduction from 8.5M to 10. The fragment step (10 to 5) requires the fragment library (Priority 1 gap).

---

## 6. Sherlock's Failure Cases (5/45)

All five failures share the same root cause: **high proton deficiency** leading to insufficient HMBC coverage.

| Case | Compound | Problem |
|------|----------|---------|
| 41 | Rubterolone A | Insufficient HMBC for highly substituted ring system |
| 42 | Actinospirol A | 13/25 structural units disconnected in MCD |
| 43 | Pseudoxylallemycin B | Complex cyclic tetrapeptide |
| 44 | Necroxime A | Proton deficiency + complexity |
| 45 | Gladiofungin A | Proton deficiency + complexity |

**Wenk's suggested solutions:** INADEQUATE experiments (C-C bonds), LR-HSQMBC (long-range), DFT re-ranking, custom fragment import, IR/UV integration.

---

## 7. Thesis Outlook Features (Chapter 6)

| Feature | Thesis Assessment | lucy-ng Relevance | Priority |
|---------|-------------------|-------------------|----------|
| 1H NMR prediction | High value for ranking | Useful but 13C is primary | Medium |
| IR/UV integration | Additional structural evidence | Different domain | Low |
| INADEQUATE support | Direct C-C bonds, solves proton-deficient | Rare experiment | Medium |
| LR-HSQMBC | 4+ bond correlations, explicit long-range | Directly addresses 4J problem | High |
| Stereochemistry + DFT re-ranking | Post-solution refinement | Complex, deferred | Low |
| NP-likeness scoring | Filter by natural product similarity | Cheap to add with RDKit | Medium |
| Tautomer grouping | Reduce duplicate solutions | Low impact | Low |

---

## 8. Default Parameters Reference

### Detection Thresholds

| Parameter | Default | Description |
|-----------|---------|-------------|
| Hybridisation threshold | 1% | States below this excluded |
| Non-neighbour (NN) threshold | 1% | Elements below this forbidden |
| Set-neighbour (SN) threshold | 95% | Elements above this mandatory |
| HHB threshold | 1% | Below = forbid hetero-hetero bonds |
| Detection search window | +/- 2 ppm | Chemical shift tolerance for queries |

### Signal Grouping Tolerances

| Element | Tolerance (ppm) |
|---------|----------------|
| 13C | 0.25 |
| 1H | 0.02 |
| 15N | 0.25 |
| 19F | 0.25 |
| 29Si | 0.25 |
| 31P | 0.25 |

### Prediction Parameters

| Parameter | Value |
|-----------|-------|
| HOSE max sphere | 6 |
| Fallback | 6 -> 5 -> 4 -> 3 -> 2 -> 1 |
| Prediction value | Mean of medians per solvent group |
| Ranking tolerance | 10 ppm (DEV for matching) |

---

## 9. Suggested Milestone Sequence

Based on impact, feasibility, and dependencies:

| Milestone | Key Feature | Effort | Expected Impact |
|-----------|-------------|--------|-----------------|
| **v5.0** | Fragment Library + Search | High | 34/40 single-solution (Sherlock parity) |
| **v5.1** | Statistical 4J Detection | Medium | Solves ibuprofen and similar aromatics |
| **v5.2** | COSY Integration + NP-Likeness | Low-Medium | Additional constraint source + solution filter |
| **v6.0** | Multi-Compound UAT (45 cases) | Medium | Benchmark against Sherlock's 40/45 |
| **Future** | Solvent-aware prediction, LR-HSQMBC, DFT re-ranking | Variable | Incremental quality improvements |

The fragment library is the single feature that would most dramatically improve lucy-ng's CASE success rate. It should be the next major milestone.

---

## 10. lucy-ng Unique Advantages

Lucy-ng has capabilities Sherlock lacks:

1. **Fully automated peak picking** — Sherlock requires manual peak picking through NMRium GUI
2. **Autonomous AI-driven workflow** — No human interaction needed for complete CASE run
3. **Pre-run validation gate** — Devils-advocate catches constraint errors before wasting solver time
4. **Aromatic ring sanity check** — Post-ranking verification when NMR shows aromaticity but solutions lack rings
5. **Constraint inventory persistence** — Explicit tracking prevents loss across iterations
6. **Multi-agent peer review** — 5 agents cross-check each other's work in real time

If lucy-ng matches Sherlock's solution quality (via fragment library), the automation advantage makes it genuinely more powerful for unattended structure elucidation.

---

## 11. Software References

| Component | Repository/DOI |
|-----------|---------------|
| Sherlock backend | github.com/michaelwenk/sherlock |
| Sherlock frontend | github.com/michaelwenk/sherlock-frontend |
| casekit library | github.com/michaelwenk/casekit |
| Backend DOI | 10.5281/zenodo.7037546 |
| Frontend DOI | 10.5281/zenodo.7032805 |
| casekit DOI | 10.5281/zenodo.7115819 |
| Test datasets | nmrXiv (45 DOIs, see thesis Table 13) |

---

*Last updated: 2026-02-19 — post v4.0 gap closure assessment*

# Feature Landscape: Statistical Detection for CASE

**Domain:** Computer-Assisted Structure Elucidation (CASE) statistical detection
**Researched:** 2026-02-10
**Context:** Subsequent milestone adding data-driven statistical detection to existing lucy-ng CASE system

## Table Stakes

Features users expect from a statistical CASE system. Missing = search space explosion.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Hybridisation detection** | Sherlock demonstrates 5-orders-of-magnitude reduction (Caripyrin: 8.5M → 30 structures). Without this, LSD runs for hours or produces thousands of wrong solutions. | Medium | Query existing HOSE database with +/- 2 ppm window, count sp1/sp2/sp3 occurrences, exclude < 1% |
| **Neighbourhood detection (forbidden)** | Prevents chemically unreasonable bonds (e.g., O-O in absence of peroxides). Sherlock's 1% NN threshold excludes elements with < 1% bond partner frequency. | Medium | Query bond partner distributions per HOSE code/shift, filter by < 1% threshold |
| **Neighbourhood detection (mandatory)** | Enforces strong chemical evidence (e.g., carbonyl C MUST bond to O). Sherlock's 95% SN threshold. | Medium | Query bond partner distributions, filter by > 95% threshold |
| **Two-tier ranking** | Prevents wrong solutions with coincidentally low MAE. Sherlock ranks by (1) signal match count, (2) average deviation. Lucy-ng's MAE-only ranking caused ibuprofen hallucination (cyclohexadiene MAE 1.93 ppm looked "excellent"). | Low | Algorithmic change, no database needed. Count experimental shifts within tolerance of predictions, sort by count DESC, then deviation ASC |
| **Badlist filters** | Excludes 3- and 4-membered rings by default (chemically rare in natural products). Sherlock applies these as DEFF/FEXP NOT constraints. | Low | Hardcoded SMARTS patterns for strained rings, generate LSD DEFF commands |

## Differentiators

Features that set advanced CASE systems apart. Not expected, but highly valued.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Hetero-hetero bond (HHB) allowance** | Automatically determines if heteroatom-heteroatom bonds should be allowed based on formula composition. Sherlock's 1% threshold on bond pair statistics prevents unrealistic peroxide/hydrazine structures in typical organic compounds. | Medium | Query compound database for heteroatom bond pair frequencies given formula elements, calculate ratio, set HETE command |
| **Signal grouping (close shifts)** | Groups signals within tolerance (0.25 ppm for 13C). When > 1 member, enables combinatorial atom exchange. Sherlock explicitly states this was REQUIRED to solve ibuprofen (C4/C5 at 44.90/45.03 ppm, difference 0.13 ppm). Without this, candidate list was empty. | Medium | Simple tolerance comparison on experimental shifts, but requires LSD file generation with parenthesized atom lists in HMBC commands |
| **Fragment library search** | 24.5M substructure-subspectrum correlations (SSCs). Sherlock reduced 27/40 multi-solution cases; 34/40 converged to single solution after fragment application. Allantofuranone: 336 → 1 solution with single fragment. | Very High | Largest engineering effort: extract SSCs from compound database, build fingerprint index for pre-screening, spectral matching with DEV/AVGDEV, inject as DEFF/FEXP goodlist constraints |
| **Solvent-aware prediction** | Per-solvent statistics (CDCl3, DMSO, etc.) reduce prediction error. Sherlock achieves 0.83 ppm mean deviation vs lucy-ng's ~2.5 ppm. | High | Requires database schema change to store solvent metadata, parsing solvent from Bruker acqus files, separate HOSE stats per solvent |
| **Combinatorial pyLSD files** | Multiple LSD input files for atom exchange scenarios. Sherlock generates separate files for each exchange permutation. | Medium | Depends on signal grouping; generates N LSD files for N permutations, runs each, merges solution sets |

## Anti-Features

Features to explicitly NOT build in v3.0. Common mistakes or over-engineering.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **GUI for parameter adjustment** | Sherlock's GUI requires manual tweaking (tolerance, thresholds, fragment selection). Lucy-ng's AI agent autonomy is a differentiator — don't regress to manual control. | Let AI agent use CLI detection commands with default thresholds. Agent can adjust if needed, but default behavior should work. |
| **ELIM command automation** | ELIM (eliminate atoms from substructure match) is notoriously finicky and often causes 0 solutions. Sherlock disables by default, requires manual activation. | v3.0: Do NOT add automatic ELIM. Agent may use manually in exceptional cases. Defer smarter ELIM logic to v3.1+. |
| **4-bond HMBC automatic handling** | 4-bond HMBC correlations exist but are hard to distinguish from noise. Sherlock requires manual marking. Automatic detection has high false positive rate. | v3.0: Ignore. Agent treats all HMBC as 2-3 bond. Defer 4-bond detection to v3.2 if needed. |
| **Stereochemistry (E/Z, R/S)** | LSD doesn't handle stereochemistry well. Sherlock uses stereo-enhanced HOSE codes but doesn't enforce stereochemical constraints in LSD. | v3.0: Out of scope. Defer to v4.0 with stereo-enhanced HOSE and post-LSD DFT ranking. |
| **Interactive CASE mode** | Sherlock's web UI allows mid-run parameter changes. This breaks autonomous agent workflow. | v3.0: Fully autonomous only. Agent runs to completion, orchestrator intervenes on loops. No interactive mode. |
| **COSY correlation constraints** | COSY (H-H correlations) are notoriously difficult to analyze (complex multiplets, overlapping signals). Sherlock supports them but they rarely improve results and often hurt. | v3.0: Do NOT add COSY processing. HSQC + HMBC are sufficient for most cases. Defer COSY to v3.3+ if demand exists. |

## Feature Dependencies

```
Statistical Detection Foundation (v3.0):
  - Hybridisation detection → LSD MULT command generation
  - Neighbourhood detection → LSD LIST/PROP/BOND command generation
  - HHB detection → LSD HETE command generation
  - Signal grouping → LSD HMBC parenthesized atom lists
  - Two-tier ranking → Post-LSD ranking algorithm
  - Badlist filters → LSD DEFF/FEXP NOT commands

Fragment Library (v3.1):
  - SSC extraction (depends on: existing compound database)
  - Fingerprint index (depends on: SSC extraction)
  - Fragment search (depends on: SSC extraction, fingerprint index)
  - Fragment injection (depends on: fragment search, LSD integration)

Advanced Features (v3.2+):
  - Solvent-aware prediction (depends on: database schema v2, Bruker acqus parsing)
  - Combinatorial pyLSD (depends on: signal grouping)
  - 4-bond HMBC detection (depends on: statistical validation)
  - COSY processing (depends on: multi-dimensional peak analysis)

Stereo Features (v4.0):
  - Stereo-enhanced HOSE (depends on: database rebuild, RDKit stereo)
  - DFT re-ranking (depends on: external DFT engine, computational resources)
```

## MVP Recommendation

For v3.0 MVP, prioritize the foundation:

1. **Hybridisation detection** (CRITICAL)
   - Query: shift + multiplicity → sp1/sp2/sp3 distribution
   - Impact: 5 orders of magnitude search space reduction
   - CLI: `lucy detect hybridisation --shift <ppm> --multiplicity <0-3>`

2. **Neighbourhood detection** (CRITICAL)
   - Query: shift + hybridisation + formula elements → bond partner distribution
   - Impact: Prevents chemically unreasonable bonds, enforces mandatory bonds
   - CLI: `lucy detect neighbours --shift <ppm> --hybridisation <sp1/sp2/sp3> --elements <C,O,N,...>`

3. **HHB detection** (HIGH)
   - Query: formula elements → hetero-hetero bond pair statistics
   - Impact: Prevents peroxide/hydrazine hallucinations in standard organic compounds
   - CLI: `lucy detect hhb --elements <C,O,N,...>`

4. **Signal grouping** (HIGH)
   - Query: experimental shifts → groups within tolerance
   - Impact: Required for ibuprofen-class cases with close shifts
   - CLI: `lucy analyze grouping --shifts "44.90,45.03,..." --tolerance 0.25`

5. **Two-tier ranking** (HIGH)
   - Algorithmic change to `lucy lsd rank`
   - Impact: Prevents MAE-only hallucinations
   - CLI: `lucy lsd rank <solutions.smi> --shifts "..." --match-tolerance 10.0`

6. **Badlist filters** (MEDIUM)
   - Hardcoded patterns in agent knowledge
   - Impact: Excludes chemically unreasonable strained rings
   - Implementation: Agent adds DEFF/FEXP NOT lines to LSD files

Defer to post-MVP:

- **Fragment library** (v3.1): Largest effort, highest single-case impact
- **Solvent-aware prediction** (v3.2): Improves MAE but requires schema changes
- **Combinatorial pyLSD** (v3.2): Depends on signal grouping working first
- **All anti-features**: ELIM, 4-bond HMBC, stereochemistry, COSY, interactive mode

## Detailed Feature Specifications

### 1. Hybridisation Detection

**Expected behavior (from Sherlock):**

Given a 13C chemical shift and multiplicity, return the distribution of sp1/sp2/sp3 hybridisation states observed in the knowledge base.

**Query algorithm:**
1. Construct shift window: [shift - 2.0 ppm, shift + 2.0 ppm]
2. Query all HOSE codes with mean shift in that window at radius 6 (or highest available)
3. For each matching HOSE code, decode hybridisation from HOSE syntax:
   - First character after element indicates hybridisation
   - `C-4` = sp3 (tetrahedral, 4 bonds)
   - `C-3` = sp2 (trigonal, 3 bonds)
   - `C-2` = sp1 (linear, 2 bonds)
4. Weight by observation count: multiply hybridisation occurrences by HOSE stat count
5. Calculate percentage distribution
6. Exclude states with < 1% frequency (Sherlock's hybridisation threshold)

**CLI command signature:**
```bash
lucy detect hybridisation --shift 180.5 --multiplicity 0 [--format json]
```

**Expected JSON output:**
```json
{
  "shift": 180.5,
  "multiplicity": 0,
  "search_window": [178.5, 182.5],
  "total_observations": 15234,
  "distributions": {
    "sp2": {"count": 15123, "percentage": 99.3},
    "sp3": {"count": 111, "percentage": 0.7}
  },
  "excluded": {
    "sp1": {"count": 0, "percentage": 0.0, "reason": "below_threshold"}
  },
  "threshold_pct": 1.0
}
```

**How AI agent uses output:**
- Generates LSD MULT command with allowed hybridisations
- Example: if only sp2 detected, `MULT 1 C 2 0` (carbon, sp2, no hydrogens)
- If multiple allowed, agent chooses most probable or generates multiple LSD files

**Dependencies:**
- Existing HOSE stats database (hose_stats table with hose_code, mean, count)
- HOSE code parser to extract hybridisation from syntax
- No new database tables needed

**Edge cases:**
- **No matches in window:** Widen search window to +/- 5 ppm, report LOW confidence
- **Multiplicity mismatch:** If multiplicity 0 (quaternary) but only sp3 found with hydrogens in HOSE, flag inconsistency
- **All states below threshold:** Allow all states, report warning

### 2. Neighbourhood Detection

**Expected behavior (from Sherlock):**

Given a carbon's shift, hybridisation, and formula elements, return the distribution of bonded element types.

**Query algorithm:**
1. Construct shift window: [shift - 2.0 ppm, shift + 2.0 ppm]
2. Query HOSE codes matching shift and hybridisation
3. For each HOSE code, parse first sphere (immediate neighbours):
   - HOSE syntax: `C-4;XYZ(//...)` where X, Y, Z are bonded elements
   - Example: `C-4;CO(//C,C)` has neighbours C, O in first sphere
4. Count occurrences of each element type weighted by observation count
5. Calculate percentage distribution
6. Classify:
   - **Forbidden (NN):** Element < 1% → generate LSD LIST NOT command
   - **Mandatory (SN):** Element > 95% → generate LSD PROP/BOND command
   - **Allowed:** 1% ≤ element ≤ 95% → no constraint (LSD explores)

**CLI command signature:**
```bash
lucy detect neighbours --shift 180.5 --hybridisation sp2 --elements C,O,N [--format json]
```

**Expected JSON output:**
```json
{
  "shift": 180.5,
  "hybridisation": "sp2",
  "formula_elements": ["C", "O", "N"],
  "search_window": [178.5, 182.5],
  "total_observations": 8234,
  "distributions": {
    "O": {"count": 8102, "percentage": 98.4, "classification": "mandatory"},
    "C": {"count": 120, "percentage": 1.5, "classification": "allowed"},
    "N": {"count": 12, "percentage": 0.1, "classification": "forbidden"}
  },
  "thresholds": {"nn_pct": 1.0, "sn_pct": 95.0}
}
```

**How AI agent uses output:**
- **Forbidden (< 1%):** `LIST 1 NOT N` (carbon 1 must NOT bond to nitrogen)
- **Mandatory (> 95%):** `BOND 1 2` (carbon 1 MUST bond to oxygen 2) — use sparingly, only when very strong evidence
- **Allowed (1-95%):** No constraint, let LSD decide

**Dependencies:**
- Existing HOSE stats database
- HOSE code parser to extract first sphere neighbours
- No new database tables needed

**Edge cases:**
- **Formula element not in database:** Warn, allow by default (no constraint)
- **All elements forbidden:** Error, cannot proceed (inconsistent data)
- **Multiple mandatory elements:** Valid for polyatomic groups (e.g., C=O needs both C and O neighbours)

### 3. Hetero-Hetero Bond (HHB) Allowance

**Expected behavior (from Sherlock):**

Given the element composition of a molecular formula, determine if heteroatom-heteroatom bonds (O-O, N-N, O-N, etc.) should be allowed.

**Query algorithm:**
1. Extract heteroatoms from formula (all non-C, non-H elements)
2. Query compound database for all compounds containing those heteroatoms
3. For each compound, extract SMILES and count heteroatom bond pairs:
   - Parse SMILES to molecular graph
   - For each bond, check if both endpoints are heteroatoms
   - Count O-O, N-N, O-N, S-S, etc.
4. Calculate ratio: (compounds with HHB) / (total compounds with these heteroatoms)
5. If ratio < 1%, forbid HHB (set LSD HETE 0)
6. If ratio ≥ 1%, allow HHB (set LSD HETE 1)

**CLI command signature:**
```bash
lucy detect hhb --elements C,O,N [--format json]
```

**Expected JSON output:**
```json
{
  "formula_elements": ["C", "O", "N"],
  "heteroatoms": ["O", "N"],
  "total_compounds": 125340,
  "compounds_with_hhb": 412,
  "hhb_ratio": 0.0033,
  "hhb_pairs": {
    "O-O": 203,
    "N-N": 189,
    "O-N": 20
  },
  "allow_hhb": false,
  "threshold_pct": 1.0,
  "lsd_hete_value": 0
}
```

**How AI agent uses output:**
- Adds `HETE 0` (forbid HHB) or `HETE 1` (allow HHB) to LSD file
- Default: forbid (most natural products don't have HHB)

**Dependencies:**
- Existing compound database (compounds table with SMILES)
- SMILES parser (RDKit) to extract bond types
- No new database tables needed

**Edge cases:**
- **No heteroatoms in formula:** Skip HHB detection entirely (all-hydrocarbon)
- **Rare heteroatoms (P, Si, etc.):** Low compound count, may need to lower threshold or allow by default
- **Mixed results:** If some pairs are common (S-S in disulfides) but others rare (O-O), report per-pair statistics, let agent decide

### 4. Signal Grouping

**Expected behavior (from Sherlock):**

Given a list of experimental 13C shifts, identify groups of signals within a tolerance (default 0.25 ppm for 13C).

**Algorithm:**
1. Sort experimental shifts ascending
2. Iterate through sorted shifts
3. For each shift, check if within tolerance of previous shift
4. If yes, add to current group
5. If no, start new group
6. Return groups with > 1 member

**CLI command signature:**
```bash
lucy analyze grouping --shifts "44.90,45.03,129.38,127.26" --tolerance 0.25 [--format json]
```

**Expected JSON output:**
```json
{
  "tolerance": 0.25,
  "total_signals": 4,
  "groups": [
    {
      "members": [44.90, 45.03],
      "count": 2,
      "min": 44.90,
      "max": 45.03,
      "span": 0.13,
      "centroid": 44.965
    }
  ],
  "ungrouped": [127.26, 129.38]
}
```

**How AI agent uses output:**

When a group has > 1 member, generate LSD HMBC commands with parenthesized atom lists for combinatorial exchange:

**Without grouping (rigid assignment):**
```
HMBC 2 8    ; C2 correlates to H8
HMBC 3 8    ; C3 correlates to H8
```

**With grouping (combinatorial exchange):**
```
HMBC (2 3) 8    ; Either C2 or C3 correlates to H8, LSD tries both
```

This is **CRITICAL** for ibuprofen-class cases where shifts are < 0.25 ppm apart and manual assignment would guess wrong.

**Dependencies:**
- None (pure algorithmic, no database queries)

**Edge cases:**
- **All signals grouped:** Likely data error, check for calibration issues
- **No groups:** Normal, most signals well-separated
- **Overlapping groups (tolerance too large):** Groups should be non-overlapping by construction

**Implementation note:**

This requires LSD file generation logic changes. Agent must:
1. Run `lucy analyze grouping` on experimental shifts
2. For each HMBC correlation, check if carbon shift is in a group
3. If in group, use `(atom1 atom2 ...)` syntax
4. If not in group, use single atom ID

### 5. Two-Tier Ranking

**Expected behavior (from Sherlock):**

Rank LSD solutions by (1) number of matching signals, then (2) average deviation among matched signals.

**Algorithm:**
1. For each LSD solution SMILES:
   - Predict 13C shifts using HOSE-based predictor
   - For each experimental shift, find closest predicted shift
   - If within tolerance (default 10 ppm), count as "match"
   - Calculate average deviation among matched signals
2. Sort solutions:
   - Primary key: match_count (descending)
   - Secondary key: average_deviation (ascending)

**CLI command signature (modified existing command):**
```bash
lucy lsd rank solutions.smi --shifts "180.5,140.8,..." --match-tolerance 10.0 [--format json]
```

**Expected JSON output:**
```json
{
  "solutions": [
    {
      "smiles": "CC(C)Cc1ccc(cc1)C(C)C(=O)O",
      "rank": 1,
      "match_count": 13,
      "total_signals": 13,
      "coverage": 1.0,
      "average_deviation": 0.28,
      "mae": 0.31,
      "quality": "Excellent"
    },
    {
      "smiles": "CC1=CC(C)C(C)CC1C(=O)O",
      "rank": 2,
      "match_count": 11,
      "total_signals": 13,
      "coverage": 0.85,
      "average_deviation": 1.93,
      "mae": 5.42,
      "quality": "Poor"
    }
  ],
  "ranking_method": "two_tier",
  "match_tolerance_ppm": 10.0
}
```

**How AI agent uses output:**
- Prioritizes solutions with high match count (complete spectral coverage)
- Among solutions with equal match count, chooses lowest deviation
- Reports `coverage` to user: 1.0 = all experimental signals matched

**Dependencies:**
- Existing HOSE-based prediction (`lucy predict c13`)
- Modified ranking logic in `lucy lsd rank`

**Edge cases:**
- **All solutions have same match count:** Ranking reduces to MAE (current behavior)
- **No solutions with > 50% match count:** Warn that LSD constraints may be wrong
- **Tolerance too tight:** If tolerance < 2 ppm, very few matches, ranking becomes unreliable

**Why this matters:**

Lucy-ng's MAE-only ranking caused the ibuprofen hallucination. Wrong cyclohexadiene solutions had MAE 1.93 ppm across 13 carbons, which appeared "excellent". But those 13 carbons were mapped to WRONG structural positions. Two-tier ranking counts how many experimental signals are ACTUALLY matched (within tolerance) before considering deviation, preventing this failure mode.

### 6. Badlist Filters

**Expected behavior (from Sherlock):**

Exclude chemically unreasonable 3-membered and 4-membered rings by default.

**Implementation:**

Add DEFF/FEXP NOT commands to LSD file with SMARTS patterns for strained rings.

**SMARTS patterns:**
- 3-membered ring: `C1CC1` (cyclopropane)
- 4-membered ring: `C1CCC1` (cyclobutane)
- 3-membered heterocycle: `C1OC1` (epoxide), `C1NC1` (aziridine)
- 4-membered heterocycle: `C1OCC1` (oxetane), `C1NCC1` (azetidine)

**LSD file addition:**
```
; Exclude strained rings
DEFF NOT C1CC1
DEFF NOT C1CCC1
DEFF NOT C1OC1
DEFF NOT C1NC1
DEFF NOT C1OCC1
DEFF NOT C1NCC1
```

**How AI agent uses this:**

Agent adds these lines to EVERY LSD file by default unless:
- Formula or shift evidence suggests epoxide (C-O at ~50 ppm with correct formula)
- User explicitly requests strained ring search (unlikely)

**Dependencies:**
- None (hardcoded patterns in agent knowledge)

**Edge cases:**
- **Epoxide in formula:** Agent should recognize this and NOT exclude 3-membered C1OC1
- **Bridged ring systems:** Some bicyclic compounds have 4-membered rings as bridges (norbornane); if these fail, agent can remove constraint

**Why this matters:**

Natural products rarely contain strained rings. Without this filter, LSD explores unrealistic ring systems, increasing solution count and runtime unnecessarily.

## Implementation Priority (v3.0)

Based on impact, feasibility, and dependencies:

| Priority | Feature | Effort | Impact | Dependencies |
|----------|---------|--------|--------|-------------|
| **P0** | Two-tier ranking | Low (1-2 days) | High (prevents MAE hallucinations) | Modify existing `lucy lsd rank` |
| **P0** | Badlist filters | Low (1 day) | Medium (excludes unrealistic rings) | Agent knowledge update only |
| **P1** | Hybridisation detection | Medium (3-5 days) | Very High (5 orders of magnitude reduction) | HOSE parser, DB query, new CLI command |
| **P1** | Neighbourhood detection | Medium (3-5 days) | Very High (prevents unreasonable bonds) | HOSE parser, DB query, new CLI command |
| **P2** | HHB detection | Medium (2-3 days) | High (prevents hetero-hetero hallucinations) | SMILES bond analysis, DB query, new CLI command |
| **P2** | Signal grouping | Medium (2-3 days) | Very High (required for close-shift cases) | Algorithmic, LSD generation logic changes |
| **P3** | Agent integration | High (5-7 days) | Critical (enables autonomous use) | All above features complete, agent skill updates |

**Total estimated effort:** 18-28 days for full v3.0 statistical detection foundation

**Recommended sequence:**
1. **P0 features** (2-3 days): Quick wins, immediate impact
2. **P1 features** (6-10 days): Core statistical detection, highest search space reduction
3. **P2 features** (4-6 days): Rounding out the foundation
4. **P3 agent integration** (5-7 days): Teaching agent to use new CLI commands autonomously

## Confidence Assessment

| Area | Confidence | Source |
|------|------------|--------|
| Hybridisation detection specs | HIGH | Sherlock thesis Section 4.4.4, Table 4.3 |
| Neighbourhood detection specs | HIGH | Sherlock thesis Section 4.4.5, Caripyrin example |
| HHB detection specs | HIGH | Sherlock thesis Section 4.4.6, 1% threshold documented |
| Signal grouping specs | HIGH | Sherlock thesis Section 4.4.7, ibuprofen case study |
| Two-tier ranking specs | HIGH | Sherlock thesis Section 4.5.4, ranking algorithm |
| Badlist filters | MEDIUM | Sherlock thesis mentions DEFF/FEXP, specific patterns inferred |
| Thresholds (1%, 95%, 2 ppm, 0.25 ppm) | HIGH | Sherlock thesis Table 4.3 (default parameters) |
| HOSE database sufficiency | HIGH | lucy-ng has 7.9M HOSE stats, Sherlock has ~6.3M |
| CLI output format | MEDIUM | Designed for agent consumption, may need adjustment |

## Open Questions

- **Q1:** Do we need separate hybridisation stats table, or can we parse HOSE codes on-the-fly?
  - **A:** Parse on-the-fly for v3.0 (simpler). If performance is poor, add stats table in v3.1.

- **Q2:** Should signal grouping generate multiple LSD files or single file with parenthesized lists?
  - **A:** Single file with parenthesized lists (Sherlock's approach). Multiple files is Sherlock's "combinatorial pyLSD" which is deferred to v3.2.

- **Q3:** What match tolerance for two-tier ranking? Sherlock uses 10 ppm (DEV parameter).
  - **A:** Start with 10 ppm (Sherlock default), make it configurable via CLI flag.

- **Q4:** Do we need per-nucleus tolerances for signal grouping (0.02 ppm for 1H vs 0.25 ppm for 13C)?
  - **A:** v3.0 is 13C-only. Defer 1H grouping to v3.2 if multi-nucleus detection is added.

- **Q5:** How to handle compounds with no HOSE matches (novel scaffolds)?
  - **A:** Widen search window, report LOW confidence, let agent decide whether to proceed. This is expected for novel natural products.

## Sources

- **Primary:** Michael Wenk, PhD Thesis, Friedrich-Schiller-Universitat Jena, 2023 (local file: background/sherlock-analysis.md)
- **Secondary:** lucy-ng codebase analysis (existing HOSE database structure, prediction API, LSD integration)
- **Confidence:** HIGH for all specifications (directly from authoritative Sherlock thesis with test case validation)

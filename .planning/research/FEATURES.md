# Feature Landscape: Fragment Library and SSC Search

**Domain:** Substructure-subspectrum correlation (SSC) fragment library for CASE
**Researched:** 2026-02-19
**Confidence:** HIGH — Wenk thesis (Sherlock) provides algorithmic specification; existing lucy-ng codebase provides integration context

---

## Background: What SSC Search Does and Why It Matters

The fragment library answers the question: "Given an experimental 13C spectrum, what previously characterized substructures are consistent with these chemical shifts?" Matching fragments are injected as LSD goodlist constraints (DEFF/FEXP), forcing every generated solution to contain those substructures. The effect is dramatic: in Sherlock, 34/40 cases reduced to a single solution with the first matched fragment.

The mechanism has three stages:

1. **Offline extraction** (one-time, slow): For each of 928K compounds in the database, generate all substructures (SSCs) using breadth-first fragmentation. Store each SSC with its associated subspectrum (chemical shifts of atoms remaining after fragmentation) and a 256-bit fingerprint (2 ppm bins, 0-510 ppm range).

2. **Online pre-screening** (fast, bitset): Given experimental shifts, build a query fingerprint. For each SSC in the library, apply Boolean AND. If `AND(query, SSC) == SSC`, the SSC's signals are all present in the experimental spectrum — candidate passes.

3. **Online fine matching** (slower, per-signal): For each pre-screening survivor, compute signal pairs using minimum-distance matching (same as dereplication). Filter by DEV (max per-signal deviation, default 2 ppm) and AVGDEV (average deviation, default 1 ppm). Require multiplicity match. The surviving fragments are ranked by size (descending) then AVGDEV (ascending).

The first/best fragment is injected as a DEFF goodlist file + FEXP constraint into the LSD input. In Sherlock, only the first fragment is used — this is sufficient to reduce 34/40 cases to single solutions.

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features that the CASE system needs for SSC search to be functional. Missing any of these means the feature does not work.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **SSC extraction from compound database** | The fragment library must be built from the existing 928K compounds | HIGH | One-time offline batch process. Fragmentation rules: preserve heteroatom bonds, preserve double/triple bonds, preserve carbon-to-multiple-heteroatom bonds, preserve ring systems as whole units. Max sphere = 3 (for atom-centered fragments), max sphere = 1 (for ring-system-centered fragments). Max ring size for ring detection = 6. |
| **Duplicate SSC deduplication** | Different atoms in same compound or across compounds produce identical substructures | MEDIUM | SMILES-based deduplication. When duplicates found: keep record with lower AVGDEV to experimental spectrum. Sherlock produces 24.5M SSCs from 892K compounds — dedup is essential. |
| **256-bit fingerprint per SSC** | Boolean AND pre-screening requires pre-computed bitstrings | MEDIUM | 2 ppm bins covering 0-510 ppm = 255 bins. Bit i = 1 if any SSC signal falls in [i*2, (i+1)*2) ppm. All 256 bits in a single integer or bytes object. |
| **Fragment database table** | SSC records must be stored and indexed for efficient retrieval | HIGH | New SQLite table (schema v7). Columns: smiles, subspectrum_shifts, fingerprint, heavy_atom_count, avgdev. Index on fingerprint for bitset comparison. Estimated size: 24.5M records * ~200 bytes = ~5 GB. May require separate database file from compound/HOSE database. |
| **Query fingerprint construction with tolerance expansion** | Query bits need ±1-bin tolerance to avoid boundary misses | LOW | Before screening, set each query bit's neighbors also to 1. Prevents misses when experimental signal at 44.9 and SSC signal at 45.1 fall in different 2 ppm bins. |
| **Boolean AND pre-screening** | Eliminates non-matching SSCs fast without per-signal comparison | MEDIUM | `(query_fp & ssc_fp) == ssc_fp` — if true, all SSC signals are accounted for in query. Implemented as integer bitwise AND on 256-bit stored fingerprints. |
| **Fine spectral matching** | Pre-screening passes many false positives; fine match filters by actual shift deviations | HIGH | Same algorithm as existing dereplication: minimum-distance signal pair assignment, require multiplicity match, check DEV <= 2 ppm per pair, check AVGDEV <= 1 ppm overall. Requires subspectrum stored with multiplicities per atom. |
| **Fragment result ranking** | Multiple fragments pass fine matching; best one used as constraint | LOW | Primary: heavy atom count descending (larger fragments = stronger constraint). Secondary: AVGDEV ascending (better spectral fit). Implemented in ranker. |
| **CLI command: `lucy fragment search`** | Agent needs to invoke fragment search from Bash | MEDIUM | `lucy fragment search --shifts "127.26,129.38,..." --formula C13H18O2 --format json`. Output: ranked list of fragments with SMILES, heavy atom count, AVGDEV, matched signal pairs. |
| **LSD goodlist file generation** | Fragment must be written as DEFF/FEXP syntax for LSD | MEDIUM | Fragment SMILES → LSD SSTR/LINK syntax. Open sites (R groups from fragmentation) become generic atoms in LSD notation. The DEFF file contains the substructure definition; FEXP says `'F1'` to mandate it. |
| **Agent integration: lsd-engineer writes fragment constraints** | CASE team must automatically apply the best fragment | MEDIUM | lsd-engineer runs `lucy fragment search`, takes rank #1 fragment, writes goodlist file, adds DEFF/FEXP to LSD input file. |
| **Hybridisation check during fine matching** | Fragment atom hybridisations must match detected hybridisations for query signals | LOW | Already available from `lucy detect hybridisation`. If detected hybridisation list is non-empty for a query signal, the matching fragment atom's hybridisation must be in that list. |

### Differentiators (Competitive Advantage)

Features that improve SSC search quality beyond the Sherlock baseline.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Multi-fragment injection strategy** | Use top N fragments instead of just the first when single fragment doesn't yield single solution | MEDIUM | Sherlock uses only the first fragment. Extension: if first fragment yields >5 solutions after LSD, inject second fragment via `FEXP 'F1 AND F2'`. Reduces residual multi-solution cases. |
| **Fragment size filter** | Exclude very small fragments (1-3 heavy atoms) that provide no structural information | LOW | Threshold: minimum heavy atom count of 4. Small fragments match too broadly and waste constraint power. |
| **Formula-aware pre-screening** | Filter SSCs by molecular formula compatibility before fingerprint comparison | MEDIUM | SSC atom composition must be a subset of the query compound formula. E.g., if query is C13H18O2, reject SSCs containing nitrogen. Eliminates chemically impossible fragments early. |
| **Incremental fragment application** | Start with largest fragment; add smaller ones only if solution count remains high | MEDIUM | After applying fragment 1, if solutions > 10, apply fragment 2 as additional FEXP constraint. This avoids over-constraining when a good fragment already solves the problem. |
| **Fragment display in CASE-PROGRESS.md** | Report which fragment was found and applied, with matched signals highlighted | LOW | Shows chemist what structural subunit was confirmed. Helps diagnose why fragment didn't reduce to single solution (wrong fragment, 4J issue, etc.). |
| **Resumable extraction pipeline** | SSC extraction runs for hours; must survive interruption | MEDIUM | Checkpoint table already exists in schema. Track last processed compound_id. Resume from checkpoint on restart. |
| **Fragment search statistics in CLI output** | Report pre-screening count, fine-match count, and final count | LOW | Diagnostic information. Helps tune DEV/AVGDEV thresholds. E.g., "24.5M SSCs → 2,341 passed pre-screen → 47 passed fine match → 5 after dedup". |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **Storing all 24.5M fragments in the main compound database** | Single database is simpler | Main database is already 2.8 GB. Adding 24.5M SSC records (~5 GB) makes the file unmanageable and slows all existing queries (dereplication, prediction) due to SQLite page cache pressure. | Separate database file `lucy-ng-fragments.db` with symlink or config-based path. Fragment search CLI opens this file independently. |
| **Real-time SSC extraction on each CASE run** | Avoids separate extraction step | 24.5M fragments from 928K compounds takes hours. Completely impractical per-run. Sherlock pre-builds this offline. | Pre-built fragment database shipped alongside compound database (Figshare). One-time extraction for users who build from source. |
| **Using HOSE codes instead of fragmentation** | HOSE codes already exist in database | HOSE codes are atom-level descriptors (one HOSE per atom, single chemical shift). SSCs are substructure-level (a SMILES fragment + multiple shifts). They answer fundamentally different questions: HOSE says "what shift does this atom type have?" while SSC says "does this known substructure match my spectrum?" Cannot substitute. | Keep HOSE codes for prediction/ranking; add SSC library for fragment search. These are complementary, not competing. |
| **Injecting many fragments simultaneously** | More constraints = fewer solutions | Injecting 3+ fragments simultaneously with FEXP 'F1 AND F2 AND F3' often over-constrains and produces zero solutions, particularly when one fragment has a borderline spectral match. | Use fragments sequentially: apply first, run LSD, count solutions. If still multiple, apply second. |
| **Using fragment library for initial hypothesis** | Fragment search can provide structural hints | At the start of CASE (before any LSD run), the experimental spectrum fingerprint matches too many SSCs to be useful. Fragment constraints only become powerful in combination with MULT/HSQC/HMBC constraints. | Fragment search runs AFTER initial LSD to reduce multi-solution sets, not INSTEAD of initial setup. |
| **Custom user-uploaded fragments** | Advanced users may want to add known substructures | Increases system complexity (upload, storage, validation), fragment format is non-trivial (SSTR/LINK syntax), and the workflow is manual. | Agent can write DEFF/FEXP manually if chemist provides a known substructure. Fragment library is for automatic discovery, not manual entry. |

---

## Feature Dependencies

```
SSC extraction pipeline
    └── requires --> Compound database (928K compounds) [EXISTING]
    └── requires --> RDKit fragmentation with bond-preservation rules [NEW]
    └── requires --> Fragment database schema (v7) [NEW]
    └── produces --> 24.5M SSC records with subspectra + fingerprints

CLI: lucy fragment search
    └── requires --> Fragment database [NEW, from extraction]
    └── requires --> Bitset fingerprint computation [NEW]
    └── requires --> Fine spectral matching algorithm [NEW, similar to dereplication]
    └── requires --> Experimental shifts (from existing lucy pick 1d / CASE workflow)

LSD goodlist file generation
    └── requires --> Fragment SMILES [from CLI search]
    └── requires --> SSTR/LINK syntax knowledge [in agent skill]
    └── produces --> goodlist .def file for DEFF/FEXP in LSD

Agent integration (lsd-engineer)
    └── requires --> CLI: lucy fragment search [NEW]
    └── requires --> LSD goodlist file generation [NEW]
    └── requires --> lsd-engineer agent skill update [NEW]
    └── enhances --> Constraint inventory (DEFF/FEXP now tracked) [EXISTING]

Multi-fragment injection
    └── requires --> Agent integration working [NEW, above]
    └── requires --> Coordinator knowing current solution count [EXISTING]
    └── enhances --> Fragment search (uses top-N result) [NEW, above]
```

### Dependency Notes

- **SSC extraction requires formula-aware pre-screening:** During fine matching, the fragment's atom composition (from SMILES) must be checked against the query formula. This check needs compound formula data, already in the compounds table.
- **Fragment database is a prerequisite for all search features:** No fragment search CLI, no agent integration, no multi-fragment injection works without the pre-built database. Extraction is phase 1 blocker.
- **Agent integration depends on SSTR/LINK syntax knowledge:** The lsd-engineer agent must know how to convert a fragment SMILES with R groups to LSD SSTR/LINK notation. This is agent skill knowledge (similar to how LSD commands are currently inlined), not Python code.
- **Checkpoint system enhances but does not block extraction:** Resumable extraction is a robustness feature for the extraction pipeline. Non-resumable extraction still works but wastes compute on failure.
- **Multi-fragment injection conflicts with over-constraining:** Must only apply second fragment if solution count after first fragment is still above threshold. Coordinator checks `lucy lsd rank` output before deciding.

---

## MVP Definition

### Launch With (v5.0 core)

Minimum viable feature set to validate that SSC search reduces solution counts.

- [x] **SSC extraction pipeline** — Without the library, nothing else works. Extract from all 928K compounds, store in separate fragment database.
- [x] **256-bit fingerprint generation and Boolean AND pre-screening** — Core speed advantage. Without this, fine matching 24.5M SSCs per CASE run is computationally infeasible.
- [x] **Fine spectral matching (DEV/AVGDEV)** — Pre-screening alone has too many false positives. Fine matching required to find the actually useful fragment.
- [x] **CLI: `lucy fragment search`** — Agent-accessible interface. Required for lsd-engineer integration.
- [x] **LSD goodlist file generation** — Fragment is only useful if it can be expressed in LSD syntax and applied as a constraint.
- [x] **Agent integration: lsd-engineer applies first fragment** — The end-to-end workflow payoff. Agent runs fragment search, applies best fragment, sees reduced solution count.
- [x] **Multi-compound UAT** — Validate impact on at least 5 compounds (ibuprofen + 4 others from Sherlock's test set). Confirm solution count reduction matches expected pattern.

### Add After Validation (v5.x)

- [ ] **Multi-fragment injection strategy** — Trigger: UAT shows cases where first fragment insufficient (solution count still > 5 after first fragment).
- [ ] **Fragment search statistics in CLI output** — Trigger: debugging needs during UAT (thresholds need tuning).
- [ ] **Formula-aware pre-screening** — Trigger: fragment search performance is slow (>5 seconds per search).
- [ ] **Fragment display in CASE-PROGRESS.md** — Trigger: agent review of what fragment was used.
- [ ] **Resumable extraction pipeline** — Trigger: extraction fails on interrupted run. Add checkpoint support then re-run.

### Future Consideration (v5.2+)

- [ ] **Fragment size filter (min 4 heavy atoms)** — May not be needed if fine matching already filters small fragments by AVGDEV.
- [ ] **Solvent-aware fragment search** — Requires solvent-tracking infrastructure (separate milestone). Not needed for core fragment library.
- [ ] **Custom user-uploaded fragments** — Low value, high complexity. Deferred indefinitely.
- [ ] **Fragment database regeneration from updated compound database** — Only needed when compound database is updated (rare).

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| SSC extraction pipeline | HIGH | HIGH | P1 — must-have |
| 256-bit fingerprint + Boolean AND | HIGH | MEDIUM | P1 — enables feasible search |
| Fine spectral matching | HIGH | MEDIUM | P1 — eliminates false positives |
| CLI: `lucy fragment search` | HIGH | MEDIUM | P1 — agent interface |
| LSD goodlist file generation | HIGH | MEDIUM | P1 — constraint application |
| Agent integration (lsd-engineer) | HIGH | MEDIUM | P1 — end-to-end workflow |
| Fragment database schema (v7) | HIGH | LOW | P1 — infrastructure |
| Resumable extraction | MEDIUM | LOW | P2 — robustness |
| Fragment stats in CLI | MEDIUM | LOW | P2 — observability |
| Multi-fragment injection | MEDIUM | MEDIUM | P2 — edge case improvement |
| Formula-aware pre-screening | MEDIUM | MEDIUM | P2 — performance optimization |
| Fragment display in progress log | LOW | LOW | P2 — transparency |
| Fragment size filter | LOW | LOW | P3 — marginal quality |
| Custom user fragments | LOW | HIGH | P3 — don't build |

---

## Workflow Steps (Concrete)

The complete SSC workflow from experimental spectrum to LSD constraint:

### Step 1: Pre-build (One-time, Offline)
```bash
# New CLI command — extracts all SSCs from compound database
lucy fragment build --database data/reference/lucy-ng-derep.db \
                   --output data/reference/lucy-ng-fragments.db
# Expected runtime: several hours for 928K compounds
# Expected output: ~24.5M SSC records
```

### Step 2: Fragment Search (Per CASE Iteration, After Initial LSD)
```bash
# lsd-engineer calls this after initial LSD yields multiple solutions
lucy fragment search \
  --shifts "18.08,22.37,30.14,44.90,45.03,127.26,129.38,136.96,140.84,180.56" \
  --formula C13H18O2 \
  --database data/reference/lucy-ng-fragments.db \
  --top 5 \
  --format json
```

Expected JSON output:
```json
{
  "query_shifts": [18.08, 22.37, ...],
  "prescreening_count": 2341,
  "fine_match_count": 47,
  "result_count": 5,
  "fragments": [
    {
      "rank": 1,
      "smiles": "c1cc(CC(C)C(=O)O)ccc1CC(C)C",
      "heavy_atom_count": 13,
      "avgdev": 0.17,
      "matched_signals": [
        {"query_shift": 18.08, "fragment_shift": 18.55, "deviation": 0.47},
        ...
      ]
    },
    ...
  ]
}
```

### Step 3: Goodlist File Generation
```bash
# lsd-engineer generates the LSD fragment definition file
lucy fragment to-lsd \
  --smiles "c1cc(CC(C)C(=O)O)ccc1CC(C)C" \
  --output analysis/iteration_02/fragment.def
```

Fragment .def file format (SSTR/LINK notation):
```
; Fragment: ibuprofen-like skeleton (rank 1, AVGDEV 0.17 ppm)
; SMILES: c1cc(CC(C)C(=O)O)ccc1CC(C)C
SSTR S1 C* (2 3) (1 2)    ; aromatic C
SSTR S2 C* (2 3) (1 2)    ; aromatic C
...
LINK S1 S2
...
```

### Step 4: LSD Integration
lsd-engineer adds to compound.lsd:
```
; === Fragment constraints ===
DEFF F1 'analysis/iteration_02/fragment.def'
FEXP 'F1'
```

Then runs LSD. Solution count drops from 7 to 1 (in the Sherlock ibuprofen example).

### Step 5: Constraint Inventory Update
lsd-engineer adds to the JSON inventory block in the LSD header:
```json
{
  "fragments": [
    {"rank": 1, "smiles": "...", "avgdev": 0.17, "heavy_atoms": 13, "iteration_applied": 2}
  ]
}
```

Devils-advocate verifies DEFF/FEXP present in current iteration before each LSD run.

---

## Search Algorithm Parameters (Defaults from Sherlock)

| Parameter | Default | Description | Source |
|-----------|---------|-------------|--------|
| Max fragment sphere (atom-centered) | 3 | Breadth-first radius from each non-H atom | Wenk thesis §3.1.4.1.4 |
| Max fragment sphere (ring-centered) | 1 | Radius around complete ring systems | Wenk thesis §3.1.4.1.4 |
| Max ring size for ring detection | 6 | Only rings with ≤6 heavy atoms kept whole | Wenk thesis §3.1.4.1.4 |
| Fingerprint bit width | 2 ppm | Each bit covers a 2 ppm bin | Wenk thesis §3.1.4.1.4 |
| Fingerprint range | 0-510 ppm | Covers all practical 13C shifts | Wenk thesis Fig. 26-27 |
| Fingerprint bits total | 256 | 510/2 = 255 bins, round to 256 | Wenk thesis §3.1.4.1.4 |
| Tolerance expansion | ±1 bin | Each set query bit expands to neighbors | Wenk thesis §3.1.4.1.4 |
| Fine match DEV | 2 ppm | Max per-signal deviation | Wenk thesis §3.1.4.1.4 |
| Fine match AVGDEV | 1 ppm | Max average deviation across matched signals | Wenk thesis §3.1.4.1.4 |
| Multiplicity match required | true | Query and fragment atom must have same H count | Wenk thesis §3.1.4.1.4 |
| Equivalence match required | true | Equivalence count must match | Wenk thesis §3.1.4.1.4 |
| Fragment ranking primary | heavy atom count desc | Larger fragments = stronger constraint | Wenk thesis Table 5 |
| Fragment ranking secondary | AVGDEV asc | Better spectral fit preferred | Wenk thesis Table 5 |
| Fragments used per LSD run | 1 (first) | Only first fragment injected by default | Wenk thesis §4.2.2 |

---

## Bond-Preservation Rules (Fragmentation Algorithm)

These rules determine which bonds are NOT cut during breadth-first fragmentation. A bond is preserved (atom kept, not replaced by R) when ANY of the following holds:

1. **Heteroatom-heteroatom bond:** Both endpoint atoms are non-carbon (e.g., O-N, O-P). These encode functional group connectivity that must be preserved.

2. **Bond order > 1:** Double or triple bonds encode hybridisation information. Always preserved.

3. **Carbon bonded to multiple heteroatoms:** If a carbon connects to more than one non-carbon heavy atom (e.g., carboxyl carbon C(=O)O, which bonds to two oxygens), those bonds are preserved. This retains functional group context.

4. **Ring atoms:** Any atom in a ring (detected using SSSR) is treated as part of the complete ring system. The entire ring (including all ring atoms and ring bonds) becomes a single starting point with radius 1 sphere, not just an individual atom with radius 3.

When none of these conditions holds, the connected atom is replaced by R (an open-site pseudo-atom indicating an attachment point). Bond type to R is preserved (single R, double R=, etc.).

Note: lucy-ng currently uses implicit hydrogens throughout HOSE code generation (no `AddHs()`). The same approach must be applied consistently during SSC extraction — work with RDKit molecules without explicit hydrogens.

---

## Expected Impact

Based on Sherlock's published results (HIGH confidence — from Wenk thesis §4.2.2):

| Metric | Sherlock Result | lucy-ng Baseline | Expected After v5.0 |
|--------|-----------------|------------------|---------------------|
| Cases reduced by first fragment | 27/40 had multiple solutions; 27 reduced | N/A | Similar reduction expected |
| Cases reduced to single solution | 34/40 | 1/1 tested (ibuprofen failed — not fragmented) | Target: 34/40 parity |
| Ibuprofen solution count | 2 → 1 (with fragment) | 7 (all wrong due to 4J) | Unknown — depends on whether correct structure is in solution set |
| Fragment search time (per CASE run) | <2 seconds (Java/MongoDB) | TBD (Python/SQLite) | Likely 10-30 seconds (acceptable) |
| Library size | 24.5M SSCs (892K compounds) | N/A | ~26M SSCs expected (928K compounds) |

**Important caveat:** Ibuprofen specifically may not benefit from fragment search if the 4J HMBC constraint problem persists. Fragment constraints only help select among valid solutions — if the correct structure is excluded by wrong HMBC constraints (4J problem), no fragment can fix that. Fragment library (v5.0) and 4J detection (v5.1) are complementary.

---

## Competitor Feature Analysis

| Feature | Sherlock | ACD/Structure Elucidator | lucy-ng v5.0 |
|---------|----------|--------------------------|--------------|
| Fragment library size | 24.5M SSCs | Large (proprietary, commercial) | ~26M SSCs (from 928K compounds) |
| Fragment pre-screening | 256-bit bitsets, Boolean AND | Unknown (commercial) | 256-bit bitsets, Boolean AND (matching Sherlock) |
| Fine matching | DEV/AVGDEV + multiplicity | Unknown | DEV/AVGDEV + multiplicity (matching Sherlock) |
| Fragment injection | DEFF/FEXP goodlist | Automated goodlist | DEFF/FEXP goodlist (same LSD mechanism) |
| Fragments per run | 1 (first) | Multiple (automated) | 1 default, N optional |
| Impact (single solution) | 34/40 (85%) | High (commercial, not benchmarked) | Target 34/40 parity |
| Autonomous operation | No (manual GUI) | No (requires user interaction) | Yes (agent-driven) — lucy-ng advantage |
| Speed | <2 seconds (Java/MongoDB) | Fast (commercial) | Slower (Python/SQLite) but acceptable |

---

## Sources

**HIGH confidence (authoritative):**
- Wenk, M. (2023). *Development of a System for Computer-Assisted Structure Elucidation of Small Organic Compounds.* PhD Thesis, Friedrich-Schiller-Universitat Jena. (`background/wenk-thesis.txt` and `background/Dissertation Michael Wenk.pdf`) — Primary specification source for all SSC algorithm parameters, bond-preservation rules, fingerprint dimensions, thresholds, and impact statistics.
- `background/sherlock-analysis.md` — Project-specific synthesis of Sherlock capabilities vs. lucy-ng gaps, updated 2026-02-19.
- `src/lucy_ng/database/schema.py` — Existing v6 schema; v7 extension point for fragment table.
- `src/lucy_ng/dereplication/` — Existing fine-matching algorithm (reusable for fragment fine matching).
- `.planning/PROJECT.md` — Current milestone definition and deferred feature list.

**MEDIUM confidence:**
- Sherlock casekit library (GitHub: github.com/michaelwenk/casekit) — Java implementation of fragmentation and fragment search. Provides implementation reference but requires translation to Python/RDKit.
- Elyashberg, M. et al. — Referenced in thesis (Chapter 7.4.1) as inspiration for SSC approach. Not directly accessed.

---

*Feature research for: v5.0 Fragment Library and SSC Search*
*Researched: 2026-02-19*

# Domain Pitfalls: Statistical Detection for CASE

**Domain:** Adding statistical detection to existing HOSE-based CASE system
**Researched:** 2026-02-10
**Confidence:** HIGH (informed by Sherlock analysis, RDKit documentation, lucy-ng architecture)

---

## Critical Pitfalls

Mistakes that cause prediction failures, data inconsistencies, or system rewrites.

### Pitfall 1: HOSE Code Hydrogen Consistency Violation

**What goes wrong:** Extracting hybridisation or bond partner statistics from molecules WITH explicit hydrogens, while the existing HOSE prediction pipeline uses molecules WITHOUT explicit hydrogens. This creates a fundamental mismatch where statistical queries return data based on H-included environments but predictions use H-excluded environments.

**Why it happens:**
- RDKit's `GetHybridization()` and `GetNeighbors()` are straightforward to use after `AddHs()`
- Natural to think "I need complete molecular graph to analyze bonding"
- The critical architecture decision in CLAUDE.md is easy to overlook during feature development
- HOSE codes from `mol` vs `AddHs(mol)` are structurally different for the same atom

**Consequences:**
- **100% prediction failure rate** - statistics won't match HOSE lookup keys
- Example: Ethanol carbon-0 with implicit H generates `"C-4;C(//)"`; with explicit H generates `"C-4;HHHC(//)"`
- Database queries for hybridisation/neighbours return zero results or wrong environments
- Silent failure - code runs, just produces wrong constraints
- Very difficult to debug without understanding HOSE internals

**Prevention:**

```python
# CORRECT - matches lucy-ng architecture
mol = Chem.MolFromSmiles("CCO")  # implicit H only
for atom in mol.GetAtoms():
    if atom.GetSymbol() == "C":
        hybridization = atom.GetHybridization()  # works with implicit H
        neighbors = [n.GetSymbol() for n in atom.GetNeighbors()]  # excludes H
        # Use GetNumImplicitHs() + GetNumExplicitHs() to count hydrogens
        h_count = atom.GetNumImplicitHs() + atom.GetNumExplicitHs()

# WRONG - breaks HOSE consistency
mol_h = Chem.AddHs(Chem.MolFromSmiles("CCO"))
for atom in mol_h.GetAtoms():
    neighbors = [n.GetSymbol() for n in atom.GetNeighbors()]  # includes H atoms!
```

**Detection:**
- CLI test: `lucy predict c13 "CCO"` should return predictions with mean/std/count > 0
- If adding hybridisation detection, test same molecule: should return frequencies that sum to ~100%
- Unit test: verify HOSE code from stats molecule == HOSE code from prediction molecule
- Warning sign: "No matching HOSE codes found" for common fragments in statistical queries

**Phase impact:** Phase 34-01 (hybridisation detection) and 34-02 (neighbour detection) must enforce this constraint in all code that processes molecules for statistical analysis.

---

### Pitfall 2: Threshold Over-Sensitivity Without User Override

**What goes wrong:** Hardcoded detection thresholds (1% NN, 95% SN, 1% HHB) work for most cases but fail for edge cases, forcing users to abandon the system or manually edit LSD files. Sherlock's 37/45 success with defaults, 5/45 requiring overrides demonstrates this is a real problem.

**Why it happens:**
- Developer chooses "reasonable" defaults from literature (Sherlock thesis)
- Works for 80-90% of test cases, seems fine
- Edge cases emerge only during production use with diverse compound classes
- No escape hatch for the AI agent to adjust thresholds when patterns fail

**Consequences:**
- **Agent gets stuck in loops:** Detection says "mandatory", but LSD can't satisfy → 0 solutions → agent retries with same constraints
- Example from Sherlock: Case required lowering NN threshold to 0.5% for rare heteroatom neighbors
- Without override mechanism, the only fix is to disable statistical detection entirely
- Loss of confidence in the system: "It works except when it doesn't, and then there's nothing I can do"

**Real failure modes from Sherlock:**

| Case | Issue | Required Override |
|------|-------|-------------------|
| 5/45 cases | Rare heteroatom patterns | NN threshold 1% → 0.5% |
| 3/45 cases | Unusual hybridisation states | Hybridisation threshold 1% → 0.1% |
| 2/45 cases | Multiple constraint conflicts | Disable mandatory SN temporarily |

**Prevention:**

1. **CLI design with override flags:**
```bash
# Default behavior
lucy detect hybridisation --shift 180.5 --multiplicity 0

# Override threshold
lucy detect hybridisation --shift 180.5 --multiplicity 0 --min-frequency 0.005

# Or use strict/relaxed presets
lucy detect hybridisation --shift 180.5 --multiplicity 0 --mode relaxed
```

2. **Agent intervention protocol:** Orchestrator detects "0 solutions with statistical constraints" pattern → suggests relaxed thresholds in advisory intervention

3. **Document threshold semantics:**
   - `min_frequency=0.01` → "exclude states seen < 1% of the time"
   - `mandatory_frequency=0.95` → "require elements seen > 95% of the time"
   - `relaxed mode` → halve all exclusion thresholds (0.01 → 0.005)

**Detection:**
- Warning sign: LSD produces 0 solutions when statistical detection is ON, >0 solutions when OFF
- Log the actual frequency values when excluding/requiring elements
- Test suite should include known edge cases (e.g., rare heteroatoms, unusual oxidation states)

**Phase impact:** Phase 34-01 through 34-03 must include threshold override parameters. Phase 34-06 (agent integration) must teach intervention protocol.

---

### Pitfall 3: Circular Validation Risk (Same Data for Constraints and Ranking)

**What goes wrong:** Using the HOSE database for BOTH statistical constraint generation (pre-LSD) AND solution ranking (post-LSD) creates a circular reasoning risk. If the database has systematic biases (e.g., over-representation of aromatic carbons), both constraints and ranking will reinforce those biases, potentially excluding valid but under-represented structures.

**Why it happens:**
- Same database (928K compounds) is the only available training data
- Convenient to use existing HOSE stats for all statistical operations
- Not obvious that constraint generation and ranking are logically distinct validation steps
- No independent validation dataset to catch the circularity

**Consequences:**
- **Systematic bias toward database-common structures:** Novel natural products with rare structural features get lower confidence
- Example: If database has 90% aromatic C-O bonds (phenols) and 10% aliphatic C-O bonds (alcohols), constraints will favor aromatic, ranking will favor aromatic → alcohol misidentified
- **False confidence:** Both steps agree, but only because they share the same biases
- **Training data leakage:** If test compounds are in the HOSE database, they'll be artificially favored

**Is this actually a problem?**

Sherlock's success (40/45 solved, 38/40 at rank #1) suggests the circular risk is MITIGATED by:
1. Database size (892K compounds) provides diverse coverage
2. Constraints are threshold-filtered (only strong patterns, >95% or <1%)
3. LSD's combinatorial search still explores constraint-satisfying space

However, lucy-ng's ibuprofen failure shows the RISK when constraints are wrong:
- Statistical detection might have said "sp2 carbons at 44-45 ppm are rare" → exclude
- But ibuprofen HAS sp3 carbons there → constraint would worsen the problem

**Prevention:**

1. **Acknowledge limitation in documentation:**
   - "Statistical detection is trained on the same database used for ranking. For novel compound classes not well-represented in COCONUT/NMRShiftDB, constraints may be over-restrictive."

2. **Validation approach:**
   - Hold out 10% of database compounds during HOSE stats generation
   - Test constraint quality on held-out set: do constraints exclude correct structure?
   - Measure: "% of held-out compounds where correct structure satisfies all statistical constraints"

3. **Agent fallback protocol:**
   - If LSD produces 0 solutions with statistical constraints, agent should try WITHOUT constraints
   - If solutions appear, flag as "low confidence - statistical constraints may not apply"

4. **Threshold conservatism:**
   - Use strict thresholds (1% NN, 95% SN) as documented in Sherlock
   - These minimize false exclusions at cost of allowing more solutions (then ranking filters)

**Detection:**
- Warning sign: Test compound gives 0 solutions with stats, >0 without stats, and manual inspection shows correct structure violated a statistical constraint
- Validation metric: "constraint violation rate on held-out test set"
- Long-term: track cases where agent disabled stats to solve → pattern indicates under-represented compound class

**Phase impact:** Not a blocker, but Phase 34 planning should include validation protocol. Documentation should acknowledge this limitation. Phase 34-06 (agent integration) should include fallback behavior.

---

### Pitfall 4: COCONUT Predicted Data Quality Unknown for Bond Statistics

**What goes wrong:** 96.87% of HOSE data comes from COCONUT (predicted spectra using NMRShiftDB model, not experimental). Hybridisation detection queries chemical shifts (prediction quality known ~2 ppm MAE), but neighbourhood/bond statistics require extracting molecular graph features (hybridisation type, bond partners) from COCONUT structures. If COCONUT structures have errors (wrong stereochemistry, tautomers, protonation states), bond statistics will be systematically wrong.

**Why it happens:**
- COCONUT aggregates 63+ databases with varying curation quality
- Structures are "as-deposited" from original sources
- No systematic validation of bond assignments, hybridisation states, tautomeric forms
- Easy to assume "structure is structure" without checking quality

**Consequences:**
- **Systematic errors in neighbourhood statistics:** If COCONUT has wrong bond types (single vs aromatic, ether vs alcohol), neighbour frequencies will be wrong
- **Tautomer ambiguity:** Enol vs keto, imine vs amine → different hybridisation states for same carbon shift
- **Protonation state errors:** Neutral vs charged forms → different neighbor counts
- Example: If 20% of carboxylic acids stored as COO- instead of COOH, oxygen neighbor statistics will be skewed

**Evidence from literature:**

Based on research, COCONUT 2.0 (2024 update) aggregates 63+ open NP resources and underwent "comprehensive overhaul and curation" but specific bond-level validation metrics are not reported in search results. The focus is on compound-level curation (duplicates, InChI standardization), not systematic bond assignment validation.

NMR prediction quality: DFT methods achieve ~2.0 ppm MAE for 13C (acceptable for shift-based queries), but bond topology accuracy is a separate concern not addressed in prediction validation.

**Prevention:**

1. **Direct extraction approach (BETTER):**
   - Don't trust COCONUT's bond types or hybridisation labels
   - Extract hybridisation from sanitized RDKit molecule: `atom.GetHybridization()` after `Chem.MolFromSmiles()`
   - RDKit sanitization corrects many structure errors automatically
   - Still vulnerable to wrong input SMILES, but better than as-deposited

2. **Validation sampling:**
   - Manually inspect 100 random COCONUT structures from the database
   - Check: bond orders, hybridisation states, tautomeric forms
   - If >5% have errors, consider filtering (e.g., exclude low-confidence sources)

3. **Cross-reference with NMRShiftDB subset:**
   - NMRShiftDB compounds (3.13% of data) are experimental spectra with curated structures
   - Compare hybridisation/bond statistics from COCONUT-only vs NMRShiftDB-only
   - Large divergence (>10%) indicates COCONUT quality issue

4. **Conservative thresholds:**
   - Use 1% NN threshold as Sherlock does → tolerates some noise
   - Avoid 99%+ thresholds for mandatory neighbors → too strict for noisy data

**Detection:**
- Warning sign: Hybridisation frequencies don't match chemistry intuition (e.g., "90% of carbons at 130 ppm are sp3")
- Validation test: Query known fragment (benzene ring), check if C neighbor frequency ~95% (should be, for aromatic CH)
- Agent confusion: Statistical constraints produce chemically nonsensical LSD files

**Phase impact:** Phase 34-01/34-02 should include validation sampling step. Document data quality caveat. Not a blocker unless validation reveals >10% error rate.

---

### Pitfall 5: Signal Grouping False Positives (0.24 ppm Truly Different)

**What goes wrong:** Sherlock groups signals within 0.25 ppm tolerance and forces combinatorial HMBC exchange, assuming they're ambiguous assignments. But what if two carbons are 0.24 ppm apart AND confidently assigned to different positions based on HSQC multiplicities or other orthogonal data? Forcing combinatorial exchange creates spurious LSD solutions that waste ranking time.

**Why it happens:**
- 0.25 ppm is a reasonable tolerance for 13C ambiguity (experimental uncertainty ~0.1 ppm, prediction error ~2 ppm)
- Sherlock's algorithm is simple: distance < threshold → group them
- No mechanism to override grouping when user has high confidence in assignment
- AI agent may have used DEPT or other data to disambiguate, but grouping logic doesn't know this

**Consequences:**
- **Combinatorial explosion:** If 3 signals are within 0.25 ppm, all HMBC correlations are 3x duplicated → LSD search space grows cubically
- **Spurious solutions:** Structures that swap the close-shift carbons are generated and must be ranked
- **Wasted compute time:** Ranking hundreds of near-identical solutions that only differ in swapped assignments
- Example: C4 at 44.90, C5 at 45.03, C6 at 45.20 → 3! = 6x search space expansion, 5 of those permutations are likely wrong

**When is grouping correct?**

- **Correct case (ibuprofen):** C4/C5 are 0.13 ppm apart, BOTH are CH2 (indistinguishable by DEPT), HMBC pattern is symmetric → truly ambiguous, grouping is essential
- **False positive case:** C4 at 44.90 (CH2), C5 at 45.03 (CH), C6 at 45.20 (CH3) → multiplicities distinguish them, grouping creates spurious swaps

**Prevention:**

1. **Multiplicity-aware grouping:**
```python
def should_group(shift1, mult1, shift2, mult2, tolerance=0.25):
    """Group only if within tolerance AND same multiplicity."""
    if abs(shift1 - shift2) > tolerance:
        return False
    # Same multiplicity (both CH2) or both ambiguous (CH/CH3) → group
    if mult1 == mult2 or (mult1 in ["CH", "CH3"] and mult2 in ["CH", "CH3"]):
        return True
    return False
```

2. **Agent override mechanism:**
   - If agent has high confidence in assignment (e.g., used COSY to confirm), mark signals as "do not group"
   - CLI flag: `lucy analyze grouping --shifts "44.90,45.03" --no-group-indices 0,1`

3. **Post-ranking filter:**
   - If top 10 solutions only differ by swapped assignments of close signals, collapse them to single representative
   - Report: "Solution #1 and #2 differ only in C4/C5 assignment (0.13 ppm apart)"

4. **Tolerance tuning:**
   - 0.25 ppm is aggressive for cases with DEPT data (multiplicities reduce ambiguity)
   - Consider 0.15 ppm threshold when DEPT is available, 0.25 ppm when not

**Detection:**
- Warning sign: LSD produces 100+ solutions, top 10 all have MAE <0.5 ppm and differ only in assignment of close signals
- Test case: Compound with 3 carbons at 45.0, 45.1, 45.2 ppm with DIFFERENT multiplicities (CH, CH2, CH3) → grouping should NOT force combinatorial exchange
- Agent log: "Grouping created NNN permutations" where NNN > 100

**Phase impact:** Phase 34-04 (signal grouping) should implement multiplicity-aware logic, not just distance threshold. Phase 34-06 (agent integration) should teach when to override.

---

### Pitfall 6: Database Size Explosion from Per-Shift Statistics

**What goes wrong:** Storing hybridisation and neighbourhood statistics AT THE SHIFT LEVEL (not HOSE code level) creates massive new tables. With 928K compounds × 13C shifts per compound (avg ~20) × hybridisation states (3) × elements (C, O, N, etc.) = potentially 50M+ rows for neighbourhood stats alone.

**Why it happens:**
- Naive design: "For each shift, store hybridisation frequencies and neighbor frequencies"
- Seems simpler than HOSE-based lookup
- Doesn't account for sparsity: most shift/element combinations never occur
- SQLite can handle it, but queries become slow and database size balloons

**Consequences:**
- **Database size explosion:** 2.8 GB current → potentially 10+ GB with per-shift statistics
- **Slow queries:** Finding neighbours for shift=180.5 ppm requires scanning millions of rows
- **Redundant storage:** Shifts at 180.4, 180.5, 180.6 ppm likely have SAME statistics (all sp2 carbonyl), but stored separately
- **Download/distribution problem:** Users must download 10 GB database instead of 2.8 GB

**Sherlock's approach (from thesis):**

- Query HOSE database with shift tolerance (±2 ppm)
- Find all HOSE codes matching shift range
- Extract structures for those HOSE codes
- Compute statistics ON THE FLY from matching structures

This avoids pre-computing shift-level statistics. Cost: slower query (but acceptable for interactive use).

**Better approaches:**

**Option A: HOSE-based lookup (Sherlock's approach)**
```sql
-- Query: What hybridisations exist at shift 180.5 ppm?
-- Step 1: Find HOSE codes with mean within tolerance
SELECT DISTINCT hose_code FROM hose_stats
WHERE mean BETWEEN 178.5 AND 182.5 AND radius = 6;

-- Step 2: For each HOSE code, extract structure and get hybridisation
-- (Requires re-parsing structures, but no new tables)
```

**Option B: Binned statistics (2 ppm bins)**
```sql
-- Pre-compute statistics in 2 ppm bins (0-2, 2-4, ..., 218-220)
CREATE TABLE shift_bins (
    bin_start REAL,
    element TEXT,
    hybridisation TEXT,
    frequency REAL,
    PRIMARY KEY (bin_start, element, hybridisation)
);
-- Only 110 bins × 10 elements × 3 hybrids = 3,300 rows (tiny!)
```

**Option C: Compound-level extraction (store structures, compute on query)**
```sql
-- Don't store statistics at all
-- Query compounds with shifts in range, extract hybridisation from SMILES
-- Slower but zero storage overhead
```

**Recommendation:**

Use **Option B** (binned statistics) for hybridisation (fast, small). Use **Option A** (HOSE-based) for neighbourhood detection (leverages existing HOSE data). Avoid Option C (too slow for interactive use).

**Prevention:**

1. **Design review before implementation:**
   - Estimate table sizes BEFORE writing code
   - Formula: rows = compounds × avg_carbons × dimensions
   - If >10M rows, reconsider design

2. **Test with full database:**
   - Generate statistics on full 928K compound database
   - Measure: storage size, query time, index size
   - Reject design if query time >1 second or size >5 GB

3. **Use binning for coarse features:**
   - Hybridisation: 2 ppm bins (110 bins total, tiny table)
   - Neighbours: HOSE-based (reuse existing data)
   - Hetero-hetero bonds: global statistic (single value!)

**Detection:**
- Warning sign during development: `CREATE TABLE` statement estimates >10M rows
- Benchmark query time on small sample (1K compounds) and extrapolate to 928K
- Monitor database file size during generation: if growing >100 MB/hour, design is wrong

**Phase impact:** Phase 34-01 (hybridisation) and 34-02 (neighbours) MUST include storage design review. Recommend binning for 34-01, HOSE-lookup for 34-02, global stat for 34-03 (HHB).

---

### Pitfall 7: Agent Workflow Confusion (Stats Contradict NMR Knowledge)

**What goes wrong:** The CASE agent currently writes LSD files using inlined NMR knowledge ("carbons at 120-140 ppm are typically sp2"). Statistical detection may return different results ("87% sp2, 13% sp3 at 125 ppm"). When agent receives contradictory guidance, it may:
- Ignore statistical detection (defeating the purpose)
- Over-trust statistics and violate basic chemistry
- Get stuck in decision paralysis
- Write malformed LSD files trying to satisfy both

**Why it happens:**
- Agent has 666 lines of CASE knowledge, including shift range heuristics
- Statistical detection is new information source without integration guidance
- No clear hierarchy: "When stats contradict knowledge, which wins?"
- Agent's prompt doesn't explain HOW to use statistical output

**Consequences:**
- **Agent ignores stats:** Defeats the purpose of adding statistical detection
- **Agent over-trusts stats:** Example: "Database says 5% sp1 at 130 ppm" → agent writes `MULT 1 C 1 0` (alkyne) for an aromatic signal → chemically nonsensical
- **Prompt confusion:** "I detected sp2 from shift range, but lucy detect says sp3. Which should I use?"
- **Loop risk:** Agent tries stats → fails → tries knowledge → fails → repeats

**Real example from lucy-ng memory:**

Pitfall 6 rewrite (from ibuprofen CASE): "Don't over-constrain heteroatoms. Only BOND C=O. Use LIST/ELEM/PROP for flexible connectivity." This shows the agent already has guidance on constraint conservatism. Statistical detection must fit this philosophy.

**Prevention:**

1. **Agent integration guidance (in lucy-case-agent.md):**

```markdown
## Statistical Detection Protocol

Use statistical detection to AUGMENT NMR knowledge, not replace it.

**Hierarchy:**
1. Chemistry first: Never violate basic chemistry (e.g., sp1 carbon at aromatic shift)
2. Statistics second: Use to narrow among chemically valid options
3. Knowledge third: Fall back to shift ranges if statistics unavailable

**Example:**
- Signal at 130 ppm, multiplicity CH
- NMR knowledge: "120-140 ppm is typically sp2 (aromatic or alkene)"
- Statistical query: `lucy detect hybridisation --shift 130 --multiplicity 1`
  → Returns: {sp2: 92%, sp3: 7%, sp1: 1%}
- Decision: Use sp2 (stats confirm knowledge)
- LSD: `MULT 1 C 2 1` (sp2, 1H)

**Contradiction example:**
- Signal at 125 ppm, multiplicity CH
- Stats return: {sp3: 60%, sp2: 40%}
- Contradiction detected (aromatic shift with sp3 majority?)
- Resolution: Trust chemistry → use sp2, flag stats as low-confidence
```

2. **CLI design to minimize ambiguity:**

```bash
# Output should include confidence and chemistry check
lucy detect hybridisation --shift 125 --multiplicity 1

# Output:
# {
#   "shift": 125.0,
#   "hybridisations": {
#     "sp2": {"frequency": 0.92, "count": 1523},
#     "sp3": {"frequency": 0.07, "count": 115},
#     "sp1": {"frequency": 0.01, "count": 18}
#   },
#   "recommendation": "sp2",
#   "confidence": "HIGH",
#   "chemistry_check": "PASS (aromatic/alkene shift range)"
# }
```

3. **Orchestrator intervention when agent ignores stats:**
   - Pattern: Agent ran statistical detection, received result, wrote LSD without using it
   - Advisory: "You detected sp2 at 130 ppm but wrote sp3 MULT. Reconsider using statistical result."

4. **Test scenarios in agent training:**
   - Scenario 1: Stats confirm knowledge (easy case)
   - Scenario 2: Stats contradict knowledge (chemistry wins)
   - Scenario 3: Stats provide NO data (fall back to knowledge)
   - Scenario 4: Stats ambiguous (sp2: 52%, sp3: 48%) → agent decides based on other evidence

**Detection:**
- Warning sign: Agent writes LSD files identical to v2.1 behavior (not using stats at all)
- Log analysis: "lucy detect" commands run but MULT lines don't reflect output
- Test case: Give agent a compound where stats differ from shift-range heuristic → verify correct resolution

**Phase impact:** Phase 34-06 (agent integration) is CRITICAL. Must include extensive testing of stats-vs-knowledge scenarios. Update lucy-case-agent.md with clear hierarchy and examples.

---

## Moderate Pitfalls

Mistakes that cause delays, suboptimal results, or require rework but don't break the system.

### Pitfall 8: Two-Tier Ranking Edge Cases (Fewer Matches, Lower MAE)

**What goes wrong:** Two-tier ranking (match count first, MAE second) correctly handles most cases, but edge case exists: what if the CORRECT structure has 10/13 matching signals (MAE 1.8 ppm) while an INCORRECT structure has 13/13 matches (MAE 2.1 ppm) because all its predictions happened to fall within tolerance by coincidence?

**Real case from Sherlock:**

Case 21 (3-hydroxy-drimenol): Correct solution had 10/13 matching signals, incorrect had 13/13 but lower quality matches. Two-tier ranking caught this BECAUSE match count won. But the opposite can occur for novel compounds with many fallback-only HOSE matches.

**Why it happens:**
- HOSE fallback mechanism (radius 6 → 5 → 4 → ... → 1) means rare structures get low-radius matches
- Low-radius matches have high variance (std ~10 ppm at radius 1)
- By chance, some low-radius predictions land within 10 ppm tolerance → counted as "match"
- Wrong structure with MORE common fragments gets more matches

**Prevention:**

1. **Weighted match counting:**
```python
# Don't count all matches equally
match_score = 0
for atom in structure:
    predicted_shift, radius_used = predict_with_radius(atom)
    if abs(predicted_shift - experimental_shift) < 10:  # within tolerance
        # Weight by radius used (radius 6 = 1.0, radius 1 = 0.2)
        match_score += radius_used / 6.0
```

2. **Report HOSE radii in ranking output:**
```
Rank #1: SMILES, matches=10/13, MAE=1.8 ppm
  - 7 matches at radius 6 (high confidence)
  - 2 matches at radius 4 (medium confidence)
  - 1 match at radius 2 (low confidence)

Rank #2: SMILES, matches=13/13, MAE=2.1 ppm
  - 3 matches at radius 6
  - 5 matches at radius 4
  - 5 matches at radius 1 (suspicious - many fallbacks)
```

3. **Flag all-fallback solutions:**
   - If >50% of matches are radius ≤2, mark as "LOW CONFIDENCE - novel structure"

**Detection:**
- Test case: Novel natural product with unique fragment → verify ranking doesn't favor common-fragment wrong structure
- Manual inspection of test failures: check if wrong structure at rank #1 has many low-radius matches
- Agent confusion: "Rank #1 looks wrong but has more matches than rank #2"

**Phase impact:** Phase 34-05 (two-tier ranking) should include radius-weighted scoring or at minimum report radius distribution. Not a blocker but improves ranking quality.

---

### Pitfall 9: No Validation Dataset for Statistical Detection Quality

**What goes wrong:** Adding statistical detection without held-out validation means you can't measure whether constraints are HELPING or HURTING. Did solution count drop because constraints are good, or because they're excluding the correct structure?

**Why it happens:**
- Eager to ship: "Sherlock's thresholds work, we'll use those"
- No time budgeted for validation infrastructure
- Assumes "more constraints = better" without testing

**Consequences:**
- Can't answer: "What % of test cases have correct structure satisfying all statistical constraints?"
- Can't detect regression: If database changes (new COCONUT version), constraints might get worse
- Can't optimize thresholds: Is 1% better than 0.5% for NN threshold? Unknown without data

**Prevention:**

1. **Create validation set:**
   - Use Sherlock's 45 test cases (DOIs in thesis Table 13)
   - Download from nmrXiv, sanitize, run through lucy-ng pipeline
   - For each case, check: does correct structure satisfy statistical constraints?

2. **Metrics to track:**
   - **Constraint accuracy:** % of cases where correct structure satisfies all constraints
   - **Search space reduction:** Median solution count with vs without constraints
   - **Rank improvement:** Mean rank of correct structure with vs without constraints
   - **Threshold sensitivity:** Rerun with 0.5%, 1%, 2% thresholds → which is best?

3. **Regression testing:**
   - Add validation cases to test suite
   - CI fails if constraint accuracy drops below 90%

**Detection:**
- Before Phase 34: No validation dataset exists
- After Phase 34: Validation dataset exists and metrics reported

**Phase impact:** Phase 34-07 (validation) should be added to roadmap. Not critical for initial implementation, but required before v3.0 release.

---

### Pitfall 10: Badlist Filters Applied Too Broadly

**What goes wrong:** Adding 3/4-membered ring filters as Sherlock does, but applying them to ALL compound classes including those where strained rings are common (alkaloids, terpenoids with cyclopropane).

**Why it happens:**
- Sherlock's documentation says "apply by default"
- Natural products literature shows most NPs don't have 3/4-rings
- Easy to hardcode filter without escape hatch

**Consequences:**
- **False exclusion:** Compounds with cyclopropane rings eliminated
- Example: Chrysanthemic acid (pyrethroid precursor) has cyclopropane → badlist excludes correct structure
- Agent has no way to override: "I see HMBC pattern suggesting cyclopropane, but badlist forbids it"

**Prevention:**

1. **Molecular formula hint:**
   - If formula indicates high unsaturation (many rings/double bonds), disable 4-ring filter
   - Cyclopropane compounds often have odd hydrogen counts or low H/C ratio

2. **Agent override:**
   - CLI flag: `--allow-strained-rings`
   - Agent decides based on HMBC pattern: "Correlations suggest cyclopropane, enabling strained rings"

3. **Conservative default:**
   - Apply 3-ring filter (true cyclopropane is rare)
   - Skip 4-ring filter by default (cyclobutane more common in NPs than expected)

**Detection:**
- Test case: Known cyclopropane compound → verify not excluded
- Agent log: "Badlist prevented solutions, retrying with override"

**Phase impact:** Phase 34-05 (badlist) should include override mechanism. Document when strained rings are chemically plausible.

---

## Minor Pitfalls

Mistakes that cause annoyance, suboptimal UX, or minor inefficiencies but are easily fixed.

### Pitfall 11: Statistical Detection Slows CASE Workflow (Too Many CLI Calls)

**What goes wrong:** Agent must run separate `lucy detect` commands for every carbon (e.g., 13 carbons = 13 × 3 CLI calls for hybridisation/neighbours/HHB). Each call has subprocess overhead (~50ms). Total: 13 × 3 × 50ms = 2 seconds of pure overhead.

**Prevention:**

Batch API:
```bash
lucy detect batch --shifts shifts.json --output constraints.json
# Processes all shifts in one call, returns all constraints
```

**Phase impact:** Phase 34-06 (agent integration) should add batch command if profiling shows >5 second overhead.

---

### Pitfall 12: Neighbour Detection Returns Too Many Elements

**What goes wrong:** Neighbourhood detection for a carbonyl carbon at 200 ppm might return: `{C: 65%, O: 30%, N: 3%, S: 1.5%, P: 0.5%}`. With 1% NN threshold, ALL five elements are allowed. LSD search space doesn't shrink much.

**Prevention:**

Report only elements >5% frequency by default:
```bash
lucy detect neighbours --shift 200 --min-report 0.05
# Returns: {C: 65%, O: 30%} (N, S, P below 5%, omitted)
```

**Phase impact:** Phase 34-02 should include min-report threshold.

---

### Pitfall 13: No Human-Readable Summary of Statistical Constraints

**What goes wrong:** Agent runs detection, gets JSON output, writes LSD file. User can't easily see WHAT constraints were applied without parsing LSD commands.

**Prevention:**

Generate summary file:
```markdown
# Statistical Constraints Applied

## Carbon 1 (180.5 ppm, multiplicity 0)
- Hybridisation: sp2 (99.2% frequency)
- Forbidden neighbors: N (<1%), S (<1%)
- Mandatory neighbors: O (96% frequency)
```

**Phase impact:** Phase 34-06 (agent) should write constraints summary to analysis/ folder.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| 34-01 Hybridisation Detection | Pitfall 1 (H consistency), Pitfall 6 (storage) | Use binned stats (2 ppm bins), enforce no-explicit-H in code review |
| 34-02 Neighbour Detection | Pitfall 2 (threshold sensitivity), Pitfall 6 (storage) | HOSE-based lookup, include override flags |
| 34-03 HHB Detection | Pitfall 4 (COCONUT quality) | Global statistic (single query), cross-check with NMRShiftDB subset |
| 34-04 Signal Grouping | Pitfall 5 (false positives) | Multiplicity-aware grouping, document edge cases |
| 34-05 Ranking + Badlist | Pitfall 8 (match quality), Pitfall 10 (cyclopropane) | Report HOSE radii, add override for strained rings |
| 34-06 Agent Integration | Pitfall 7 (workflow confusion), Pitfall 11 (CLI overhead) | Clear hierarchy in prompt, batch API if needed |
| 34-07 Validation (proposed) | Pitfall 9 (no validation) | Use Sherlock's 45 test cases, track metrics |

---

## Success Criteria for Pitfall Avoidance

Before v3.0 release, verify:

- [ ] **Pitfall 1:** Test case confirms HOSE consistency (ethanol prediction works, hybridisation detection works)
- [ ] **Pitfall 2:** CLI includes threshold override flags, documented in agent skill
- [ ] **Pitfall 3:** Documentation acknowledges circular risk, agent has fallback protocol
- [ ] **Pitfall 4:** Validation sampling completed (100 structures inspected), quality >90%
- [ ] **Pitfall 5:** Signal grouping uses multiplicity, not just distance
- [ ] **Pitfall 6:** Database size <5 GB after stats generation, query time <1 sec
- [ ] **Pitfall 7:** Agent integration tested with stats-vs-knowledge scenarios
- [ ] **Pitfall 8:** Ranking reports HOSE radii or uses weighted scoring
- [ ] **Pitfall 9:** Validation dataset created (Sherlock's 45 cases or subset)
- [ ] **Pitfall 10:** Badlist includes override mechanism, tested with cyclopropane

---

## Sources

### RDKit Documentation
- [RDKit Cookbook](https://www.rdkit.org/docs/Cookbook.html) - GetHybridization and molecular operations
- [rdkit.Chem.rdchem module](https://www.rdkit.org/docs/source/rdkit.Chem.rdchem.html) - Atom and bond methods
- [RDKit GitHub Issues #3643](https://github.com/rdkit/rdkit/issues/3643) - Hybridization with hydrogen atoms
- [Where is my H dude? (in GetNeighbors)](https://rdkit-discuss.narkive.com/XIwGn1BT/where-is-my-h-dude-in-getneighbors) - Implicit vs explicit hydrogen handling

### NMR Prediction and HOSE Codes
- [NMR shift prediction from small data quantities](https://jcheminf.biomedcentral.com/articles/10.1186/s13321-023-00785-x) - HOSE code performance metrics
- [Stereo-Aware Extension of HOSE Codes](https://pubs.acs.org/doi/10.1021/acsomega.9b00488) - Enhanced HOSE code methods
- [NMRShiftDB history](https://nmrshiftdb2.sourceforge.io/predictionhistory/history.html) - HOSE code database evolution

### COCONUT Database
- [COCONUT online: Collection of Open Natural Products database](https://jcheminf.biomedcentral.com/articles/10.1186/s13321-020-00478-9) - Original publication
- [COCONUT 2.0](https://academic.oup.com/nar/article/53/D1/D634/7908792) - 2024 comprehensive overhaul
- [COCONUT website](https://coconut.naturalproducts.net/) - Database access

### Sherlock CASE System
- [Sherlock—A Free and Open-Source System for CASE](https://www.mdpi.com/1420-3049/28/3/1448) - Wenk et al. 2023 publication
- [Sherlock PMC version](https://pmc.ncbi.nlm.nih.gov/articles/PMC9920390/) - Full text
- [Sherlock GitHub](https://github.com/michaelwenk/sherlock) - Source code

### NMR Prediction Performance
- [Accurate Prediction of 1H NMR Chemical Shifts](https://pmc.ncbi.nlm.nih.gov/articles/PMC11123270/) - Machine learning approaches
- [Transfer Learning from Simulation to Experimental Data](https://pubs.acs.org/doi/10.1021/acs.jpclett.1c00578) - DFT vs HOSE methods
- [NMRexp: A database of 3.3 million experimental NMR spectra](https://www.nature.com/articles/s41597-025-06245-5) - Experimental vs predicted quality

---

**Overall Assessment:** The highest-risk pitfalls are #1 (HOSE hydrogen consistency - causes 100% failure), #2 (threshold sensitivity - causes unsolvable edge cases), and #7 (agent workflow confusion - defeats the feature's purpose). Remaining pitfalls are manageable with good design and testing.

**Confidence Level:** HIGH for pitfalls 1-7 (informed by lucy-ng architecture, Sherlock analysis, RDKit documentation). MEDIUM for pitfalls 8-10 (edge cases, less documentation). LOW for pitfalls 11-13 (UX/performance issues, speculative).

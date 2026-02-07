---
name: lucy-ng
description: Computer-Assisted Structure Elucidation (CASE) for organic natural products using NMR spectroscopy. Use when the user asks to identify an unknown compound from NMR data, perform structure elucidation, analyze HSQC/HMBC/DEPT/COSY spectra, run dereplication against natural product databases (COCONUT, NMRShiftDB), generate LSD solver input, rank candidate structures by 13C prediction, or determine molecular structure from Bruker NMR data. Requires molecular formula and Bruker-format NMR spectra.
tools:
  - read_spectrum_1d
  - read_spectrum_2d
  - pick_peaks_1d
  - pick_hsqc_peaks
  - pick_hmbc_peaks
  - analyze_symmetry
  - dereplicate_c13
  - check_lsd_availability
  - generate_lsd_input
  - run_lsd
  - rank_lsd_solutions
  - predict_c13_shifts
  - get_hose_stats_info
  - fetch_nmrxiv_dataset
  - generate_correlation_diagram
---

# lucy-ng CASE Domain Knowledge

This document contains all domain knowledge needed for Computer-Assisted Structure Elucidation (CASE). An AI agent performing structure elucidation should consult this document for NMR spectroscopy background, peak picking strategies, symmetry detection, dereplication, LSD constraint building, ranking, and workflow guidance.

---

## 1. NMR Background

### Experiment Types and Information

| Experiment | Information Provided | Key Insight |
|------------|---------------------|-------------|
| **1H** | Proton chemical shifts | Hydrogen environment |
| **13C** | Carbon chemical shifts | All carbons including quaternary |
| **DEPT-135** | Protonated carbons only | CH/CH3 positive, CH2 negative |
| **DEPT-90** | CH only | Distinguishes CH from CH3 |
| **HSQC** | Direct C-H connections | Which H is attached to which C |
| **HMBC** | 2-3 bond C-H correlations | Connectivity through bonds |
| **COSY** | H-H correlations | Adjacent protons |

### 13C Chemical Shift Regions

| Region (ppm) | Typical Assignment |
|--------------|-------------------|
| 0-50 | Aliphatic carbons (CH3, CH2, CH) |
| 50-90 | Carbons attached to oxygen (C-O) |
| 90-120 | Anomeric carbons, alkenes |
| 120-160 | Aromatic carbons, alkenes |
| 160-180 | Carboxylic acids, esters, amides |
| 180-220 | Aldehydes, ketones |

### Common Pitfalls

#### Pitfall 1: Signal Count ≠ Atom Count (Symmetry)

Molecular symmetry causes equivalent atoms to produce overlapping signals. If the molecular formula indicates 13 carbons but only 10-11 peaks appear in the 13C spectrum, this is usually symmetry, not missing data. Use `analyze_symmetry` to detect discrepancies. Check HSQC intensities - doubled signals show ~2x intensity. Common symmetric motifs: para-substituted benzene (2 pairs of equivalent CH), isopropyl groups (2 equivalent CH3), gem-dimethyl groups, symmetric ethers/esters. If formula hydrogens exceed the sum of (multiplicity × count) from HSQC, equivalent positions are present.

#### Pitfall 2: Quaternary Carbons Are Invisible in DEPT/HSQC

Quaternary carbons (no attached H) appear in 13C but not in DEPT or HSQC. The difference between 13C peak count and DEPT-135 peak count equals the number of quaternary carbons. These connect only through HMBC correlations. Common quaternary carbons: carbonyl C=O (160-220 ppm), aromatic junction carbons (120-160 ppm), bridgehead carbons.

#### Pitfall 3: HMBC Noise Creates False Correlations

Raw HMBC peak picking finds hundreds of peaks, most of which are noise (t1 noise, 1J bleeding). Always use guided HMBC picking. See Peak Picking Strategy section. Guided picking validates carbon positions against 13C/DEPT and proton positions against HSQC, reducing peak count from hundreds to tens. More correlations improve LSD results only if they are real.

#### Pitfall 4: Too Many LSD Solutions

Hundreds or thousands of LSD solutions indicate insufficient constraints. Common causes: missing HMBC correlations, incorrect multiplicities, unaccounted symmetry, quaternary carbons with no HMBC connections. See LSD Reference section for troubleshooting. Do not use ELIM prematurely.

#### Pitfall 5: Heteroatom Positions

Oxygen and nitrogen atoms do not appear directly in standard NMR. Infer positions from: molecular formula (count), chemical shifts (C-O at 50-90 ppm, carbonyl at 160-220 ppm), and HMBC connectivity. See LSD Reference section for heteroatom constraint strategies (BOND vs LIST/PROP).

---

## 2. Spectral Quality Assessment

### When to Assess

Assess quality of EVERY spectrum before peak picking. Start with 1D spectra (13C, DEPT), then 2D (HSQC, HMBC). Quality assessment comes BEFORE any peak picking or analysis. Quality findings actively modify the agent's strategy.

### S/N Ratio Evaluation (QUAL-01)

Compute signal-to-noise ratio relative to the spectrum's own noise floor (NOT fixed absolute values).

**Noise floor calculation:** Median of absolute data values in a quiet region (e.g., -5 to -2 ppm for 13C, or any region clearly free of peaks).

**SNR = tallest peak / noise floor**

**Quality tiers with strategy adjustments:**

| SNR Range | Quality | Strategy Adjustments |
|-----------|---------|---------------------|
| > 100 | Excellent | Use default threshold (0.05), trust all validated peaks |
| 30-100 | Good | Use default threshold (0.05-0.08), standard tolerances |
| 10-30 | Moderate | Raise threshold to 0.10, widen tolerances, trust only top 50% of HMBC correlations by intensity, use batch size 3 (not 5) for HMBC iteration |
| < 10 | Poor | Raise threshold further, expect missed peaks, reduce trusted HMBC to top 25%, document significant quality caveats in results, consider requesting re-acquisition |

These thresholds are pragmatic defaults subject to refinement based on real-world usage.

### Digital Resolution Impact (QUAL-02)

**Digital resolution** = number of data points per ppm in the 13C dimension. Low resolution causes peaks to merge and increases positional uncertainty.

**Resolution tiers:**

| Pts/ppm | Quality | Strategy Adjustments |
|---------|---------|---------------------|
| > 10 | Excellent | Standard ±1.5 ppm tolerance |
| 5-10 | Good | Standard tolerance acceptable |
| 2-5 | Moderate | Increase tolerance to ±2.0 ppm, expect aliasing, close carbons (< 2 ppm apart) may be unresolvable |
| < 2 | Poor | Increase tolerance to ±3.0 ppm, warn user about severe limitations |

**Critical for HMBC:** If 13C dimension has < 5 pts/ppm, two carbons within 2 ppm cannot be reliably distinguished. Mark all correlations involving close carbons as AMBIGUOUS.

### Artifact Recognition (QUAL-03)

Three artifacts most relevant for automated CASE:

#### 1J Leakage (HMBC)

HMBC experiments suppress but do not fully eliminate direct 1JCH couplings. Strong peaks in HMBC that appear at the same (C, H) position as an HSQC peak are likely 1J artifacts, NOT long-range correlations.

**Detection:** If an HMBC peak is within ±1.5 ppm (carbon) of any HSQC correlation AND the proton shifts match within ±0.3 ppm, flag as potential 1J artifact.

**Impact:** Including 1J artifacts as HMBC constraints tells LSD that "C is 2-3 bonds from H" when in fact C is directly bonded to H. This creates impossible constraints and zero solutions.

**Action:** Exclude flagged peaks from HMBC constraint list; document exclusions.

#### t1 Noise (2D spectra)

Manifests as horizontal streaks in the F1 (indirect) dimension of 2D spectra. More common in non-gradient-selected experiments.

**Impact:** Creates false peaks at correct 1H positions but incorrect 13C positions.

**Action:** If > 20% of "validated" HMBC peaks cluster at identical proton positions across different carbon positions, suspect t1 noise; reduce trusted correlation count; increase validation threshold.

#### Baseline Roll (1D spectra)

Broad undulation in 1D 13C baseline, can shift apparent peak positions by 0.5-1 ppm.

**Impact:** Shifts 13C peak positions, causing mismatches between 1D 13C and 2D carbon dimensions.

**Action:** If observed 13C peaks differ by > 1.0 ppm from HSQC carbon positions for the same carbon, baseline roll is likely present; increase all carbon tolerances by 0.5 ppm.

### Strategy Adjustments Summary

**Compact decision table:**

| Condition | Actions |
|-----------|---------|
| SNR < 30 AND digital resolution < 5 pts/ppm | Trust only top 50% of HMBC correlations, increase 13C tolerance to ±2.5 ppm, use batch size 3, document quality caveats |
| SNR < 10 OR digital resolution < 2 pts/ppm | Warn user that automated elucidation may not produce reliable results, consider requesting better data |
| 1J artifacts detected | Exclude affected peaks, note in analysis |

**Quality assessment findings MUST be documented in the analysis folder before proceeding to peak picking.**

---

## 3. Peak Picking Strategy

### Scientific Rationale for Guided Picking

Raw 2D peak picking produces noise peaks and artifacts (1J bleeding, t1 noise). Use 1D spectra as ground truth to filter 2D peaks. DEPT provides ground truth for protonated carbons (CH, CH2, CH3). 13C provides all carbon positions including quaternary. HSQC cross-validated against DEPT carbon positions provides valid proton shifts. HMBC cross-validated against both 13C and HSQC provides real long-range correlations. Unfiltered picking causes LSD to produce thousands of solutions instead of a manageable set.

### 1D Adaptive Picker

Use threshold 0.05 as default. The picker uses a two-pass algorithm with FWHM factor 1.5 for baseline discrimination. Override threshold when: spectrum has unusually high noise (increase to 0.08-0.10) or very low intensity peaks are expected (decrease to 0.03). For most well-acquired spectra, 0.05 is optimal.

### HSQC DEPT-Guided Strategy

Use `pick_hsqc_peaks` with DEPT-135 as ground truth. Algorithm iteratively lowers HSQC threshold (starting 0.10, down to 0.005) until all DEPT carbons are matched. Only HSQC peaks at valid DEPT positions are retained. Multiplicity extraction from DEPT-135 peak sign: positive peaks = CH or CH3, negative peaks = CH2. With DEPT-90, distinguish CH (visible) from CH3 (invisible in DEPT-90).

Python API:
```python
result = DEPTGuidedPicker.pick_hsqc_peaks_with_dept90(hsqc, dept135, dept90)
# or
result = DEPTGuidedPicker.pick_hsqc_peaks(hsqc, dept135)
```

Override threshold manually if DEPT contains very weak signals not found by iterative lowering or if HSQC has unusual artifacts requiring a higher starting threshold.

### HMBC Cross-Validation Strategy

Use `pick_hmbc_peaks` to cross-validate against known 13C and HSQC positions. Tolerances: 13C ±1.5 ppm (carbon dimension less precise than proton), 1H ±0.1 ppm. A real HMBC correlation requires the carbon exists (visible in 13C or DEPT) and the proton exists (attached to a carbon visible in HSQC). Include quaternary carbons from 13C when checking HMBC signals.

Python API:
```python
result = HMBCGuidedPicker.pick_hmbc_peaks_from_spectra(
    hmbc=hmbc,
    carbon_spectrum=c13,
    hsqc=hsqc,
    dept135=dept135  # optional, adds extra carbon positions
)
```

Adjust tolerances when: 13C dimension has poor digital resolution (increase to ±2.0 ppm) or 1H dimension shows line broadening (increase to ±0.15 ppm). Most spectra use default tolerances.

### APT as DEPT Alternative

APT (Attached Proton Test) can replace DEPT-135 when unavailable. Positive peaks = CH and CH3 (odd number of attached H). Negative peaks = CH2 and quaternary C (even number). Use `pick_peaks_1d` on APT for carbon positions. Pick HSQC with raw threshold 0.05. Cross-reference APT phase with HSQC intensity: high-intensity HSQC + positive APT = likely CH3, medium-intensity + positive APT = likely CH, HSQC present + negative APT = CH2, no HSQC + negative APT = quaternary C. APT cannot distinguish CH from CH3 without HSQC intensity or shift patterns.

---

## 4. Symmetry Detection

### Expected vs Observed Signal Count

Molecular formula defines expected carbon count. 13C spectrum shows observed signal count. If observed < expected, molecular symmetry is causing equivalent atoms to overlap. The difference indicates how many carbons are symmetrically equivalent. Use `analyze_symmetry` to detect and quantify discrepancies.

### Intensity-Based Equivalence

Relative intensity >= 1.5x the median intensity suggests overlapping signals from equivalent carbons. A doubled signal (2 equivalent carbons) shows ~2x intensity. Check HSQC intensities to confirm carbon equivalence.

### Shift-Based Multiplicity Guessing

When DEPT is unavailable, infer likely multiplicity from shift and intensity. Shifts < 30 ppm are likely CH3 (aliphatic methyl). Shifts > 100 ppm are likely aromatic CH. This is a heuristic, not definitive. Use DEPT when available.

### Common Symmetric Motifs

- **Para-substituted benzene**: 2 pairs of equivalent CH (4 carbons produce 2 signals)
- **Isopropyl groups**: 2 equivalent CH3 (2 carbons produce 1 signal)
- **Gem-dimethyl groups**: 2 equivalent CH3 (2 carbons produce 1 signal)
- **Symmetric ethers/esters**: equivalent CH2 or O-CH2-O patterns

### Handling Symmetry Decision Tree

- **Observed == expected**: No symmetry, proceed normally
- **Difference = 2**: One pair of equivalent carbons (e.g., para-benzene CH pair or isopropyl CH3 pair)
- **Difference = 4**: Two pairs of equivalent carbons (e.g., full para-benzene ring)
- **Larger difference**: Highly symmetric molecule (C2 or higher symmetry)
- Check HSQC intensities to confirm: doubled signals have ~2x intensity

---

## 5. Dereplication

### When to Use Dereplication

Always check databases FIRST before de novo structure elucidation. Dereplication is faster, more reliable, and avoids the combinatorial explosion of LSD. Only proceed to full CASE if dereplication fails to find a match.

### CLI Syntax

From Bruker spectrum (preferred):
```bash
lucy dereplicate c13 <bruker_experiment_path> <formula>
```

From shift list:
```bash
lucy dereplicate c13 --shifts "139.94,138.51,137.16" <formula> -n 10
```

### Region-Specific Tolerances and Scoring

The dereplication algorithm uses region-specific tolerances: aliphatic carbons ±0.8 ppm, aromatic carbons ±1.2 ppm, carbonyl carbons ±1.5 ppm. These reflect intrinsic precision differences across chemical shift regions. Scoring uses geometric mean to balance overlap fraction and average deviation. Results rank by score (higher is better), with average deviation as tiebreaker (lower is better).

### Score Interpretation

| Score | Interpretation | Recommended Action |
|-------|---------------|-------------------|
| > 0.85 | Strong match | Likely identified; verify with literature |
| 0.65 - 0.85 | Possible match | Top candidate often correct; verify carefully |
| 0.50 - 0.65 | Weak match | Use as starting hypothesis; full elucidation recommended |
| < 0.50 | No match | Likely novel compound; proceed with full elucidation |

A score of 0.65-0.85 often indicates the correct compound, especially when molecular formula matches exactly. The score reflects peak overlap, affected by reference data quality and experimental conditions.

---

## 6. LSD Reference

### Command Format

**MULT** - Atom definitions with element, hybridization (2=sp2, 3=sp3), and hydrogen count:
```
MULT 1 C 2 0    ; carbon, sp2, 0 hydrogens (quaternary)
MULT 2 C 2 1    ; carbon, sp2, 1 hydrogen (CH)
MULT 3 C 3 3    ; carbon, sp3, 3 hydrogens (CH3)
MULT 4 N 3 0    ; nitrogen, sp3, 0 hydrogens
MULT 5 O 2 0    ; oxygen, sp2, 0 hydrogens (carbonyl)
```

**HSQC** - Direct C-H attachment:
```
HSQC 2 2    ; carbon 2 has directly attached proton (defines H2)
HSQC 3 3    ; carbon 3 has directly attached protons (defines H3)
```

**HMBC** - 2-3 bond C-H correlations:
```
HMBC 1 2    ; carbon 1 correlates to proton attached to carbon 2
HMBC 1 3    ; carbon 1 correlates to protons attached to carbon 3
```

**BOND** - Explicit bond constraint:
```
BOND 1 13   ; atom 1 bonded to atom 13
```

**LIST**, **ELEM**, **PROP** - Flexible heteroatom constraints:
```
LIST L1 1 2         ; create list of atoms 1 and 2
ELEM L2 O           ; create list of all oxygens
PROP L1 1 L2        ; each atom in L1 must have exactly 1 neighbor from L2
```

### Correlation Order Rule

HSQC/HMQC commands MUST appear BEFORE any HMBC commands that reference those proton positions. LSD defines proton positions through HSQC correlations. Correct order: (1) MULT atom definitions, (2) HSQC correlations (defines H positions), (3) HMBC correlations (references H positions). Error if wrong order: "Cannot set an HMBC correlation between X and H-Y because H-Y is not defined by an HMQC command."

### Hybridization Rules

LSD requires an EVEN number of sp2 atoms. Each double bond connects two sp2 atoms, so an odd count is invalid.

Common sp2 atoms: carbonyl carbons (C=O), carbonyl oxygens (C=O), aromatic carbons, aromatic nitrogens (pyridine-type).

Common sp3 atoms: saturated carbons (CH3, CH2, CH), ether/hydroxyl oxygens, amine nitrogens (NR3), N-methyl nitrogens.

Count all sp2 atoms before running LSD. If odd, adjust one atom's hybridization. Example (Caffeine C8H10N4O2): 5 sp2 carbons (2 carbonyl + 3 aromatic), 2 sp2 oxygens (2 carbonyl), 1 sp2 nitrogen (imidazole ring), 3 sp3 nitrogens (N-methyl) = 8 sp2 atoms (even).

### Heteroatom Attachment Constraints

**Approach A: Direct BOND** - Use when exact atoms are known. Simple and explicit, but less flexible. May over-constrain.
```
BOND 1 13   ; C1 (carbonyl) bonded to O13
BOND 6 9    ; N-CH3 carbon bonded to nitrogen
```

**Approach B: LIST + ELEM + PROP** - Use when constraining by element type without specifying exact atoms. More flexible, lets LSD find optimal assignment, but more verbose.
```
LIST L1 1 2         ; carbonyl carbons
ELEM L2 O           ; all oxygens
PROP L1 1 L2        ; each carbonyl must have exactly 1 oxygen neighbor
```

Decision logic:
- **Carbonyl C=O**: Use BOND (usually clear which oxygen)
- **N-CH3 attachment**: Use LIST/PROP (nitrogen assignment flexible)
- **Ether oxygen**: Use LIST/PROP (attachment position flexible)

### ELIM Command

ELIM allows elimination of invalid HMBC/COSY correlations. Use ONLY as last resort after exhausting all other diagnostics.

```
ELIM P1 P2
; P1 = maximum number of correlations that can be eliminated
; P2 = maximum bond distance limit (0 = no limit)
```

Do NOT include ELIM in the first LSD run. Only add if LSD returns 0 solutions AND you have verified: sp2 count is even, hydrogen count matches formula, HMBC correlations are correct, molecular formula is correct. Using ELIM prematurely can lead to thousands of incorrect solutions instead of a unique correct one. Start with `ELIM 1 0` (eliminate 1 correlation), then `ELIM 2 0`, etc. incrementally.

### Solution Count Interpretation

- **0 solutions**: Over-constrained. Check in order: (1) sp2 count is even, (2) hydrogen count matches formula, (3) HMBC correlations correct, (4) wrong molecular formula, (5) only after all above, try ELIM 1 0.
- **1 solution**: IDEAL result. High confidence. Verify solution makes chemical sense. Check for unusual features. Verify with ranking (MAE score).
- **2-10 solutions**: Good result. Use ranking to identify best match. Examine differences between top candidates (often stereochemistry or regiochemistry).
- **10-100 solutions**: Under-constrained. Add missing HMBC correlations. Check if ELIM was used (remove it). Use ranking to narrow candidates.
- **>100 solutions**: Severely under-constrained. Was ELIM used (remove it first). Request additional NMR data. Add more HMBC correlations. Add heteroatom constraints (BOND or LIST/PROP).

### Manual File Construction Checklist

1. All carbons from 13C defined with MULT
2. Heteroatoms from formula added (N, O, S, etc.)
3. sp2 count is EVEN
4. HSQC correlations defined for protonated carbons
5. HMBC correlations reference only defined H positions
6. Heteroatom constraints added (BOND or LIST/PROP)
7. NO ELIM command on first run (add only if 0 solutions found)

### Troubleshooting Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| "Odd total sum of valences" | Hydrogen count wrong | Verify: sum of (multiplicity × count) = formula H |
| "Cannot set HMBC correlation" | HSQC not defined first | Move all HSQC commands before HMBC |
| "No solution found" | Over-constrained | See Solution Count Interpretation above |
| Too many solutions (>100) | Under-constrained | Add more HMBC correlations, verify existing ones are correct |

Before running LSD: verify hydrogen count matches formula, sp2 count is even, NO ELIM on first run, all HSQC before HMBC.

### Converting Solutions to SMILES

After LSD generates solutions, convert to SMILES using `outlsd`:
```bash
outlsd 5 < compound.sol > solutions.smi
```

Format codes: 1=bond lists, 5=SMILES, 6=2D coordinates, 7=SDF 2D, 8=SDF 3D without H, 9=SDF 3D with H.

---

## 7. Incremental HMBC Constraint Strategy

### Core Principle

**NEVER add all HMBC correlations to an LSD file at once** -- this is the most common cause of zero-solution or thousands-of-solutions failures.

Instead, add correlations in small batches (3-5 per iteration), observing how the solution count changes. This adaptive iteration approach lets you build a solid structural core from high-confidence signals before adding more constrained relationships.

**Maximum ~10 LSD iterations** before stopping and presenting whatever results exist (prevents runaway loops).

### High-Confidence Correlation Selection

How to select the best 3-5 correlations for each batch:

1. **Unique carbon assignment**: The HMBC carbon shift has no other carbon within 2x tolerance (±3.0 ppm). Isolated carbons have unambiguous assignment.
2. **Unique proton assignment**: The HMBC proton shift has no other proton within 2x tolerance (±0.2 ppm).
3. **Strong peak intensity**: Prefer peaks in the top quartile of validated HMBC peak intensities.
4. **Quaternary carbon involvement**: Correlations to quaternary carbons (visible in 13C but not HSQC/DEPT) are especially valuable because they are the ONLY way to connect these atoms to the structure.

**Document reasoning for each selected correlation:** "Starting with C-155.2/H-7.8 because carbon shift is isolated (nearest carbon 4.3 ppm away), proton shift is unique, and peak is strong."

### The Adaptive Iteration Loop

Clear algorithmic procedure:

```
1. Start with MULT definitions, HSQC correlations, and heteroatom constraints (NO HMBC yet)

2. Run LSD -- this gives the unconstrained solution count (baseline)

3. Select first batch of 3-5 high-confidence HMBC correlations

4. Add batch to LSD file, run LSD

5. Observe solution count:

   IF solution_count <= 10:
       STOP -- proceed to ranking (Section 8)

   IF solution_count == 0:
       STOP iteration -- go to Zero-Solution Recovery below

   IF solution_count decreased significantly (>30% reduction):
       CONTINUE -- these correlations are productive, select next batch

   IF solution_count barely changed (<10% reduction for 2+ consecutive iterations):
       STALLED -- go to Convergence Stall below

   IF solution_count INCREASED:
       CONFLICT -- remove last batch, diagnose why it caused more solutions

6. Repeat from step 3 until:
   - solution_count <= 10 (success -- rank)
   - iterations >= 10 (safety cap -- rank anyway with caveats)
   - all HMBC correlations exhausted (rank with caveats)
```

### Stopping Conditions

- **Success:** solution_count <= 10 -- proceed to ranking with standard confidence
- **Iteration cap (~10):** Safety limit, NOT a normal outcome. If hit, treat as diagnostic failure: review correlation selection, check for systematic issues (wrong formula, missing heteroatom constraints), document "structure elucidation incomplete, requires manual review"
- **Correlations exhausted:** All HMBC correlations added, solution_count still > 10 -- rank anyway, present top results with caveat that structure is under-determined
- **Target:** Successful cases typically converge in 3-5 iterations. If taking > 7, something is likely wrong.

### Zero-Solution Recovery

When LSD returns 0 solutions after adding a batch, diagnose in this order:

1. **Remove last batch** and verify solutions return (confirms the batch caused the conflict)
2. **Check sp2 atom count** -- must be EVEN (most common cause of zero solutions)
3. **Verify hydrogen count** -- sum of all hydrogen counts from MULT must match molecular formula
4. **Review the conflicting batch** -- are any correlations potential 1J artifacts? Are carbon assignments ambiguous (close shifts)?
5. **Try individual correlations** from the batch one at a time to find the specific conflict
6. **Check molecular formula** -- if all correlations seem valid, formula may be wrong
7. **ONLY AFTER all above:** consider ELIM 1 0 to eliminate one correlation. ELIM is a LAST RESORT, not a first response.

### Convergence Stall Detection

If 3 consecutive iterations each show < 10% relative reduction in solution count AND solution_count > 50:

- Stop adding correlations -- further constraints are not productive
- Diagnose: Are remaining correlations low-confidence? Is the molecule under-determined by available data?
- Rank current solutions with caveat: "Structure is under-determined; additional NMR data may be needed"
- If solution_count is 10-50, rank and present (may still contain the correct structure)

### What NOT to Do (HMBC-04)

- **NEVER dump all HMBC correlations into LSD at once** -- this eliminates diagnostic feedback and either over-constrains (0 solutions) or under-constrains (thousands of solutions) without telling you why
- **NEVER add ELIM before diagnosing** -- ELIM tells LSD to ignore correlations, which masks real problems
- **NEVER ignore solution count trends** -- if 3 iterations show 500->450->420 (slow decline), continuing is futile; stop and diagnose
- **NEVER treat the iteration cap as a strategy** -- hitting 10 iterations means something went wrong, not that you tried hard enough

---

## 8. Ranking and Prediction

### HOSE Prediction Strategy

13C prediction uses HOSE codes with radius fallback (6->1). Radius 6 is most specific (6 bond spheres), radius 1 is most general. If no match at radius 6, fall back to 5, then 4, etc. Confidence score (0-1) reflects: radius (50% weight - higher radius = higher confidence), match count (30% weight - more matches = higher confidence), standard deviation (20% weight - lower std dev = higher confidence).

### N:1 Symmetry Matching

When ranking LSD solutions, the predictor generates one shift per carbon atom, but symmetry causes multiple atoms to produce one experimental signal. The ranking algorithm finds the closest experimental peak for each predicted shift. This N:1 matching (N predicted shifts, 1 experimental signal) is expected for symmetric molecules. Do not penalize solutions for this.

### MAE Quality Thresholds

| MAE (ppm) | Quality Label | Interpretation |
|-----------|---------------|----------------|
| < 2.0 | Excellent | High confidence in structure |
| 2.0 - 3.5 | Good | Reasonable confidence |
| 3.5 - 5.0 | Moderate | Review carefully, check alternatives |
| > 5.0 | Poor | Likely incorrect or unusual structure |

### Ranking Output Format and Interpretation

Output shows MAE with quality label and multi-level tolerance:
```
  1. Solution 188: MAE=3.26 ppm (Good)
     CC1CC(C)=C(C1)CC(=O)C
     ≤3ppm: 6/10 | ≤5ppm: 9/10
```

The tolerance summary shows how many predicted shifts fall within 3 ppm and 5 ppm of experimental peaks. This multi-level view is more informative than a single hard cutoff. `≤3ppm: 6/10` means 6 of 10 predicted shifts are within 3 ppm. `≤5ppm: 9/10` means 9 of 10 are within 5 ppm.

### Why Correct Structures May Not Rank #1

HOSE prediction errors: carbonyl carbons can vary ±5-10 ppm, conjugated systems are harder to predict. Symmetry effects: equivalent carbons produce one signal but multiple predictions. Unusual environments: strained rings, unusual substituents reduce prediction accuracy. Always examine the top 10-20 candidates for chemical reasonableness. A structure with MAE=3.5 (Good) and sensible chemistry may be correct over one with MAE=3.2 but unusual features. Cross-reference with dereplication hits if available.

---

## 9. CASE Workflow

**Note:** This workflow assumes you have assessed spectral quality (Section 2) and will use the incremental HMBC strategy (Section 7) for constraint building.

### Step-by-Step Workflow

0. **Documentation**: Create `analysis/` folder to document all steps and results. Document immediately after each step so the user can follow while you work.

1. **Dereplication**: Check known compounds first using `dereplicate_c13`. If score > 0.85, likely identified. If score 0.65-0.85, possible match (verify carefully). If score < 0.50, proceed to full elucidation.

2. **Symmetry**: Run `analyze_symmetry` to detect equivalent atoms. If observed carbons < expected carbons, account for symmetry in LSD constraints.

2.5. **Quality Assessment**: Assess spectral quality (S/N, digital resolution, artifacts) for ALL spectra before peak picking. See Section 2 for quality tiers and strategy adjustments. Document quality findings in analysis folder. If quality is poor (SNR < 10 or resolution < 2 pts/ppm), warn user before proceeding.

3. **Peak Picking**:
   - `pick_peaks_1d` for 13C carbon peaks
   - `pick_hsqc_peaks` with DEPT-135 for direct C-H correlations (use DEPT-guided picker)
   - `pick_hmbc_peaks` with 13C and HSQC for long-range correlations (use cross-validated picker)
   - Apply quality-based adjustments from Section 2 (thresholds, tolerances)

4. **LSD Generation**: Generate initial LSD file with MULT definitions, HSQC correlations, and heteroatom constraints. Do NOT add HMBC correlations yet. See Section 7 for the incremental approach. Verify checklist before running: all carbons defined, heteroatoms added, sp2 count is EVEN, HSQC before HMBC, NO ELIM on first run.

5. **Solve**: Follow the Incremental HMBC Constraint Strategy (Section 7). Add 3-5 high-confidence HMBC correlations per iteration. Stop when solution_count ≤ 10 or after ~10 iterations. Check solution count after each iteration:
   - **0 solutions**: Follow Zero-Solution Recovery (Section 7).
   - **1-10 solutions**: Success. Proceed to step 6.
   - **>10 solutions**: Under-constrained. Continue incremental HMBC iteration (Section 7). Do NOT proceed to ranking until ≤10 solutions or all correlations/iterations exhausted.

6. **Rank**: Run `rank_lsd_solutions` (only after achieving ≤10 solutions or exhausting all correlations/iterations). Examine top 10-20 candidates. Cross-reference with dereplication hits if available.

### When to Proceed vs Request More Data

**Proceed** if: dereplication found no match (or weak match < 0.65), all necessary spectra available (at minimum 13C, HSQC, HMBC; DEPT highly recommended), molecular formula provided.

**Request more data** if: missing critical spectra (13C, HSQC, or HMBC), molecular formula not provided (essential), conflicting data between experiments, unusual chemical shifts outside normal ranges.

### Result Reporting Templates

**Strong dereplication match (score > 0.85)**:
"The compound matches [NAME] in the database with a score of [X]. This is a known compound: [SMILES]. The match is based on [N] carbon shifts with an average deviation of [Y] ppm."

**Possible match (score 0.50-0.85)**:
"There is a potential match to [NAME] with a score of [X]. This should be verified by comparing predicted vs. observed shifts. Consider proceeding with structure elucidation to confirm. Key differences are at positions: [list outliers]."

**No match (score < 0.50)**:
"No database match found. This may be a novel compound, a known compound with different stereochemistry, or a compound not yet in the reference database. Proceeding with de novo structure elucidation."

**LSD results (1-10 solutions)**:
"LSD found [N] candidate structure(s). Solution 1: [Description]. Core scaffold: [aromatic/aliphatic/mixed]. Key features: [functional groups, ring systems]. Consistent with: [spectroscopic features]. [If multiple solutions, describe key differences: position of functional group, ring fusion pattern, stereochemistry]."

**Reporting uncertainty**:
Always be transparent about missing data that would improve confidence, assumptions made during analysis, alternative interpretations, and recommended additional experiments.

---

## 10. Error Tolerance and Ambiguity Detection

**Core principle:** Proactively detect and document ambiguity instead of guessing through it. Ambiguity arises from three sources: (1) close carbons unresolvable by digital resolution, (2) DEPT/HSQC multiplicity conflicts, and (3) quaternary carbons with sparse HMBC correlations. All ambiguities must be documented in a dedicated output section with quantitative resolution details.

This section references quality assessment from Section 2 and extends the LSD constraint mechanisms from Section 6.

### 10.1 Close Carbon Detection (Resolution-Based)

**Detection strategy:** Calculate digital resolution independently for each spectrum dimension. Two carbons are unresolvable if their spacing is smaller than the minimum distinguishable separation based on that dimension's resolution.

**Resolution calculation:**

For any spectrum dimension:
```
resolution = len(ppm_scale) / (ppm_max - ppm_min)  # points per ppm
min_spacing = 1.5 / resolution  # minimum distinguishable spacing in ppm
```

**Apply to each dimension independently:**
- **1D 13C spectrum**: Calculate from 13C ppm_scale
- **HSQC F1 (carbon axis)**: Calculate from HSQC F1 dimension ppm_scale
- **HMBC F1 (carbon axis)**: Calculate from HMBC F1 dimension ppm_scale

Each dimension may have different resolution. A carbon pair may be resolvable in 1D 13C (high resolution) but unresolvable in HMBC F1 (lower resolution).

**Quality-dependent minimum spacing** (from Section 2):
- > 10 pts/ppm (Excellent): ~0.15 ppm minimum spacing
- 5-10 pts/ppm (Good): ~0.30 ppm minimum spacing
- 2-5 pts/ppm (Moderate): ~0.75 ppm minimum spacing
- < 2 pts/ppm (Poor): 1.5+ ppm minimum spacing

**Ambiguity criterion:** Two carbons at shifts A and B are unresolvable if:
```
abs(shift_A - shift_B) < min_spacing
```

**Physical grounding:** This approach is resolution-aware, not based on arbitrary hard-coded ppm thresholds. A 0.3 ppm spacing may be clearly resolvable in one spectrum (10 pts/ppm) but completely merged in another (2 pts/ppm). Always calculate resolution for the specific spectrum being analyzed.

**Future extensibility:** This detection mechanism is designed for future augmentation by an atom environment database. A learned model could refine the 1.5-point threshold based on peak shape, overlap characteristics, and chemical environment. The core resolution calculation remains unchanged.

**When carbons are unresolvable:**

1. **Use LSD LIST/PROP mechanism** to encode ambiguity in a SINGLE LSD file (NOT separate variant files):

```
; Example: carbons at 155.08 and 155.32 ppm cannot be distinguished
; in HMBC F1 dimension (4.2 pts/ppm, 0.36 ppm minimum spacing, 0.24 ppm apart)

MULT 5 C 2 0   ; could be either 155.08 or 155.32 ppm
MULT 6 C 2 0   ; could be either 155.08 or 155.32 ppm
LIST L1 5 6    ; group these unresolvable carbons

; When HMBC shows correlation to one of them (but unclear which):
; Use PROP to express "at least one atom in L1 connects to proton X"
; Example: HMBC shows peak at (155.2, 7.8) correlating to H12
; PROP L1 1 LIST_H12  ; one of {C5, C6} has exactly 1 connection to H12
```

2. **Document in Ambiguities Detected section** (see 10.4 below) with quantitative details:
   - The specific carbon shifts
   - Calculated resolution (pts/ppm)
   - Calculated minimum spacing
   - Actual spacing between peaks
   - Impact on LSD constraints (which LIST/PROP was used)

**Verification across dimensions:** Check ambiguity in ALL relevant dimensions. If two carbons are resolvable in 1D 13C but unresolvable in HMBC F1, HMBC correlations involving those carbons are ambiguous even though the 1D assignment is clear.

### 10.2 DEPT/HSQC Multiplicity Conflict Resolution

**Core principle:** No blanket rule. Resolution is context-dependent based on experiment quality, availability, and chemical shift expectations.

**Priority-ordered decision tree:**

**1. DEPT-90 availability (highest priority)**

DEPT-90 shows ONLY CH carbons — this is near-definitive identification. If DEPT-90 is available:
- Peak visible in DEPT-90 → **CH with high confidence** (overrides HSQC pattern inference)
- Peak absent in DEPT-90 but positive in DEPT-135 → **CH3** (overrides HSQC if conflict)
- Peak negative in DEPT-135 → **CH2**

DEPT-90 provides the most definitive multiplicity assignment. When available, trust it over HSQC pattern-based inference.

**2. S/N comparison**

When DEPT-90 is unavailable, compare S/N ratios (from Section 2 quality assessment):
- DEPT-135 SNR > 50, HSQC SNR < 20 → trust DEPT-135
- HSQC SNR > 50, DEPT-135 SNR < 20 → trust HSQC
- Both SNR in similar range (20-100) → proceed to next criterion
- **Both SNR < 20** → mark as explicitly ambiguous (see edge case below)

**3. Chemical shift expectations**

Use shift-based heuristics as tiebreaker:
- < 30 ppm → likely **CH3** (aliphatic methyl)
- 100-160 ppm → likely aromatic **CH**
- 50-90 ppm with negative DEPT-135 → likely **CH2** attached to oxygen (O-CH2)
- 30-50 ppm positive DEPT-135 → could be CH or CH3, examine HSQC intensity

**4. Consistency check**

Cross-validate with other data:
- **HMBC correlation count**: CH typically shows 2-4 HMBC correlations, CH2 shows 2-3, CH3 shows 1-2 (fewer bonds to other carbons)
- **Hydrogen budget**: Sum all assigned multiplicities — does total H count match molecular formula?
- **HSQC intensity**: CH3 groups often show higher HSQC intensity than CH (3 equivalent protons vs 1)

**Edge case: Both experiments poor S/N (< 20)**

When both DEPT-135 and HSQC show S/N < 20 for the same peak:
- **Mark as explicitly ambiguous** — neither experiment is trustworthy
- **Assign Low confidence** to this carbon's multiplicity
- **Use shift-based heuristic as last resort** (criterion 3 above)
- **Suggest re-acquisition**: "Re-acquire DEPT-135 or HSQC with longer acquisition time to improve S/N for peak at X ppm"

**Resolution strategy:**

- **Resolve to ONE multiplicity** based on weight of evidence from the decision tree
- **Do NOT create separate LSD runs** for alternative assignments
- **Document the conflict** in Ambiguities Detected section (see 10.4) with:
  - DEPT-135 indication (positive/negative/absent)
  - HSQC pattern inference
  - S/N ratios for both experiments
  - Which criterion was used to resolve (DEPT-90, S/N, shift, consistency)
  - The chosen multiplicity and the rejected alternative
  - Confidence level (Low/Medium based on strength of evidence)

**Audit trail:** Document ALL disagreements, even minor ones. This builds a complete record for validation and enables future review if structure is later questioned.

### 10.3 Quaternary Carbon HMBC Sparsity

**Challenge:** Quaternary carbons (no attached H) appear in 13C but not in HSQC/DEPT. HMBC is their ONLY structural connection. When HMBC correlations are sparse (0-1 visible), use shift-based constraints and targeted threshold reduction.

#### Shift-Based Constraint Mapping

When a quaternary carbon has 0 HMBC correlations, use chemical shift to infer likely environment and add LSD constraints.

**Mapping table** (explicitly modular for future replacement):

| Shift Range (ppm) | Likely Environment | LSD Constraint |
|-------------------|-------------------|----------------|
| 160-180 | Carboxylic acid/ester/amide C=O | `BOND Quat_idx O_idx` (bond to oxygen) |
| 180-220 | Ketone/aldehyde C=O | `BOND Quat_idx O_idx` (bond to oxygen) |
| 120-160 (aromatic context) | Aromatic junction | Use LIST/PROP to constrain to aromatic ring carbons |
| < 50 | Quaternary aliphatic | Rare (e.g., tert-butyl); note as unusual, minimal constraint |

**Important note:** This mapping is heuristic and designed for future replacement by an atom environment database. The specific shift ranges and constraint types should be treated as initial guidelines, not rigid rules. Edge cases (e.g., conjugated carbonyls 170-180 ppm, nitriles 115-120 ppm) should be flagged in Ambiguities Detected section as potentially ambiguous.

**Rationale:** A quaternary carbon with 0 HMBC correlations provides no connectivity information. Shift-based constraints prevent LSD from producing thousands of disconnected solutions. The constraint is weak but better than none.

#### Single HMBC Correlation

When a quaternary carbon has exactly 1 HMBC correlation:
- **Treat with HIGHER confidence** (not suspicion)
- This is the only connectivity information for that atom — it is precious, not dubious
- Do NOT discard or downweight single correlations to quaternary carbons
- Validate normally (cross-check carbon and proton positions against 13C and HSQC)

#### Targeted HMBC Threshold Reduction

When a quaternary carbon has 0-1 HMBC correlations after guided picking, perform targeted search at lower thresholds to find weak correlations that may have been missed.

**Incremental reduction strategy:**

```
1. Start at current threshold from guided picking (typically 0.05-0.08)

2. For each quaternary carbon with 0-1 correlations:

   current_threshold = starting_threshold

   WHILE correlation_count <= 1 AND current_threshold > floor:

       # Reduce threshold by 20% (user-preferred gradual approach)
       current_threshold = current_threshold × 0.8

       # Re-examine HMBC in ±2.5 ppm window around quaternary carbon shift
       new_peaks = pick_hmbc_in_region(
           carbon_range=(quat_shift - 2.5, quat_shift + 2.5),
           threshold=current_threshold
       )

       # Validate new peaks against 13C and HSQC (guided picking logic)
       validated_peaks = validate_against_13C_and_HSQC(new_peaks)

       correlation_count = count(validated_peaks)

       # Stopping conditions:
       IF correlation_count > 1:
           STOP → correlations found, use them

       IF 3 consecutive reductions yield 0 new validated peaks:
           STOP → diminishing returns, no more signal here

       IF current_threshold <= floor:
           STOP → reached noise floor, further reduction futile

   # Document outcome in Ambiguities Detected section

3. Determine floor based on spectrum noise characteristics:

   # Claude determines reasonable floor from noise_floor (Section 2):
   # Conservative: noise_floor × 3 (high confidence 3:1 S/N)
   # Moderate: noise_floor × 2 (standard 2:1 S/N)
   # Aggressive (only for excellent spectra): noise_floor × 1.5
```

**Rationale for 20% reduction:** User explicitly preferred gradual reduction over aggressive 50% halving. 20% per step allows 5-7 steps before reaching 1/3 of starting threshold, providing fine-grained control with controlled risk of noise leakage.

**Floor determination:** Claude assesses noise characteristics from the specific spectrum (noise floor calculation from Section 2). For a spectrum with low noise (SNR > 100), floor = noise_floor × 1.5 is reasonable. For noisy spectra (SNR < 30), use floor = noise_floor × 3 to avoid false positives.

**Validation is mandatory:** Each threshold reduction MUST validate new peaks using guided picking logic (carbon position exists in 13C, proton position exists in HSQC). Do NOT simply accept all peaks above threshold — most will be noise.

**Outcome documentation:** If targeted search finds new correlations, note in Ambiguities section: "Quaternary carbon at 155.2 ppm initially showed 0 HMBC correlations. Targeted search at threshold 0.032 (reduced from 0.05) found 2 correlations: C155.2-H7.8, C155.2-H3.2." If search fails, note: "Quaternary at 172.4 ppm: 0 correlations after threshold reduction to 0.025 (noise_floor × 2.5). Used shift constraint: BOND to oxygen based on 172 ppm carbonyl region."

### 10.4 Ambiguities Detected Output Section

**Mandatory documentation:** All detected ambiguities MUST be documented in a dedicated "Ambiguities Detected" section in the analysis output. If zero ambiguities are detected, state explicitly: "No ambiguities detected."

**Standard table format:**

```markdown
## Ambiguities Detected

| Carbon/Issue | Type | Resolution Detail | Impact on Constraints |
|-------------|------|-------------------|----------------------|
| 155.08 / 155.32 ppm | Close carbons | HMBC F1: 4.2 pts/ppm, min spacing 0.36 ppm, actual spacing 0.24 ppm → unresolvable | Used LIST L1 {5,6} and PROP for C-H12 correlation (cannot distinguish which carbon) |
| 28.5 ppm | DEPT/HSQC conflict | DEPT-135 positive (CH/CH3), HSQC pattern suggests CH3, no DEPT-90 available | Assigned CH3 based on shift < 30 ppm (aliphatic), alternative CH possible, Medium confidence |
| 172.4 ppm (C=O) | Sparse HMBC | 0 correlations after threshold reduction to 0.025 (noise_floor × 2.5) | Added shift constraint: BOND to oxygen based on 172 ppm carbonyl region |
| 138.6 ppm | DEPT/HSQC conflict | DEPT-135 SNR = 18, HSQC SNR = 15 (both poor) | Assigned CH based on shift (aromatic region), Low confidence, suggest re-acquisition |
```

**Required elements for each entry:**

1. **Carbon/Issue:** Specific chemical shift(s) or carbon identifier
2. **Type:** Category of ambiguity
   - "Close carbons" (resolution-limited)
   - "DEPT/HSQC conflict" (multiplicity disagreement)
   - "Sparse HMBC" (quaternary with 0-1 correlations)
   - "Other" (any additional ambiguity type)
3. **Resolution Detail:** Quantitative specifics
   - For close carbons: pts/ppm, minimum spacing, actual spacing
   - For conflicts: S/N values, DEPT-90 availability, which criterion was decisive
   - For sparse HMBC: threshold reduction steps, final threshold, floor value
4. **Impact on Constraints:** Specific action taken
   - Which LSD LIST/PROP/BOND was added
   - Which multiplicity was assigned
   - Confidence level assigned
   - What the alternative interpretation would be

**Transparency principle:** The user must be able to see exactly what ambiguity was detected, why it was detected (quantitative criteria), how it was resolved (which decision rule), and what the impact is (which constraints were affected). This enables validation, manual review, and future refinement.

**Cross-reference to suggested experiments:** Ambiguities documented here feed into "Recommended Additional Experiments" section (if that workflow is implemented in future phases). Example: "DEPT-90 acquisition would resolve CH/CH3 ambiguities at 28.5 ppm and 32.1 ppm."

---

## 11. Quick Reference

### Key Tolerances

- 13C chemical shift matching: ±1.5 ppm (carbonyl), ±0.8 ppm (aliphatic)
- HSQC validation: ±1.0 ppm (13C dimension)
- HMBC validation: ±1.5 ppm (13C), ±0.1 ppm (1H)
- Dereplication: score > 0.85 strong, 0.65-0.85 possible, < 0.50 no match
- Solution ranking: MAE < 2.0 = Excellent, 2-3.5 = Good, 3.5-5 = Moderate, > 5 = Poor
- Spectral quality (SNR): > 100 excellent, 30-100 good, 10-30 moderate, < 10 poor
- Digital resolution: > 10 pts/ppm excellent, 5-10 good, 2-5 moderate, < 2 poor
- HMBC batch size: 3-5 correlations per iteration
- HMBC iteration cap: ~10 iterations maximum
- High-confidence threshold: no other carbon within ±3.0 ppm, no other proton within ±0.2 ppm

### Red Flags

- Fewer signals than expected atoms: Symmetry (see Section 4)
- More signals than expected: Impurity or wrong formula
- Zero LSD solutions: Over-constrained (see Section 6 troubleshooting)
- Thousands of LSD solutions: Under-constrained OR using ELIM when not needed
- Solution count stalled for 3+ iterations: Under-determined structure (see Section 7)
- Hitting 10-iteration cap: Systematic issue, not normal convergence
- > 200 "validated" HMBC correlations: Likely noise leakage from poor quality spectrum
- 1J artifact peaks in HMBC: Exclude from constraints (see Section 2)

### When to Ask for Help

- Conflicting data between experiments
- Unusual chemical shifts outside normal ranges
- Molecular formula does not match observed data
- User requests interpretation beyond available data

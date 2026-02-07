---
phase: 23-error-tolerance-confidence
verified: 2026-02-07T19:30:00Z
status: passed
score: 7/7 must-haves verified
---

# Phase 23: Error Tolerance and Confidence Verification Report

**Phase Goal:** Encode error detection patterns and confidence-annotated output into `skill/SKILL.md` so the AI agent proactively identifies and documents ambiguity instead of guessing through it.

**Verified:** 2026-02-07T19:30:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | AI agent can detect close carbons using digital resolution (NOT hard-coded thresholds) | ✓ VERIFIED | Section 10.1 contains resolution formula `resolution = len(ppm_scale) / (ppm_max - ppm_min)`, min_spacing formula, quality-dependent thresholds (0.15-1.5+ ppm based on pts/ppm) |
| 2 | AI agent resolves DEPT/HSQC conflicts using context-dependent priority tree | ✓ VERIFIED | Section 10.2 contains 4-level priority tree (DEPT-90 > S/N > shift > consistency), explicit rejection of blanket rules |
| 3 | AI agent encodes ambiguous HMBC assignments via LIST/PROP in single LSD file | ✓ VERIFIED | Section 10.1 contains LIST/PROP examples, explicit "SINGLE LSD file (NOT separate variant files)" instruction |
| 4 | AI agent handles quaternary carbon sparsity with shift constraints and targeted threshold reduction | ✓ VERIFIED | Section 10.3 contains shift-constraint mapping table (160-180 → carboxylic, etc.) and 20% threshold reduction algorithm |
| 5 | CASE workflow produces confidence-annotated output (High/Medium/Low) | ✓ VERIFIED | Section 11 defines qualitative 3-level system, per-atom 3-factor model, per-structure derivation; integrated into workflow step 7 |
| 6 | Ambiguous assignments are documented with reasoning | ✓ VERIFIED | Section 10.4 defines mandatory "Ambiguities Detected" table format with quantitative details and impact documentation |
| 7 | Analysis output suggests specific additional NMR experiments | ✓ VERIFIED | Section 11.5 defines experiment suggestions with WHAT/WHY/WHICH structure, includes prioritized output template |

**Score:** 7/7 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `skill/SKILL.md` | ~1,079 lines with error tolerance and confidence sections | ✓ VERIFIED | 1,079 lines, 12 sections (Sections 10 and 11 added) |
| Section 10 (Error Tolerance) | Resolution detection, DEPT/HSQC conflicts, quaternary sparsity, ambiguities output | ✓ VERIFIED | 254 lines (585-838), 4 subsections present |
| Section 11 (Confidence Scoring) | Per-atom factors, downgrade rules, per-structure derivation, suggested experiments | ✓ VERIFIED | 202 lines (839-1040), 5 subsections present |
| Section 9 integration | Workflow step 7 includes confidence assessment | ✓ VERIFIED | Line 558 contains complete confidence assessment step |
| Section 12 integration | Quick Reference includes confidence thresholds and ambiguity red flags | ✓ VERIFIED | Lines 1055-1056 (confidence thresholds), 1068-1070 (ambiguity red flags) |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| Section 10 | Section 2 (Quality) | Resolution thresholds reference quality tiers | ✓ WIRED | Line 610 references Section 2 quality tiers |
| Section 10 | Section 6 (LSD) | LIST/PROP examples extend LSD command reference | ✓ WIRED | Lines 629-641 contain LIST/PROP examples |
| Section 11 | Section 8 (Ranking) | MAE thresholds from ranking quality labels | ✓ WIRED | Line 865 references Section 8 MAE thresholds |
| Section 9 (Workflow) | Section 10 | Steps 3-4 reference resolution detection and conflict resolution | ✓ WIRED | Lines 546-549 integrate ambiguity detection |
| Section 9 (Workflow) | Section 11 | Step 7 mandates confidence assessment | ✓ WIRED | Line 558 complete confidence assessment integration |
| Section 12 (Quick Reference) | Sections 10-11 | Confidence thresholds and ambiguity red flags | ✓ WIRED | Lines 1055-1056, 1068-1070 |

### Requirements Coverage

All 7 requirements from Phase 23 SATISFIED:

| Requirement | Status | Evidence |
|-------------|--------|----------|
| ETOL-01: Resolution-based close carbon detection using digital resolution, NOT hard-coded ppm thresholds | ✓ SATISFIED | Section 10.1 lines 595-624: formula-based resolution calculation (`resolution = len(ppm_scale) / (ppm_max - ppm_min)`, `min_spacing = 1.5 / resolution`), quality-dependent thresholds (0.15-1.5+ ppm based on pts/ppm), explicit rejection of hard-coded thresholds ("resolution-aware, not based on arbitrary hard-coded ppm thresholds") |
| ETOL-02: Context-dependent DEPT/HSQC multiplicity conflict resolution with priority tree | ✓ SATISFIED | Section 10.2 lines 652-711: 4-level priority tree (1. DEPT-90 availability, 2. S/N comparison, 3. Chemical shift expectations, 4. Consistency check), explicit "No blanket rule" principle, edge case handling for both SNR < 20 |
| ETOL-03: Ambiguous HMBC encoded via LSD LIST/PROP mechanism in single file | ✓ SATISFIED | Section 10.1 lines 625-641: LIST/PROP examples with unresolvable carbons, explicit "SINGLE LSD file (NOT separate variant files)" instruction, complete code examples with comments |
| ETOL-04: Quaternary carbon HMBC sparsity handling with shift-based constraints and 20% threshold reduction | ✓ SATISFIED | Section 10.3 lines 712-797: shift-constraint mapping table (160-180 → carboxylic, 180-220 → ketone, 120-160 → aromatic, <50 → aliphatic), 20% threshold reduction algorithm (lines 747-788: `current_threshold × 0.8`), floor determination, validation requirements |
| CONF-01: Per-atom and per-structure confidence levels (qualitative High/Medium/Low, NOT computed percentages) | ✓ SATISFIED | Section 11.1-11.3 lines 843-957: explicit "qualitative judgment, NOT computed percentages" (line 841), per-atom 3-factor model (resolution, HOSE MAE, correlations), per-structure derivation with thresholds (High: >=80% H/M + <=1 Low, Medium: >=50% H/M, Low: <50% H/M), worked examples |
| CONF-02: Ambiguous assignments documented with reasoning | ✓ SATISFIED | Section 10.4 lines 798-836: mandatory "Ambiguities Detected" table format, required elements (Carbon/Issue, Type, Resolution Detail, Impact on Constraints), quantitative specifics (pts/ppm, S/N values, threshold steps), transparency principle, cross-reference to experiments |
| CONF-03: Suggested additional NMR experiments (WHAT, WHY, WHICH atom) | ✓ SATISFIED | Section 11.5 lines 993-1038: specific experiment suggestion format (WHAT experiment, WHY it helps, WHICH atom/issue), 5 complete examples (DEPT-90, optimized HMBC, higher-resolution HSQC, re-acquisition, 1,1-ADEQUATE), prioritized output template with impact assessment |

### Anti-Patterns Found

None. Clean implementation.

### Human Verification Required

None. All requirements can be verified by examining SKILL.md content, which is complete and substantive.

### Gaps Summary

No gaps. All 7 requirements are fully satisfied in SKILL.md with substantive content, proper integration into workflow and quick reference, and correct cross-referencing to existing sections.

---

## Detailed Verification

### ETOL-01: Resolution-Based Close Carbon Detection

**Requirement:** "Resolution-based close carbon detection using digital resolution (pts/ppm), NOT hard-coded ppm thresholds"

**Evidence in Section 10.1 (lines 591-651):**

1. **Resolution calculation formula** (lines 595-601):
   ```
   resolution = len(ppm_scale) / (ppm_max - ppm_min)  # points per ppm
   min_spacing = 1.5 / resolution  # minimum distinguishable spacing in ppm
   ```
   Formula-based, not hard-coded.

2. **Quality-dependent minimum spacing** (lines 610-614):
   - >10 pts/ppm → ~0.15 ppm minimum spacing
   - 5-10 pts/ppm → ~0.30 ppm minimum spacing
   - 2-5 pts/ppm → ~0.75 ppm minimum spacing
   - <2 pts/ppm → 1.5+ ppm minimum spacing
   
   Thresholds derived from formula applied to quality tiers, not arbitrary values.

3. **Physical grounding** (line 621):
   "This approach is resolution-aware, not based on arbitrary hard-coded ppm thresholds."
   
   Explicit rejection of hard-coded approach.

4. **Dimension-independent calculation** (lines 603-608):
   Applies to 1D 13C, HSQC F1, HMBC F1 independently, each with potentially different resolution.

**Verification:** ✓ PASSED — Formula-based resolution calculation with quality-dependent thresholds, explicit rejection of hard-coded values.

### ETOL-02: Context-Dependent DEPT/HSQC Conflict Resolution

**Requirement:** "Context-dependent DEPT/HSQC multiplicity conflict resolution with priority tree"

**Evidence in Section 10.2 (lines 652-711):**

1. **Core principle** (line 654):
   "No blanket rule. Resolution is context-dependent based on experiment quality, availability, and chemical shift expectations."

2. **Priority-ordered decision tree** (lines 656-689):
   - **Priority 1:** DEPT-90 availability (lines 658-665) — "near-definitive identification"
   - **Priority 2:** S/N comparison (lines 667-673) — trust higher-quality experiment
   - **Priority 3:** Chemical shift expectations (lines 675-681) — shift-based heuristics
   - **Priority 4:** Consistency check (lines 683-688) — HMBC count, hydrogen budget, HSQC intensity

3. **Edge case handling** (lines 690-696):
   Both SNR < 20 → mark explicitly ambiguous, assign Low confidence, use shift heuristic as last resort, suggest re-acquisition.

4. **Resolution strategy** (lines 698-708):
   Resolve to ONE multiplicity, document conflict in Ambiguities section with full decision trail.

**Verification:** ✓ PASSED — Complete priority tree with 4 levels, explicit rejection of blanket rules, edge case handling documented.

### ETOL-03: Ambiguous HMBC via LSD LIST/PROP

**Requirement:** "Ambiguous HMBC encoded via LSD LIST/PROP mechanism in single file"

**Evidence in Section 10.1 (lines 625-641):**

1. **Single-file approach** (line 627):
   "Use LSD LIST/PROP mechanism to encode ambiguity in a SINGLE LSD file (NOT separate variant files)"

2. **Complete code example** (lines 629-641):
   ```
   ; Example: carbons at 155.08 and 155.32 ppm cannot be distinguished
   MULT 5 C 2 0   ; could be either 155.08 or 155.32 ppm
   MULT 6 C 2 0   ; could be either 155.08 or 155.32 ppm
   LIST L1 5 6    ; group these unresolvable carbons
   ; PROP L1 1 LIST_H12  ; one of {C5, C6} has exactly 1 connection to H12
   ```

3. **Documentation requirement** (lines 643-648):
   Must document in Ambiguities Detected section with quantitative details and LSD constraints used.

**Verification:** ✓ PASSED — Single-file approach explicitly stated, complete LIST/PROP examples provided, documentation requirements clear.

### ETOL-04: Quaternary Carbon HMBC Sparsity

**Requirement:** "Quaternary carbon HMBC sparsity handling with shift-based constraints and 20% threshold reduction"

**Evidence in Section 10.3 (lines 712-797):**

1. **Shift-based constraint mapping table** (lines 722-727):
   | Shift Range | Environment | Constraint |
   |-------------|-------------|------------|
   | 160-180 | Carboxylic/ester/amide | BOND to oxygen |
   | 180-220 | Ketone/aldehyde | BOND to oxygen |
   | 120-160 | Aromatic junction | LIST/PROP constraints |
   | <50 | Quaternary aliphatic | Minimal constraint |

2. **20% threshold reduction algorithm** (lines 747-788):
   - Formula: `current_threshold = current_threshold × 0.8` (line 757)
   - Rationale: "20% per step allows 5-7 steps before reaching 1/3 of starting threshold" (line 790)
   - User preference: "User explicitly preferred gradual reduction over aggressive 50% halving" (line 790)

3. **Floor determination** (lines 782-792):
   - Conservative: `noise_floor × 3` (high confidence 3:1 S/N)
   - Moderate: `noise_floor × 2` (standard 2:1 S/N)
   - Aggressive: `noise_floor × 1.5` (only for excellent spectra)
   
   Claude determines floor based on specific spectrum noise characteristics.

4. **Stopping conditions** (lines 771-778):
   - Correlations found (>1)
   - 3 consecutive reductions yield 0 validated peaks
   - Threshold reaches noise floor

5. **Validation requirement** (line 794):
   "Each threshold reduction MUST validate new peaks using guided picking logic"

**Verification:** ✓ PASSED — Shift-constraint table present with 4 ranges, 20% reduction algorithm with formula, floor determination documented, validation requirements clear.

### CONF-01: Confidence Levels

**Requirement:** "Per-atom and per-structure confidence levels (qualitative High/Medium/Low, NOT computed percentages)"

**Evidence in Section 11 (lines 839-957):**

1. **Qualitative approach** (line 841):
   "Confidence assessment is **qualitative judgment**, NOT computed percentages."

2. **Per-atom 3-factor model** (lines 843-906):
   - **Factor 1:** Digital resolution (High: >2× limit, Medium: 2-3× limit, Low: <1× limit)
   - **Factor 2:** HOSE prediction quality (High: <2.0 ppm, Medium: 2-3.5 ppm, Low: >3.5 ppm)
   - **Factor 3:** Supporting correlations (High: 3+ HMBC + HSQC, Medium: 1-2 HMBC + HSQC, Low: 0 HMBC)

3. **Overall atom-level judgment** (lines 877-905):
   "Agent evaluates all three factors and assigns High/Medium/Low based on judgment. No formula."
   Three worked examples showing judgment process.

4. **Explicit downgrade rules** (lines 907-928):
   Five automatic downgrade rules preventing confidence inflation:
   - Any ambiguity → Medium at best
   - MAE >3.5 → Low
   - 0 HMBC on quaternary → Low
   - DEPT/HSQC conflict → Medium at best
   - Targeted threshold reduction failed → Low

5. **Per-structure confidence derivation** (lines 930-957):
   - High: >=80% H/M atoms + <=1 Low + no Low in critical positions
   - Medium: >=50% H/M OR 2-3 Low (not critical) OR 1 Low in critical position
   - Low: <50% H/M OR 3+ Low OR critical atoms Low
   
   Critical positions defined: ring junctions, bridgeheads, stereogenic centers, carbonyls, heteroatom sites.

6. **Honesty principle** (line 956):
   "Better to report Medium confidence and be right than High confidence and be wrong."

**Verification:** ✓ PASSED — Qualitative approach explicitly stated, per-atom 3-factor model documented, per-structure derivation with thresholds, downgrade rules prevent inflation, worked examples provided.

### CONF-02: Ambiguous Assignments Documented

**Requirement:** "Ambiguous assignments explicitly documented with reasoning"

**Evidence in Section 10.4 (lines 798-836):**

1. **Mandatory documentation** (line 800):
   "All detected ambiguities MUST be documented in a dedicated 'Ambiguities Detected' section in the analysis output."

2. **Standard table format** (lines 804-813):
   | Carbon/Issue | Type | Resolution Detail | Impact on Constraints |
   
   Four complete example rows showing different ambiguity types.

3. **Required elements** (lines 815-831):
   - **Carbon/Issue:** Specific shifts or identifier
   - **Type:** Category (Close carbons, DEPT/HSQC conflict, Sparse HMBC, Other)
   - **Resolution Detail:** Quantitative specifics:
     - For close carbons: pts/ppm, min spacing, actual spacing
     - For conflicts: S/N values, DEPT-90 availability, decisive criterion
     - For sparse HMBC: threshold steps, final threshold, floor value
   - **Impact on Constraints:** Specific actions:
     - Which LSD commands added
     - Which multiplicity assigned
     - Confidence level assigned
     - Alternative interpretation

4. **Transparency principle** (line 833):
   "The user must be able to see exactly what ambiguity was detected, why it was detected (quantitative criteria), how it was resolved (which decision rule), and what the impact is (which constraints were affected)."

**Verification:** ✓ PASSED — Mandatory documentation requirement, standard table format with 4 required columns, quantitative detail specifications, transparency principle, complete examples.

### CONF-03: Suggested Additional Experiments

**Requirement:** "Suggested additional NMR experiments (WHAT, WHY, WHICH atom)"

**Evidence in Section 11.5 (lines 993-1038):**

1. **Specificity requirement** (line 995):
   "Suggestions must be actionable for a spectroscopist: include WHAT experiment, WHY it helps, and WHICH specific atom/issue it resolves."

2. **Template examples** (lines 997-1013):
   Five complete examples demonstrating WHAT/WHY/WHICH structure:
   
   **Example 1 (DEPT-90):**
   - WHAT: "Acquire **DEPT-90**"
   - WHY: "shows only CH carbons — peak visible = CH, peak absent = CH3"
   - WHICH: "to resolve CH/CH3 ambiguity at 28.5 ppm"
   
   **Example 2 (optimized HMBC):**
   - WHAT: "Acquire **HMBC with optimized nJCH delay (5 Hz instead of 8 Hz)**"
   - WHY: "Longer-range couplings (3JCH) are enhanced at lower nJCH values"
   - WHICH: "targeting C=O at 172.4 ppm which shows 0 correlations after threshold reduction"
   
   Plus 3 more examples (higher-resolution HSQC, re-acquisition for S/N, 1,1-ADEQUATE).

3. **Output template** (lines 1016-1035):
   ```markdown
   ## Recommended Additional Experiments
   
   1. **DEPT-90 acquisition** (highest priority)
      - Resolves: CH/CH3 ambiguities at 28.5 ppm and 32.1 ppm
      - Why: Definitive CH identification (CH visible, CH3 absent in DEPT-90)
      - Impact: Upgrades C3 and C7 from Medium to High confidence
   ```
   Complete template with prioritization.

4. **Prioritization guidance** (line 1037):
   "Order suggestions by impact (number of atoms affected, criticality of affected positions) and feasibility (standard experiments like DEPT-90 before advanced experiments like 1,1-ADEQUATE)."

**Verification:** ✓ PASSED — WHAT/WHY/WHICH structure explicitly required, 5 complete examples provided, output template includes impact assessment, prioritization guidance documented.

### Workflow Integration

**Verification of Section 9 integration:**

**Step 7 (line 558):**
"**Confidence Assessment**: After ranking, assess confidence for each carbon atom using the three-factor model (Section 11). Derive overall structure confidence. Document ambiguous assignments with reasoning in the Ambiguities Detected section (Section 10.4). If confidence is Medium or Low for specific atoms, suggest additional NMR experiments that would resolve the uncertainty (Section 11.5). Include 'Ambiguities Detected' and 'Assignment Confidence' sections in the analysis output."

**Integration points:**
- Step 3 (line 546): "scan all carbon pairs for close carbons using resolution-based detection (Section 10.1)"
- Step 3 (line 547): "if DEPT and HSQC disagree on multiplicity for any carbon, resolve using the priority tree (Section 10.2) and document in Ambiguities Detected section"
- Step 4 (line 549): "When close carbons are detected (Section 10.1), use LIST/PROP to encode ambiguity"
- Step 4 (line 549): "For quaternary carbons with 0 HMBC correlations, apply shift-based constraints (Section 10.3) and attempt targeted threshold reduction"

**Verification:** ✓ WIRED — Complete integration into workflow steps 3, 4, and 7 with specific section references.

### Quick Reference Integration

**Verification of Section 12 integration:**

**Confidence thresholds (lines 1055-1056):**
- "Per-atom confidence: High (MAE < 2.0, 3+ correlations, well-resolved), Medium (MAE 2-3.5, 1-2 correlations), Low (MAE > 3.5, 0 correlations, unresolved ambiguity)"
- "Structure confidence: High (>= 80% atoms High/Medium, <= 1 Low), Medium (>= 50% High/Medium), Low (< 50% High/Medium OR critical atoms Low)"

**Ambiguity red flags (lines 1068-1070):**
- "All atoms rated High confidence despite detected ambiguities: Confidence inflation (violates downgrade rules, Section 11)"
- "DEPT/HSQC multiplicity changing between iterations: Flip-flop (resolve once per Section 10.2, not repeatedly)"
- "Threshold reduction below 0.01 for quaternary carbon search: Noise territory (Section 10.3 floor determination)"

**Verification:** ✓ WIRED — Confidence thresholds and ambiguity red flags properly integrated into Quick Reference with section cross-references.

---

## Verification Methodology

### Automated Checks Performed

1. **Line count verification:** `wc -l skill/SKILL.md` → 1,079 lines (target: ~1,079)
2. **Section count verification:** `grep -c "^## [0-9]" skill/SKILL.md` → 12 sections (target: 12)
3. **Formula presence:** `grep "resolution = len(ppm_scale)"` → 1 occurrence
4. **Priority tree:** `grep "Priority-ordered decision tree"` → 1 occurrence
5. **LIST/PROP:** `grep "LIST/PROP mechanism"` → 1 occurrence
6. **Shift table:** `grep "160-180.*carboxylic"` → 1 occurrence (table present)
7. **20% reduction:** `grep "current_threshold.*0.8"` → 1 occurrence
8. **Qualitative approach:** `grep "qualitative judgment.*NOT computed percentages"` → 1 occurrence
9. **Ambiguities section:** `grep "Ambiguities Detected Output Section"` → 1 occurrence
10. **Experiments section:** `grep "Suggesting Additional NMR Experiments"` → 1 occurrence

### Content Quality Checks

1. **Section 10:** 254 lines (585-838), 4 subsections, substantive content with formulas, tables, algorithms
2. **Section 11:** 202 lines (839-1040), 5 subsections, worked examples, templates
3. **Workflow integration:** Step 7 complete, steps 3-4 reference ambiguity detection
4. **Quick Reference integration:** Confidence thresholds and red flags present
5. **Cross-references:** Sections 10-11 reference Sections 2, 6, 8 appropriately

### Anti-Pattern Scan

**Checked for:**
- Hard-coded 0.3-0.5 ppm thresholds → NOT FOUND (uses formula instead)
- Blanket DEPT/HSQC rules → NOT FOUND (explicit rejection present)
- Separate LSD variant files → NOT FOUND (single-file approach documented)
- Computed percentage confidence → NOT FOUND (qualitative judgment documented)
- Generic experiment suggestions → NOT FOUND (WHAT/WHY/WHICH structure enforced)

**Result:** No anti-patterns found.

---

## Summary

**All 7 requirements VERIFIED:**

- ✓ ETOL-01: Resolution-based close carbon detection (formula-based, NOT hard-coded)
- ✓ ETOL-02: Context-dependent DEPT/HSQC conflict resolution (priority tree, NOT blanket rule)
- ✓ ETOL-03: Ambiguous HMBC via LIST/PROP (single file, NOT separate variants)
- ✓ ETOL-04: Quaternary carbon sparsity (shift constraints + 20% threshold reduction)
- ✓ CONF-01: Confidence levels (qualitative High/Medium/Low, NOT computed percentages)
- ✓ CONF-02: Ambiguous assignments documented (mandatory table with reasoning)
- ✓ CONF-03: Suggested experiments (WHAT/WHY/WHICH structure)

**Phase goal ACHIEVED:** Error detection patterns and confidence-annotated output are fully encoded in skill/SKILL.md with substantive content, proper integration, and correct cross-referencing.

**Next phase ready:** Phase 24 (Supervisor Agent) can proceed with complete error tolerance and confidence framework in place.

---

_Verified: 2026-02-07T19:30:00Z_
_Verifier: Claude (gsd-verifier)_

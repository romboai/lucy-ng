---
phase: 22-hmbc-strategy-quality
plan: 01
subsystem: case-domain-knowledge
tags: [skill-authoring, hmbc-strategy, spectral-quality, nmr-analysis]

requires:
  - phase-21-skill-restructure
  - skill/SKILL.md foundation (8 sections, 418 lines)

provides:
  - spectral-quality-assessment-knowledge
  - incremental-hmbc-strategy-knowledge
  - quality-driven-workflow-adjustments
  - failure-decision-trees

affects:
  - phase-22-plan-02 (quality assessment tool implementation)
  - phase-22-plan-03 (incremental HMBC agent behavior)
  - phase-24-supervisor (convergence detection, loop prevention)

tech-stack:
  added: []
  patterns:
    - Adaptive iteration with small batches (3-5 correlations)
    - Quality-driven strategy adjustment (SNR/resolution thresholds)
    - Decision trees for zero-solution and convergence-stall recovery

key-files:
  created: []
  modified:
    - skill/SKILL.md: "Added 2 sections (quality + HMBC strategy), updated 2 sections (workflow + reference), 418 -> 610 lines (+192)"

decisions:
  - id: HMBC-ADAPTIVE
    choice: "Adaptive iteration approach, NOT fixed 3-phase recipe"
    rationale: "User's vision: 'starts carefully and continues until no structure is found'"
    alternatives: "Fixed 3-phase recipe rejected as too rigid"
  - id: BATCH-SIZE
    choice: "3-5 correlations per iteration"
    rationale: "Gives fine-grained control over solution count changes"
    alternatives: "Confidence-tier batching rejected for less controllability"
  - id: QUALITY-STRATEGY
    choice: "Quality findings actively modify agent strategy"
    rationale: "Not just warnings - agent adapts thresholds, tolerances, batch sizes"
    alternatives: "Passive warnings rejected as insufficient"
  - id: ITERATION-CAP
    choice: "~10 iterations maximum as safety cap"
    rationale: "Prevents runaway loops before Phase 24 supervisor exists"
    alternatives: "No cap rejected due to loop risk"

metrics:
  duration: 3 minutes
  completed: 2026-02-06
---

# Phase 22 Plan 01: HMBC Strategy and Spectral Quality Documentation Summary

**One-liner:** Teach AI agents adaptive HMBC iteration (3-5 batch) and quality-driven strategy adjustments through skill documentation

---

## What Was Built

Added two major sections to skill/SKILL.md teaching domain knowledge for robust CASE:

### Section 2: Spectral Quality Assessment (80 lines)
- S/N ratio evaluation with quality tiers (excellent/good/moderate/poor)
- Digital resolution impact and tolerance adjustments
- Artifact recognition (1J leakage, t1 noise, baseline roll)
- Strategy adjustment decision table
- Quality-driven modifications to thresholds, tolerances, and batch sizes

### Section 7: Incremental HMBC Constraint Strategy (95 lines)
- Core principle: NEVER dump all correlations at once
- High-confidence correlation selection criteria (unique assignment, strong intensity, quaternary involvement)
- Adaptive iteration loop (3-5 batch, observe solution count)
- Stopping conditions (success at ≤10, iteration cap at ~10, correlations exhausted)
- Zero-solution recovery diagnostic tree
- Convergence stall detection (3 iterations < 10% reduction)
- What NOT to do (prohibitions)

### Updated Sections
- **Section 9 (CASE Workflow):** Added quality assessment step 2.5, replaced one-shot LSD with incremental approach
- **Section 10 (Quick Reference):** Added quality thresholds, HMBC parameters, new red flags

File growth: 418 -> 610 lines (+192, within estimated 160-200)

---

## How It Works

### Spectral Quality Assessment
Agent assesses EVERY spectrum before peak picking:
1. Compute SNR = tallest peak / noise floor (relative, not absolute)
2. Calculate digital resolution = pts/ppm in 13C dimension
3. Detect artifacts (1J leakage, t1 noise, baseline roll)
4. Apply strategy adjustments based on quality tier

Quality findings actively modify behavior:
- SNR < 30: trust only top 50% HMBC, batch size 3
- Resolution < 5 pts/ppm: increase tolerance to ±2.5 ppm
- 1J artifacts detected: exclude from constraints

### Incremental HMBC Strategy
Agent builds LSD files iteratively instead of dumping all correlations:
1. Start with MULT + HSQC + heteroatom constraints (NO HMBC)
2. Run LSD to get baseline solution count
3. Select 3-5 high-confidence HMBC correlations
4. Add batch, run LSD, observe solution count change
5. Decision tree:
   - ≤10 solutions: STOP, rank
   - 0 solutions: Zero-solution recovery
   - >30% reduction: productive, continue
   - <10% reduction (3 iterations): stalled, diagnose
6. Repeat until success, cap (~10 iterations), or exhausted

High-confidence selection prioritizes:
- Unique carbon assignment (no others within ±3.0 ppm)
- Unique proton assignment (no others within ±0.2 ppm)
- Strong peak intensity (top quartile)
- Quaternary carbon involvement

---

## Key Decisions

### HMBC-ADAPTIVE: Adaptive Iteration, Not Fixed Recipe
User's vision was "starts carefully and continues until no structure is found" - an adaptive loop, not a rigid 3-phase recipe. The agent iterates continuously with small batches, observing solution count trends, rather than following a predetermined phase structure.

### BATCH-SIZE: 3-5 Correlations Per Iteration
Small batches give fine-grained control over solution count changes. The agent can detect which specific correlations are productive vs. conflicting. Larger batches or confidence-tier grouping would obscure this diagnostic feedback.

### QUALITY-STRATEGY: Active Modification, Not Passive Warnings
Quality findings modify agent behavior (thresholds, tolerances, batch sizes, trusted correlation percentage), not just generate warnings. Poor quality spectra get different processing strategies automatically.

### ITERATION-CAP: ~10 Iterations as Safety Limit
Prevents runaway loops before Phase 24 supervisor agent exists. Hitting the cap is treated as diagnostic failure (systematic issue), not normal convergence. Successful cases typically converge in 3-5 iterations.

---

## Requirements Coverage

All 7 requirements met:

| Requirement | Coverage | Evidence |
|-------------|----------|----------|
| HMBC-01 (Adaptive iteration) | ✓ Complete | Section 7 "Adaptive Iteration Loop" - iterative, not fixed recipe |
| HMBC-02 (Start 3-5 high-confidence) | ✓ Complete | Section 7 "High-Confidence Correlation Selection" + batch size |
| HMBC-03 (Decision trees) | ✓ Complete | Section 7 "Zero-Solution Recovery" + "Convergence Stall Detection" |
| HMBC-04 (Prohibit dump-all) | ✓ Complete | Section 7 "What NOT to Do" + Core Principle |
| QUAL-01 (S/N assessment) | ✓ Complete | Section 2 "S/N Ratio Evaluation" with quality tiers |
| QUAL-02 (Digital resolution) | ✓ Complete | Section 2 "Digital Resolution Impact" with resolution tiers |
| QUAL-03 (Artifact recognition) | ✓ Complete | Section 2 "Artifact Recognition" (1J, t1, baseline) |

---

## Deviations from Plan

None - plan executed exactly as written.

---

## What's Next

### Immediate (Phase 22 Plan 02)
Implement spectral quality assessment tool:
- Add MCP tool `assess_spectrum_quality` computing SNR, resolution, artifacts
- Return quality tier with recommended strategy adjustments
- Integrate into CASE workflow before peak picking

### Near-term (Phase 22 Plan 03)
Teach agent to use incremental HMBC strategy:
- Update LSD generation to start without HMBC
- Add iteration loop logic to agent behavior
- Implement high-confidence correlation selection
- Add convergence detection and failure recovery

### Phase 24 (Supervisor Agent)
Leverage this knowledge:
- Convergence stall detection -> escalation
- Iteration cap hit -> escalation
- Quality-driven timeout adjustments

---

## Testing Notes

No code changes - skill documentation only. Verification performed:

1. **Section count:** 10 sections (was 8) ✓
2. **Section numbering:** No duplicates, sequential 1-10 ✓
3. **Content verification:**
   - HMBC-01: "Adaptive Iteration Loop" found ✓
   - HMBC-02: "3-5 high-confidence" found (2 occurrences) ✓
   - HMBC-03: "Zero-Solution Recovery" + "Convergence Stall" found ✓
   - HMBC-04: "NEVER dump all HMBC" found ✓
   - QUAL-01: "S/N Ratio Evaluation" found ✓
   - QUAL-02: "Digital Resolution Impact" found ✓
   - QUAL-03: All 3 artifacts (1J, t1, baseline) found ✓
4. **Cross-references:** Section 2, Section 7 references in workflow ✓
5. **Quick Reference:** Quality thresholds + HMBC parameters added ✓

Real-world testing will occur when Phase 22 Plans 02-03 implement tools and agent behavior based on this knowledge.

---

## Notes

### Design Rationale

**Why adaptive iteration instead of fixed recipe?**
User's vision emphasized flexibility: "starts carefully and continues until no structure is found." Real molecules vary widely in constraint requirements. A fixed recipe (e.g., "Phase 1: quaternary, Phase 2: strong peaks, Phase 3: all remaining") would either under-constrain simple molecules or over-constrain complex ones. Adaptive iteration responds to the specific molecule's behavior.

**Why ~10 iteration cap?**
Two reasons:
1. Safety: prevents runaway loops before Phase 24 supervisor exists
2. Diagnostic: if 10 iterations haven't converged, something is systematically wrong (wrong formula, poor data quality, fundamental incompatibility). The cap forces the agent to surface the issue rather than iterate indefinitely.

Typical convergence: 3-5 iterations for successful cases. If taking >7, already diagnostic-worthy.

**Why quality-driven strategy adjustments?**
Poor quality spectra can't be rescued by better algorithms - they need different processing strategies. SNR < 30 means noise peaks outnumber real peaks; the agent must be more selective (top 50% HMBC only, batch size 3). Resolution < 5 pts/ppm means close carbons can't be distinguished; the agent must widen tolerances and mark ambiguous correlations. These adjustments prevent the agent from generating garbage results from poor data.

### Virgiline Case Study Deferred

User explicitly excluded adding Virgiline/CASE7 case study to SKILL.md due to concerns about dataset quality (potential data processing errors causing near-duplicate shifts). The case study may be added later if data quality is verified or used as a negative example of quality issues.

### No "Fixed 3-Phase Recipe"

The plan explicitly avoided this pattern. Language throughout Section 7 emphasizes adaptive, iterative, observational approach:
- "This adaptive iteration approach"
- "observing how the solution count changes"
- "Repeat from step 3 until..."

If any language suggests a fixed recipe, it's a documentation bug.

---

**Plan status:** Complete ✓
**Commit:** 1915bd4
**Files modified:** skill/SKILL.md (+192 lines)
**Duration:** 3 minutes
**Next:** Phase 22 Plan 02 (quality assessment tool)

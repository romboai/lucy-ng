# Phase 25: Diagnostic Specialist - Research

**Researched:** 2026-02-07
**Domain:** AI diagnostic specialist agents for LSD failure root cause analysis
**Confidence:** HIGH

## Summary

The diagnostic specialist is a Claude Code subagent that the supervisor spawns (via Task tool) to systematically diagnose LSD failures. The specialist has deep knowledge of the LSD manual (MULT, HSQC, HMBC, BOND, LIST, PROP, ELEM, SYME, DEFF, ELIM commands), NMR spectroscopy constraints, and common failure modes. When the CASE agent encounters stuck situations (0 solutions, 1000+ solutions), the supervisor delegates diagnostic analysis to this specialist, which produces a structured markdown report with findings, root cause, and recommended fixes.

This pattern leverages Claude Code's native subagent system (2026): supervisor spawns both CASE agent AND diagnostic specialist as separate subagents, avoiding nesting limitations. The diagnostic specialist uses systematic check procedures similar to multi-agent root cause analysis frameworks (MA-RCA pattern), where specialized agents handle distinct diagnostic subtasks with structured reporting outputs.

**Primary recommendation:** Define diagnostic specialist as a markdown agent in `.claude/agents/` with embedded LSD manual knowledge and systematic diagnostic procedures, spawned by supervisor via Task tool when CASE agent is stuck, producing structured markdown reports consumed by both supervisor and CASE agent.

## Standard Stack

The established architecture for diagnostic specialist agents in Claude Code 2026:

### Core

| Component | Version | Purpose | Why Standard |
|-----------|---------|---------|--------------|
| Claude Code subagents | Native | Specialist agent architecture | Official Claude Code feature; supervisor spawns via Task tool |
| Markdown + YAML | Standard | Agent definition format | YAML frontmatter for config, markdown for system prompt with embedded domain knowledge |
| Structured markdown reports | Standard | Diagnostic output format | Human-readable, AI-parseable, consumed by supervisor and CASE agent |
| Task tool | Native | Supervisor delegates to specialist | Built-in delegation mechanism; runs specialists in parallel with CASE agent |
| LSD manual knowledge | Embedded | Domain expertise for diagnostics | System prompt contains full LSD command reference, failure patterns, check procedures |

### Supporting

| Component | Version | Purpose | When to Use |
|-----------|---------|---------|-------------|
| Multi-level reasoning | Pattern | Systematic diagnostic checks | Structured procedures: check sp2 count → H budget → correlations → formula |
| Confidence scoring | Pattern | Rate findings as HIGH/MEDIUM/LOW | Quantify diagnostic certainty; LOW = suggest manual verification |
| Root cause taxonomies | Pattern | Classify failure types | Standard categories: constraint conflict, formula error, data quality, constraint insufficiency |
| Actionable recommendations | Pattern | Fix suggestions, not just diagnosis | Specific next steps with LSD command examples |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Separate diagnostic specialist | Supervisor does all diagnosis | Simpler but supervisor skill becomes bloated; Phase 24 does basic diagnosis, Phase 25 adds deep specialist |
| Python diagnostic scripts | LSD-specific rule engine | More precise rules but requires maintaining code; AI specialist adapts to new patterns |
| Knowledge base lookup | Hard-coded diagnostic decision tree | Faster but brittle; AI specialist reasons about novel combinations |
| JSON diagnostic reports | Markdown structured reports | More machine-parseable but less readable; AI agents understand natural language better |

**Installation:**

No installation required — Claude Code subagents are built-in. Diagnostic specialist defined in `.claude/agents/diagnostic-specialist.md`.

## Architecture Patterns

### Recommended Project Structure

```
.claude/
├── agents/
│   ├── supervisor.md               # Supervisor (spawns CASE + diagnostic specialist)
│   ├── case-agent.md               # CASE agent (optional - can use general-purpose)
│   └── diagnostic-specialist.md    # Diagnostic specialist (Phase 25)
skill/
├── supervisor/
│   └── SKILL.md                    # Supervisor domain knowledge (loop patterns)
├── diagnostic/
│   └── SKILL.md                    # Diagnostic specialist domain knowledge (LSD manual, check procedures)
└── SKILL.md                        # CASE domain knowledge (NMR, peak picking, LSD generation)
data/compound/
└── <compound-name>/
    ├── CASE-PROGRESS.md            # Written by CASE agent, read by supervisor
    ├── DIAGNOSTIC-REPORT.md        # Written by diagnostic specialist, read by supervisor + CASE agent
    ├── *.lsd                       # LSD input files
    └── *.sol                       # LSD solution files
```

### Pattern 1: Supervisor Spawns Diagnostic Specialist

**What:** When supervisor detects stuck state, it spawns diagnostic specialist as separate subagent (not nested under CASE agent).

**When to use:** When basic supervisor diagnosis (Phase 24) is insufficient; specialist performs deep LSD manual analysis.

**Example:**

```yaml
# Source: Phase 24 research on subagent nesting limitation
# Supervisor spawns diagnostic specialist when CASE agent is stuck

SUPERVISOR detects: Zero-solution loop (3+ iterations, 0 solutions)

SUPERVISOR action:
1. Read CASE-PROGRESS.md for full iteration history
2. Read latest LSD file
3. Spawn diagnostic specialist via Task tool:

Task(
  agent_type="diagnostic-specialist",
  instructions="Analyze LSD failure for compound at data/compound/virgiline.

  Read:
  - data/compound/virgiline/CASE-PROGRESS.md (iteration history)
  - data/compound/virgiline/virgiline-03.lsd (latest LSD file)
  - Spectra metadata if needed

  Diagnose:
  - Why did LSD return 0 solutions?
  - Systematic checks: sp2 count, H budget, HMBC conflicts, correlation order
  - Root cause identification

  Output:
  - Write structured report to data/compound/virgiline/DIAGNOSTIC-REPORT.md
  - Include: findings, root cause, recommended fixes with LSD command examples
  "
)

DIAGNOSTIC SPECIALIST runs, writes DIAGNOSTIC-REPORT.md

SUPERVISOR reads DIAGNOSTIC-REPORT.md, advises CASE agent with specific constraints
```

**Critical:** Supervisor spawns BOTH CASE agent AND diagnostic specialist. They are siblings, not parent-child (avoids nesting limitation).

### Pattern 2: Systematic Diagnostic Procedures

**What:** Diagnostic specialist follows systematic check procedures for each failure type (0 solutions, 1000+ solutions).

**When to use:** When root cause is unclear; systematic checks eliminate hypotheses methodically.

**Example:**

```markdown
# Diagnostic procedure for 0-solution failures
# Source: skill/SKILL.md Section 6 (LSD Reference) + Phase 24 loop detection patterns

## Check 1: sp2 Count (MUST BE EVEN)

Procedure:
1. Parse all MULT commands from LSD file
2. Count atoms with hybridization = 2
3. If count is odd → ROOT CAUSE FOUND

Example from virgiline-03.lsd:
```
MULT 1 C 2 0    ; sp2
MULT 2 C 2 1    ; sp2
MULT 3 C 2 1    ; sp2
MULT 4 C 3 2    ; sp3
MULT 5 C 3 3    ; sp3
MULT 6 O 2 0    ; sp2
MULT 7 O 2 0    ; sp2
MULT 8 N 3 0    ; sp3
```
sp2 count: 1 + 2 + 3 + 6 + 7 = 5 atoms (ODD)
**ROOT CAUSE: Odd sp2 count violates LSD constraint**

Recommended fix:
- Check molecular formula for correct heteroatom count
- Verify O6 and O7 hybridization (carbonyls are sp2, ethers are sp3)
- Example fix: If O7 is ether, change to "MULT 7 O 3 0"
```

## Check 2: Hydrogen Budget

Procedure:
1. Sum hydrogen counts from all MULT commands
2. Compare to molecular formula
3. If mismatch → ROOT CAUSE FOUND

Example:
```
Formula: C16H21NO2
MULT hydrogens: 1(0) + 2(1) + 3(1) + 4(2) + 5(3) + ... = 19 H
Expected: 21 H
**ROOT CAUSE: Missing 2 hydrogens**

Recommended fix:
- Check HSQC multiplicity assignments
- Likely: two CH carbons misassigned as quaternary
- Review DEPT-135 data for carbons with unclear multiplicity
```

## Check 3: HMBC 1J Artifacts

Procedure:
1. Compare HMBC correlations to HSQC positions
2. If HMBC peak within ±1.5 ppm (C) and ±0.3 ppm (H) of HSQC → likely 1J artifact
3. If artifact found → ROOT CAUSE FOUND

Example:
```
HSQC: C155.2-H7.8 (direct bond)
HMBC: C155.2-H7.8 (2-3 bond correlation)

**ROOT CAUSE: 1J artifact included as HMBC constraint**

LSD interpretation: C155.2 is both directly bonded to H7.8 (HSQC) AND 2-3 bonds away (HMBC)
This is impossible → 0 solutions

Recommended fix:
- Remove HMBC command for C155.2-H7.8
- Re-run LSD
```

## Check 4: Correlation Order

Procedure:
1. Verify all HSQC commands appear BEFORE HMBC commands in file
2. If HMBC references undefined H position → ROOT CAUSE FOUND

Example:
```
HMBC 1 5     ; carbon 1 correlates to H5
HSQC 5 5     ; defines H5

**ROOT CAUSE: HMBC appears before HSQC**

LSD error: "Cannot set HMBC correlation between 1 and H-5 because H-5 is not defined"

Recommended fix:
- Move all HSQC commands before HMBC commands
- Correct order: MULT → HSQC → HMBC
```
```

### Pattern 3: Structured Diagnostic Report Format

**What:** Diagnostic specialist produces markdown report with fixed structure: findings, root cause, recommendations.

**When to use:** Every diagnostic specialist invocation; supervisor and CASE agent consume this report.

**Example:**

```markdown
# Source: Root cause analysis template research (2026 RCA patterns)
# Adapted for LSD failure diagnosis

# Diagnostic Report: Virgiline LSD Failure

**Compound:** data/compound/virgiline
**Formula:** C16H21NO2
**Failure Type:** Zero solutions (iteration 3)
**Diagnostic Date:** 2026-02-07 15:42:18
**Diagnostic Agent:** diagnostic-specialist

---

## Summary

LSD returned 0 solutions after adding quaternary carbon HMBC batch (iteration 3). Root cause: 1J artifact included as HMBC constraint, creating impossible connectivity.

**Confidence:** HIGH — 1J artifact confirmed by comparing HMBC to HSQC positions.

---

## Findings

### Finding 1: 1J Artifact Detected (CRITICAL)

**What:** HMBC correlation C155.2-H2.1 matches HSQC position C155.2-H2.1 within artifact tolerance.

**Evidence:**
- HSQC peak: (155.08 ppm C, 2.08 ppm H)
- HMBC peak: (155.15 ppm C, 2.12 ppm H)
- Carbon difference: 0.07 ppm (within ±1.5 ppm threshold)
- Proton difference: 0.04 ppm (within ±0.3 ppm threshold)

**Impact:** LSD interprets this as "C155.2 is 2-3 bonds from H2.1" but HSQC says "C155.2 is directly bonded to H2.1". This is impossible.

**Confidence:** HIGH — textbook 1J artifact pattern.

### Finding 2: sp2 Count Correct

**What:** Verified sp2 atom count = 8 (even).

**Evidence:**
- sp2 carbons: 5 (from aromatic ring + carbonyl)
- sp2 oxygens: 2 (two carbonyls)
- sp2 nitrogens: 1 (pyridine-type)
- Total: 8 (EVEN) ✓

**Impact:** sp2 count is not the root cause.

**Confidence:** HIGH — count verified from MULT commands.

### Finding 3: Hydrogen Budget Correct

**What:** Verified total H count = 21 (matches formula).

**Evidence:**
- Sum of MULT hydrogen counts: 21 H
- Formula: C16H21NO2 (21 H)
- Match: ✓

**Impact:** Hydrogen budget is not the root cause.

**Confidence:** HIGH — verified from MULT commands and formula.

---

## Root Cause

**Primary:** 1J artifact (HMBC C155.2-H2.1) included as long-range correlation constraint.

**Why it caused failure:** HSQC defines C155.2 as directly bonded to H2.1 (1JCH). HMBC constraint says C155.2 is 2-3 bonds from H2.1. LSD cannot satisfy both constraints → 0 solutions.

**Contributing factors:** None — this is a single-cause failure.

---

## Recommended Fixes

### Fix 1: Remove 1J Artifact from HMBC Constraints (PRIMARY)

**Action:** Remove line from virgiline-03.lsd:
```
HMBC 5 12    ; C155.2-H2.1 (carbon 5, proton from carbon 12)
```

**Verification:** After removal, re-run LSD. If solutions return, 1J artifact was the root cause.

**Confidence:** HIGH — removing 1J artifacts is standard practice.

### Fix 2: Review Other HMBC Correlations for Artifacts (SECONDARY)

**Action:** Apply 1J artifact detection to all HMBC correlations added in iteration 3:
- C155.2-H2.1 (already identified)
- C155.2-H4.3 (check against HSQC)
- C172.4-H2.1 (check against HSQC)

**Verification:** Use tolerance ±1.5 ppm (C) and ±0.3 ppm (H). Flag any matches.

**Confidence:** MEDIUM — proactive check; may find additional artifacts.

### Fix 3: Re-run Guided HMBC Picker with Artifact Exclusion

**Action:** If multiple artifacts found, regenerate HMBC correlation list using `pick_hmbc_peaks` with stricter artifact exclusion.

**Verification:** Check that guided picker excluded flagged correlations.

**Confidence:** MEDIUM — depends on picker already having artifact detection (may need implementation).

---

## Supporting Data

### LSD File Analyzed
- Path: data/compound/virgiline/virgiline-03.lsd
- MULT commands: 16 atoms (16 C, 2 O, 1 N)
- HSQC correlations: 13
- HMBC correlations: 8 (including 3 added in iteration 3)

### Iteration History Context
- Iteration 1: 1,234 solutions (baseline, MULT + HSQC only)
- Iteration 2: 187 solutions (added 5 high-confidence HMBC, 85% reduction)
- Iteration 3: 0 solutions (added 3 quaternary HMBC, over-constrained)

### Spectral Quality (from CASE-PROGRESS.md notes)
- 13C S/N: Good (estimated 50+)
- HSQC S/N: Good
- HMBC S/N: Moderate (some weak correlations)

---

## Next Steps

1. **Immediate:** Remove HMBC C155.2-H2.1 from virgiline-03.lsd
2. **Verify:** Re-run LSD, expect solutions > 0
3. **Review:** Check remaining iteration 3 correlations (C155.2-H4.3, C172.4-H2.1) for artifacts
4. **Document:** Update CASE-PROGRESS.md with diagnostic findings and corrective action

---

## Diagnostic Methodology

**Systematic checks performed:**
1. sp2 count (EVEN requirement) → ✓ PASS
2. Hydrogen budget (matches formula) → ✓ PASS
3. 1J artifact detection (HMBC vs HSQC) → ✗ FAIL (artifact found)
4. Correlation order (HSQC before HMBC) → ✓ PASS (not checked, file structure correct)

**Time to diagnosis:** ~2 minutes

**Tools used:** Read (LSD file, CASE-PROGRESS.md), systematic check procedures

---

## Metadata

**Diagnostic confidence breakdown:**
- Finding 1 (1J artifact): HIGH — pattern confirmed with quantitative evidence
- Finding 2 (sp2 count): HIGH — deterministic count
- Finding 3 (H budget): HIGH — deterministic count
- Root cause: HIGH — 1J artifact is well-established failure mode
- Fix 1 recommendation: HIGH — standard corrective action

**Specialist model:** diagnostic-specialist subagent
**Supervisor:** lucy-supervisor
**CASE agent:** general-purpose (virgiline analysis)
```

### Pattern 4: Multi-Level Reasoning for 1000+ Solutions

**What:** For solution explosion failures, diagnostic specialist checks constraint count, quaternary connectivity, heteroatom constraints, symmetry encoding.

**When to use:** When LSD returns 1000+ solutions (severely under-constrained).

**Example:**

```markdown
# Diagnostic procedure for 1000+ solution failures
# Source: skill/SKILL.md Section 6.7 Solution Count Interpretation

## Check 1: ELIM Command Presence

Procedure:
1. Search LSD file for "ELIM" command
2. If found → ROOT CAUSE likely

Rationale: ELIM increases solution space by allowing correlation elimination. Should NEVER be in file unless 0-solution failure already diagnosed.

Recommended fix:
- Remove ELIM command
- Re-run LSD
- Expect massive reduction in solution count

## Check 2: Constraint Count vs. Atom Count

Procedure:
1. Count MULT atoms (carbons + heteroatoms)
2. Count HMBC correlations
3. Calculate ratio: correlations / atoms
4. If ratio < 0.5 → INSUFFICIENT constraints

Example:
```
16 atoms (13 C, 2 O, 1 N)
3 HMBC correlations
Ratio: 3/16 = 0.19 (VERY LOW)

**ROOT CAUSE: Insufficient HMBC constraints**

Recommended fix:
- Add high-confidence HMBC correlations (aim for ratio > 0.5)
- Follow incremental HMBC strategy (skill/SKILL.md Section 7)
- Target: 8-10 correlations minimum for 16 atoms
```

## Check 3: Quaternary Carbon Connectivity

Procedure:
1. Identify quaternary carbons (MULT with 0 H, no HSQC)
2. Count HMBC correlations involving each quaternary carbon
3. If quaternary has 0 HMBC → MAJOR constraint gap

Rationale: Quaternary carbons ONLY connect via HMBC. 0 HMBC = floating atom = thousands of solutions.

Example:
```
MULT 1 C 2 0    ; quaternary carbonyl
MULT 9 C 2 0    ; quaternary aromatic

HMBC correlations: none involving carbon 1 or 9

**ROOT CAUSE: Quaternary carbons with 0 HMBC correlations**

Recommended fix:
- Search HMBC spectrum for correlations to quaternary shifts
- Lower threshold if needed (see skill/SKILL.md Section 10.3)
- Add shift-based constraints if no HMBC visible
- Example: LIST L1 1 9; PROP L1 1 ELEM_O (carbonyls bonded to oxygen)
```

## Check 4: Heteroatom Position Constraints

Procedure:
1. Count heteroatoms (O, N, S) from MULT commands
2. Check for BOND or LIST/PROP constraints involving heteroatoms
3. If 0 heteroatom constraints → MAJOR constraint gap

Rationale: Heteroatom positions strongly constrain structure. No constraints = LSD tries all permutations.

Example:
```
MULT 13 O 2 0   ; carbonyl oxygen
MULT 14 O 3 0   ; ether oxygen
MULT 15 N 3 0   ; amine nitrogen

No BOND or LIST/PROP commands involving atoms 13, 14, 15

**ROOT CAUSE: Heteroatom positions unconstrained**

Recommended fix:
- Add BOND for known positions (carbonyl O bonded to specific C)
- Add LIST/PROP for ambiguous positions
- Example:
  BOND 1 13        ; C1 (carbonyl) bonded to O13
  LIST L2 6 7 8    ; possible N-CH3 carbons
  ELEM L3 N        ; all nitrogens
  PROP L2 1 L3     ; one of {C6,C7,C8} bonded to nitrogen
```

## Check 5: Symmetry Encoding

Procedure:
1. Check CASE-PROGRESS.md for symmetry detection
2. If symmetry detected but not encoded in LSD → constraint gap
3. Use SYME command to constrain equivalent atoms

Example:
```
Symmetry detected: para-substituted benzene (2 pairs of equivalent CH)

MULT 5 C 2 1    ; aromatic CH
MULT 6 C 2 1    ; aromatic CH (equivalent to C5)
MULT 7 C 2 1    ; aromatic CH
MULT 8 C 2 1    ; aromatic CH (equivalent to C7)

No SYME constraints

**ROOT CAUSE: Symmetry not encoded, LSD treats as independent atoms**

Recommended fix:
- Add SYME commands (if supported by LSD version)
- Or use LIST/PROP to encode symmetry constraints
- Check LSD manual for symmetry command syntax
```
```

### Anti-Patterns to Avoid

- **Generic diagnosis without evidence:** "Probably a constraint issue" — specialist must provide quantitative findings
- **Recommending fixes without LSD command examples:** Supervisor/CASE agent need concrete syntax
- **Single-check diagnosis:** Always run full systematic procedure, document all checks (even PASSes)
- **Ignoring spectral quality context:** Check CASE-PROGRESS.md for quality notes; poor S/N affects diagnosis
- **Spawning diagnostic specialist from CASE agent:** Only supervisor can spawn (nesting limitation)
- **Overwriting DIAGNOSTIC-REPORT.md:** Append new reports or use timestamped filenames for multiple diagnostics

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| LSD command parsing | Custom regex parser | Read file, extract patterns with string methods | LSD syntax is simple; complex parser overkill; AI can read markdown examples directly |
| Diagnostic report templates | JSON schema with strict fields | Markdown with structured sections | AI agents consume natural language better; markdown is human-readable |
| Root cause taxonomies | Hard-coded decision tree | Systematic check procedures in system prompt | AI specialist can adapt to novel combinations; decision trees are brittle |
| Artifact detection thresholds | Fixed ±1.5 ppm rule | Context-dependent tolerance from spectral quality | Different spectra have different resolutions; one threshold doesn't fit all |
| Confidence scoring formulas | Mathematical weighted sum | Qualitative HIGH/MEDIUM/LOW with reasoning | Transparency > precision; user wants to understand WHY confidence is low |

**Key insight:** Diagnostic specialist is an AI agent, not a rules engine. Leverage natural language understanding for diagnosis; use structured markdown for reporting. Don't rebuild expert system infrastructure that was common in the 1990s-2000s — modern LLMs handle diagnostic reasoning natively when given domain knowledge and systematic procedures.

## Common Pitfalls

### Pitfall 1: Spawning Diagnostic Specialist from CASE Agent

**What goes wrong:** CASE agent tries to spawn diagnostic specialist via Task tool; fails due to nesting limitation.

**Why it happens:** Misunderstanding Claude Code subagent architecture; assuming any agent can spawn any other agent.

**How to avoid:** Only supervisor spawns subagents. CASE agent reports to supervisor; supervisor spawns diagnostic specialist. They are siblings, not parent-child.

**Warning signs:** Task tool error "nesting not allowed"; diagnostic specialist never runs; CASE agent stuck without diagnosis.

### Pitfall 2: Diagnostic Specialist Without LSD Manual Knowledge

**What goes wrong:** Specialist produces vague diagnosis like "check your constraints" without specific LSD command guidance.

**Why it happens:** LSD manual knowledge not embedded in system prompt; specialist has only general knowledge.

**How to avoid:** Include full LSD command reference in diagnostic specialist system prompt or skill document. Specialist must know MULT, HSQC, HMBC, BOND, LIST, PROP, ELEM, SYME, DEFF, ELIM syntax.

**Warning signs:** Recommendations lack LSD command examples; specialist says "add heteroatom constraints" without showing how; CASE agent can't act on vague advice.

### Pitfall 3: Unstructured Diagnostic Reports

**What goes wrong:** Specialist writes free-form narrative; supervisor can't parse findings; CASE agent unclear what to fix.

**Why it happens:** No template enforced; specialist improvises report structure.

**How to avoid:** Enforce structured markdown format in diagnostic specialist system prompt: Summary → Findings → Root Cause → Recommended Fixes → Supporting Data. Use consistent section headers.

**Warning signs:** Each diagnostic report has different structure; supervisor can't extract root cause reliably; CASE agent misinterprets recommendations.

### Pitfall 4: Single-Check Diagnosis

**What goes wrong:** Specialist checks sp2 count, finds it's even, stops — misses actual root cause (1J artifact).

**Why it happens:** Specialist stops at first PASS instead of completing full systematic procedure.

**How to avoid:** Systematic procedures MUST check ALL items, not stop at first pass. Document all checks (PASS or FAIL) in report. Root cause may be combination of factors.

**Warning signs:** Diagnostic reports show only 1-2 checks; root cause misidentified; fixes don't resolve issue.

### Pitfall 5: Ignoring Spectral Quality Context

**What goes wrong:** Specialist diagnoses "insufficient HMBC constraints" when actual issue is poor HMBC S/N (weak correlations not picked).

**Why it happens:** Specialist doesn't read spectral quality notes from CASE-PROGRESS.md.

**How to avoid:** Diagnostic specialist MUST read CASE-PROGRESS.md for quality assessment context. Poor S/N, low resolution, artifacts affect diagnosis. Include quality notes in Supporting Data section of report.

**Warning signs:** Recommendations ignore known quality issues; specialist suggests "add more HMBC" when HMBC S/N < 10 (not feasible).

### Pitfall 6: Diagnostic Specialist for Every Iteration

**What goes wrong:** Supervisor spawns diagnostic specialist after every CASE iteration; unnecessary overhead.

**Why it happens:** Misunderstanding when to delegate; supervisor should do basic diagnosis, specialist for deep analysis only.

**How to avoid:** Supervisor does basic diagnosis (Phase 24 loop detection). Spawn diagnostic specialist only for stuck states: 3+ iterations zero solutions, 3+ iterations solution explosion without progress, 10+ iterations constraint churning.

**Warning signs:** DIAGNOSTIC-REPORT.md created for routine iterations; specialist provides obvious diagnosis ("add more constraints" for iteration 2 with 1000 solutions); wasted subagent invocations.

## Code Examples

Verified patterns from official sources:

### Diagnostic Specialist Agent Definition

```yaml
# Source: https://code.claude.com/docs/en/sub-agents (Claude Code subagent architecture)
---
name: diagnostic-specialist
description: >
  LSD failure diagnostic specialist. Systematically analyzes zero-solution and
  solution-explosion failures. Deep knowledge of LSD manual (MULT, HSQC, HMBC,
  BOND, LIST, PROP, ELEM, SYME, DEFF, ELIM). Produces structured diagnostic
  reports with findings, root cause, and recommended fixes.
tools:
  - Read
  - Bash
model: sonnet
permissionMode: default
---

# LSD Diagnostic Specialist

You are a diagnostic specialist for LSD (Logic for Structure Determination) failures in NMR-based structure elucidation.

## Your Role

When the supervisor detects that the CASE agent is stuck (0 solutions, 1000+ solutions, constraint churning), you are spawned to perform systematic root cause analysis and produce a structured diagnostic report.

You have deep knowledge of:
- LSD manual commands (MULT, HSQC, HMBC, BOND, LIST, PROP, ELEM, SYME, DEFF, ELIM)
- Common LSD failure modes
- NMR spectroscopy constraints (1J artifacts, digital resolution, S/N impact)
- Systematic diagnostic procedures

## Domain Knowledge

**LSD command reference:** See skill/diagnostic/SKILL.md for full LSD manual.

**Systematic check procedures:** See skill/diagnostic/SKILL.md for 0-solution and 1000+ solution diagnostic procedures.

**NMR constraints:** See skill/SKILL.md for spectral quality impact on constraints.

Do not duplicate content from these skill documents. Reference them when needed.

---

## Diagnostic Workflow

When spawned by supervisor, you will receive:
- Compound path
- Latest LSD file path
- CASE-PROGRESS.md path
- Failure type (0 solutions, 1000+ solutions, other)

### Step 1: Gather Context

Read:
1. CASE-PROGRESS.md — iteration history, solution counts, constraints added/removed
2. Latest LSD file — MULT, HSQC, HMBC, BOND, LIST, PROP, ELEM commands
3. Spectral quality notes from CASE-PROGRESS.md

### Step 2: Run Systematic Checks

For 0-solution failures, check in order:
1. sp2 count (MUST be even)
2. Hydrogen budget (matches formula)
3. 1J artifacts in HMBC (compare to HSQC positions)
4. Correlation order (HSQC before HMBC)
5. Close carbons causing ambiguous assignment

For 1000+ solution failures, check:
1. ELIM command presence (remove if found)
2. Constraint count vs. atom count (ratio should be > 0.5)
3. Quaternary carbon connectivity (0 HMBC = major gap)
4. Heteroatom position constraints (BOND or LIST/PROP)
5. Symmetry encoding (if symmetry detected)

Document ALL checks (PASS or FAIL), not just failures.

### Step 3: Identify Root Cause

From findings, identify THE PRIMARY root cause:
- Single-cause failures: "1J artifact in HMBC C155.2-H2.1"
- Multi-cause failures: "Primary: insufficient HMBC constraints (3/16 ratio). Contributing: quaternary carbons with 0 HMBC."

Rate confidence: HIGH (confirmed with evidence), MEDIUM (strong hypothesis), LOW (educated guess).

### Step 4: Recommend Fixes

Provide SPECIFIC, ACTIONABLE fixes:
- Include LSD command examples
- Explain what to remove/add/change
- Provide verification steps ("After removal, re-run LSD, expect solutions > 0")
- Prioritize fixes (PRIMARY, SECONDARY)

### Step 5: Write Structured Report

Write DIAGNOSTIC-REPORT.md to compound directory with this structure:

```markdown
# Diagnostic Report: <Compound Name> LSD Failure

**Compound:** <path>
**Formula:** <formula>
**Failure Type:** <0 solutions | 1000+ solutions | other>
**Diagnostic Date:** <timestamp>
**Diagnostic Agent:** diagnostic-specialist

---

## Summary

[1-2 paragraph executive summary]
[Root cause in one sentence]
[Confidence level]

---

## Findings

### Finding 1: <Title> (CRITICAL | MAJOR | MINOR)

**What:** [Description]
**Evidence:** [Quantitative data]
**Impact:** [Why this matters]
**Confidence:** HIGH | MEDIUM | LOW

[Repeat for each finding]

---

## Root Cause

**Primary:** [Main cause]
**Why it caused failure:** [Mechanism]
**Contributing factors:** [Secondary causes or "None"]

---

## Recommended Fixes

### Fix 1: <Title> (PRIMARY | SECONDARY)

**Action:** [Specific steps with LSD commands]
**Verification:** [How to confirm fix worked]
**Confidence:** HIGH | MEDIUM | LOW

[Repeat for each fix]

---

## Supporting Data

### LSD File Analyzed
- Path: <path>
- MULT commands: <count>
- HSQC correlations: <count>
- HMBC correlations: <count>

### Iteration History Context
[Brief summary from CASE-PROGRESS.md]

### Spectral Quality
[S/N, resolution notes from CASE-PROGRESS.md]

---

## Next Steps

1. [Immediate action]
2. [Verification step]
3. [Follow-up action]

---

## Diagnostic Methodology

**Systematic checks performed:**
1. <Check name> → ✓ PASS | ✗ FAIL
[List all checks]

**Time to diagnosis:** <estimate>
**Tools used:** <Read, Bash, etc.>

---

## Metadata

**Diagnostic confidence breakdown:**
- Finding 1: <level> — <reason>
- Root cause: <level> — <reason>
- Fix 1: <level> — <reason>

**Specialist model:** diagnostic-specialist subagent
**Supervisor:** lucy-supervisor
**CASE agent:** <agent identifier>
```

---

## Important Rules

1. **ALWAYS run full systematic procedure** — document all checks, not just failures
2. **NEVER give generic advice** — provide specific LSD commands, not "add constraints"
3. **ALWAYS include evidence** — quantitative data, not hunches
4. **RATE confidence honestly** — LOW confidence flags need for manual verification
5. **PRIORITIZE fixes** — PRIMARY fix first, SECONDARY optional
6. **Reference skill documents** — don't duplicate LSD manual, reference skill/diagnostic/SKILL.md

---

## Example Diagnostic Outputs

See skill/diagnostic/SKILL.md for full example diagnostic reports:
- 0-solution failure (1J artifact)
- 1000+ solution failure (insufficient constraints)
- Multi-cause failure (quaternary carbons + heteroatom constraints)
```

### Supervisor Spawning Diagnostic Specialist

```markdown
# Source: Phase 24 research (supervisor-agent patterns)
# Supervisor detects stuck state, spawns diagnostic specialist

# In supervisor.md system prompt:

When CASE agent is stuck (detected via loop patterns in Section 4), perform basic diagnosis first.

If basic diagnosis is insufficient (e.g., zero-solution loop but all basic checks pass), spawn diagnostic specialist for deep analysis:

```
Task(
  agent_type="diagnostic-specialist",
  instructions="Analyze LSD failure for compound at <path>.

  Read:
  - <path>/CASE-PROGRESS.md (iteration history)
  - <path>/<filename>.lsd (latest LSD file)

  Diagnose:
  - Why did LSD return <0 solutions | 1000+ solutions>?
  - Run systematic checks for <failure type>
  - Identify root cause with evidence

  Output:
  - Write structured report to <path>/DIAGNOSTIC-REPORT.md
  - Include: findings, root cause, recommended fixes with LSD command examples

  Confidence: Rate all findings and recommendations as HIGH/MEDIUM/LOW
  "
)
```

After diagnostic specialist completes:
1. Read DIAGNOSTIC-REPORT.md
2. Extract root cause and primary fix
3. Advise CASE agent with specific constraints based on diagnostic report
4. Include reference to report: "See DIAGNOSTIC-REPORT.md for full analysis"

Do NOT spawn diagnostic specialist for routine iterations (basic diagnosis is sufficient).

Spawn diagnostic specialist when:
- Zero-solution loop (3+ iterations, 0 solutions) AND basic checks pass
- Solution explosion (3+ iterations, >100 solutions, <10% reduction) AND basic checks pass
- Constraint churning (5+ iterations, high churn, no convergence) AND unclear root cause
```

### LSD 1J Artifact Detection Procedure

```python
# Source: skill/SKILL.md Section 2.3 Artifact Recognition
# Pseudocode for 1J artifact detection (diagnostic specialist reasoning)

def detect_1j_artifacts(hmbc_correlations, hsqc_correlations):
    """
    Check if HMBC correlations are actually 1J artifacts (direct bonds).

    1J artifacts appear in HMBC at same (C, H) position as HSQC peak.
    Tolerance: ±1.5 ppm (carbon), ±0.3 ppm (proton).

    Diagnostic specialist uses this logic in systematic checks.
    """
    artifacts = []

    for hmbc in hmbc_correlations:
        hmbc_c = hmbc.carbon_ppm
        hmbc_h = hmbc.proton_ppm

        for hsqc in hsqc_correlations:
            hsqc_c = hsqc.carbon_ppm
            hsqc_h = hsqc.proton_ppm

            carbon_match = abs(hmbc_c - hsqc_c) <= 1.5
            proton_match = abs(hmbc_h - hsqc_h) <= 0.3

            if carbon_match and proton_match:
                artifacts.append({
                    'hmbc': hmbc,
                    'hsqc': hsqc,
                    'c_diff': abs(hmbc_c - hsqc_c),
                    'h_diff': abs(hmbc_h - hsqc_h),
                    'confidence': 'HIGH'
                })

    return artifacts

# Diagnostic specialist reports:
# Finding: "1J artifact detected — HMBC C155.2-H2.1 matches HSQC within tolerance"
# Evidence: "Carbon difference: 0.07 ppm (threshold ±1.5), Proton difference: 0.04 ppm (threshold ±0.3)"
# Impact: "LSD sees impossible constraint (1-bond from HSQC, 2-3 bonds from HMBC)"
# Fix: "Remove HMBC command for C155.2-H2.1"
```

### Systematic Check Execution Log

```markdown
# Source: Multi-agent RCA framework (MA-RCA pattern from research)
# Diagnostic specialist documents ALL checks, not just failures

## Diagnostic Methodology

**Systematic checks performed:**

1. **sp2 count (EVEN requirement)** → ✓ PASS
   - sp2 atoms counted: 8 (5 C, 2 O, 1 N)
   - Even count: YES
   - Result: Not root cause

2. **Hydrogen budget (matches formula)** → ✓ PASS
   - MULT hydrogen sum: 21 H
   - Formula hydrogen count: 21 H
   - Match: YES
   - Result: Not root cause

3. **1J artifact detection (HMBC vs HSQC)** → ✗ FAIL
   - Artifacts found: 1
   - Location: HMBC C155.2-H2.1 matches HSQC (155.08, 2.08)
   - Carbon difference: 0.07 ppm (within ±1.5 ppm tolerance)
   - Proton difference: 0.04 ppm (within ±0.3 ppm tolerance)
   - Result: ROOT CAUSE IDENTIFIED

4. **Correlation order (HSQC before HMBC)** → ✓ PASS
   - HSQC commands at lines: 18-30
   - HMBC commands at lines: 32-39
   - Order correct: YES
   - Result: Not root cause

**Root cause determination:** Check 3 failed (1J artifact detected)

**Confidence:** HIGH — artifact confirmed with quantitative position matching

**Time to diagnosis:** ~90 seconds (4 checks, 1 root cause)

**Checks NOT performed (not applicable):**
- Close carbon detection (not zero-solution cause; applies to ambiguity encoding)
- ELIM command presence (file has no ELIM; check applies to 1000+ solutions)
```

## State of the Art

| Old Approach | Current Approach (2026) | When Changed | Impact |
|--------------|------------------------|--------------|--------|
| Rule-based expert systems (1990s-2000s) | AI diagnostic specialist with embedded knowledge | 2025-2026 | More flexible; handles novel failure combinations; natural language reasoning |
| Hard-coded diagnostic decision trees | Systematic check procedures in markdown | 2026 | Extensible; AI adapts to context; no code maintenance |
| Single-agent CASE with retry logic | Supervisor + diagnostic specialist delegation | 2026 | Separation of concerns; specialist has deep LSD knowledge; supervisor coordinates |
| JSON diagnostic outputs | Structured markdown reports | 2026 | Human-readable; AI-parseable; includes reasoning, not just findings |
| Generic "constraint issue" diagnosis | Specific root cause with LSD command examples | 2026 | Actionable; CASE agent can implement fix immediately |
| Diagnostic specialist spawned by CASE agent | Diagnostic specialist spawned by supervisor | 2026 | Avoids nesting limitation; supervisor coordinates both CASE + specialist |

**Deprecated/outdated:**
- Rule-based expert systems requiring code for each diagnostic rule (replaced by AI reasoning with embedded procedures)
- Generic retry advice without diagnosis (replaced by systematic root cause analysis)
- Spawning diagnostic specialist from CASE agent (replaced by supervisor delegation to avoid nesting)

## Open Questions

Things that couldn't be fully resolved:

1. **LSD SYME command support**
   - What we know: LSD has symmetry commands (SYME, DEFF) in manual
   - What's unclear: Are these commands supported in current LSD version used by lucy-ng? Syntax variations?
   - Recommendation: Diagnostic specialist should check LSD manual reference for SYME; if unsupported, use LIST/PROP to encode symmetry constraints; document in skill/diagnostic/SKILL.md

2. **Optimal diagnostic specialist invocation threshold**
   - What we know: Supervisor does basic diagnosis (Phase 24), specialist for deep analysis
   - What's unclear: Exactly when to delegate? After 1 failed supervisor intervention? After 3?
   - Recommendation: Start conservative: delegate after 2 failed supervisor interventions with same pattern OR when basic checks all pass but still stuck; refine based on usage

3. **Multi-cause failure prioritization**
   - What we know: Some failures have multiple root causes (e.g., insufficient constraints + quaternary carbons with 0 HMBC)
   - What's unclear: How should specialist prioritize fixes when multiple causes contribute?
   - Recommendation: Diagnostic specialist ranks fixes by impact: fix causing most constraint violation first (PRIMARY), then contributing factors (SECONDARY); document prioritization reasoning

4. **Diagnostic report retention policy**
   - What we know: Each diagnostic creates DIAGNOSTIC-REPORT.md in compound directory
   - What's unclear: Should old reports be overwritten, appended, or timestamped? How long to retain?
   - Recommendation: Use timestamped filenames (DIAGNOSTIC-REPORT-2026-02-07-154218.md) to preserve diagnostic history; helpful for understanding which fixes were attempted; supervisor references latest report

5. **Spectral quality impact on diagnostics**
   - What we know: Poor S/N and low resolution affect constraint validity (skill/SKILL.md Section 2)
   - What's unclear: Should diagnostic specialist suggest re-acquisition if quality is root cause? Who decides if re-acquisition is feasible?
   - Recommendation: Specialist flags quality issues in Supporting Data section; if root cause is "poor HMBC S/N preventing correlation detection", recommend re-acquisition as SECONDARY fix (PRIMARY: work with available data using shift-based constraints); supervisor escalates to user

## Sources

### Primary (HIGH confidence)

- [Create custom subagents - Claude Code Docs](https://code.claude.com/docs/en/sub-agents) - Official documentation on subagent architecture, spawning via Task tool
- [The LSD manual](https://nuzillard.github.io/LSD/MANUAL_ENG.html) - Official LSD command reference (MULT, HSQC, HMBC, BOND, LIST, PROP, ELEM)
- [Tutorial for the structure elucidation of small molecules by means of the LSD software - PubMed](https://pubmed.ncbi.nlm.nih.gov/28543725/) - LSD workflow and command examples
- skill/SKILL.md (1,079 lines, local file) - CASE domain knowledge including LSD reference (Section 6), error tolerance (Section 10)
- skill/supervisor/SKILL.md (678 lines, local file) - Supervisor loop detection patterns (Section 4), intervention procedures
- Phase 24 research (24-RESEARCH.md) - Supervisor architecture, subagent nesting limitation, advisory intervention model

### Secondary (MEDIUM confidence)

- [Leveraging multi-agent framework for root cause analysis | Complex & Intelligent Systems](https://link.springer.com/article/10.1007/s40747-025-02096-0) - MA-RCA multi-agent framework for systematic root cause analysis
- [Root cause analysis templates: 15 ready-to-use examples for 2026](https://monday.com/blog/project-management/root-cause-analysis-template/) - Structured RCA report format (findings, root cause, recommendations)
- [Root Cause Analysis Template from Frontline Data Solutions](https://www.fldata.com/root-cause-analysis-template/) - RCA sections: event description, timeline, investigative team, findings, corrective action
- [Logz.io AI Agent for RCA - AI-Powered Root Cause Analysis](https://logz.io/platform/features/ai-powered-root-cause-analysis/) - AI-powered RCA with structured reports, automated correlation
- [Claude Code multiple agent systems: Complete 2026 guide](https://www.eesel.ai/blog/claude-code-multiple-agent-systems-complete-2026-guide) - Multi-agent architecture patterns, specialist delegation
- [Complex System Diagnostics Using a Knowledge Graph-Informed and Large Language Model-Enhanced Framework](https://arxiv.org/abs/2505.21291) - Knowledge graph integration with LLM agents for structured diagnostic reasoning

### Tertiary (LOW confidence - informational only)

- [Knowledge Representation in Expert Systems: Structure](https://egarp.lt/index.php/LUMIN/article/download/85/82) - Expert system knowledge base patterns (historical context)
- [Expert Systems for Engineering Diagnosis: Styles, Requirements for Tools, and Adaptability](https://link.springer.com/chapter/10.1007/978-1-4899-2471-1_3) - Engineering diagnostic reasoning styles (1990s patterns, now superseded by AI)
- [How AI Improves Root Cause Analysis Automation](https://latenode.com/blog/workflow-automation-business-processes/business-process-automation-fundamentals/how-ai-improves-root-cause-analysis-automation) - AI RCA automation trends

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Claude Code subagents documented, LSD manual authoritative, MA-RCA framework validated
- Architecture: HIGH - Patterns verified in Phase 24 research, supervisor spawning mechanism confirmed, structured report format established
- LSD diagnostic procedures: HIGH - Based on LSD manual and skill/SKILL.md Section 6 (LSD Reference), Section 10 (Error Tolerance)
- Pitfalls: MEDIUM - Derived from subagent architecture constraints (nesting limitation) and multi-agent RCA patterns; some lucy-ng-specific issues inferred

**Research date:** 2026-02-07
**Valid until:** 30 days (stable LSD manual, but multi-agent diagnostic patterns evolving rapidly in 2026)

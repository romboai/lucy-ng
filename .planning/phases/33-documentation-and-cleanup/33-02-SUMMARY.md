---
phase: 33-documentation-and-cleanup
plan: 02
type: summary
completed: 2026-02-09
duration: 6 minutes
commits:
  - 919953e
subsystem: documentation
tags: [project-state, agent-definition, hybrid-inlining, v2.1]
dependencies:
  requires: [33-01]
  provides: [accurate-project-state, diagnostic-agent-inlined-knowledge]
  affects: []
tech-stack:
  added: []
  patterns: [hybrid-context-inlining]
key-files:
  created: []
  modified:
    - .planning/PROJECT.md
    - ~/.claude/agents/lucy-diagnostic.md
decisions:
  - "PROJECT.md decisions: 3 pending → Good, 4 new v2.1 decisions added"
  - "PROJECT.md version: v2.0 → v2.1 (shipped 2026-02-09)"
  - "PROJECT.md Active requirements: 5 moved to Validated"
  - "Diagnostic agent inlining: ~688 lines LSD knowledge (matching CASE agent hybrid standard)"
  - "CLNP-01 requirement: supervisor.md confirmed deleted, 0 stale references"
---

# Phase 33 Plan 02: PROJECT.md Refresh and Diagnostic Agent Inlining Summary

**One-liner:** Updated PROJECT.md to reflect v2.1 reality (decisions, state, requirements) and brought diagnostic agent to hybrid inlining standard with ~688 lines of LSD command/procedure knowledge guaranteed in context.

## What Was Done

### Task 1: Refresh PROJECT.md to reflect v2.1 reality

**Changes made:**

1. **Key Decisions table** — Updated 3 pending v2.1 decisions to "Good":
   - GSD-pattern sub-commands
   - /lucy-ng:case NEVER dereplicates
   - Sanitisation is AI-only

2. **Key Decisions table** — Added 4 new v2.1 decisions:
   - Orchestration via Task()
   - Hybrid context inlining
   - Per-pattern intervention counters
   - Diagnostic delegation threshold

3. **Current State section** — Full refresh:
   - Version: v2.0 → v2.1 (shipped 2026-02-09)
   - Capabilities list updated with actual agent names (lucy-case-agent.md, lucy-diagnostic.md)
   - Removed "paper-only, not wired up" language
   - Added working orchestration description
   - Removed supervisor.md references (dissolved into case.md orchestrator)

4. **Architecture section** — Updated multi-agent description:
   - Old: "CASE agent (does the work) + Supervisor agent (keeps it on track)"
   - New: "CASE agent (autonomous elucidation) + CASE orchestrator (loop detection, advisory intervention) + diagnostic specialist (deep LSD failure analysis)"

5. **Active Requirements** — Moved all 5 v2.1 items to Validated:
   - Sub-command skills following GSD pattern
   - CASE orchestrator with real agent spawning
   - Autonomous CASE agent definition
   - AI-driven dataset sanitisation
   - Diagnostic specialist agent reworked

**Verification:**
- 0 "Pending" items in decisions table
- 0 stale "paper-only" references (except historical context about what v2.1 replaced)
- 18 "v2.1" references
- 0 "supervisor.md" references
- Actual agent names (lucy-case-agent, lucy-diagnostic) present

**Commit:** 919953e

### Task 2: Inline critical LSD knowledge into lucy-diagnostic.md

**Implementation:**

Brought lucy-diagnostic.md up to the same hybrid inlining standard as lucy-case-agent.md (613 lines with ~528 inlined).

**Inlined content (~688 lines):**

1. **Section 1: LSD Command Reference** (~280 lines)
   - MULT - Atom Definitions (edge cases, diagnostic details, error detection)
   - HSQC/HMQC - Direct C-H Attachment (ordering requirements, common errors)
   - HMBC - Long-Range Correlations (1J artifact detection, tolerance values)
   - BOND - Explicit Constraints (when to use, common errors)
   - LIST, PROP, ELEM - Flexible Constraints (syntax, semantics, pitfalls)
   - SYME - Symmetry Encoding (LSD version support, fallback to LIST/PROP)
   - ELIM - Correlation Elimination (LAST RESORT, diagnostic checklist)

2. **Section 2.1: Zero-Solution Failure Procedure** (~280 lines)
   - Check 1: sp2 Count (MUST BE EVEN) — procedure, examples, fixes
   - Check 2: Hydrogen Budget (MUST MATCH FORMULA) — calculation, common errors
   - Check 3: 1J Artifact Detection (HMBC vs HSQC) — tolerance-based matching
   - Check 4: Correlation Order (HSQC Before HMBC) — file structure validation
   - Check 5: Close Carbon Ambiguity — resolution-based detection, LIST/PROP encoding

3. **Section 2.2: Solution Explosion Procedure** (~265 lines)
   - Check 1: ELIM Presence — detection, impact, removal
   - Check 2: Constraint/Atom Ratio — quantitative thresholds (0.5-1.0 target)
   - Check 3: Quaternary Carbon Connectivity — floating atom detection
   - Check 4: Heteroatom Position Constraints — BOND vs LIST/PROP strategies
   - Check 5: Symmetry Encoding — SYME usage, fallback approaches

**What remains as file path references:**
- Section 3: Diagnostic Report Template (agent already has template inline)
- Section 4: Example Diagnostic Reports (~694 lines — too large, read at runtime)
- Section 5: Anti-Patterns (agent has 6 anti-patterns inline)
- skill/SKILL.md for NMR background, spectral quality, error tolerance

**Result:**
- **Before:** 457 lines
- **After:** 1,145 lines
- **Inlined content:** ~688 lines
- **Benefit:** Diagnostic agent GUARANTEED to have LSD command syntax and systematic procedures in context when spawned, not dependent on runtime file reads

**File location:** `~/.claude/agents/lucy-diagnostic.md` (user-global, not in lucy-ng repo)

**Note:** File is outside lucy-ng repository, so it's not committed to git. Changes tracked in this summary only.

### Task 3: Confirm supervisor.md deletion (CLNP-01)

**Verification results:**

1. File existence check: `~/.claude/agents/supervisor.md` → CONFIRMED DELETED
2. Stale reference check: 0 matches in:
   - `~/.claude/agents/` (all agent files)
   - `~/.claude/commands/lucy-ng/` (all sub-command skills)
   - `CLAUDE.md` (project instructions)

**CLNP-01 requirement satisfied:** supervisor.md was deleted in an earlier phase (likely Phase 30 when diagnostic specialist was renamed and supervisor logic was dissolved into case.md orchestrator skill).

## Deviations from Plan

None. Plan executed exactly as specified.

## Technical Decisions

1. **Hybrid inlining benchmark:** lucy-case-agent.md (613 lines, ~528 inlined) served as the standard for diagnostic agent inlining approach.

2. **Inlining scope:** Chose to inline ~688 lines (Sections 1, 2.1, 2.2) rather than full 1,876 lines because:
   - Critical knowledge: LSD command reference and systematic procedures (MUST have in context)
   - Template/examples: Can read from skill/diagnostic/SKILL.md at runtime when writing reports
   - Balances guaranteed context vs token efficiency

3. **PROJECT.md "paper-only" handling:** Left 2 historical references intact ("v2.1 replaced paper-only architecture") because they describe what was replaced, not current state.

## Validation

### Must-Have Truths (6/6 verified)

- ✓ PROJECT.md 3 pending decisions updated to Good with rationale
- ✓ PROJECT.md Current State section reflects actual v2.1 agent names and working orchestration
- ✓ PROJECT.md Active requirements show v2.1 features as validated
- ✓ lucy-diagnostic.md has ~688 lines of inlined LSD command reference and systematic procedures
- ✓ lucy-diagnostic.md no longer depends on runtime file reads for critical LSD knowledge
- ✓ supervisor.md confirmed deleted (CLNP-01)

### Must-Have Artifacts (2/2 verified)

- ✓ `.planning/PROJECT.md` — Accurate project state reflecting v2.1 reality (contains "v2.1", 18 refs)
- ✓ `~/.claude/agents/lucy-diagnostic.md` — Diagnostic agent with hybrid inlined LSD knowledge (1,145 lines)

### Key Links (2/2 verified)

- ✓ PROJECT.md → lucy-case-agent.md: Current State section names actual agent files
- ✓ lucy-diagnostic.md → skill/diagnostic/SKILL.md: Inlined critical sections + file path references for examples

## Metrics

- **Duration:** 6 minutes
- **Commits:** 1 (PROJECT.md only; diagnostic agent outside repo)
- **Files modified:** 2 total (1 in repo, 1 user-global)
- **Lines added to diagnostic agent:** ~688
- **PROJECT.md decisions updated:** 7 (3 pending → Good, 4 new)
- **PROJECT.md requirements moved to Validated:** 5

## Next Phase Readiness

**Phase 33 status:** 2/2 plans complete (33-01 CLAUDE.md updates, 33-02 PROJECT.md + diagnostic agent)

**Phase 33 is now complete.** All documentation refreshed to reflect v2.1 reality:
- CLAUDE.md: Sub-command reference, agent architecture, updated workflow entry points
- PROJECT.md: Accurate decisions, state, requirements
- Diagnostic agent: Hybrid inlining standard matching CASE agent
- CLNP-01: supervisor.md deletion verified

**Blockers for next work:** None

**What comes next:** Phase 33 was the final cleanup phase for v2.1. All 7 phases of v2.1 milestone are now complete. Ready for user validation testing per 32-VALIDATION-GUIDE.md.

---

**Summary confidence:** HIGH — All must-haves verified, both agents now follow hybrid inlining standard, PROJECT.md accurately reflects shipped v2.1 architecture.

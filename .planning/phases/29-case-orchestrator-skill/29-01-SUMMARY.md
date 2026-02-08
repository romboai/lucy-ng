---
phase: 29
plan: 01
subsystem: multi-agent-orchestration
tags: [orchestrator, supervision, loop-detection, task-tool, sub-command]
requires: [28-01]
provides: [case-orchestrator-skill, loop-detection-logic, advisory-intervention]
affects: [30-diagnostic-specialist, 32-case-validation]
tech-stack:
  added: []
  patterns: [task-tool-spawning, append-only-progress-monitoring, per-pattern-tracking]
key-files:
  created:
    - "~/.claude/commands/lucy-ng/case.md"
  modified:
    - "~/.claude/commands/lucy-ng/lucy-ng.md"
decisions:
  - id: ORCH-ADVISORY-NOT-DIRECTIVE
    what: Advisory interventions say WHAT to fix, never HOW
    why: Preserves agent autonomy from Phase 28 design
    date: 2026-02-08
  - id: ORCH-PER-PATTERN-COUNTERS
    what: Track intervention failures separately for each of 4 loop patterns
    why: Different patterns have different root causes, global counter masks diagnostics
    date: 2026-02-08
  - id: ORCH-BATCH-MONITORING
    what: Spawn agent once for ~10 iterations, read progress after batch
    why: Efficient vs synchronous per-iteration spawning, agent runs autonomously
    date: 2026-02-08
  - id: ORCH-10-CYCLE-ESCALATION
    what: Escalate to user after 10 failed intervention cycles per pattern
    why: Balances automated recovery vs preventing infinite loops
    date: 2026-02-08
duration: 3 minutes
completed: 2026-02-08
---

# Phase 29 Plan 01: CASE Orchestrator Skill Summary

**One-liner:** Task-tool orchestrator that spawns lucy-case-agent, monitors via CASE-PROGRESS.md, detects 4 loop patterns, diagnoses with sp2/H/1J checks, intervenes advisory-style, tracks per-pattern failures, escalates after 10 cycles.

## What Was Built

Created the `/lucy-ng:case` orchestrator skill at `~/.claude/commands/lucy-ng/case.md` (622 lines) that dissolves v2.0 supervisor.md logic into a sub-command skill. The orchestrator spawns the autonomous CASE agent from Phase 28, monitors its progress through CASE-PROGRESS.md, detects unproductive loop patterns, performs basic diagnosis, generates advisory interventions, and escalates after 10 failed cycles per pattern.

**Key components:**

1. **12-step orchestration process:**
   - parse_arguments, validate_prerequisites, check_dereplication_first
   - spawn_case_agent (Task tool invocation)
   - monitor_progress (read CASE-PROGRESS.md)
   - detect_loops (4 pattern matching)
   - diagnose (basic checks)
   - intervene (advisory generation)
   - track_and_decide (per-pattern counters)
   - escalate (10-cycle threshold)
   - respawn (with advisory + skip-completed-work)
   - present_results (success or failure report)

2. **Loop detection patterns:**
   - ELIM_THRASHING: ELIM added 2+ times
   - ZERO_SOLUTION_LOOP: 3+ consecutive 0 solutions
   - SOLUTION_EXPLOSION: 3 iterations >100, <10% reduction each
   - CONSTRAINT_CHURNING: 5 iterations, >10 adds AND >5 removes, >50 solutions

3. **Basic diagnosis procedures:**
   - sp2 atom count (must be even)
   - Hydrogen budget (matches molecular formula)
   - 1J artifact detection (±1.5 ppm C, ±0.3 ppm H tolerance)

4. **Advisory intervention templates:**
   - One template per pattern
   - Says WHAT to fix (e.g., "sp2 count is odd")
   - Agent decides HOW to fix it
   - Never prescribes specific LSD file edits

5. **Per-pattern intervention tracking:**
   - 4 separate counters (not 1 global)
   - Escalate when SPECIFIC pattern hits 10 cycles
   - Escalation report identifies which pattern failed

6. **Updated routing page:**
   - Moved `/lucy-ng:case` from "Coming Soon" to main table
   - Added Quick Start example for full CASE workflow

## Decisions Made

**ORCH-ADVISORY-NOT-DIRECTIVE:** Advisory interventions tell agent WHAT to fix (e.g., "sp2 count is odd"), never HOW to fix it (e.g., "change line 15 from X to Y"). This preserves the agent autonomy design from Phase 28 where the agent has full domain knowledge to make correct implementation decisions.

**ORCH-PER-PATTERN-COUNTERS:** Track intervention failures separately for each of the 4 loop patterns using distinct counters (ELIM_THRASHING: N, ZERO_SOLUTION_LOOP: M, ...). Different patterns have different root causes (odd sp2 count vs 1J artifacts vs missing heteroatom constraints vs random correlation selection). A global counter would mask which specific failure mode is recurring and lose diagnostic value.

**ORCH-BATCH-MONITORING:** Spawn agent once with instructions to iterate ~10 times autonomously, read CASE-PROGRESS.md after batch completes. Agent runs multiple LSD iterations within its own execution and writes progress after each. Orchestrator monitors asynchronously, not synchronously per iteration. Re-spawn only when loop detected and intervention needed. This is efficient vs synchronous per-iteration spawning which would cause excessive Task calls.

**ORCH-10-CYCLE-ESCALATION:** Escalate to user after 10 failed intervention cycles for the SAME pattern. This balances automated recovery attempts (gives agent multiple chances to fix the issue with advisory guidance) vs preventing infinite loops (if 10 diagnostics don't resolve it, manual review is needed). Escalation report includes all attempted diagnostics and supervisor recommendation.

## How It Works

**Spawning:** Orchestrator uses Task tool to spawn lucy-case-agent with task-specific instructions (compound path, formula, optional advisory constraints). Agent already has 500-700 lines of inlined knowledge from Phase 28, so orchestrator does NOT duplicate that content. Agent runs autonomously for ~10 iterations, writes CASE-PROGRESS.md after each LSD run.

**Monitoring:** After agent batch completes, orchestrator reads CASE-PROGRESS.md to parse iteration history: solution counts, constraints added/removed, sp2 checks, H budget status, HMBC usage. Checks for convergence (solution_count ≤ 10 = success) or loop patterns.

**Loop detection:** Pattern matching on iteration history. ELIM thrashing = ELIM added 2+ times. Zero-solution loop = 3+ consecutive 0s. Solution explosion = 3 iterations >100 with <10% reduction. Constraint churning = 5 iterations with >10 adds AND >5 removes, still >50 solutions.

**Diagnosis:** For detected pattern, run basic checks. ELIM thrashing: count sp2 atoms (even?), verify H budget, check 1J artifacts. Zero-solution: identify conflicting batch, check for 1J artifacts, check close carbons. Solution explosion: check if ELIM present, check heteroatom constraints. Constraint churning: check if systematic strategy followed.

**Intervention:** Generate advisory based on diagnosis. Advisory says WHAT to fix with references to skill knowledge. Example: "ELIM thrashing detected. Root cause: sp2 atom count is 9 (odd). Before retrying: 1. Re-examine DEPT-135 spectrum to verify sp2 assignments. 2. Check if carbonyl oxygen is sp2 (should be) or sp3 (incorrect). 3. Adjust one MULT definition to make total sp2 count even. Reference: skill/SKILL.md Section 5.3. Do NOT add ELIM again until sp2 count is even."

**Tracking:** Increment intervention counter for THIS pattern only. If counter < 10, re-spawn agent with advisory. If counter ≥ 10, escalate to user with structured report (what was detected, diagnostics attempted, current state, supervisor recommendation).

**Re-spawning:** Task invocation includes: "Read CASE-PROGRESS.md to understand current iteration state. Resume from iteration N+1. Do NOT redo completed iterations. ADVISORY CONSTRAINTS from supervisor: [text]. Apply advisory guidance (WHAT to fix), decide HOW to implement it."

## Testing Evidence

**Validation approach:** Manual verification of requirement coverage (all 9 requirements from REQUIREMENTS.md).

**Verified:**
- SCMD-02: Skill spawns via Task(), monitors CASE-PROGRESS.md, detects loops, intervenes ✓
- ORCH-01: Task instructions task-specific only, not duplicating agent knowledge ✓
- ORCH-02: monitor_progress reads CASE-PROGRESS.md, parses solution counts/constraints/checks ✓
- ORCH-03: detect_loops checks 4 patterns with correct criteria (ELIM 2+, zero 3+, explosion 3/>100/<10%, churning 5/>10/>5/>50) ✓
- ORCH-04: diagnose performs sp2 count, H budget, 1J artifact checks (±1.5 ppm C, ±0.3 ppm H) ✓
- ORCH-05: intervene generates advisory (WHAT not HOW), anti-pattern documents "never directive" ✓
- ORCH-06: track_and_decide maintains 4 separate per-pattern counters ✓
- ORCH-07: escalate triggers after 10 cycles per pattern ✓
- ORCH-08: respawn includes advisory + skip-completed-work instructions ✓

**Verified outputs:**
- case.md exists at ~/.claude/commands/lucy-ng/case.md ✓
- 622 lines (exceeds 250 line minimum) ✓
- YAML frontmatter has name (lucy-ng:case), description, argument-hint, allowed-tools including Task ✓
- Contains all 12 step names from parse_arguments through present_results ✓
- References "lucy-case-agent" (agent to spawn) ✓
- Contains all 4 loop pattern names (ELIM_THRASHING, ZERO_SOLUTION_LOOP, SOLUTION_EXPLOSION, CONSTRAINT_CHURNING) ✓
- Contains per-pattern counter concept (4 separate counters explained at lines 313-323) ✓
- Contains "10" as escalation threshold (lines 322, 329) ✓
- Advisory templates say WHAT not HOW (lines 236-301) ✓
- Contains "CASE-PROGRESS.md" as monitoring interface (multiple references) ✓
- lucy-ng.md updated: case moved from "Coming Soon" to main table, Quick Start includes case example ✓

## Known Limitations

**Basic diagnosis only:** Phase 29 implements basic supervisor diagnosis (sp2 count, H budget, 1J artifacts). Phase 30 will add diagnostic specialist delegation for deep root cause analysis. For now, if basic diagnosis doesn't resolve the issue after 2 failures with same pattern, orchestrator continues basic diagnosis for all 10 cycles before escalating (not ideal, but Phase 30 will fix).

**No diagnostic specialist integration yet:** The diagnostic_specialist_placeholder section documents future delegation interface but does not implement it. Phase 30 will create the diagnostic-specialist agent and add delegation trigger logic (2 failures with same pattern). Phase 29 prepares the interface but doesn't use it.

**In-memory intervention counters:** Counters are maintained in-memory during a single CASE session. If user wants to resume a failed CASE session later, intervention history is lost. This is acceptable because CASE sessions are typically single-run (not multi-session like coding projects). If user feedback indicates need for persistence, can add in future.

**No validation via actual CASE run:** Phase 29 creates the orchestrator skill but does not execute a full CASE workflow to validate it works. Phase 32 (CASE Agent Validation) will run end-to-end tests with real compound data to prove the agent/orchestrator actually work. Phase 29 is skill definition only.

## Integration Points

**Spawns (Task tool):**
- lucy-case-agent (Phase 28) - autonomous CASE agent with 500-700 lines inlined knowledge

**Reads:**
- CASE-PROGRESS.md (written by agent after each iteration) - monitoring interface
- Latest LSD file (for diagnosis: sp2 count, H budget)
- skill/supervisor/SKILL.md (loop patterns, diagnostic procedures, advisory templates)
- skill/SKILL.md (referenced in advisories for agent to consult)

**Writes:**
- None (orchestrator only reads, spawns, and presents results)

**Future integration (Phase 30):**
- diagnostic-specialist agent (for deep root cause analysis after 2 basic diagnosis failures)
- DIAGNOSTIC-REPORT.md (specialist output, orchestrator will read to formulate specialist-informed advisory)

## Next Phase Readiness

**Phase 30 (Diagnostic Specialist Agent):**
- Can implement diagnostic specialist agent definition immediately
- Delegation interface documented in diagnostic_specialist_placeholder section (lines 521-540)
- Delegation trigger: 2 failed basic interventions with SAME pattern
- Specialist reads CASE-PROGRESS.md + latest LSD file, writes DIAGNOSTIC-REPORT.md
- Orchestrator reads report, formulates specialist-informed advisory, continues supervision

**Phase 32 (CASE Agent Validation):**
- Orchestrator skill ready for end-to-end validation
- Validation will prove: Task spawning works, agent writes progress correctly, loop detection triggers, advisory intervention reaches agent, escalation threshold enforced
- No blockers to Phase 32 execution

**No blockers identified.** All prerequisites for Phase 30 and Phase 32 are in place. The orchestrator skill is complete per the plan requirements.

## Deviations from Plan

None - plan executed exactly as written.

## Files Created

1. **~/.claude/commands/lucy-ng/case.md** (622 lines)
   - YAML frontmatter with lucy-ng:case command definition
   - 12-step orchestration process (parse, validate, spawn, monitor, detect, diagnose, intervene, track, escalate, respawn, present)
   - Task tool spawning with task-specific instructions only (not duplicating agent knowledge)
   - CASE-PROGRESS.md monitoring and parsing
   - 4 loop pattern detection with correct criteria
   - Basic diagnosis procedures (sp2, H budget, 1J artifacts)
   - Advisory intervention templates (WHAT not HOW)
   - Per-pattern intervention counters (4 separate)
   - 10-cycle escalation threshold per pattern
   - Agent re-spawning with advisory + skip-completed-work
   - loop_detection_reference section (pattern definitions)
   - diagnostic_specialist_placeholder section (Phase 30 interface)
   - anti_patterns section (what NOT to do)

## Files Modified

1. **~/.claude/commands/lucy-ng/lucy-ng.md**
   - Added `/lucy-ng:case` to main sub-commands table
   - Moved case from "Coming Soon" section
   - Added Quick Start example: `/lucy-ng:case data/compound/virgiline C16H21NO2`
   - Kept `/lucy-ng:sanitise` in "Coming Soon" (Phase 31)

## Metrics

- **Lines of code created:** 622 (case.md)
- **Lines of code modified:** 8 (lucy-ng.md)
- **Files created:** 1
- **Files modified:** 1
- **Orchestration steps:** 12
- **Loop patterns detected:** 4
- **Advisory templates:** 4
- **Diagnostic procedures:** 3 (sp2 count, H budget, 1J artifacts)
- **Escalation threshold:** 10 cycles per pattern
- **Requirements validated:** 9/9

## Lessons Learned

**Task tool spawning with hybrid context:** The Phase 28 agent already has 500-700 lines of inlined critical knowledge. Orchestrator Task instructions should add ONLY task-specific details (compound path, formula, advisory constraints). Duplicating the inlined content causes context bloat and wastes tokens. This pattern—agent has inlined knowledge, orchestrator adds task specifics—is the correct approach for multi-agent orchestration.

**Advisory vs directive intervention:** Advisory interventions (WHAT to fix) preserve agent autonomy. Directive interventions (HOW to fix it with specific file edits) make orchestrator brittle and violate the Phase 28 design where agent retains decision-making authority. The anti_patterns section documents this explicitly to prevent future developers from making directive interventions.

**Per-pattern tracking essential:** Tracking intervention failures per pattern (not globally) provides diagnostic value. When escalation happens, the structured report can say "ELIM thrashing failed 10 times" vs generic "10 interventions attempted." This tells the user which specific failure mode is recurring and what the supervisor tried. Global counters mask this information.

**Batch monitoring over synchronous:** Spawning the agent once for ~10 iterations (batch) and reading progress after batch completes is far more efficient than spawning per iteration. The agent runs autonomously, writes progress after each LSD run within its own execution, and returns when done or stuck. Orchestrator monitors asynchronously. This is the correct pattern for autonomous agents that perform multi-iteration work.

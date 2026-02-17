# Phase 47: UAT with Live Compounds - Research

**Researched:** 2026-02-17
**Domain:** End-to-end CASE team execution, live UAT protocol, regression testing
**Confidence:** HIGH (all findings from direct code inspection of the actual system)

---

## Summary

Phase 47 is the first live execution of the v4.0 5-agent CASE team (orchestrator + nmr-chemist + lsd-engineer + solution-analyst + devils-advocate). All team components were built across Phases 41-46 but have NEVER been run together on real NMR data. This UAT serves two purposes: validate the team fixes the 5 constraint-loss bugs documented from v3.0, and establish a performance baseline for v4.0 (iteration count, constraint coverage, solution quality) against the v3.0 Ibuprofen result (rank #1, MAE=2.23, 4 iterations, 13 solutions).

The UAT is a pure execution-and-observation exercise, not a coding phase. The primary task is running `/lucy-ng:case data/Ibuprofen C13H18O2`, observing the team's output, and comparing against the v3.0 baseline across 5 specific bug categories. There are no code changes planned — findings go into a report, and bugs discovered go into the next milestone. Additional test compounds (Pulegone, Virgiline) are listed as optional stretch goals but no NMR data for them currently exists in the repository; this is a significant constraint.

The v4.0 team architecture is fully specified. The orchestrator skill (`~/.claude/commands/lucy-ng/case.md`) is 1,060 lines. Four agent definitions exist at `~/.claude/agents/lucy-{role}.md`, each with explicit constraints, domain knowledge, and message templates. The `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` environment variable is already set to `1`. LSD solver and outlsd are both available. The environment is ready.

**Primary recommendation:** Plan one structured UAT plan that (1) runs the live team with Ibuprofen, (2) captures a structured pass/fail evaluation across the 5 v3.0 bugs and the 4 success criteria, and (3) writes a performance comparison report. Keep the plan linear — one run, one report, no coding.

---

## No User Constraints (CONTEXT.md not found)

No CONTEXT.md exists for Phase 47. All decisions are at Claude's discretion.

---

## Standard Stack

### Core (what Phase 47 actually uses)

| Tool | Version | Purpose | Notes |
|------|---------|---------|-------|
| `/lucy-ng:case` skill | v4.0 | Orchestrator that spawns the team | `~/.claude/commands/lucy-ng/case.md` — 1,060 lines |
| `lucy-nmr-chemist` agent | v4.0 | Peak picking + statistical detection | `~/.claude/agents/lucy-nmr-chemist.md` |
| `lucy-lsd-engineer` agent | v4.0 | LSD file construction + solver | `~/.claude/agents/lucy-lsd-engineer.md` |
| `lucy-solution-analyst` agent | v4.0 | Solution ranking + plausibility | `~/.claude/agents/lucy-solution-analyst.md` |
| `lucy-devils-advocate` agent | v4.0 | Pre-run validation gate | `~/.claude/agents/lucy-devils-advocate.md` |
| lucy-ng CLI | 0.1.0 | All NMR/LSD commands | `lucy --version` confirmed |
| LSD solver | available | Structure elucidation solver | `lucy lsd check` confirms both LSD and outlsd |
| Agent Teams | enabled | Multi-agent coordination | `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` confirmed |

### Test Data

| Compound | Formula | Data Path | Bruker Experiments |
|----------|---------|-----------|-------------------|
| Ibuprofen (required) | C13H18O2 | `data/Ibuprofen/` | 1-6: 13C, DEPT-135, DEPT-90, COSY, HSQC, HMBC + Ibuprofen.mol |
| PSP | unknown | `data/PSP/` | 1,2,5,6,7 + mol file |
| MC047_9 | unknown | `data/MC047_9/` | 1,2,3,5,6 |
| 4-(1-Hydroxyethyl)benzoic acid isopropylester | unknown | `data/4-(1-Hydroxyethyl)benzoic acid isopropylester/` | exists |

**Pulegone and Virgiline:** No NMR data for these compounds exists in the repository. Success criterion 4 in the phase description says "if time permits" — but "time permits" requires data to exist. The planner should note this as a blocker for those compounds. PSP and MC047_9 are the available alternative compounds, if their formulas are known.

---

## Architecture Patterns

### How the v4.0 CASE Team Runs

The team spawns exactly as specified in `case.md`:

1. **TeamCreate:** Creates team namespace `case-Ibuprofen` with task list.
2. **Task spawning:** Four agents spawned via `Task(team_name=...)`. Orchestrator IS the coordinator — no 5th coordinator agent spawned.
3. **Initial tasks:** Two tasks pre-created: `peak-picking` (claimed by nmr-chemist) and `lsd-iteration-01` (claimed by lsd-engineer).
4. **Message flow:** Agents post structured messages to coordinator. Coordinator writes CASE-PROGRESS.md as sole author.
5. **Iteration lifecycle:** Orchestrator creates each `lsd-iteration-NN` task after receiving [ITERATION-COMPLETE] + [VALIDATION-PASSED].
6. **Devils-advocate gate:** Every LSD file must pass validation before solver runs. BLOCKED = fix required, APPROVED = proceed.
7. **Termination:** Orchestrator sends shutdown_request to all 4 agents, TeamDelete cleans up.

### v3.0 Bug Evaluation Matrix

These 5 bugs are the primary regression tests. Each has a specific check:

| Bug | Description | v3.0 What Happened | v4.0 Fix | How to Verify |
|-----|-------------|-------------------|----------|---------------|
| Bug 1 | DEFF NOT dropped | 6 patterns written in iter 1, dropped in iter 2-4 | lsd-engineer: persists via inventory. DA: CRITICAL block if count drops | DEFF NOT count constant across all iterations in CASE-PROGRESS.md |
| Bug 2 | Signal grouping not applied | [44.90, 45.03] detected but never translated to SYME | DA: `pending_from_detection` check triggers WARNING after 3 iters | Check CASE-PROGRESS.md for SYME or grouped HMBC `(N M)` notation |
| Bug 3 | Grouped notation dropped | iter 1 `HMBC (6 7) 2` reverted to `HMBC 6 2` in iter 2+ | DA: grouped_hmbc array content check triggers CRITICAL if count drops | `HMBC (` notation count never decreases in CASE-PROGRESS.md |
| Bug 4 | PROP documented but BOND used | CASE-PROGRESS.md said PROP but LSD had BOND | DA: INFO check (BOND is valid if justified) | Document which was used and why |
| Bug 5 | No constraints from detection | Neighbours ran, only BOND C=O written | DA: `applied_from_detection` check triggers INFO/WARNING | Check inventory `applied_from_detection` vs `pending_from_detection` |

### CASE-PROGRESS.md as UAT Evidence

The orchestrator writes CASE-PROGRESS.md as sole author, creating a complete audit trail. After the run, the UAT evaluator (the researcher/human) reads this file to determine:
- Whether each bug was caught by devils-advocate (look for [VALIDATION-BLOCKED] with specific bug descriptions)
- Whether ibuprofen appears in top-3 rankings
- Iteration count vs v3.0 baseline (4 iterations)
- HMBC correlations used (X/Y ratio — measures constraint efficiency)

### Performance Comparison Report

The phase requires a v3.0 vs v4.0 comparison. The v3.0 baseline is:
- **Solution quality:** Ibuprofen rank #1, MAE=2.23, 13 final solutions
- **Iterations:** 4
- **Constraint bugs:** 5 bugs present (all listed above)
- **Wall-clock time:** Not recorded in v3.0 (iteration count is the surrogate metric)

v4.0 comparison metrics to capture:
- Ibuprofen rank and MAE in final ranking
- Iteration count
- Solution count at convergence
- DEFF NOT persistence across all iterations (0 = perfect, > 0 = regression)
- SYME or grouped notation applied for [44.90, 45.03] signal group
- Grouped HMBC notation persistence
- Constraints from detection (`applied_from_detection` count)

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Bug verification | Manual LSD file inspection scripts | Read CASE-PROGRESS.md and agent inventories | DA already logs all constraint counts; CASE-PROGRESS.md is the audit trail |
| Additional test compounds | Source NMR data from external databases | Use existing `data/PSP/` and `data/MC047_9/` (formulas needed) | Pulegone/Virgiline data doesn't exist; PSP/MC047_9 do |
| Agent timing | Custom instrumentation | Parse CASE-PROGRESS.md `Started:` timestamp + compute from final entry | Case.md already specifies elapsed time computation |
| Team health monitoring | Polling TaskList manually | Orchestrator's monitor_progress step handles this | Part of the existing orchestrator logic |

---

## Common Pitfalls

### Pitfall 1: Running the team without clearing the analysis/ directory

**What goes wrong:** If `data/Ibuprofen/analysis/` exists from a previous partial run, the lsd-engineer finds old LSD files, confusion about iteration numbering, constraint inventory from old run appears in new run.

**Why it happens:** The directory doesn't exist yet (confirmed: `ls data/Ibuprofen/analysis/` returned no such directory). But if a test run is done before the full UAT, it will be created.

**How to avoid:** Before the official UAT run, verify `data/Ibuprofen/analysis/` does not exist or is empty. If re-running, delete the directory first.

**Warning signs:** Iteration numbers jump (starts at 02, not 01), or CASE-PROGRESS.md has entries from a prior run.

### Pitfall 2: CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS not set in the session running the case command

**What goes wrong:** Orchestrator checks for this environment variable in `validate_prerequisites` step and stops if not set. Team never spawns.

**Why it happens:** The env var is set in the user's shell but may not be available in the Claude Code session context.

**How to avoid:** The prerequisite check in case.md explicitly checks `echo $CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS`. Run `/lucy-ng:status` first to verify environment. Confirmed: CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1 is currently set.

**Warning signs:** Orchestrator reports "Agent Teams required" and stops.

### Pitfall 3: UAT evaluates agent behavior, not tool behavior

**What goes wrong:** Finding that a CLI command produced wrong output and treating it as a UAT failure. Or conversely, finding a tool works but agent didn't use it, and treating this as a CLI bug.

**Why it happens:** v3.0 post-UAT findings were explicitly "confirmed agent behavior bugs — tools work, agent doesn't use them consistently."

**How to avoid:** Distinguish evaluation categories clearly. Tool failures are bugs in lucy-ng Python code (762 tests). Agent failures are gaps in agent definitions (the actual UAT target). Report these separately.

**Warning signs:** Confusing "detection ran correctly but agent ignored it" (agent bug) with "detection returned wrong data" (tool bug).

### Pitfall 4: No baseline measurement makes comparison meaningless

**What goes wrong:** UAT report says "v4.0 is better than v3.0" without specific metrics. Impossible to validate in future milestones.

**Why it happens:** Easy to run a successful CASE and write qualitative conclusions.

**How to avoid:** The comparison report must capture specific numbers: iteration count, final solution count, Ibuprofen rank, MAE, and per-bug status (fixed/regression). The planner should include a structured evaluation matrix in the plan.

**Warning signs:** Report uses words like "improved" or "better" without numbers.

### Pitfall 5: DA blocks cause the UAT to fail even when working correctly

**What goes wrong:** Devils-advocate catches a CRITICAL issue (e.g., sp2 count odd) in iteration 1, blocks the run, lsd-engineer fixes and resubmits. This looks like a "failure" in the UAT but is actually the system working as designed.

**Why it happens:** DA is expected to block. The fix-and-resubmit cycle is part of the protocol (intra-iteration revision).

**How to avoid:** UAT success criteria do not require zero DA blocks. A DA block that is correctly fixed is evidence the system is working. UAT failure is: DA blocks but lsd-engineer proceeds anyway, or DA doesn't catch known bugs.

**Warning signs:** Treating any [VALIDATION-BLOCKED] as a UAT failure.

### Pitfall 6: v4.0 coordination overhead may increase iteration count

**What goes wrong:** v4.0 requires DA gate before every solver run. If DA blocks once per iteration and lsd-engineer needs to fix, each "iteration" in v4.0 may consume 2 solver runs vs v3.0's 1. Iteration count may legitimately be higher than v3.0's 4.

**Why it happens:** v4.0 adds explicit validation that v3.0 didn't have. The DA gate is a feature, not overhead, but it adds round-trips.

**How to avoid:** Success criterion 3 says "time to solution < 2x v3.0 baseline (coordination overhead acceptable)." Use iteration count as surrogate. Up to 8 iterations is acceptable. Report the DA block count separately from iteration count.

**Warning signs:** Concluding v4.0 "failed" because it used 6 iterations vs v3.0's 4, without accounting for the additional quality assurance.

---

## Code Examples

### Running the CASE Team (the UAT trigger)

```bash
# From the lucy-ng project directory
cd /Users/steinbeck/Dropbox/develop/lucy-ng

# Then run via Claude Code:
# /lucy-ng:case data/Ibuprofen C13H18O2
```

### Evaluating DEFF NOT persistence (Bug 1 check)

After the run, verify in CASE-PROGRESS.md that each iteration shows:
```
DEFF NOT: 8 patterns (preserved from iteration N-1 / initialized)
```

If any iteration shows a count < 8, Bug 1 has regressed.

### Evaluating constraint inventory (DA validation)

Each LSD file written by lsd-engineer will contain:
```
; === CONSTRAINT INVENTORY v1 ===
; { "deff_not_patterns": ["C1CC1", "C1CCC1", ...], ...}
; === END CONSTRAINT INVENTORY ===
```

After the run, read any iteration's `compound.lsd` to verify the inventory block exists and `deff_not_patterns` is populated with 8 entries.

### Verifying Ibuprofen correct structure in top-3

Ibuprofen SMILES: `CC(C)Cc1ccc(cc1)C(C)C(=O)O`

In `analysis/final_results.md`:
- Check top-3 SMILES — at least one must match Ibuprofen (or be an enantiomer/conformer).
- v3.0 baseline: rank #1, MAE=2.23 ppm.

### Verifying grouped notation (Bug 3 check)

Ibuprofen has two isobutyl group carbons at [44.90, 45.03] ppm. After detection:
- nmr-chemist should report these as a group.
- lsd-engineer should use `HMBC (6 7) N` notation (parenthesized).
- DA should catch any reversion to simple `HMBC 6 N` in subsequent iterations.

Look in CASE-PROGRESS.md under ### Devils-Advocate for each iteration: `Grouped notation: N entries (preserved / N/A)`.

---

## Architecture: What Each Plan Should Do

Phase 47 needs 2 plans:

**Plan 47-01: Live UAT Run (Ibuprofen)**

This is the execution plan. Steps:
1. Verify environment (lucy version, LSD, teams env var, analysis/ dir does not exist)
2. Run `/lucy-ng:case data/Ibuprofen C13H18O2`
3. Observe the team running — no intervention unless something catastrophically wrong
4. After convergence or 10-iteration cap: read CASE-PROGRESS.md, read final_results.md
5. Evaluate against the 5-bug matrix (pass/fail per bug)
6. Evaluate against 4 success criteria from the phase description
7. Document findings: what passed, what regressed, what new issues appeared

**Plan 47-02: Performance Comparison Report**

This is the documentation plan. Steps:
1. Read Phase 47-01 findings
2. Compile structured comparison table: v3.0 vs v4.0 on solution quality, constraint coverage, iteration count
3. Document which v3.0 bugs are fixed, which regressed, which are new
4. If environment allows and data exists: run optional PSP/MC047_9 compound (need formula first)
5. Write the comparison report to `data/Ibuprofen/analysis/v4.0-UAT-report.md`

---

## Open Questions

1. **Formulas for PSP and MC047_9**
   - What we know: Bruker NMR data exists in `data/PSP/` and `data/MC047_9/`
   - What's unclear: The molecular formulas for these compounds (required for CASE)
   - Recommendation: Planner should note this as a data dependency. If formulas are known to the user, they can be added to the plan. Otherwise, Ibuprofen is the only confirmed test compound.

2. **Expected v4.0 iteration count**
   - What we know: v3.0 used 4 iterations. v4.0 adds DA gate. Each DA block adds at least one solver re-run.
   - What's unclear: How many DA blocks will occur in practice. Could be 0 (lsd-engineer follows protocol perfectly) or several.
   - Recommendation: Accept up to 8 iterations as within the "< 2x baseline" criterion. Report DA block count separately.

3. **New bugs not in the v3.0 list**
   - What we know: The 5 v3.0 bugs are the primary regression targets.
   - What's unclear: The v4.0 architecture is new — team coordination may introduce new failure modes not seen in the monolithic v3.0 agent (e.g., message ordering, task creation timing, agent idleness).
   - Recommendation: Keep an open "New Issues" section in the evaluation matrix for anything that wasn't in the v3.0 bug list.

4. **Should the UAT planner account for a loop-pattern intervention?**
   - What we know: The orchestrator's detect_loops step fires after each iteration. In v3.0 Ibuprofen, no loop patterns were detected (clean 4-iteration run).
   - What's unclear: Whether v4.0's stricter validation (DA gate) might cause zero-solution loops from overcorrection.
   - Recommendation: Include observation of any intervention events in the UAT evaluation. If detect_loops fires and sends an advisory, document it as evidence the orchestrator works — not as a failure.

---

## Sources

### Primary (HIGH confidence — direct code inspection)

- `~/.claude/commands/lucy-ng/case.md` — 1,060-line orchestrator skill (all team spawn, monitor, detect_loops, intervention, present_results logic)
- `~/.claude/agents/lucy-lsd-engineer.md` — constraint inventory system, DEFF NOT persistence rules, [ITERATION-COMPLETE] template
- `~/.claude/agents/lucy-nmr-chemist.md` — peak picking workflow, statistical detection protocol, [SETUP-COMPLETE] template
- `~/.claude/agents/lucy-solution-analyst.md` — two-tier ranking, chemical plausibility checks, [RANKING-COMPLETE] template
- `~/.claude/agents/lucy-devils-advocate.md` — three-check inventory reconciliation, v3.0 bug checklist, severity classification
- `/Users/steinbeck/Dropbox/develop/lucy-ng/.planning/STATE.md` — Phase 41-46 decisions, accumulated context, v3.0 baseline metrics
- `/Users/steinbeck/Dropbox/develop/lucy-ng/.planning/phases/v2.1-milestone-uat/v2.1-UAT.md` — v3.0 UAT run details, root causes, fixes applied

### Secondary (MEDIUM confidence — environment verification)

- `lucy --version` → 0.1.0 (confirmed working)
- `lucy lsd check` → LSD and outlsd both available
- `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` → confirmed set in current environment
- `data/Ibuprofen/` directory inspection → experiments 1-6 confirmed, Ibuprofen.mol present
- `data/PSP/`, `data/MC047_9/` → directories exist with Bruker data, formulas unknown
- 762 tests collected (pytest --collect-only confirms test suite intact)

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all components directly inspected, environment verified
- Architecture: HIGH — agent definitions, orchestrator skill, and coordination protocol all read in full
- Pitfalls: HIGH — grounded in v3.0 live UAT findings (confirmed bugs, not speculation)
- Open questions: MEDIUM — future agent behavior is unknown until the run happens

**Research date:** 2026-02-17
**Valid until:** Phase 47 execution (static architecture — no moving parts until the team runs live)

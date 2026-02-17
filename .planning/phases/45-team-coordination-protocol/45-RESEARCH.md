# Phase 45: Team Coordination Protocol - Research

**Researched:** 2026-02-17
**Domain:** Multi-agent CASE team coordination: task sequencing, stopping conditions, result synthesis, time measurement
**Confidence:** HIGH (all findings grounded in shipped Phases 41-44 artifacts, read directly from agent definitions and orchestrator skill)

---

## Summary

Phase 45 is primarily a **gap-filling and integration testing phase**, not a design phase. Phases 41-44 have already implemented the core coordination mechanics: spawn_case_team creates the team and initial tasks, monitor_progress handles message-based coordination, detect_loops enforces stopping conditions, and present_results synthesizes the final report. All 4 specialist agents have full workflow sections with TaskList/TaskUpdate/SendMessage protocols.

However, reading the actual shipped files reveals **four concrete gaps** that Phase 45 must close before the coordination protocol can be considered complete:

1. **Next-iteration task creation is missing from lsd-engineer's agent definition.** The case.md spawn prompt tells lsd-engineer to "Create lsd-iteration-02 task when done," but the lucy-lsd-engineer.md workflow has no TaskCreate step. The agent will complete iteration 1 and mark it done, but no iteration-02 task will be created unless the orchestrator creates it—which the orchestrator's workflow does not currently do either.

2. **Experimental shift list delivery to solution-analyst is underspecified.** solution-analyst workflow step 2 says "Read solutions.smi path and experimental shifts from task/messages." The task description does not include the shift list. The agent must find it in nmr-chemist's [SETUP-COMPLETE] message, but no protocol exists for this handoff: does solution-analyst read it from the task list, from team message history, or from the task description when the coordinator creates the ranking task?

3. **Parallel task execution (SC2) is not actualized.** The roadmap requires NMR detection and solution review to run in parallel where possible. Currently, only one ranking task is created (by the orchestrator) and only one peak-picking task is created. No mechanism exists for the orchestrator to create a "detect-more-hmbc" task (for nmr-chemist) and a "ranking" task (for solution-analyst) at the same time while lsd-engineer waits.

4. **Time-to-solution measurement (SC6) has no implementation.** Timestamps appear in CASE-PROGRESS.md (Started, Time per iteration), but no code computes elapsed time or compares to a v3.0 baseline. SC6 requires this to be measured and reported.

**Primary recommendation:** Phase 45 should have two plans: (1) close the four identified gaps in agent definitions and orchestrator workflow, (2) define and run a dry-run coordination test to verify the full iteration loop completes before Phase 47 UAT.

---

## What Was Shipped by Prior Phases (Critical Context)

### Current State After Phase 44

**Files shipped and verified:**
- `~/.claude/agents/lucy-nmr-chemist.md` (260 lines) — full workflow, [SETUP-COMPLETE] protocol
- `~/.claude/agents/lucy-lsd-engineer.md` (394 lines) — constraint inventory, [ITERATION-COMPLETE] protocol
- `~/.claude/agents/lucy-solution-analyst.md` (228 lines) — ranking workflow, [RANKING-COMPLETE] protocol
- `~/.claude/agents/lucy-devils-advocate.md` (337 lines) — inventory validation, [VALIDATION-PASSED/BLOCKED] protocol
- `~/.claude/commands/lucy-ng/case.md` (976 lines) — full orchestrator with spawn_case_team, write_progress, monitor_progress, detect_loops, diagnose, intervene, deliver_advisory, present_results, terminate_team

**Coordination mechanics already implemented:**

| Mechanism | Where | Status |
|-----------|-------|--------|
| Team spawn (TeamCreate + 4 Task calls) | case.md spawn_case_team | COMPLETE |
| Initial task creation (peak-picking, lsd-iteration-01) | case.md spawn_case_team | COMPLETE |
| Devils-advocate validation gate (lsd-engineer waits for APPROVED) | lucy-lsd-engineer.md workflow step 8 | COMPLETE |
| Coordinator-as-sole-writer for CASE-PROGRESS.md | case.md write_progress (9 triggers) | COMPLETE |
| Message-based progress monitoring | case.md monitor_progress | COMPLETE |
| Loop detection (4 patterns, per-pattern counters) | case.md detect_loops | COMPLETE |
| Stopping conditions (solution <= 10, iterations >= 10) | case.md detect_loops + monitor_progress | COMPLETE |
| Final report synthesis | case.md present_results | COMPLETE |
| Team termination (shutdown_request + TeamDelete) | case.md terminate_team | COMPLETE |

**What the orchestrator's spawn prompts tell lsd-engineer to do (but agent definition doesn't implement):**

```
"Create lsd-iteration-02 task when done.
 Convert solutions: outlsd 5 < compound.sol > solutions.smi"
```

The spawn prompt is correct (tells the agent what to do), but the agent's internal workflow (Section 6 of lucy-lsd-engineer.md) has only 14 steps and NONE of them is "create next iteration task via TaskCreate."

---

## Gap Analysis: What Phase 45 Must Add

### Gap 1: Next-Iteration Task Creation (CRITICAL)

**Problem:** The CASE workflow is iterative (3-10 LSD iterations). After lsd-iteration-01 completes, someone must create lsd-iteration-02. Currently:
- case.md creates lsd-iteration-01 in spawn_case_team
- lsd-engineer's workflow (14 steps) ends at "Mark task completed via TaskUpdate" — no TaskCreate step
- case.md's monitor_progress does not create next iteration tasks on message receipt

**Impact:** Without this gap fixed, the workflow stops after one LSD iteration. The team has no pending task to claim.

**Resolution options:**

Option A (Orchestrator creates next task): When case.md receives [ITERATION-COMPLETE] with solution_count > 10, it calls TaskCreate for lsd-iteration-{N+1}. Orchestrator is already the team manager; this fits the pattern. Requires adding TaskCreate call in monitor_progress after loop detection.

Option B (LSD-Engineer creates next task): Add TaskCreate step to lsd-engineer workflow after marking iteration complete. The spawn prompt already says to do this. Requires adding TaskCreate step to lucy-lsd-engineer.md.

Option C (Hybrid): Orchestrator creates the ranking task (if solution_count <= 10) OR creates next iteration task (if solution_count > 10), after receiving [ITERATION-COMPLETE]. lsd-engineer only claims tasks, never creates them.

**Recommendation: Option A (Orchestrator creates all tasks).** The orchestrator is already the task manager — it creates peak-picking and lsd-iteration-01 in spawn_case_team. Extending this pattern to subsequent iterations is consistent. It also gives the orchestrator full visibility into when iteration N+1 should start. The spawn prompt text should be cleaned up to remove the "Create lsd-iteration-02 task" instruction from lsd-engineer.

**What changes:**
- case.md `monitor_progress` step: after receiving [ITERATION-COMPLETE], after loop detection decides "continue," call `TaskCreate(subject="lsd-iteration-{N+1}", ...)` before returning to monitoring
- lucy-lsd-engineer.md: Remove "Create next iteration task" from spawn prompt text in case.md. The agent definition itself does not need TaskCreate.

### Gap 2: Experimental Shift List Delivery to Solution-Analyst (HIGH)

**Problem:** `lucy lsd rank solutions.smi --shifts "<comma_separated_shifts>"` requires the experimental 13C shifts as a comma-separated string. The solution-analyst's workflow says "Read solutions.smi path and experimental shifts from task/messages" but:
- The ranking task description (created by case.md spawn_case_team) does not include shifts
- The spawn task description says "Run: lucy lsd rank solutions.smi --shifts '...'" with literal ellipsis

**The 13C shifts are in nmr-chemist's [SETUP-COMPLETE] message** (sent to coordinator, not to task list). Solution-analyst needs to get them somehow.

**Resolution options:**

Option A: Coordinator embeds shifts in ranking task description when creating it. When solution count drops to <= 10, the orchestrator creates a ranking task with the shift list explicitly included.

Option B: Coordinator sends a direct SendMessage to solution-analyst with the shift list when creating the ranking task.

Option C: Solution-analyst reads from nmr-chemist's [SETUP-COMPLETE] output directly (from the CASE-PROGRESS.md ## Setup section, where coordinator writes all peaks).

**Recommendation: Option A (Orchestrator includes shifts in ranking task description).** The orchestrator has the [SETUP-COMPLETE] data (it wrote it to CASE-PROGRESS.md). When it creates a ranking task, it should embed the shift list: `"Run: lucy lsd rank analysis/iteration_NN/solutions.smi --shifts '155.08,132.1,...'"`. This makes the task description self-contained and eliminates inter-agent messaging for this dependency.

**What changes:**
- case.md `monitor_progress`: when solution_count <= 10 triggers ranking task creation, read shift list from CASE-PROGRESS.md (already written to ## Setup section by coordinator from [SETUP-COMPLETE]) and embed it in the TaskCreate description

### Gap 3: Parallel Task Execution (SC2) — Clarification Needed

**SC2 requires:** "Task assignment parallelizes where possible (NMR detection and solution review are independent)"

**Current state:** Only sequential tasks are created:
- peak-picking (nmr-chemist only) → then lsd-iteration-01 → then ranking (if converged)
- No parallel task creation mechanism exists

**What parallelization is actually possible?**

1. **NMR detection for next iteration vs solution review**: When solution_count is 10-50 (converging but not done), nmr-chemist could be selecting the next HMBC batch while solution-analyst reviews current solutions. This is genuinely parallel.

2. **Validation vs NMR work**: Devils-advocate validates the current LSD file while... nothing else is happening. This is already sequential by design (lsd-engineer must wait for APPROVED before running).

**Honest assessment:** True parallelization requires a fundamentally different task structure. Currently, each iteration is strictly sequential: nmr-chemist → lsd-engineer → devils-advocate → coordinator (run LSD) → solution-analyst. Parallelizing requires:
- Routing: "While lsd-engineer is building iteration N+1, solution-analyst reviews iteration N's solutions"
- This requires two independent tasks to exist at the same time

**Recommendation:** Define the one parallelization opportunity that is genuinely safe and add it to the orchestrator workflow. When solution_count > 10 after iteration N:
- Create lsd-iteration-{N+1} task (for lsd-engineer to start building)
- Create nmr-hmbc-batch-{N+1} task (for nmr-chemist to select next HMBC batch)
- These two tasks can run in parallel if nmr-chemist is selecting the batch and lsd-engineer is... waiting for the batch. This is actually NOT parallel—lsd-engineer needs nmr-chemist's output.

**The real parallelization:** When solution_count is exactly right for ranking (< 50, say), but not done (> 10), the orchestrator could:
- Trigger nmr-chemist to select the next HMBC batch (working toward iteration N+1)
- Trigger solution-analyst to rank current solutions (examining iteration N's quality)
- These are genuinely independent

**For planning purposes:** SC2 should be met by adding one parallel task creation pattern: after a non-converging iteration, create both an "hmbc-selection" task for nmr-chemist AND a "ranking" task for solution-analyst simultaneously. Both agents work while the other proceeds.

### Gap 4: Time-to-Solution Measurement (SC6) — Minimal Implementation

**SC6 requires:** "Time to solution measured and compared against v3.0 baseline (target: < 2x)"

**Current state:** case.md writes `**Started:** <timestamp>` in the CASE-PROGRESS.md header and `**Time:** <timestamp>` at each iteration header. No elapsed time computation exists anywhere.

**v3.0 baseline:** The Ibuprofen UAT ran in 4 iterations. Wall-clock time was not recorded in any log. The target "< 2x" implies a rough benchmark, not a precise measurement.

**Recommendation:** Add simple time measurement to present_results step:
- Record start time at spawn_case_team (already in CASE-PROGRESS.md header as "Started")
- At present_results, compute elapsed = now() - started
- Report in final summary: "Time to solution: N minutes (v3.0 baseline: unknown — note start/end timestamps for future comparison)"

The v3.0 baseline is not stored anywhere. For Phase 45, the goal is to record the v4.0 time so it CAN be compared in Phase 47. SC6 is really about "instrument for measurement" not "compare right now."

---

## Standard Stack

No new libraries or tools are needed for Phase 45. This phase operates entirely within the existing:

| Component | Tool | Status |
|-----------|------|--------|
| Team management | TeamCreate, TaskCreate, TaskUpdate, TaskList, SendMessage | Already in case.md allowed-tools |
| Agent workflows | SendMessage, TaskUpdate, TaskList | Already in all agent definitions |
| Timing | Bash `date` command | Standard, no import needed |
| Progress tracking | CASE-PROGRESS.md append-only writes | Implemented in write_progress |

**No new dependencies.** Phase 45 is purely about wiring existing mechanisms together correctly.

---

## Architecture Patterns

### Pattern 1: Orchestrator-Driven Iteration Creation

The orchestrator (case.md) is the SOLE creator of new iteration tasks. This is consistent with it being the sole writer of CASE-PROGRESS.md and the team manager.

```
On receive [ITERATION-COMPLETE] from lsd-engineer:
  1. Write ### LSD-Engineer section to CASE-PROGRESS.md (existing)
  2. Wait for [VALIDATION-PASSED] or [VALIDATION-BLOCKED] from devils-advocate (existing)
  3. Write ### Devils-Advocate section (existing)
  4. Write ### Coordinator solution count (existing)
  5. Run detect_loops (existing)
  6. If no loop and solution_count > 10 and iterations < 10:
     a. TaskCreate(subject="lsd-iteration-{N+1}", description="...with explicit context...")  ← NEW
     b. If appropriate: TaskCreate(subject="hmbc-selection-{N+1}", ...)  ← NEW (optional parallelism)
  7. Return to monitor_progress
```

### Pattern 2: Ranking Task With Embedded Shift List

When the orchestrator decides to trigger ranking (solution_count <= 10 OR safety cap reached), it creates the ranking task with all needed information:

```python
# Orchestrator creates ranking task (pseudocode)
TaskCreate(
  subject="ranking-iteration-{N}",
  description=f"""
    Rank LSD solutions from iteration {N}.
    solutions.smi path: analysis/iteration_{N:02d}/solutions.smi
    Experimental 13C shifts: {shift_list}  ← extracted from CASE-PROGRESS.md ## Setup
    Run: lucy lsd rank analysis/iteration_{N:02d}/solutions.smi --shifts "{shift_list}"
    Assess chemical plausibility.
    Write analysis/final_results.md.
    Send [RANKING-COMPLETE] message to coordinator.
  """
)
```

The shift list is extracted by the orchestrator from the `## Setup / ### NMR-Chemist` section of CASE-PROGRESS.md, where peak counts were written from [SETUP-COMPLETE].

### Pattern 3: Stopping Condition Decision Tree

```
After each iteration:
  IF solution_count == 0: check zero_solution counter (existing loop detection)
  IF solution_count <= 10: create ranking task, proceed to present_results
  IF iteration_count >= 10: proceed to present_results with "safety cap" caveat
  IF no loop detected AND solution_count > 10 AND iterations < 10: create next iteration task
  IF loop detected: diagnose + intervene (existing)
```

This decision tree already exists in detect_loops and monitor_progress. Phase 45 adds only the "create next iteration task" branch.

### Pattern 4: Simple Elapsed Time Recording

```bash
# In present_results, compute elapsed time:
START_TIME=$(grep "Started:" analysis/CASE-PROGRESS.md | head -1 | awk '{print $2, $3}')
END_TIME=$(date)
# Report in final summary
```

Since CASE-PROGRESS.md's header contains `**Started:** <timestamp>`, the orchestrator can parse this and compute elapsed time at the end. This is all that SC6 requires for Phase 45.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Task sequencing | Custom event queue, state machine | Orchestrator creates TaskCreate after each message | TeamCreate task list IS the event queue |
| Shift list storage | Separate state file, database | Embed in CASE-PROGRESS.md ## Setup (already written there) | Coordinator already wrote this data |
| Time measurement | Complex telemetry | `date` before/after, parse from CASE-PROGRESS.md header | SC6 needs "measured," not "analyzed" |
| Next-iteration triggering | Background poller, cron | On message receipt in monitor_progress | Messages arrive automatically; react then |

---

## Common Pitfalls

### Pitfall 1: LSD-Engineer Creates Next Task (Wrong Direction)

**What goes wrong:** Adding TaskCreate to lucy-lsd-engineer.md workflow creates confusion about who manages task flow. The lsd-engineer is a specialist — it does LSD work. If it also manages task sequencing, it has mixed responsibilities.

**Why it happens:** The case.md spawn prompt tells lsd-engineer to "Create lsd-iteration-02 task." If the planner reads only the spawn prompt and not the agent definition, they may implement TaskCreate in the agent.

**How to avoid:** Put TaskCreate in the orchestrator (case.md monitor_progress), not in the agent definition. Remove the "Create next iteration task" instruction from lsd-engineer's spawn prompt.

**Warning sign:** If lucy-lsd-engineer.md gains a TaskCreate tool in its frontmatter, this pitfall has occurred.

### Pitfall 2: Blocking Wait for Devil's Advocate Before Creating Next Task

**What goes wrong:** Orchestrator creates lsd-iteration-{N+1} task immediately after receiving [ITERATION-COMPLETE], but lsd-engineer tries to claim it before devils-advocate has validated the current file. Now two iterations run in parallel — but lsd-engineer should wait for APPROVED before running iteration N's solver.

**Why it happens:** Task creation and validation are decoupled if orchestrator creates next task too early.

**How to avoid:** The orchestrator creates lsd-iteration-{N+1} task ONLY AFTER receiving [VALIDATION-PASSED] for iteration N (not when receiving [ITERATION-COMPLETE]). The sequence is:
1. [ITERATION-COMPLETE] arrives → orchestrator writes LSD-Engineer section, asks DA to validate
2. [VALIDATION-PASSED] arrives → orchestrator writes DA section, LSD-Engineer runs solver
3. [ITERATION-COMPLETE] with solution_count → orchestrator creates next iteration task OR ranking task

Actually, this is already safe: the lsd-engineer workflow says "WAIT for devils-advocate approval before running solver." The iteration task can be created early without issue, because lsd-engineer for that task can't start until it gets approval for the current one. But to be safe, create next task only after convergence decision is made.

**Warning sign:** If solution count goes up unexpectedly (parallel over-constraining), check if two iterations ran simultaneously.

### Pitfall 3: Experimental Shifts Not Available at Ranking Time

**What goes wrong:** Orchestrator creates ranking task but forgets to embed the shift list. Solution-analyst runs `lucy lsd rank solutions.smi --shifts ""` with empty shifts, gets meaningless ranking.

**Why it happens:** The shift list is in the [SETUP-COMPLETE] message that arrived at the start of the workflow. By iteration 5, the orchestrator has processed many messages and may not have the shift list in easy scope.

**How to avoid:** The shift list is always in CASE-PROGRESS.md `## Setup / ### NMR-Chemist` section (written by coordinator from [SETUP-COMPLETE]). Orchestrator reads it from there when creating the ranking task. Alternatively, store it in a dedicated variable in monitor_progress.

**Warning sign:** If `lucy lsd rank` is called without `--shifts`, the ranking output will be wrong. Look for this in Phase 47 UAT.

### Pitfall 4: SC6 Time Baseline Not Recorded

**What goes wrong:** Phase 45 instructs orchestrator to "measure time" but no one records the v3.0 baseline (it was not recorded during Phase 32-47 UAT). At Phase 47, "< 2x" cannot be verified.

**Why it happens:** The v3.0 Ibuprofen UAT run succeeded but no timing was logged in CASE-PROGRESS.md.

**How to avoid:** For Phase 45, accept that the v3.0 baseline is unavailable. SC6's intent is: "This is a new architecture with coordination overhead; confirm it's not catastrophically slow." Record v4.0 time. Compare iteration counts (v3.0 had 4 iterations). If v4.0 needs <= 8 iterations and each iteration takes similar time, it's within 2x.

**Alternative baseline:** The MEMORY.md states "4 iterations, 13 solutions" for the v3.0 Ibuprofen run. The iteration count IS the available baseline. Phase 45 should use "iteration count <= 2x v3.0 iteration count" as the surrogate for time comparison.

---

## Code Examples

Verified patterns from existing shipped files (all confirmed by reading actual agent/orchestrator files):

### Orchestrator Creates Next Iteration Task (New — to add to case.md monitor_progress)

```markdown
After receiving [ITERATION-COMPLETE] and [VALIDATION-PASSED], after running LSD:

If solution_count > 10 AND iterations < safety_cap AND no loop detected:

  next_iteration = current_iteration + 1
  TaskCreate(
    subject="lsd-iteration-{next_iteration:02d}",
    description="Build LSD file for iteration {next_iteration} of {formula} at {compound_path}.
                 Read previous: analysis/iteration_{current_iteration:02d}/compound.lsd
                 Use constraint inventory to copy all constraints.
                 Add next HMBC batch (3-5 correlations, best remaining).
                 Send validation request to devils-advocate.
                 WAIT for approval.
                 Run LSD from analysis/iteration_{next_iteration:02d}/.
                 Convert solutions: outlsd 5 < compound.sol > solutions.smi
                 Send [ITERATION-COMPLETE] to coordinator.",
    activeForm="LSD iteration {next_iteration}"
  )

If solution_count <= 10:
  TaskCreate(
    subject="ranking-iteration-{current_iteration:02d}",
    description="Rank solutions from iteration {current_iteration}.
                 solutions.smi: analysis/iteration_{current_iteration:02d}/solutions.smi
                 Experimental shifts: {shift_list}
                 Run: lucy lsd rank analysis/iteration_{current_iteration:02d}/solutions.smi --shifts '{shift_list}'
                 Assess chemical plausibility.
                 Write analysis/final_results.md.
                 Send [RANKING-COMPLETE] to coordinator.",
    activeForm="Ranking LSD solutions"
  )
```

### Orchestrator Extracts Shift List From CASE-PROGRESS.md

The peak list is in the `## Setup / ### NMR-Chemist` section. The coordinator wrote it there from [SETUP-COMPLETE]. At ranking time:

```bash
# Orchestrator reads CASE-PROGRESS.md to get shifts
# The NMR-Chemist section contains "Peak counts: 13C: N" and the shift assignments
# The orchestrator (LLM) reads this section and reconstructs the shift list
# Or: parse from the task description of the peak-picking task (shift list embedded there)
```

**Better pattern:** The orchestrator should store the shift list as a variable during monitor_progress when [SETUP-COMPLETE] arrives, keeping it in scope for later ranking task creation. The orchestrator is an LLM — it should retain this from the message it received.

### Time Recording in present_results

```markdown
## CASE Results

**Compound:** {compound_path}
**Formula:** {formula}
**Iterations:** {N}
**Started:** {start_timestamp from CASE-PROGRESS.md header}
**Completed:** {current timestamp}
**Time to solution:** ~{elapsed_minutes} minutes ({N} iterations × ~{minutes_per_iteration} min/iteration estimated)
**v3.0 baseline (Ibuprofen):** 4 iterations — v4.0 used {N} iterations ({N/4:.1f}x)
```

---

## Phase 45 Plans Recommendation

### Plan 45-01: Close Coordination Gaps (4 files)

**Target:** Add next-iteration task creation to orchestrator, add shift list delivery protocol, clean up spawn prompt mismatches.

**Files to modify:**
- `~/.claude/commands/lucy-ng/case.md` — add TaskCreate(next iteration) to monitor_progress; add TaskCreate(ranking) with shift list; add time recording to present_results
- `~/.claude/agents/lucy-lsd-engineer.md` — remove "Create next iteration task" from role description (orchestrator does it); agent needs no TaskCreate
- `~/.claude/agents/lucy-solution-analyst.md` — update workflow step 2 to say "Read shifts from task description (coordinator provides)"

**Out of scope for 45-01:** New agents, new protocols, restructuring existing workflows.

### Plan 45-02: Dry-Run Coordination Verification (documentation + checklist)

**Target:** Verify the full iteration loop is executable by tracing through the message flow manually (or via a dry-run).

**What to verify:**
1. Spawn team → peak-picking task created → nmr-chemist claims it → [SETUP-COMPLETE] sent → coordinator writes setup section ✓
2. lsd-iteration-01 task → lsd-engineer claims → builds LSD → sends DA validation request → DA validates → [VALIDATION-PASSED] → lsd-engineer runs solver → [ITERATION-COMPLETE] ✓
3. Coordinator receives [ITERATION-COMPLETE] → solution_count > 10 → creates lsd-iteration-02 task ← NEW
4. solution-analyst monitoring: sees no pending ranking task → waits ✓
5. After N iterations → solution_count <= 10 → coordinator creates ranking task with shifts ← NEW
6. solution-analyst claims ranking task → reads shifts from description → runs ranking → [RANKING-COMPLETE] ✓
7. Coordinator writes final section → present_results → terminate_team ✓

**Output:** A VERIFICATION.md trace showing the message flow is complete and consistent. No actual compound needed — trace the protocol.

---

## Open Questions

1. **Does lsd-engineer need the TaskCreate tool in its frontmatter?**
   - If orchestrator creates all iteration tasks (Option A): NO. lsd-engineer only needs TaskList (claim) and TaskUpdate (mark done). Its current tool list (Read, Write, Bash, Glob, Grep) is sufficient.
   - Recommendation: Keep lsd-engineer without TaskCreate. The spawn prompt must be updated to remove "Create next iteration task" language.

2. **Should ranking happen at every iteration or only when solution_count <= 10?**
   - Current case.md spawn prompt: "When solution_count <= 10, claim ranking task"
   - current solution-analyst: "Monitor TaskList for ranking tasks"
   - The orchestrator currently says "only when solution count <= 10 or as needed"
   - For Phase 45: Keep this as-is (rank only at convergence). Ranking at every iteration is unnecessarily expensive and not required by any success criterion.

3. **Who creates the ranking task — orchestrator or lsd-engineer?**
   - Answer (per Gap 2 resolution): Orchestrator creates it in monitor_progress.
   - This is consistent with orchestrator-driven task management pattern.

4. **How does lsd-engineer know what HMBC correlations to add for iteration N+1?**
   - Confirmed: lsd-engineer's workflow says "Read previous iteration's LSD file" → its constraint inventory contains the HMBC batches already used → it selects from remaining HMBC peaks that haven't been added yet.
   - The HMBC peaks list comes from nmr-chemist's [SETUP-COMPLETE] message (picked HMBC peaks count). These are available to lsd-engineer because the coordinator writes them to CASE-PROGRESS.md.
   - No gap here — lsd-engineer can extract remaining HMBC correlations from CASE-PROGRESS.md ## Setup section.

5. **Does the orchestrator have a way to read the shift list from the [SETUP-COMPLETE] message?**
   - YES — the orchestrator IS the sole writer of CASE-PROGRESS.md. It received [SETUP-COMPLETE] and wrote the NMR-Chemist section. The shift data is in memory from that message processing step.
   - Pattern: At [SETUP-COMPLETE] receipt, orchestrator stores the shift list as a named variable in its working context. Uses it when creating ranking task.
   - This requires a note in monitor_progress: "When writing Setup from [SETUP-COMPLETE], extract and retain shift_list for later use in ranking task creation."

---

## State of the Art

| Old Approach (v3.0) | v4.0 Approach | Impact |
|---------------------|---------------|--------|
| Single Task() spawns agent | TeamCreate + 4 Task() calls | Real-time peer review, constraint validation |
| Agent writes CASE-PROGRESS.md directly | Coordinator-only writes (9 triggers) | No corruption risk |
| No constraint tracking | JSON inventory in LSD file header | Prevents constraint loss across iterations |
| Agent creates all iterations itself | Orchestrator creates iteration tasks | Coordinator controls workflow pacing |
| No pre-run validation | Devils-advocate approval gate | Catches structural issues before solver |
| Agent re-spawn for advisory | SendMessage to running team | Team retains context, no restart overhead |

---

## Sources

### Primary (HIGH confidence)

All findings are directly from reading shipped files:

- `~/.claude/commands/lucy-ng/case.md` (976 lines, post-Phase 44) — spawn_case_team, write_progress, monitor_progress steps; spawn prompts for all 4 agents; stopping conditions; present_results
- `~/.claude/agents/lucy-lsd-engineer.md` (394 lines, post-Phase 43) — workflow steps 1-14; constraint inventory; no TaskCreate present
- `~/.claude/agents/lucy-nmr-chemist.md` (260 lines, post-Phase 44) — [SETUP-COMPLETE] template; workflow steps
- `~/.claude/agents/lucy-solution-analyst.md` (228 lines, post-Phase 44) — workflow step 2 ("Read shifts from task/messages"); [RANKING-COMPLETE] template
- `~/.claude/agents/lucy-devils-advocate.md` (337 lines, post-Phase 43) — validation workflow; [VALIDATION-PASSED/BLOCKED] templates
- `.planning/phases/43-constraint-inventory-system/43-VERIFICATION.md` — 6/6 pass; confirms inventory in lsd-engineer, validation in devils-advocate
- `.planning/phases/44-case-progress-format/44-VERIFICATION.md` — 5/5 pass; confirms coordinator-only writes, all agent message templates
- `.planning/ROADMAP.md` Phase 45 section — 6 success criteria, requirements TEAM-10/11/12

### Secondary (MEDIUM confidence)

- `.planning/research/ARCHITECTURE.md` Section 6 "Team Lifecycle and Coordination Flow" — coordination flow reference; some details superseded by Phases 41-44 decisions
- `.planning/research/SUMMARY-v4.0.md` Phase 5 research flags — "Likely needs iterative tuning — coordination efficiency unknown until tested with real compounds"

---

## Metadata

**Confidence breakdown:**
- Gap identification: HIGH — directly verified by reading shipped files; gaps confirmed absent in code
- Gap resolutions: HIGH — all resolutions follow existing patterns; no new mechanisms needed
- Standard stack: HIGH — no new tools needed; all mechanisms already in case.md allowed-tools
- Pitfalls: HIGH — all pitfalls derived from actual agent/orchestrator code inspection
- SC6 time measurement: MEDIUM — v3.0 baseline unavailable; surrogate (iteration count) recommended

**Research date:** 2026-02-17
**Valid until:** Phase 46 (diagnostic integration may change coordinator's message handling)

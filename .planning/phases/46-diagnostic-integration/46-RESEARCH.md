# Phase 46: Diagnostic Integration - Research

**Researched:** 2026-02-17
**Domain:** Diagnostic specialist integration with multi-agent team context — what already exists vs what needs changing
**Confidence:** HIGH

---

## Summary

Phase 46 asks: "Does the diagnostic specialist need changes to work correctly with the v4.0 team architecture?" The answer is: **almost nothing needs to change.** The diagnostic specialist was already integrated into case.md in Phase 41, already receives CASE-PROGRESS.md and the latest LSD file, and the constraint inventory (Phase 43) is embedded inside the LSD file header — so the specialist gets it automatically when reading the LSD file.

The four Phase 46 success criteria are already satisfied or trivially met by the current implementation. SC1 (specialist remains orchestrator-spawned, not a team member) is already true — `delegate_specialist` uses `Task()` without `team_name`. SC2 (specialist receives team context including CASE-PROGRESS.md and constraint inventory) is already true — CASE-PROGRESS.md is passed explicitly, and the constraint inventory lives inside the LSD file header (the specialist reads both). SC3 (diagnostic report delivered to coordinator via orchestrator advisory) is already true — `extract_diagnostic_findings` reads DIAGNOSTIC-REPORT.md and generates a specialist-informed advisory delivered via `deliver_advisory`. SC4 (delegation trigger unchanged) is already true — counter == 2 threshold remains.

**The only real question for planning is:** should the `delegate_specialist` instructions be updated to explicitly mention the constraint inventory block in the LSD file, so the diagnostic specialist knows to parse it? The current instructions say "Read: compound_path/analysis/CASE-PROGRESS.md and compound_path/latest_lsd_file" — the constraint inventory is in the LSD file but the specialist is not explicitly told to parse the `; === CONSTRAINT INVENTORY v1 ===` block.

**Primary recommendation:** Phase 46 is a thin verification-and-minor-update phase. One plan: verify all four success criteria against the current case.md and lucy-diagnostic.md; update the `delegate_specialist` instructions to explicitly reference the constraint inventory block; update lucy-diagnostic.md to know about the inventory format. Commit. No architecture changes.

---

## Standard Stack

### Core — Already Existing Files

| File | Current State | Phase 46 Role |
|------|--------------|---------------|
| `~/.claude/commands/lucy-ng/case.md` | Has `delegate_specialist`, `extract_diagnostic_findings`, `deliver_advisory` steps | Minor update to specialist instructions only |
| `~/.claude/agents/lucy-diagnostic.md` | 1146 lines — deep LSD diagnostic knowledge, systematic procedures, report template | May need minor update to parse constraint inventory block from LSD header |
| `.planning/phases/46-diagnostic-integration/` | Empty (this phase creates the plan) | Phase 46 output directory |

### Supporting — Constraint Inventory Format (Phase 43 Output)

The constraint inventory is written as a JSON comment block at the TOP of every LSD file, delimited by:

```
; === CONSTRAINT INVENTORY v1 ===
; {"version": 1, "mult_count": 13, "hsqc_count": 9, "hmbc_batches": [...], ...}
; === END CONSTRAINT INVENTORY ===
```

This is part of the LSD file the diagnostic specialist already reads. The specialist can extract it with:

```bash
sed -n '/=== CONSTRAINT INVENTORY/,/=== END CONSTRAINT INVENTORY/p' compound.lsd
```

No new file format. No new data source. The inventory is already in the artifact the specialist reads.

---

## Architecture Patterns

### What Already Exists (Phase 41 Implementation)

The `delegate_specialist` step in case.md (lines 931-972) already:

1. Spawns `Task(agent_type="lucy-diagnostic", model="opus")` WITHOUT `team_name` — specialist is independent from team
2. Passes compound_path, CASE-PROGRESS.md path, latest LSD file path, and failure_type
3. After Task completes, calls `extract_diagnostic_findings` which reads DIAGNOSTIC-REPORT.md and generates specialist-informed advisory
4. Advisory delivered via `deliver_advisory` step using SendMessage to lsd-engineer

**This is the correct architecture.** Nothing in Phase 41-45 broke it or changed the contract.

### What the Specialist Currently Receives

Current `delegate_specialist` instructions pass:
```
Read:
- <compound_path>/analysis/CASE-PROGRESS.md (iteration history)
- <compound_path>/<latest_lsd_file> (latest LSD file)

Failure type: <failure_type>
```

**Team context already included:**
- CASE-PROGRESS.md: Contains full iteration history — all per-agent sections (NMR-Chemist setup, LSD-Engineer iteration details, Devils-Advocate validations, Coordinator coordination notes). The v4.0 multi-agent format is MORE informative than the v3.0 single-agent narrative. The specialist benefits from the richer structure.
- Latest LSD file: Contains the constraint inventory JSON block (Phase 43). The specialist reads this file already, and can extract the inventory.

**What is NOT explicitly passed:**
- The constraint inventory is NOT called out separately in the instructions. The specialist may not know to look for the `; === CONSTRAINT INVENTORY v1 ===` block.
- The CASE-PROGRESS.md path format changed from v3.0 (`compound_path/CASE-PROGRESS.md`) to v4.0 (`compound_path/analysis/CASE-PROGRESS.md`). The current instructions already say `compound_path/analysis/CASE-PROGRESS.md` — correct.

### The Gap: Specialist Not Told About Inventory Block

The diagnostic specialist's current instructions do not mention the constraint inventory. The specialist workflow (Steps 1-5 in lucy-diagnostic.md) says "Read the latest LSD file" and then analyzes MULT, HSQC, HMBC commands. It does not mention extracting the `; === CONSTRAINT INVENTORY v1 ===` block.

**Impact:** The specialist can still read all the raw commands (MULT, HSQC, HMBC, DEFF NOT, SYME) from the LSD file body. The inventory is a convenience summary, not the only source of truth. So the gap is LOW severity — the diagnostic checks still work without the inventory.

**Fix:** Two-line update to `delegate_specialist` instructions and one paragraph in lucy-diagnostic.md Step 1 (Gather Context) to mention the constraint inventory block.

### Advisory Delivery Pattern

The v3.0 pattern was: run diagnostic specialist → read report → re-spawn CASE agent with advisory.

The v4.0 pattern is: run diagnostic specialist → read report → SendMessage advisory to lsd-engineer (running team). This was implemented in Phase 41. The `deliver_advisory` step uses:

```
SendMessage(type="message", recipient="lsd-engineer", content="[SUPERVISOR ADVISORY] ...")
SendMessage(type="message", recipient="devils-advocate", content="[SUPERVISOR] ...")
```

The advisory path is: specialist produces DIAGNOSTIC-REPORT.md → orchestrator reads it → orchestrator sends advisory to RUNNING team via SendMessage. This is correct for v4.0.

### Objectivity Rationale (Why Specialist Stays Outside Team)

The specialist is spawned as `Task()` WITHOUT `team_name` for a documented reason: objectivity. If the specialist were a team member, it would have been exposed to all team messages and could have developed the same blind spots as the lsd-engineer. By operating independently, it brings fresh analysis with no prior context except the artifacts.

This pattern is already correct. Phase 46 must NOT change this — SC1 explicitly requires it.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Constraint inventory parsing in specialist | Custom parser logic in delegate_specialist | Tell specialist to read LSD header block | Specialist already reads the LSD file; just add instructions to parse the known delimiter |
| Separate context file for specialist | Create a "specialist-context.md" summary | Pass existing artifacts (CASE-PROGRESS.md + LSD file) | Both files already contain all required context; extra file adds complexity |
| New specialist message channel | Add specialist as team member for messaging | Orchestrator reads DIAGNOSTIC-REPORT.md and delivers advisory | Maintains objectivity; avoids team coordination overhead for a one-shot analysis task |

---

## Common Pitfalls

### Pitfall 1: Over-Engineering Phase 46

**What goes wrong:** Planner sees "team context" in the requirements and adds complex context-packaging logic — extracting constraint inventory into a separate file, summarizing CASE-PROGRESS.md, creating a structured specialist briefing document.

**Why it happens:** The phrase "receives team context" sounds like new infrastructure is needed.

**How to avoid:** Read what already exists. The specialist already receives the two key artifacts. "Team context" means CASE-PROGRESS.md (which the orchestrator writes, capturing all team contributions) and the constraint inventory (which is in the LSD file header). No new infrastructure needed.

**Warning signs:** Plan adds more than 2 files or more than 30 lines of new content.

**Confidence:** HIGH

---

### Pitfall 2: Changing the Delegation Trigger

**What goes wrong:** Planner interprets "delegation trigger unchanged" as needing a verification comment, but accidentally modifies the counter logic while commenting.

**Why it happens:** SC4 says "delegation trigger unchanged from v3.0 (2 failed basic interventions with same pattern)." The wording "from v3.0" might cause the planner to search for v3.0 code to compare against. The v4.0 code already has the correct trigger (counter == 2 threshold in `track_and_decide`).

**How to avoid:** Read track_and_decide in case.md, confirm counter == 2 trigger exists, do NOT touch it.

**Warning signs:** Plan includes "update counter logic" or "verify delegation threshold."

**Confidence:** HIGH

---

### Pitfall 3: Missing the Path Change (CASE-PROGRESS.md Location)

**What goes wrong:** A review task verifies that CASE-PROGRESS.md is passed to the specialist, but doesn't check the PATH is correct. v3.0 had `compound_path/CASE-PROGRESS.md`; v4.0 has `compound_path/analysis/CASE-PROGRESS.md`.

**Why it happens:** The path change happened in Phase 44 when the multi-agent format was defined.

**How to avoid:** The current `delegate_specialist` instructions already say `<compound_path>/analysis/CASE-PROGRESS.md` — this is correct. Just verify it hasn't regressed.

**Warning signs:** Specialist instructions reference `CASE-PROGRESS.md` without the `analysis/` subdirectory.

**Confidence:** HIGH

---

### Pitfall 4: Forgetting to Update lucy-diagnostic.md

**What goes wrong:** Planner updates `delegate_specialist` instructions to mention the constraint inventory, but doesn't update lucy-diagnostic.md Step 1 (Gather Context). The specialist sees the instruction to read the inventory block but has no knowledge of what the block format looks like or what fields to extract.

**Why it happens:** Two files need coordinated updates — case.md (instructions) and lucy-diagnostic.md (knowledge).

**How to avoid:** Update both files together. In lucy-diagnostic.md Step 1 (Gather Context), add a subsection: "Constraint inventory (from LSD header): extract JSON between `; === CONSTRAINT INVENTORY v1 ===` delimiters; check hmbc_batches, deff_not_patterns, syme_pairs, elim_value for diagnostic evidence."

**Warning signs:** Plan has only one file to modify.

**Confidence:** HIGH

---

## Code Examples

### Current delegate_specialist Instructions (case.md lines 947-968)

```
Task(
  agent_type="lucy-diagnostic",
  model="opus",
  instructions="Analyze LSD failure for compound at <compound_path>.

  Read:
  - <compound_path>/analysis/CASE-PROGRESS.md (iteration history)
  - <compound_path>/<latest_lsd_file> (latest LSD file)

  Failure type: <failure_type>

  Run systematic diagnostic checks per skill/diagnostic/SKILL.md.
  Document ALL checks (PASS and FAIL).
  Identify root cause with evidence.

  Write structured report to <compound_path>/DIAGNOSTIC-REPORT.md.
  Include: findings, root cause, recommended fixes with LSD command examples.
  Rate all findings and recommendations as HIGH/MEDIUM/LOW confidence.
  "
)
```

### Proposed Minimal Update to delegate_specialist

Add one paragraph after "Read:" block:

```
  Read:
  - <compound_path>/analysis/CASE-PROGRESS.md (iteration history with per-agent sections)
  - <compound_path>/analysis/<latest_iteration>/compound.lsd (latest LSD file)
    Note: The LSD file header contains a JSON constraint inventory block between
    ; === CONSTRAINT INVENTORY v1 === and ; === END CONSTRAINT INVENTORY ===
    Extract and include this inventory in your context gathering (Step 1).
    The inventory tracks: hmbc_batches, deff_not_patterns, syme_pairs, bond_constraints,
    list_prop_constraints, elim_value, applied/pending detection results.
```

### Proposed Addition to lucy-diagnostic.md Step 1

After "3. Spectral quality notes", add:

```markdown
4. **Constraint inventory (from LSD header):**
   ```bash
   sed -n '/CONSTRAINT INVENTORY v1/,/END CONSTRAINT INVENTORY/p' <lsd_file>
   ```
   Extract JSON. Key fields for diagnosis:
   - `hmbc_batches`: Which HMBC correlations were added in each iteration
   - `deff_not_patterns`: Strained-ring exclusion patterns — should INCREASE not decrease across iterations
   - `syme_pairs`: Symmetry constraints — check if signal grouping was detected but syme_pairs is empty
   - `elim_value`: If not null, ELIM is present (check per Section 2.2 Check 1)
   - `pending_from_detection`: Detection results not yet translated to constraints (potential fix opportunity)

   The inventory supplements the raw LSD commands — it provides the HISTORY (what changed when)
   that the raw commands don't show.
```

---

## Current State Summary (What Phase 46 Finds Already Done)

| Success Criterion | Current Status | Evidence |
|------------------|----------------|----------|
| SC1: Specialist spawned outside team (objectivity) | DONE | case.md `delegate_specialist`: `Task(agent_type="lucy-diagnostic")` without `team_name` (line 950) |
| SC2: Specialist receives CASE-PROGRESS.md | DONE | Explicit in current instructions: `<compound_path>/analysis/CASE-PROGRESS.md` |
| SC2: Specialist receives constraint inventory | PARTIAL | LSD file is passed and inventory is IN the LSD file, but specialist not explicitly told to parse it |
| SC3: Diagnostic report delivered via orchestrator advisory | DONE | `extract_diagnostic_findings` reads DIAGNOSTIC-REPORT.md → `deliver_advisory` uses SendMessage |
| SC4: Delegation trigger unchanged (counter == 2) | DONE | `track_and_decide` step: "If counter for this pattern == 2: Delegate to diagnostic specialist" |

---

## Phase Scope: What Phase 46 Actually Plans

Given the above analysis, Phase 46 is a **single-plan phase** with one modest task:

**Plan 46-01: Update specialist instructions and knowledge for constraint inventory awareness**

1. Verify case.md `delegate_specialist` step passes the correct artifact paths (SC1, SC3, SC4)
2. Update `delegate_specialist` instructions to explicitly mention the constraint inventory block in the LSD file header (SC2 gap)
3. Update `lucy-diagnostic.md` Step 1 (Gather Context) to know the inventory format and how to extract/use it (SC2 gap)
4. Verify `track_and_decide` counter == 2 trigger is unchanged (SC4)
5. Commit both files

No orchestrator architecture changes. No new steps. No new tools. No new agent definitions.

**Estimated changes:**
- case.md: ~6 lines added to `delegate_specialist` instructions (constraint inventory mention + path clarification)
- lucy-diagnostic.md: ~15 lines added to Step 1 (Gather Context section) for inventory extraction and field reference

---

## Open Questions

1. **Should the diagnostic report be written to `compound_path/DIAGNOSTIC-REPORT.md` or `compound_path/analysis/DIAGNOSTIC-REPORT.md`?**
   - Current instructions: `compound_path/DIAGNOSTIC-REPORT.md` (compound root)
   - All other CASE artifacts: `compound_path/analysis/` (analysis subfolder)
   - Recommendation: Update to `compound_path/analysis/DIAGNOSTIC-REPORT.md` for consistency
   - This would require updating both case.md `extract_diagnostic_findings` (reads the report) and lucy-diagnostic.md (writes the report)
   - Confidence: MEDIUM — the current location works but breaks the "all outputs in analysis/" convention

2. **Should the specialist receive the full CASE-PROGRESS.md or a structured summary?**
   - Current: Full file passed
   - The v4.0 CASE-PROGRESS.md can be long (per-agent sections for each iteration). For a 10-iteration run with 5 agents, this is substantial.
   - Recommendation: Full file is fine — the specialist reads it for root cause context (which iteration started failing, what changed). No summary needed.
   - Confidence: HIGH — specialist needs the history, not just current state

---

## Sources

### Primary (HIGH confidence)

- `~/.claude/commands/lucy-ng/case.md` — Phase 41 implementation: `delegate_specialist` step (lines 931-972), `extract_diagnostic_findings` step (lines 974-1011), `deliver_advisory` step (lines 685-723), `track_and_decide` step (lines 604-630)
- `~/.claude/agents/lucy-diagnostic.md` — 1146 lines, Step 1 Gather Context workflow (lines 865-888)
- Phase 41 VERIFICATION.md — confirms delegate_specialist preserved with "independent from team" note (SC5 checked)
- Phase 43 VERIFICATION.md — confirms constraint inventory JSON block in LSD file header, delimiters: `; === CONSTRAINT INVENTORY v1 ===`
- Phase 44 VERIFICATION.md — confirms CASE-PROGRESS.md path is `compound_path/analysis/CASE-PROGRESS.md`
- Phase 45 VERIFICATION.md — confirms overall team coordination is working; no changes to diagnostic integration

### Secondary (MEDIUM confidence)

- `.planning/research/SUMMARY-v4.0.md` Phase 6 note: "Research flags: None — pattern is unchanged from v3.0, just TeamMessage instead of Task re-spawn"
- Phase 41 RESEARCH.md Scope Summary: "delegate_specialist step — preserved (with note about independent-from-team spawning)"

---

## Metadata

**Confidence breakdown:**
- What already exists: HIGH — verified against actual case.md and lucy-diagnostic.md file content
- What needs changing (constraint inventory gap): HIGH — clear gap between "specialist reads LSD file" and "specialist knows to parse inventory block"
- DIAGNOSTIC-REPORT.md path question: MEDIUM — convention argument, not a functional requirement
- Phase scope (single plan): HIGH — all four success criteria map to one coordinated change

**Research date:** 2026-02-17
**Valid until:** 2026-03-17 (stable architecture, no planned changes to case.md or lucy-diagnostic.md except this phase)

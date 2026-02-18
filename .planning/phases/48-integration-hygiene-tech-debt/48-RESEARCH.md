# Phase 48: Integration Hygiene & Tech Debt (GAP CLOSURE) — Research

**Researched:** 2026-02-18
**Domain:** Agent instruction files (markdown), orchestrator skill (markdown), planning VERIFICATION.md format
**Confidence:** HIGH

---

## Summary

Phase 48 is a pure documentation and instruction-file hygiene phase. There is no Python code to change, no CLI to update, no tests to add. Every deliverable is either a markdown edit to an existing file or a new markdown document. All five gaps to close were precisely catalogued in `v4.0-MILESTONE-AUDIT.md` and cross-referenced against the source files during this research pass.

The phase has two categories of work:

**Category A — Live file edits (3 files):** Two files need specific text changes to close integration gaps: `case.md` needs a SendMessage call in `monitor_progress` (MISSING-01) and spawn prompt consistency fixes; `lucy-diagnostic.md` needs the stale "What You Receive" example block updated to reflect `analysis/` paths; `lucy-devils-advocate.md` needs a documentation note clarifying how it reads CASE-PROGRESS.md for aromatic data.

**Category B — Missing VERIFICATION.md files (2 new files):** Phases 46.1 and 47 were verified through UAT artifacts but never received formal VERIFICATION.md files. The milestone audit passed them "via UAT evaluation" — Phase 48 closes this by writing the formal verification documents that retrospectively record the actual verification evidence.

All changes are low-risk: the integration gap (MISSING-01) is medium severity and already works in practice via Team messaging runtime; the stale paths in `lucy-diagnostic.md` are illustrative text in an example block that is always overridden by the actual Task() instructions at runtime; and the VERIFICATION.md files are new documents with no runtime impact.

**Primary recommendation:** Execute all changes in a single plan. The work is cohesive, small, and entirely within agent/orchestrator markdown files. No parallelism is needed — sequential edit-and-document passes are safe and sufficient.

---

## Standard Stack

This phase has no software stack. All work is markdown editing of:

| File | Location | Current state | Change needed |
|------|----------|---------------|---------------|
| `case.md` | `~/.claude/commands/lucy-ng/case.md` | 1060 lines | Add SendMessage to lsd-engineer in monitor_progress; fix 2 spawn prompt anti-patterns |
| `lucy-diagnostic.md` | `~/.claude/agents/lucy-diagnostic.md` | 1165 lines | Update "What You Receive" example block (lines 1092-1094) |
| `lucy-devils-advocate.md` | `~/.claude/agents/lucy-devils-advocate.md` | 346 lines (post-46.1) | Add documentation note on CASE-PROGRESS.md read path for aromatic data |
| `46.1-VERIFICATION.md` | `.planning/phases/46.1-agent-aromatic-ring-awareness/` | does not exist | Create (new file) |
| `47-VERIFICATION.md` | `.planning/phases/47-uat-live-compounds/` | does not exist | Create (new file) |

---

## Architecture Patterns

### VERIFICATION.md Format (from Phase 20 and 21 through 46 examples)

All VERIFICATION.md files follow this structure (confirmed by reading six examples):

```markdown
---
phase: {slug}
verified: {ISO timestamp}
status: passed | partial | failed
score: N/N must-haves verified
---

# Phase N: {Name} Verification Report

**Phase Goal:** {one line from ROADMAP.md}
**Verified:** {date}
**Status:** passed
**Re-verification:** No -- initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | {truth} | VERIFIED | {evidence with file references} |

**Score:** N/N truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|

### Success Criteria Coverage (from ROADMAP.md)

| Success Criterion | Status | Evidence |
|-------------------|--------|----------|

### Anti-Patterns Found

{None / list with file + line + pattern + severity + impact}

### Human Verification Required (if any)

### Gaps Summary

---

_Verified: {date}_
_Verifier: Claude (gsd-verifier)_
```

**Key pattern:** The Observable Truths table drives the score. Each truth maps to a success criterion. Evidence is specific: file path, line number, exact text found.

**Key pattern for retrospective verification (Phases 46.1 and 47):** Because verification happened through UAT execution rather than static analysis, evidence comes from SUMMARY.md files, v4.0-UAT-report.md, and CASE-PROGRESS.md artifacts rather than from reading agent instruction files. State this explicitly in the Evidence column.

### MISSING-01: DA Approval Relay Pattern

**The gap:** DA sends `[VALIDATION-PASSED]` to coordinator. Coordinator writes the DA section to CASE-PROGRESS.md (via `write_progress` trigger 5). But the coordinator does NOT then explicitly SendMessage the approval decision to lsd-engineer. The `lsd-engineer` workflow step 8 says "WAIT for approval before running solver" — so in practice, the lsd-engineer watches for messages, and the Team messaging runtime apparently delivers the information. But case.md has no explicit `SendMessage(recipient="lsd-engineer", ...)` call after receiving `[VALIDATION-PASSED]`.

**What the fix looks like:** In the `monitor_progress` step, after the paragraph "After receiving [ITERATION-COMPLETE] from lsd-engineer AND [VALIDATION-PASSED] from devils-advocate, AND after writing both sections to CASE-PROGRESS.md:", add a step:

```
After writing the Devils-Advocate section to CASE-PROGRESS.md, relay the approval decision to lsd-engineer:

SendMessage(
  type="message",
  recipient="lsd-engineer",
  content="[DA-APPROVED] Iteration N — Validation passed. Proceed with solver run.
           DA findings: <brief summary from [VALIDATION-PASSED] message>",
  summary="DA approved iteration N — proceed with solver"
)

If [VALIDATION-BLOCKED] was received instead, relay the block:

SendMessage(
  type="message",
  recipient="lsd-engineer",
  content="[DA-BLOCKED] Iteration N — Validation blocked. Critical issues:
           <issues from [VALIDATION-BLOCKED] message>
           Fix these before running solver.",
  summary="DA blocked iteration N — fix required"
)
```

This closes MISSING-01 by making the relay explicit rather than relying on Team runtime behavior.

### Stale Paths in lucy-diagnostic.md

**The gap (confirmed by reading lines 1086-1106):** The "What You Receive from Orchestrator" section shows an example instruction block:

```
Read:
- <path>/CASE-PROGRESS.md (iteration history)
- <path>/<filename>.lsd (latest LSD file)
```

These paths use the OLD pre-Phase-46 convention where CASE-PROGRESS.md was at the compound root and LSD files were named per-compound. Post-Phase-46, the correct paths are:
- `<compound_path>/analysis/CASE-PROGRESS.md`
- `<compound_path>/analysis/<latest_iteration>/compound.lsd`

The actual Task() call in case.md `delegate_specialist` step (lines 952-972) already uses the correct paths. This example block is illustrative only — it shows the diagnostic specialist what kind of instructions to expect — but the stale paths could mislead a diagnostic specialist agent into looking in the wrong place if it reads this example literally.

**The fix:** Update lines 1092-1094 of `lucy-diagnostic.md` to match the actual paths used in the case.md Task() call. Specifically, the example block should show:

```
Read:
- <compound_path>/analysis/CASE-PROGRESS.md (iteration history with per-agent sections)
- <compound_path>/analysis/<latest_iteration>/compound.lsd (latest LSD file)
  Note: The LSD file header contains a JSON constraint inventory block ...
```

Note: The diagnostic specialist Step 1 body (lines 866-906) already correctly says "CASE-PROGRESS.md path (iteration history)" and references analysis/ in step 5. Only the illustrative example block at lines 1092-1094 is stale.

### Spawn Prompt Wording Inconsistencies

**Confirmed anti-patterns from Phase 45-VERIFICATION.md and the audit:**

1. **lsd-engineer spawn prompt (case.md line 160):** "Stop when solution_count <= 10 or ~10 iterations reached." This is inconsistent with the lsd-engineer agent definition, which correctly says "Claim tasks from TaskList as they become available." The spawn prompt's stop condition could be interpreted by the agent as "terminate when solution count drops to <=10" rather than "stop creating new LSD iteration tasks." Correct wording: remove the stop condition from the spawn prompt (the orchestrator manages stopping via TaskCreate absence) or rephrase to "Continue claiming tasks from TaskList. Stop when no more tasks are available."

2. **solution-analyst spawn prompt (case.md line 170):** Uses `--shifts '...'` (literal ellipsis) instead of indicating that shifts come from the task description. The solution-analyst agent definition correctly says shifts come from task description (line 217 of lucy-solution-analyst.md). Correct wording: "Read experimental 13C shifts from the task description (coordinator embeds the full shift list when creating the ranking task)."

### DA Aromatic Data Relay Path (CASE-PROGRESS.md Read)

**The gap (from audit MISSING-02 follow-on):** The DA's aromatic ring check (added in Phase 46.1, Section 3 of lucy-devils-advocate.md) reads: "If nmr-chemist's [SETUP-COMPLETE] message reports 'aromatic ring expected'..." — but the DA does NOT receive [SETUP-COMPLETE] directly. The DA receives validation requests from lsd-engineer. So how does DA know what nmr-chemist reported?

**The actual path:** The DA reads CASE-PROGRESS.md (the coordinator writes the NMR-Chemist section from [SETUP-COMPLETE] per write_progress trigger 2). The DA workflow says "Read current LSD file at the specified path" but does not explicitly say "Read CASE-PROGRESS.md to get the NMR-Chemist's aromatic expectation." This relay path works in practice (UAT showed DA correctly applied the check) but is undocumented.

**The fix:** In `lucy-devils-advocate.md`, the Aromatic Ring Expectation check (Section 3, added in Phase 46.1) should include a note: "To determine whether nmr-chemist flagged aromatic expectation, read `<compound_path>/analysis/CASE-PROGRESS.md` and look for the `Aromatic expectation:` field in the `### NMR-Chemist` subsection of `## Setup`."

---

## Evidence Matrix for VERIFICATION.md Files

### Phase 46.1 Success Criteria Evidence

From reading `46.1-01-SUMMARY.md`, `46.1-02-SUMMARY.md`, `v4.0-MILESTONE-AUDIT.md`, and `47-01-SUMMARY.md`:

| Success Criterion | Evidence Source | Result |
|-------------------|-----------------|--------|
| SC1: solution-analyst checks `warnings` field; reports aromatic warning as critical finding | 46.1-01-SUMMARY.md: "Check 6 added... parse warnings from JSON" | PASS |
| SC2: nmr-chemist flags aromatic ring expected in [SETUP-COMPLETE] when >= 4 sp2 carbons in 110-160 ppm | 46.1-02-SUMMARY.md: "Aromatic expectation field added to [SETUP-COMPLETE] template" | PASS |
| SC3: solution-analyst checks `has_aromatic_ring` on top-ranked solutions when NMR-chemist flagged aromaticity | 46.1-01-SUMMARY.md: "--format json workflow added, has_aromatic_ring check included" | PASS |
| SC4: aromatic mismatch triggers specific remediation recommendation | 46.1-01-SUMMARY.md: "QUESTIONABLE severity... remediation targets benzylic/alpha HMBC correlations" | PASS |

Phase 46.1 exercised in live ibuprofen UAT (Phase 47): 47-01-SUMMARY.md confirms "Phase 46.1 aromatic awareness correctly compensates via analyst override" and v4.0-MILESTONE-AUDIT.md confirms "Phase 46.1: Solution-analyst Check 6, nmr-chemist Aromatic expectation, and DA aromatic check all exercised successfully in the live UAT run."

### Phase 47 Success Criteria Evidence

From reading `47-01-SUMMARY.md`, `47-02-SUMMARY.md`, and `v4.0-MILESTONE-AUDIT.md`:

| Success Criterion | Evidence Source | Result |
|-------------------|-----------------|--------|
| SC1: Ibuprofen correct structure in top 3 | 47-01-SUMMARY.md: "rank #4 by algorithm, #1 by analyst override" | PARTIAL |
| SC2: All v3.0 bugs fixed | 47-01-SUMMARY.md: "5/5 PASS" with bug-by-bug evidence | PASS |
| SC3: Time < 2x v3.0 baseline | 47-01-SUMMARY.md: "4 iterations, same as v3.0" | PASS |
| SC4: Additional test compounds (Pulegone, Virgiline) | 47-01-SUMMARY.md: not executed (post-hoc evaluation) | SKIPPED |
| SC5: Performance comparison report | 47-02-SUMMARY.md: "v4.0-UAT-report.md written" with 6 metrics | PASS |

SC-1 is partial because ibuprofen ranks #4 by algorithm (match-count ranking disadvantages aromatic structures at 3 ppm tolerance). The analyst override correctly identifies it as #1. This limitation is documented in the audit as deferred to a future milestone.

---

## Common Pitfalls

### Pitfall 1: Over-engineering the MISSING-01 fix

**What goes wrong:** Adding both a `[DA-APPROVED]` and `[DA-BLOCKED]` relay, then trying to refactor the whole `monitor_progress` step structure.

**Why it happens:** The gap sounds like an architectural problem, but it is actually a single missing SendMessage call. The existing `monitor_progress` already describes the sequence correctly; the only missing piece is the explicit relay after writing the DA section.

**How to avoid:** Insert the relay SendMessage as a single block within the existing "Iteration management" section of `monitor_progress`, immediately after writing the DA section to CASE-PROGRESS.md. Do NOT restructure the step.

### Pitfall 2: Changing the wrong lines in lucy-diagnostic.md

**What goes wrong:** Editing the Step 1 body text (which already uses correct paths) rather than the "What You Receive" example block (lines 1085-1106).

**Why it happens:** The Step 1 content and the "What You Receive" example block both discuss file paths. The Step 1 body is already correct. Only the example block needs updating.

**How to avoid:** The exact location to fix is the code block within `## What You Receive from Orchestrator` section (approximately lines 1089-1106). Specifically the two lines showing `- <path>/CASE-PROGRESS.md` and `- <path>/<filename>.lsd`.

### Pitfall 3: Retroactive VERIFICATION.md misrepresenting partial SC-1

**What goes wrong:** Marking SC-1 of Phase 47 as "PASS" to make the verification look clean when the actual outcome was partial (rank #4 algorithm, #1 analyst).

**Why it happens:** The audit already shipped the milestone and the milestone audit says "PASSED via UAT." It is tempting to paper over the partial result.

**How to avoid:** Mark SC-1 as "PARTIAL" with honest evidence: "Ibuprofen at rank #4 by match-count algorithm, rank #1 by analyst override using aromatic ring awareness. Ranking algorithm limitation documented; deferred to future milestone." The VERIFICATION.md adds value precisely by recording this honestly — it is NOT a pass/fail gate (the milestone has already shipped), it is a historical record.

### Pitfall 4: Making the VERIFICATION.md files too thin

**What goes wrong:** Writing a VERIFICATION.md that just says "Phase verified by UAT" without the Observable Truths table, evidence column, or success criteria coverage table.

**Why it happens:** Since these are retroactive verifications and all evidence comes from SUMMARY.md and UAT artifacts rather than static file analysis, it is tempting to write a short narrative.

**How to avoid:** Follow the same format as other VERIFICATION.md files. The Observable Truths table, Required Artifacts table, and Success Criteria Coverage table are all mandatory. For retroactive verification, the Evidence column cites the SUMMARY.md, v4.0-UAT-report.md, and v4.0-MILESTONE-AUDIT.md rather than file line numbers in agent definitions.

### Pitfall 5: Breaking lsd-engineer behavior with spawn prompt fix

**What goes wrong:** The spawn prompt fix removes the stop condition entirely, and the lsd-engineer then continues to poll TaskList indefinitely even after CASE is complete and shutdown_request is sent.

**Why it happens:** The stop condition in the spawn prompt ("Stop when solution_count <= 10 or ~10 iterations reached") is wrong in phrasing but provides a behavioral anchor that prevents runaway polling.

**How to avoid:** Rephrase rather than delete. Correct wording: "Continue claiming tasks from TaskList. You will receive a shutdown_request when CASE is complete." This preserves termination behavior while removing the confusion with early stopping on solution_count.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| VERIFICATION.md format | Custom format | Existing VERIFICATION.md format (Phases 20-46) | Already validated by GSD workflow; planner expects this format |
| DA approval relay | New message protocol | Single SendMessage call in monitor_progress | The existing message infrastructure already supports this |
| Aromatic data relay documentation | New agent protocol | Prose note in existing Section 3 check | The DA already reads CASE-PROGRESS.md; just needs documentation |

---

## What the Planner Must NOT Do

- Do not change any Python code in `src/lucy_ng/`
- Do not change any tests
- Do not change `lucy-lsd-engineer.md`, `lucy-nmr-chemist.md`, or `lucy-solution-analyst.md` — those agents were correctly updated in Phase 46.1 and are complete
- Do not add a formal "Phase 46.1 requirement" to REQUIREMENTS.md — Phase 48 is gap closure, not a new requirement
- Do not touch the ROADMAP.md Phase 48 entry — that already exists with the correct success criteria

---

## File-Level Change Inventory

### `~/.claude/commands/lucy-ng/case.md`

**Change 1 — MISSING-01 fix (monitor_progress step):**
Location: After the paragraph starting "After receiving [ITERATION-COMPLETE] from lsd-engineer AND [VALIDATION-PASSED] from devils-advocate, AND after writing both sections to CASE-PROGRESS.md:" (currently around line 400).
Action: Insert a SendMessage block that relays `[DA-APPROVED]` to lsd-engineer, and a parallel block for `[DA-BLOCKED]` relay.

**Change 2 — lsd-engineer spawn prompt wording (spawn_case_team step):**
Location: lsd-engineer Task() prompt, around line 160, the sentence "Stop when solution_count <= 10 or ~10 iterations reached."
Action: Replace with "Continue claiming tasks from TaskList. You will receive a shutdown_request when CASE is complete."

**Change 3 — solution-analyst spawn prompt wording (spawn_case_team step):**
Location: solution-analyst Task() prompt, around line 170, the text `--shifts '...'`.
Action: Replace with "Read experimental 13C shifts from the task description (coordinator embeds the full shift list when creating the ranking task)."

### `~/.claude/agents/lucy-diagnostic.md`

**Change 4 — Stale example paths (What You Receive section):**
Location: Lines ~1092-1094, within the code block in `## What You Receive from Orchestrator`.
Action: Replace:
```
- <path>/CASE-PROGRESS.md (iteration history)
- <path>/<filename>.lsd (latest LSD file)
```
With:
```
- <compound_path>/analysis/CASE-PROGRESS.md (iteration history with per-agent sections)
- <compound_path>/analysis/<latest_iteration>/compound.lsd (latest LSD file)
```

### `~/.claude/agents/lucy-devils-advocate.md`

**Change 5 — Aromatic data relay path documentation:**
Location: Section 3, within the `### Aromatic Ring Expectation` check (added in Phase 46.1).
Action: Add a note explaining how DA accesses nmr-chemist's aromatic expectation data: "Read CASE-PROGRESS.md (`<compound_path>/analysis/CASE-PROGRESS.md`) and look for the `Aromatic expectation:` field in the `### NMR-Chemist` subsection of `## Setup`."

### `.planning/phases/46.1-agent-aromatic-ring-awareness/46.1-VERIFICATION.md` (NEW)

Content: Formal VERIFICATION.md using the standard format. Observable Truths based on the 4 Phase 46.1 success criteria, evidence from 46.1-01-SUMMARY.md, 46.1-02-SUMMARY.md, and 47-01-SUMMARY.md (UAT exercise). Status: passed (all 4 SCs verified). Notes the retroactive verification context.

### `.planning/phases/47-uat-live-compounds/47-VERIFICATION.md` (NEW)

Content: Formal VERIFICATION.md using the standard format. Observable Truths based on the 5 Phase 47 success criteria. SC-1 marked PARTIAL (rank #4 algorithm / #1 analyst). Evidence from 47-01-SUMMARY.md, 47-02-SUMMARY.md, and v4.0-MILESTONE-AUDIT.md. Notes the post-hoc evaluation context (pre-existing artifacts evaluated rather than live run observed).

---

## Open Questions

1. **Whether to create the analysis/ directory structure in CASE-PROGRESS.md read path** in the DA Aromatic check note — specifically, should the note say "read CASE-PROGRESS.md at `<compound_path>/analysis/CASE-PROGRESS.md`" or use a variable reference? Recommendation: Use the concrete path with `<compound_path>` placeholder — consistent with how other path references appear in the file.

2. **Whether the 47 VERIFICATION.md should have a human_verification_required section** given SC-4 (Pulegone/Virgiline) was explicitly skipped. Recommendation: Include a note stating "SC-4 (additional compounds) was explicitly descoped during execution — evaluated as post-hoc review of existing Ibuprofen artifacts. Pulegone and Virgiline testing deferred to future validation."

---

## Sources

### Primary (HIGH confidence)

- Direct reading of `~/.claude/commands/lucy-ng/case.md` (1060 lines, full content) — confirmed monitor_progress structure, spawn prompts, and delegate_specialist paths
- Direct reading of `~/.claude/agents/lucy-diagnostic.md` (1165 lines) — confirmed stale example block at lines 1085-1106; confirmed Step 1 is already correct
- Direct reading of `~/.claude/agents/lucy-devils-advocate.md` (346 lines post-46.1) — confirmed Aromatic Ring Expectation check exists, relay path is undocumented
- Direct reading of `.planning/v4.0-MILESTONE-AUDIT.md` — confirmed all 5 gap/tech-debt items that Phase 48 must close
- Direct reading of `.planning/phases/46.1-agent-aromatic-ring-awareness/46.1-01-SUMMARY.md` — confirmed what was implemented in Plan 01
- Direct reading of `.planning/phases/46.1-agent-aromatic-ring-awareness/46.1-02-SUMMARY.md` — confirmed what was implemented in Plan 02
- Direct reading of `.planning/phases/47-uat-live-compounds/47-01-SUMMARY.md` — confirmed UAT results and SC evaluations
- Direct reading of `.planning/phases/47-uat-live-compounds/47-02-SUMMARY.md` — confirmed performance report written
- Direct reading of `.planning/phases/46-diagnostic-integration/46-VERIFICATION.md` — confirmed stale path anti-patterns noted as Info-level at lines 1093-1094 and case.md line 317
- Direct reading of `.planning/phases/45-team-coordination-protocol/45-VERIFICATION.md` — confirmed spawn prompt anti-patterns documented at case.md lines 160 and 170
- Direct reading of `.planning/phases/21-skill-restructure/21-VERIFICATION.md` — confirmed VERIFICATION.md format pattern
- Direct reading of `.planning/ROADMAP.md` — confirmed Phase 48 success criteria and files to modify

---

## Metadata

**Confidence breakdown:**
- File locations and line numbers: HIGH — read directly from all source files
- Gap descriptions: HIGH — derived directly from v4.0-MILESTONE-AUDIT.md and cross-verified against source files
- Fix specifications: HIGH — prescribed changes are small, additive, and have no downstream side effects
- VERIFICATION.md format: HIGH — pattern confirmed from 6 existing examples
- Evidence for retroactive VERIFICATION.md files: HIGH — SUMMARY.md and UAT report artifacts are definitive records

**Research date:** 2026-02-18
**Valid until:** 2026-03-20 (all target files are stable; no active development on them)

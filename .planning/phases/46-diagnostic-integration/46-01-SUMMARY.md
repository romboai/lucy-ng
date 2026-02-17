---
phase: 46-diagnostic-integration
plan: 01
subsystem: agent-coordination
tags: [diagnostic-specialist, constraint-inventory, case-orchestrator, agent-definitions]

# Dependency graph
requires:
  - phase: 43-constraint-persistence
    provides: "Constraint inventory JSON block in LSD file headers"
  - phase: 25-agent-knowledge
    provides: "Inlined diagnostic knowledge in lucy-diagnostic.md"
provides:
  - "Diagnostic specialist awareness of constraint inventory block format and fields"
  - "Consistent analysis/ path for DIAGNOSTIC-REPORT.md across orchestrator and specialist"
  - "Field-by-field diagnostic guidance for inventory-based root cause analysis"
affects: [47-uat, case-orchestrator, diagnostic-specialist]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Constraint inventory as diagnostic data source (history not just current state)"
    - "analysis/ subdirectory convention for all CASE artifacts including diagnostic reports"

key-files:
  created: []
  modified:
    - "~/.claude/commands/lucy-ng/case.md"
    - "~/.claude/agents/lucy-diagnostic.md"

key-decisions:
  - "LSD file path in delegate_specialist follows analysis/<latest_iteration>/compound.lsd pattern"
  - "Changed skill reference from 'per skill/diagnostic/SKILL.md' to 'per your inlined knowledge' (knowledge was inlined since Phase 25)"
  - "Inventory field guidance maps directly to known agent bugs (Bug 1: deff_not dropped, Bug 2: grouping not applied, Bug 5: detection not translated)"

patterns-established:
  - "Inventory-augmented diagnostics: raw LSD commands show CURRENT state, inventory shows HISTORY (what changed between iterations)"

# Metrics
duration: 3min
completed: 2026-02-17
---

# Phase 46 Plan 01: Diagnostic Integration Summary

**Diagnostic specialist now parses constraint inventory JSON from LSD file headers for history-aware root cause analysis, with consistent analysis/ paths for all CASE artifacts**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-17T15:42:11Z
- **Completed:** 2026-02-17T15:45:03Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- delegate_specialist instructions in case.md now tell the specialist to extract the constraint inventory block and explain its key fields (hmbc_batches, deff_not_patterns, syme_pairs, etc.)
- lucy-diagnostic.md Step 1 Gather Context has new item 4 with field-by-field diagnostic guidance mapping inventory fields to known agent bugs
- DIAGNOSTIC-REPORT.md path consistently uses analysis/ subdirectory across delegate_specialist, extract_diagnostic_findings, track_and_decide, and all references in lucy-diagnostic.md
- counter == 2 delegation threshold and Task() objectivity (no team_name) preserved unchanged

## Task Commits

Both modified files (~/.claude/commands/lucy-ng/case.md and ~/.claude/agents/lucy-diagnostic.md) are outside the project git repository. No git commits were made for task work -- these are agent definition files managed outside the codebase.

1. **Task 1: Update case.md delegate_specialist and extract_diagnostic_findings** - no commit (file outside repo)
2. **Task 2: Update lucy-diagnostic.md Step 1 with inventory extraction** - no commit (file outside repo)

## Files Created/Modified
- `~/.claude/commands/lucy-ng/case.md` - Updated delegate_specialist Task() instructions with inventory awareness, LSD path convention, analysis/ report path; updated extract_diagnostic_findings and track_and_decide paths
- `~/.claude/agents/lucy-diagnostic.md` - Added Step 1 item 4 for constraint inventory extraction with field-by-field diagnostic guidance; updated all DIAGNOSTIC-REPORT.md path references to analysis/ subdirectory

## Decisions Made
- LSD file path in delegate_specialist changed from `<compound_path>/<latest_lsd_file>` to `<compound_path>/analysis/<latest_iteration>/compound.lsd` to match file organization convention
- Changed "per skill/diagnostic/SKILL.md" to "per your inlined knowledge" since specialist has knowledge inlined since Phase 25
- Inventory field guidance explicitly maps to known agent bugs: deff_not_patterns -> Bug 1 (constraint dropping), syme_pairs -> Bug 2 (grouping not applied), bond/list_prop constraints -> Bug 5 (detection not translated)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

Modified files are outside the project git repository (under ~/.claude/). This means no per-task commits exist in the project repo. The files are agent definitions and command skills that live alongside the Claude Code configuration.

## User Setup Required

None - no external service configuration required.

## Phase 46 Success Criteria Verification

| SC | Description | Status | Evidence |
|----|-------------|--------|----------|
| SC1 | Specialist remains orchestrator-spawned (not team member) | PASS | delegate_specialist Task() has no team_name parameter; line 936 states "WITHOUT team_name" |
| SC2 | Specialist receives team context (CASE-PROGRESS.md, constraint inventory) | PASS | CASE-PROGRESS.md referenced in delegate_specialist; CONSTRAINT INVENTORY in both case.md and lucy-diagnostic.md |
| SC3 | Diagnostic report delivered via orchestrator advisory | PASS | extract_diagnostic_findings and deliver_advisory steps exist; both use analysis/DIAGNOSTIC-REPORT.md path |
| SC4 | Delegation trigger unchanged | PASS | "counter for this pattern == 2" found at line 619 of case.md |

## Next Phase Readiness
- Diagnostic specialist integration complete with inventory awareness
- Ready for Phase 47 UAT testing of full CASE workflow with team coordination

## Self-Check: PASSED

- FOUND: ~/.claude/commands/lucy-ng/case.md
- FOUND: ~/.claude/agents/lucy-diagnostic.md
- FOUND: .planning/phases/46-diagnostic-integration/46-01-SUMMARY.md
- No git commits to verify (files outside project repo)

---
*Phase: 46-diagnostic-integration*
*Completed: 2026-02-17*

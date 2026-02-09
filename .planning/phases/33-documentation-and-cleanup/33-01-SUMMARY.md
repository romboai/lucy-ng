---
phase: 33-documentation-and-cleanup
plan: 01
subsystem: documentation
tags: [CLAUDE.md, release-notes, v2.1, sub-commands, architecture]

# Dependency graph
requires:
  - phase: 32-end-to-end-validation
    provides: "Phase 32 complete, v2.1 validation procedures in place"
provides:
  - "CLAUDE.md updated with sub-command references and v2.1 architecture"
  - "v2.1 release notes documenting working multi-agent CASE vs v2.0 paper design"
affects: [33-02-PROJECT-refresh]

# Tech tracking
tech-stack:
  added: []
  patterns: []

key-files:
  created:
    - ".planning/phases/33-documentation-and-cleanup/v2.1-RELEASE-NOTES.md"
  modified:
    - "CLAUDE.md"

key-decisions:
  - id: DOC-SUBCOMMAND-ENTRY
    what: "CLAUDE.md header now points to sub-commands, not skill/SKILL.md"
    why: "Sub-commands are the actual workflow entry points in v2.1"
    date: 2026-02-09
  - id: DOC-AGENT-NAMES
    what: "Document actual agent filenames (lucy-case-agent.md, lucy-diagnostic.md)"
    why: "No more vague 'supervisor' language — name the real files"
    date: 2026-02-09

patterns-established: []

# Metrics
duration: 3min
completed: 2026-02-09
---

# Phase 33 Plan 01: CLAUDE.md and v2.1 Release Notes Summary

**Updated project documentation to reflect v2.1 working multi-agent architecture with sub-command entry points, actual agent names, and comprehensive release notes**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-09
- **Completed:** 2026-02-09

## What Was Built

Updated CLAUDE.md (the primary project instruction file read by every Claude session) to accurately reflect the v2.1 architecture, and created comprehensive v2.1 release notes documenting what changed from v2.0's paper-only design to v2.1's working orchestration.

### Task 1: CLAUDE.md Updates

Made 5 specific changes to CLAUDE.md:

1. **Header reference updated** (line 5):
   - Old: "For CASE domain knowledge and workflow guidance, see skill/SKILL.md"
   - New: "For CASE workflow, run /lucy-ng:case. For all commands, run /lucy-ng (routing page)."
   - Impact: Points users to actual entry points, not internal skill docs

2. **Added Sub-Command Reference section** (new section after header):
   - Lists all 5 sub-commands: status, dereplicate, predict, sanitise, case
   - Includes agent file references: lucy-case-agent.md, lucy-diagnostic.md
   - Provides one-line descriptions of each command's purpose
   - Total: 9 lines of new content providing clear command reference

3. **CLI Output Reference intro updated** (line 55):
   - Old: "applying domain intelligence from skill/SKILL.md"
   - New: "Domain intelligence is encoded in sub-command skills and agent definitions"
   - Impact: Reflects distributed architecture vs monolithic skill

4. **LSD file structure reference fixed** (line 109):
   - Old: "skill/CASE/SKILL.md and skill/diagnostic/SKILL.md"
   - New: "skill/SKILL.md and skill/diagnostic/SKILL.md"
   - Impact: Corrects stale path (skill/CASE/ directory doesn't exist)

5. **Peak Picking API Reference updated** (line 154):
   - Old: "see skill/SKILL.md for the recommended workflow"
   - New: "see /lucy-ng:case sub-command for the recommended CASE workflow"
   - Impact: Points to actual workflow command, not internal doc

**Verification results:**
- `grep -c "skill/SKILL.md" CLAUDE.md` = 1 (only in LSD reference, correct)
- `grep -c "Sub-Command Reference" CLAUDE.md` = 1 (new section added)
- `grep -c "lucy-case-agent" CLAUDE.md` = 1 (agent file named)
- `grep -c "lucy-diagnostic" CLAUDE.md` = 1 (agent file named)
- `grep -c "supervisor" CLAUDE.md` = 0 (all stale references removed)
- `grep -c "/lucy-ng:case" CLAUDE.md` = 4 (proper references)

### Task 2: v2.1 Release Notes

Created comprehensive release notes (297 lines) at `.planning/phases/33-documentation-and-cleanup/v2.1-RELEASE-NOTES.md` documenting:

**Structure:**
1. Overview: v2.1 delivers working orchestration vs v2.0 paper design
2. What Changed from v2.0: Side-by-side comparison of v2.0 vs v2.1
3. Key Features Delivered: 5 major areas with detailed descriptions
4. Architecture Changes: Agent files, sub-command skills, orchestration mechanism
5. Key Decisions: Tables of orchestration and architectural boundary decisions
6. Phases Delivered: Summary of Phases 27-33
7. Migration from v2.0: What was removed, renamed, added
8. Technical Details: Code stats, dependencies, database info
9. What's Next: Future work directions

**Content highlights:**

- **5 sub-command skills documented:** status, dereplicate, predict, sanitise, case
- **CASE orchestrator details:** 12-step process, 4 loop patterns, batch monitoring
- **Autonomous CASE agent:** Hybrid inlining strategy (~528 lines critical knowledge)
- **Diagnostic specialist:** Delegation threshold (2 failed interventions)
- **AI-driven sanitisation:** Why AI-only, no CLI (compound identifiers require reasoning)
- **12 key decisions captured:** Advisory interventions, per-pattern counters, 10-cycle escalation, etc.
- **Migration guide:** What was removed (supervisor.md, diagnostic-specialist.md, monolithic skill), what was renamed, what was added
- **Entry point changes:** v2.0 "see skill/SKILL.md" → v2.1 "run /lucy-ng:case"

**Verification results:**
- Contains "Working Multi-Agent CASE": 1 occurrence (title)
- Contains "v2.0": 12 occurrences (comparison throughout)
- Contains "v2.1": 10 occurrences (current version references)
- Contains "lucy-case-agent": 7 occurrences (agent file references)
- Contains "lucy-diagnostic": 10 occurrences (specialist references)

## Commits

**Commit 1: CLAUDE.md updates**
- Hash: 742f24f
- Message: "docs(33-01): update CLAUDE.md with v2.1 architecture"
- Files: CLAUDE.md (22 insertions, 4 deletions)
- Changes: Sub-command reference section added, stale references updated, supervisor removed

**Commit 2: v2.1 release notes**
- Hash: 5277c5e
- Message: "docs(33-01): create v2.1 release notes"
- Files: .planning/phases/33-documentation-and-cleanup/v2.1-RELEASE-NOTES.md (297 insertions)
- Changes: Comprehensive release notes documenting v2.0 → v2.1 transition

## Deviations from Plan

None — plan executed exactly as written.

## Decisions Made

### DOC-SUBCOMMAND-ENTRY
**Decision:** CLAUDE.md header now points to sub-commands, not skill/SKILL.md
**Context:** Sub-commands are the actual workflow entry points in v2.1 — Claude sessions should be directed there first
**Rationale:** Accuracy in documentation — /lucy-ng:case is how users start CASE, not reading skill/SKILL.md
**Impact:** New Claude sessions will know to use /lucy-ng:* commands immediately

### DOC-AGENT-NAMES
**Decision:** Document actual agent filenames (lucy-case-agent.md, lucy-diagnostic.md) in CLAUDE.md
**Context:** v2.0 used vague "supervisor + CASE agent" language without naming files
**Rationale:** Transparency and accuracy — name the actual files that get spawned
**Impact:** Developers and future planning can reference exact agent files, no ambiguity

## Validation

All verification criteria from plan met:

- [x] CLAUDE.md has Sub-Command Reference section with 5 commands and 2 agent files listed
- [x] CLAUDE.md header references sub-commands, not skill/SKILL.md as primary workflow guide
- [x] No "supervisor" references remain in CLAUDE.md
- [x] v2.1 release notes exist and cover the v2.0 → v2.1 transition
- [x] All stale skill references in CLAUDE.md updated to point to sub-commands or correct paths

**Success criteria verification:**
- [x] CLAUDE.md accurately reflects v2.1 architecture with sub-command entry points
- [x] Release notes capture what v2.1 delivered and how it differs from v2.0's paper architecture
- [x] A new Claude session reading CLAUDE.md would know to use /lucy-ng:* commands and understand the agent architecture

## Next Phase Readiness

**Ready for:** 33-02 (PROJECT.md full refresh)

**Provides:**
- Accurate CLAUDE.md for all future Claude sessions
- Historical record of v2.1 architecture in release notes
- Clear sub-command reference for routing

**Notes:**
- PROJECT.md has uncommitted changes (marking v2.1 complete) — these should be handled in plan 02
- Release notes can be referenced in PROJECT.md Current State section update

## Issues & Concerns

None.

## Quality Metrics

- **Commit quality:** Atomic commits per task, clear messages with context
- **Verification:** All 6 verification checks passed
- **Documentation quality:** CLAUDE.md changes minimal and targeted (5 specific edits), release notes comprehensive (297 lines covering all aspects of v2.1)
- **Accuracy:** All references point to actual files and commands that exist

---

*Plan: 33-01*
*Completed: 2026-02-09*
*Next: 33-02 (PROJECT.md refresh)*

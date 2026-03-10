---
phase: 55-skill-architecture
plan: 02
subsystem: agents
tags: [nmr, agents, skill-architecture, refactoring]

# Dependency graph
requires:
  - phase: 55-skill-architecture
    provides: Plan 01 — Phase 55 setup and references directory structure
provides:
  - Deprecated legacy monolithic agent with clear retirement header
  - Shared NMR basics reference file (experiment types, shift regions, DEPT convention)
  - Updated nmr-chemist agent referencing shared file instead of inlining tables
affects: [lucy-nmr-chemist, lucy-case-agent, future-agent-authoring]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Shared reference files in ~/.claude/commands/lucy-ng/references/ for cross-agent reuse"
    - "Deprecation header pattern for retired agents (blockquote after frontmatter)"
    - "Read-file directive replacing inline tables in agent definitions"

key-files:
  created:
    - ~/.claude/commands/lucy-ng/references/nmr-basics.md
  modified:
    - ~/.claude/agents/lucy-case-agent.md
    - ~/.claude/agents/lucy-nmr-chemist.md

key-decisions:
  - "Deprecation via blockquote header (not deletion) — preserves historical reference while signaling retirement"
  - "Single nmr-basics.md as canonical source for NMR experiment types and 13C shift regions"
  - "Read-file directive pattern: agents reference shared files rather than duplicating tables"

patterns-established:
  - "Shared reference pattern: ~/.claude/commands/lucy-ng/references/<topic>.md for cross-agent knowledge"
  - "Deprecation pattern: blockquote DEPRECATED block immediately after frontmatter closing ---"

requirements-completed: [ARCH-02, ARCH-03]

# Metrics
duration: 2min
completed: 2026-03-10
---

# Phase 55 Plan 02: Skill Architecture — Agent Deprecation and Shared NMR Reference Summary

**Deprecated legacy monolithic CASE agent, created shared nmr-basics.md reference, and updated nmr-chemist to reference shared file eliminating ~18 lines of duplicated NMR tables**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-03-10T13:53:20Z
- **Completed:** 2026-03-10T13:54:57Z
- **Tasks:** 2
- **Files modified:** 3 (2 agent files, 1 new reference file)

## Accomplishments

- Added DEPRECATED blockquote header to lucy-case-agent.md, clearly marking it as retired since v4.0 and not spawned by any active workflow
- Created ~/.claude/commands/lucy-ng/references/nmr-basics.md (37 lines) with canonical NMR experiment types table (7 experiments including 1H and COSY), 13C chemical shift regions table (7 regions), and DEPT-135 sign convention note
- Updated lucy-nmr-chemist.md to replace inline NMR tables (22 lines) with a 4-line Read-file directive pointing to nmr-basics.md, renumbered sections 3-8 to 2-7, and updated one Section 5 cross-reference to Section 4

## Task Commits

Note: Agent and reference files are managed outside the lucy-ng git repository (~/.claude/). Commits for external files are not tracked in repo history. Changes applied directly to the files.

1. **Task 1: Archive legacy agent and create shared NMR reference** - files modified, no repo commit (files outside repo)
2. **Task 2: Update nmr-chemist to reference shared NMR basics** - files modified, no repo commit (files outside repo)

**Plan metadata:** committed with SUMMARY.md and state updates

## Files Created/Modified

- `~/.claude/agents/lucy-case-agent.md` - Added DEPRECATED blockquote header after frontmatter, no other content changed
- `~/.claude/commands/lucy-ng/references/nmr-basics.md` - Created: shared NMR experiment types, shift regions, and DEPT convention (37 lines)
- `~/.claude/agents/lucy-nmr-chemist.md` - Replaced inline NMR tables with Read-file directive, renumbered sections 3-8 to 2-7, updated Section 5 cross-reference to Section 4. Net -17 lines (261 -> 244)

## Decisions Made

- Deprecated agent via blockquote header (not deletion) to preserve historical reference while clearly signaling retirement — important for understanding v3.0 behavior
- Created references/ directory as part of this plan (Plan 01 didn't create it — confirmed by filesystem check before execution)
- Included all 7 experiment types in nmr-basics.md (added 1H and COSY from legacy agent, which had a more complete table than nmr-chemist's original 5-experiment version)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- The references/ directory was not created by Plan 01 (confirmed with filesystem check). Created it as part of Task 1 per the plan's instruction to "create it if not". Not a deviation — the plan anticipated this.
- Agent and reference files (~/.claude/) are outside the lucy-ng git repository, so per-task git commits cannot be made for these files. SUMMARY.md and STATE.md updates are committed in the repo as the metadata record.

## User Setup Required

None - no external service configuration required.

## Self-Check: PASSED

All artifacts verified:
- FOUND: ~/.claude/agents/lucy-case-agent.md (1 DEPRECATED marker)
- FOUND: ~/.claude/commands/lucy-ng/references/nmr-basics.md
- FOUND: ~/.claude/agents/lucy-nmr-chemist.md (1 nmr-basics.md reference, 0 inline tables)
- FOUND: .planning/phases/55-skill-architecture/55-02-SUMMARY.md

## Next Phase Readiness

- Shared reference infrastructure established at ~/.claude/commands/lucy-ng/references/
- Pattern is ready for use: additional shared references (e.g., lsd-commands.md, constraint-patterns.md) can follow same structure
- lucy-case-agent.md clearly marked as retired — no ambiguity about which workflow is active

---
*Phase: 55-skill-architecture*
*Completed: 2026-03-10*

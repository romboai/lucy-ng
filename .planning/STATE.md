# lucy-ng State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-06)

**Core value:** AI agent autonomously determines compound structures from NMR, with multi-agent architecture preventing loops
**Current focus:** Phase 20 complete; ready for Phase 21 (Skill Restructure)

## Current Position

**Milestone**: v2.0 Robust Multi-Agent CASE
**Phase**: 21 of 26 (Skill Restructure) -- IN PROGRESS
**Plan**: 2 of 3 in current phase (Plan 02 complete)
**Status**: Plan 02 complete (CLAUDE.md restructured, supervisor skill created)
**Last activity**: 2026-02-06 -- Completed 21-02-PLAN.md (CLAUDE.md restructure + supervisor)

Progress: [====================|.........] 73% (21/26 phases in progress, 20 complete)

## Completed Milestones

| Milestone | Phases | Shipped |
|-----------|--------|---------|
| v1.0 Core CASE Pipeline | 1-10 | 2026-01-12 |
| v1.1 Database-Backed Dereplication | 11-15 | 2026-01-15 |
| v1.2 HOSE Database Prediction | 16-19 | 2026-01-18 |

## Performance Metrics

**Velocity:**
- Total plans completed: 24 (v1.0-v1.2 + 20-01, 20-02, 20-03, 21-01, 21-02)
- Average duration: ~3 hours per phase
- Total execution time: ~60 hours

**Recent Trend:**
- Phase 20 completed in 3 plans (~15 min total execution)
- Plan 21-01 completed in 3 min (documentation writing)
- Plan 21-02 completed in 5 min (documentation restructure)
- Trend: Accelerating (audit/writing tasks faster than code tasks)

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- v2.0: AI as intelligence layer -- domain knowledge in skill, not Python code
- v2.0: Multi-agent CASE -- supervisor prevents loops, specialists handle subtasks
- v2.0: Error tolerance as skill knowledge -- teach AI to detect issues, not build Python machinery
- v2.0: Skip COSY -- notoriously difficult to analyze, defer
- 20-01: MCP tools: 7 Tier 1, 4 Tier 2, 4 Tier 3 (of 15 total)
- 20-01: CLI groups: 4 Tier 1, 3 Tier 2, 2 Tier 3 (of 9 groups, 22 commands)
- 20-01: generate_correlation_diagram = Tier 1 despite 1151 lines (pure visualization, no NMR inference)
- 20-03: SKILL.md proposed at ~500 lines with 9 sections (NMR background through quick reference)
- 20-03: SUPERVISOR.md proposed at ~40 lines for workflow selection and escalation
- 20-03: Phase 26 dual-mode architecture: MCP thin wrappers + CLI retains smart behavior
- 21-01: SKILL.md actual: 418 lines, 8 sections (NMR background through quick reference)
- 21-01: Deduplication achieved: sp2 even count (1x), ELIM usage (1x), correlation order (1x), score thresholds (1x), MAE thresholds (1x)
- 21-01: SKILL.md excludes project-level content (setup, dev reference, database stats stay in CLAUDE.md)
- 21-02: CLAUDE.md reduced from 1,080 to 305 lines (72% reduction), keeping only project-level content
- 21-02: skill/supervisor/SKILL.md created (78 lines) with workflow selection, loop detection, escalation criteria
- 21-02: Zero domain knowledge remains in CLAUDE.md -- all workflow/reasoning now in skill/SKILL.md

### Pending Todos

- Phase 21 Plan 03 ready: With CLAUDE.md lean and supervisor created, deduplicate subskills (sanitize, dereplicate, CASE) by referencing skill/SKILL.md
- Phase 24 foundation ready: skill/supervisor/SKILL.md provides routing logic, loop detection patterns, escalation criteria for full supervisor agent
- 8 intelligence hotspot modules (~2,139 lines) identified for progressive migration through Phases 22-26
- 3 code consolidation targets (experiment auto-discovery, database finder, LSD parser) queued for Phase 26

### Blockers/Concerns

- Virgiline (CASE7) failure is the motivating case for v2.0 -- supervisor and incremental HMBC should address root causes

## Session Continuity

Last session: 2026-02-06
Stopped at: Completed Phase 21 Plan 02 (CLAUDE.md restructured, supervisor skill created)
Resume file: None

---
*Last updated: 2026-02-06 after Phase 21 Plan 02 completion*

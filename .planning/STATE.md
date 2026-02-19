# lucy-ng State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-19)

**Core value:** AI agent autonomously determines compound structures from NMR, with a collaborative team architecture that self-corrects through peer review
**Current focus:** v5.0 Fragment Library — Phase 49 ready to plan

## Current Position

**Milestone**: v5.0 Fragment Library
**Phase**: 49 of 54 (Fragment Schema and Infrastructure)
**Status**: Ready to plan
**Last activity**: 2026-02-19 — v5.0 roadmap created (6 phases, 19 requirements mapped)

Progress: [░░░░░░░░░░] 0% (0 plans complete)

## Completed Milestones

| Milestone | Phases | Shipped |
|-----------|--------|---------|
| v1.0 Core CASE Pipeline | 1-10 | 2026-01-12 |
| v1.1 Database-Backed Dereplication | 11-15 | 2026-01-15 |
| v1.2 HOSE Database Prediction | 16-19 | 2026-01-18 |
| v2.0 Robust Multi-Agent CASE | 20-26 | 2026-02-08 |
| v2.1 Working Multi-Agent CASE | 27-33 | 2026-02-09 |
| v3.0 Statistical Detection | 34-40 | 2026-02-16 |
| v4.0 Team-Based CASE | 41-48 | 2026-02-18 |

## Performance Metrics

**Velocity:**
- Total plans completed: 87 across 7 milestones
- v4.0: 9 phases, 21 plans, 48 commits, 2 days
- Total execution time: ~78.2 hours

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.

Recent decisions affecting v5.0:
- Separate `lucy-ng-fragments.db` file (not merged into 2.8 GB main DB) — Dropbox sync and index contention
- Validate 2 ppm bin size on 1K sample BEFORE full 24M extraction — bin size is unrecoverable once baked in
- DEFF goodlist LSD syntax requires LSD smoke test validation BEFORE agent integration — goodlist vs DEFF NOT semantic confusion is silent failure
- Phases 51 and 52 can run in parallel — both depend only on SSCMatch model from Phase 49, not on Phase 50 data

### Pending Todos

- Statistical 4J HMBC coupling detection (deferred to v5.1)
- Multi-compound UAT (pulegone, virgiline, etc.)
- COSY correlation integration (deferred to v5.2)
- NP-likeness scoring (deferred to v5.2)

### Blockers/Concerns

- 4J HMBC couplings silently exclude correct structures — deferred to v5.1; v5.0 UAT should test non-4J compounds first
- SSC extraction runtime: projected 4-8 hours; checkpointing is mandatory before full run

### Strategic Reference

See `background/sherlock-analysis.md` for full Sherlock vs lucy-ng comparison. Fragment library is the last remaining major gap for Sherlock parity.

## Session Continuity

Last session: 2026-02-19
Stopped at: v5.0 roadmap created; 6 phases defined (49-54), 19/19 requirements mapped
Resume file: None

---
*Last updated: 2026-02-19 after v5.0 roadmap created*

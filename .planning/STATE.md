# lucy-ng State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-10)

**Core value:** AI agent autonomously determines compound structures from NMR, with data-driven statistical constraints replacing guesswork
**Current focus:** v3.0 Statistical Detection — Phase 36 (HHB and Ring Detection)

## Current Position

**Milestone**: v3.0 Statistical Detection
**Phase**: 36 of 40 (HHB and Ring Detection)
**Plan**: 01 of 03 complete (Schema extension v6)
**Status**: In progress
**Last activity**: 2026-02-11 — Completed 36-01-PLAN.md (schema extension v6)

Progress: [█████████████████████████████████░░░░░░░░] 87.5% (35/40 phases complete, 1/3 plans in phase 36)

## Completed Milestones

| Milestone | Phases | Shipped |
|-----------|--------|---------|
| v1.0 Core CASE Pipeline | 1-10 | 2026-01-12 |
| v1.1 Database-Backed Dereplication | 11-15 | 2026-01-15 |
| v1.2 HOSE Database Prediction | 16-19 | 2026-01-18 |
| v2.0 Robust Multi-Agent CASE | 20-26 | 2026-02-08 |
| v2.1 Working Multi-Agent CASE | 27-33 | 2026-02-09 |

## Performance Metrics

**Velocity:**
- Total plans completed: 47 (v1.0-v2.1: 39, v3.0: 8)
- Average duration: ~3 hours per phase (v1.0-v1.2), < 15 min per phase (v2.0-v2.1 docs/skills), ~7 min per plan (v3.0 implementation)
- Total execution time: ~66.5 hours

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- v3.0: Major version bump — statistical detection is fundamental capability addition, not incremental
- v3.0: Motivated by Sherlock CASE system analysis (Wenk PhD thesis) — identified 5 critical gaps
- v3.0: Gap 1 (statistical detection) selected as first milestone — universal benefit, builds on existing HOSE DB
- v3.0: Gaps 4+5 (ranking + badlist) bundled into v3.0 — too small for standalone milestones
- v3.0: Signal grouping detection included — identifies close shifts but combinatorial exchange deferred to v3.1
- Phase 34-01: Use ALTER TABLE ADD COLUMN for v3→v4 migration (safe, fast, in-place)
- Phase 34-01: Composite index (radius, mean) for O(log N) BETWEEN queries in detection
- Phase 34-01: All query methods backward compatible with v3 databases (try/except fallback)
- Phase 34-02: extract_hybridisation() at module level for reusability across generator classes
- Phase 34-02: update_with_hybridisation() instead of modifying update() for backward compatibility
- Phase 34-02: generate_all() returns tuple (aggregates, hybridisations) - minimal breaking change
- Phase 34-02: Treat S and UNSPECIFIED hybridisations as sp3 (conservative default)
- Phase 34-03: StatisticalDetector is pure query+frequency layer (no HOSE/RDKit logic)
- Phase 35-01: Neighbour count columns store presence frequency (count of observations with ≥1 element)
- Phase 35-01: Halogen aggregation in single has_halogen_neighbor column (F/Cl/Br/I combined)
- Phase 35-01: parse_sphere_1() uses regex [A-Z][a-z]? to extract elements, ignoring bond prefixes
- Phase 35-01: Upsert accepts 5, 8, or 13-element tuples for v3/v4/v5 backward compatibility
- Phase 35-02: update_with_neighbors() calls update_with_hybridisation() internally for composition
- Phase 35-02: WelfordAccumulator.to_tuple() extended from 6 to 11 elements for v5 schema
- Phase 35-02: HOSEStatsGenerator.generate_all() returns 3-tuple (aggregates, hybridisations, neighbour_counts)
- Phase 35-03: mandatory_elements/forbidden_elements properties use hardcoded 0.95/0.01 thresholds for convenience
- Phase 35-03: Constraints use custom thresholds passed to detect_neighbours() for flexibility
- Phase 35-03: Warn on unpopulated neighbour columns (v4 databases) rather than fail
- Phase 35-04: --mode flag overrides --min-frequency/--max-frequency when both provided
- Phase 35-04: No multiplicity argument for neighbours detection (research recommends ignoring it)
- Phase 36-01: Bond pair statistics at formula level (not HOSE level) - correct granularity for HHB queries
- Phase 36-01: Ring columns store counts (not booleans) for frequency distributions
- Phase 36-01: Composite PRIMARY KEY (formula_normalized, element1, element2) for bond_pair_stats
- Phase 36-01: Backward compatibility - get_bond_pair_stats_by_formula returns [] for v5 databases

### Pending Todos

- ~~Implement neighbourhood detection CLI commands (Phase 35)~~ → COMPLETE
- Implement HHB and ring detection (Phase 36)
- Implement signal grouping (Phase 37)
- Implement two-tier ranking and badlist (Phase 38)
- Update CASE agent to use new CLI commands for constraint generation (Phase 39)
- Validate on ibuprofen (Phase 40) — must find correct aromatic structure

### Blockers/Concerns

- ~~HOSE database schema extension requires migration or fresh generation~~ → RESOLVED: ALTER TABLE migration is instant
- HOSE database hybridisation columns exist but are unpopulated (all 0) until database regeneration (v4→v5 migration adds neighbour columns with DEFAULT 0)
- Database regeneration required: After stats generator update (35-02), full regeneration needed to populate neighbour counts
- Ibuprofen failure root cause: 4-bond HMBC + rigid assignment + no statistical constraints → cyclohexadiene solutions
- ~~Research flags threshold sensitivity~~ → RESOLVED: --mode relaxed and --min/max-frequency override flags implemented in Phase 35-04

## Session Continuity

Last session: 2026-02-11
Stopped at: Completed 36-01-PLAN.md — Phase 36 Plan 1 (schema extension v6) complete
Resume file: None — Ready for Phase 36 Plan 2 (stats generators)

---
*Last updated: 2026-02-11 after Plan 36-01 execution (Phase 36 Plan 1 complete)*

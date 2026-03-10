# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v6.0 — Skill Quality Overhaul

**Shipped:** 2026-03-10
**Phases:** 4 | **Plans:** 7 | **Sessions:** 3

### What Was Built
- Factored case.md orchestrator with 3 extracted reference files (progress-format, loop-patterns, advisory-templates)
- 4J HMBC coupling awareness pipeline: nmr-chemist flags → lsd-engineer defers → solution-analyst verifies
- Orchestrator message validation with RESEND-REQUIRED protocol
- Natural-language trigger phrases in all 5 skill descriptions + routing decision tree
- Error recovery in predict (HOSE miss) and dereplicate (0-match), dry-run gate in sanitise
- Version compatibility check in status, smoke test mode (--smoke-test) in CASE orchestrator

### What Worked
- **Auto-advance pipeline**: /gsd:plan-phase --auto executed 4 phases (plan → verify → execute → verify → complete) in a single session with minimal human interaction
- **Parallel execution**: Plans 57-01 and 57-02 ran in parallel (Wave 1) with non-overlapping file sections, completing in ~6 minutes combined
- **No Python changes**: Pure .md skill editing meant zero test failures, zero regressions, zero build issues — fastest milestone to ship
- **Integration checker**: Caught 2 genuine wiring gaps (aromatic expectation relay, 4J status validation) that individual phase verifiers missed

### What Was Inefficient
- **gsd-tools init can't find milestone-scoped phases**: Phases 55-58 exist in v6.0-ROADMAP.md but init returns phase_found=false. Required manual directory creation and variable setup each time
- **SUMMARY frontmatter inconsistency**: No `requirements-completed` field in SUMMARYs, making 3-source cross-reference incomplete in audit. The verification + traceability table was sufficient but the third source was weak

### Patterns Established
- **"Use when:" trigger phrase pattern**: Skill frontmatter descriptions with explicit trigger phrases for intent routing
- **Dry-run gate pattern**: READ-ONLY scan → manifest report → exact "proceed" confirmation before writes
- **Reference extraction pattern**: Large static content in references/ subdirectory, loaded on-demand via "Read file:" directives
- **Smoke test mode**: --smoke-test flag for 1-iteration pipeline validation with structured checkpoint table

### Key Lessons
1. **Skill-only milestones are fast**: 4 phases in 1 day with auto-advance. No test suite to run, no build to break — focus on content quality and integration wiring
2. **Integration checking matters most for .md changes**: Individual file verification passes easily but cross-file wiring (who relays what field to whom) is where gaps hide
3. **Milestone-scoped roadmaps need better tool support**: The init tool's inability to find phases in milestone-specific roadmaps added friction to every phase

### Cost Observations
- Model mix: ~30% opus (orchestration), ~70% sonnet (planning, execution, verification)
- Sessions: 3 (phases 55-56, phases 57-58, audit + complete)
- Notable: Auto-advance eliminated context switches between plan/execute/verify — single session handled phases 57 and 58 end-to-end

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Sessions | Phases | Key Change |
|-----------|----------|--------|------------|
| v6.0 | 3 | 4 | Auto-advance pipeline; pure .md editing; integration checker for wiring |

### Cumulative Quality

| Milestone | Tests | Coverage | Skill Lines |
|-----------|-------|----------|-------------|
| v6.0 | 867 (unchanged) | — | ~4,200 (skills + agents, factored with references) |

### Top Lessons (Verified Across Milestones)

1. Integration wiring is the highest-risk area for multi-agent skill architectures — individual files pass verification but cross-file field relay is where gaps hide

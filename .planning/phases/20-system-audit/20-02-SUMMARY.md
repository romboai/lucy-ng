# Plan 20-02 Summary

**Phase:** 20-system-audit
**Plan:** 02
**Status:** DONE
**Duration:** 3 minutes
**Completed:** 2026-02-06

## What Was Done

Performed a comprehensive audit of the 1,080-line CLAUDE.md file, cataloguing every section with line ranges, identifying duplication between sections, and flagging misplaced domain intelligence that belongs in skill documents rather than project-level instructions.

Three analyses were conducted:
1. **Section Catalogue**: All 14 top-level sections (## headings) and 43 subsections (### headings) catalogued with line ranges, line counts, and categories (project-setup, developer-ref, case-workflow, domain-knowledge, tool-usage)
2. **Duplication Map**: 5 duplication clusters identified with specific overlapping concepts, canonical versions, and line-level references
3. **Misplaced Intelligence**: 20+ sections flagged as containing domain knowledge/CASE workflow logic that belongs in SKILL.md or SUPERVISOR.md rather than CLAUDE.md

## Artifacts

- **audit-claude-md.md** (341 lines): Complete CLAUDE.md audit with section catalogue, duplication map, misplaced intelligence table, migration summary with destination breakdown and size projections

## Key Findings

- CLAUDE.md is approximately 80% domain knowledge and CASE workflow logic, with only ~20% being genuine project-level content (setup + developer reference)
- **LSD duplication cluster** is the largest: ~175 lines of overlapping content across 3 sections (LSD Integration, Manual LSD File Construction, Common Pitfalls), with rules like sp2-even-count, ELIM caution, and HSQC-before-HMBC each stated 4-8 times
- **Peak picking cluster**: HMBC noise problem/solution stated 3 times across Scientific Rationale, HMBC Guided Picker, and Pitfall 3
- Projected CLAUDE.md after restructuring: ~298 lines (from 1,080), well under the 800-line Phase 21 target
- ~590 lines of domain content moves to SKILL.md, ~40 lines to SUPERVISOR.md, ~32 lines to a Blind CASE skill, ~175 lines removed through deduplication

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | aba458c | Audit CLAUDE.md sections, duplication, and misplacement |

## Deviations

None -- plan executed exactly as written.

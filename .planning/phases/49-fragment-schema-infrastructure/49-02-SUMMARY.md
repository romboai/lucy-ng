---
phase: 49-fragment-schema-infrastructure
plan: 02
subsystem: cli
tags: [cli, click, fragment, sqlite, fragments]

# Dependency graph
requires:
  - phase: 49-fragment-schema-infrastructure/49-01
    provides: FragmentDatabaseManager with schema v7, get_schema_version, get_ssc_count, get_bin_size methods
provides:
  - lucy fragment CLI command group registered in main CLI
  - lucy fragment info subcommand reporting schema version, SSC count, bin size, file size
  - Helpful error message when fragment database does not exist
affects:
  - 50-ssc-extraction
  - 51-fragment-search
  - 52-lsd-integration
  - 54-uat

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Fragment CLI follows same thin-CLI pattern as database.py (no business logic in CLI layer)
    - Existence check before SQLite open prevents silent empty-file creation

key-files:
  created:
    - src/lucy_ng/cli/fragment.py
  modified:
    - src/lucy_ng/cli/main.py

key-decisions:
  - "Existence check (db_path.exists()) before opening FragmentDatabaseManager prevents sqlite3 from silently creating empty files"
  - "Top-level import of FragmentDatabaseManager follows project convention (not lazy import) — matches database.py pattern"
  - "fragment import placed alphabetically in main.py between detect and fetch"

patterns-established:
  - "Pattern: Fragment CLI thin function — all logic delegated to FragmentDatabaseManager"
  - "Pattern: Abort with helpful 'run fragment build' message when DB file missing"

requirements-completed: [FRAG-01]

# Metrics
duration: 2min
completed: 2026-02-19
---

# Phase 49 Plan 02: Fragment Schema and Infrastructure Summary

**`lucy fragment info` CLI command registered in main CLI — reports schema v7, SSC count 0, bin size 2.0 ppm for empty fragment database; errors helpfully when file does not exist**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-19T14:07:09Z
- **Completed:** 2026-02-19T14:09:07Z
- **Tasks:** 1
- **Files modified:** 2

## Accomplishments

- Created `src/lucy_ng/cli/fragment.py` with `fragment` command group and `info` subcommand
- `info` command: existence-check guard (no silent empty-file creation), schema version warning, SSC count, bin size, file size output
- Registered `fragment` group in `src/lucy_ng/cli/main.py` and added to help text
- ruff and mypy both clean; import order fixed after ruff I001 flag

## Task Commits

Each task was committed atomically:

1. **Task 1: Create fragment CLI command group with info subcommand** - `f101beb` (feat)

## Files Created/Modified

- `src/lucy_ng/cli/fragment.py` — fragment command group with info subcommand; imports FragmentDatabaseManager; existence check before DB open; outputs schema version, SSC count (comma-formatted), bin size (ppm), file size (MB)
- `src/lucy_ng/cli/main.py` — added import for fragment, added cli.add_command(fragment), added fragment to help text, fixed import ordering for ruff compliance

## Decisions Made

- Existence check (`db_path.exists()`) placed before `FragmentDatabaseManager` context manager open — SQLite would silently create an empty file without this guard
- Followed top-level import convention (not lazy import) matching `database.py` — the plan's note about lazy imports was contradicted by the note to follow `database.py` pattern, and `database.py` uses top-level imports

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed unsorted import order in main.py**
- **Found during:** Task 1 (register fragment in main.py)
- **Issue:** Inserted `from lucy_ng.cli.fragment import fragment` between `dereplicate` and `detect` alphabetically, but ruff I001 reported the block was unsorted
- **Fix:** Moved fragment import to alphabetically correct position (between `detect` and `fetch`)
- **Files modified:** src/lucy_ng/cli/main.py
- **Verification:** `ruff check src/lucy_ng/cli/main.py` — All checks passed
- **Committed in:** f101beb (part of task commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — import order)
**Impact on plan:** Trivial fix, no scope creep.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Phase 50 (SSC Extraction) can proceed: CLI infrastructure in place; `lucy fragment build` subcommand to be added in Phase 50
- Phases 51 and 52 can plan in parallel: fragment command group extensible with `search` and `to-lsd` subcommands
- FRAG-01 requirement satisfied: fragment database accessible via CLI, schema v7 confirmed

## Self-Check: PASSED

Both files exist on disk. Commit f101beb confirmed in git log.

---
*Phase: 49-fragment-schema-infrastructure*
*Completed: 2026-02-19*

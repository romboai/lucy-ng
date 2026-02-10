# Technology Stack for Statistical Detection Features

**Project:** lucy-ng v3.0 - Statistical Detection Milestone
**Researched:** 2026-02-10
**Confidence:** HIGH

## Executive Summary

Statistical detection features require **ZERO new dependencies**. The existing stack (Python 3.10+, RDKit, SQLite, nmrglue) provides all APIs needed. Implementation is primarily new database schema additions (new columns to `hose_stats`) and new query patterns. The HOSE code format already encodes hybridisation, eliminating the need for separate extraction.

## Existing Stack (v2.1) - NO CHANGES NEEDED

| Technology | Version | Purpose | Status |
|------------|---------|---------|--------|
| **Python** | 3.10+ | Language runtime | KEEP |
| **RDKit** | Latest (2025.09.5+) | Molecular structure, atom properties | KEEP |
| **SQLite** | 3.x | HOSE statistics + compound database | KEEP |
| **Pydantic** | v2 | Data validation | KEEP |
| **hosegen** | Latest | HOSE code generation | KEEP |
| **Click** | Latest | CLI framework | KEEP |

**Recommendation:** Use existing stack. All required APIs are available.

## Database Schema Changes

### Current Schema (v2.1)

```sql
-- Existing table from schema.py
CREATE TABLE hose_stats (
    hose_code TEXT NOT NULL,        -- "C-4;CCO(//)" format
    radius INTEGER NOT NULL,         -- 1-6
    mean REAL NOT NULL,              -- Mean shift in ppm
    std REAL NOT NULL,               -- Standard deviation
    count INTEGER NOT NULL,          -- Number of observations
    m2 REAL NOT NULL DEFAULT 0.0,    -- Welford's m2 for incremental updates
    PRIMARY KEY (hose_code, radius)
);

CREATE INDEX idx_hose_stats_code ON hose_stats(hose_code);
```

**Current size:** 7.9M rows across radii 1-6

| Radius | Rows |
|--------|------|
| 1 | 810 |
| 2 | 46,882 |
| 3 | 581,407 |
| 4 | 1,417,479 |
| 5 | 2,416,662 |
| 6 | 3,427,134 |


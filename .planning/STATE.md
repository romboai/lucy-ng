# lucy-ng State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-06)

**Core value:** AI agent autonomously determines compound structures from NMR, with multi-agent architecture preventing loops
**Current focus:** Defining requirements for v2.0

## Current Position

**Milestone**: v2.0 Robust Multi-Agent CASE
**Phase**: Not started (defining requirements)
**Plan**: —
**Status**: Defining requirements
**Last activity**: 2026-02-06 — Milestone v2.0 started

## Completed Milestones

| Milestone | Phases | Shipped |
|-----------|--------|---------|
| v1.0 Core CASE Pipeline | 1-10 | 2026-01-12 |
| v1.1 Database-Backed Dereplication | 11-15 | 2026-01-15 |
| v1.2 HOSE Database Prediction | 16-19 | 2026-01-18 |

## Key Decisions

| Decision | Date | Context |
|----------|------|---------|
| Hybrid CLI + MCP interface | 2026-01-08 | MCP for agent iteration, CLI for testing |
| Bruker-only for v1 | 2026-01-08 | Focus on most common format |
| LSD/pyLSD as primary solvers | 2026-01-08 | Established CASE tools with CLI |
| nmrglue for NMR parsing | 2026-01-08 | Most mature, BSD licensed, native Bruker support |
| Pydantic v2 for models | 2026-01-08 | Type safety, validation, JSON serialization |
| hatch build system | 2026-01-08 | Modern Python packaging |
| Use processed data | 2026-01-08 | Read from pdata/1/ not raw FID |
| DEPT-guided adaptive thresholding | 2026-01-10 | Lower HSQC threshold until all DEPT carbons matched |
| HMBC-guided peak picking | 2026-01-10 | Filter by requiring C match in 13C/DEPT and H match in HSQC |
| Click CLI framework | 2026-01-10 | Simpler than Typer, no extra dependencies |
| N:1 shift matching for ranking | 2026-01-12 | Handles molecular symmetry correctly |
| DOI-based data fetching | 2026-01-12 | Parse NMRXiv DOIs directly for project/study IDs |
| SQLite for dereplication DB | 2026-01-13 | Portable, no server, formula-indexed for fast lookup |
| Protocol pattern for backends | 2026-01-18 | HOSELookupProtocol for interchangeable prediction |
| Database-first auto-detection | 2026-01-18 | Prefer database over JSON table |
| Single database for both features | 2026-01-18 | Same DB powers dereplication AND prediction |
| AI as intelligence layer | 2026-02-06 | v2.0: Domain knowledge in skill, not Python code |
| Multi-agent CASE | 2026-02-06 | v2.0: Supervisor prevents loops, specialists handle subtasks |
| Error tolerance as skill knowledge | 2026-02-06 | v2.0: Teach AI to detect issues, not build Python machinery |
| Skip COSY for now | 2026-02-06 | Notoriously difficult to analyze, defer |

## v2.0 Context

**Trigger**: Virgiline (CASE7) failure analysis revealed that de novo CASE fails not due to tool bugs but due to:
1. AI agent not detecting ambiguous carbon shifts (close shifts in aliphatic region)
2. Agent using "throw everything in" HMBC strategy instead of incremental approach
3. Agent getting stuck in loops (trying ELIM, adjusting constraints, re-running) without a supervisor
4. Domain knowledge encoded in Python code instead of in the skill where the AI can reason about it

**Analysis documents**: `CASE7-failed/analysis/SYSTEM_ANALYSIS.pdf`, `CASE7-failed/analysis/Virgiline_HMBC_Analysis.pdf`

---
*Last updated: 2026-02-06 after v2.0 milestone started*

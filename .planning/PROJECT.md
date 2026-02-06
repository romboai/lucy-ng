# lucy-ng

**AI-agent powered Computer-Assisted Structure Elucidation for organic natural products**

## What This Is

Lucy-ng is an AI-agent skill for Computer-Assisted Structure Elucidation (CASE) of organic natural products from NMR spectroscopy data. The AI agent is the intelligence layer -- it reasons about spectra, detects problems, and drives the elucidation process. The Python tools are thin wrappers around external libraries (nmrglue, LSD, RDKit) that give the agent access to NMR data and solvers. The skill (CLAUDE.md) encodes domain expertise and workflow strategy.

## Core Value

An AI agent can autonomously determine the structure of an unknown organic compound from its NMR spectra, with a multi-agent architecture that prevents unproductive loops and keeps the elucidation on track.

## Current Milestone: v2.0 Robust Multi-Agent CASE

**Goal:** Transform lucy-ng from a tool-heavy system into an AI-first skill with thin tool wrappers and a multi-agent architecture that keeps structure elucidation on track.

**Three pillars:**
1. **Audit & Simplify** -- Examine every component, strip intelligence from CLI/Python code, push domain knowledge into the skill
2. **Skill Rewrite** -- Rewrite the CASE skill with clearer strategy (incremental HMBC, error tolerance as AI knowledge, not Python code)
3. **Multi-Agent CASE Architecture** -- Orchestrator/supervisor + specialist agents; supervisor detects loops and redirects the CASE agent

## Architecture

- **Skill** (CLAUDE.md/SKILL.md): Domain expertise, workflow strategy, error handling knowledge -- the intelligence layer
- **Thin Tools**: Minimal Python CLI/MCP wrappers around nmrglue, LSD, RDKit, SQLite
- **Multi-Agent**: CASE agent (does the work) + Supervisor agent (keeps it on track) + optional specialist agents
- **Database**: SQLite with 928K compounds and 7.9M HOSE statistics

## Requirements

### Validated

- Read 1D Bruker NMR files (1H, 13C) — v1.0
- Read 2D Bruker NMR files (HSQC, HMBC, COSY) — v1.0
- Automated peak picking for 1D spectra — v1.0
- Automated peak picking for 2D spectra (DEPT-guided, HMBC-guided) — v1.0
- Generate LSD/pyLSD input file format — v1.0
- Execute LSD/pyLSD and parse results — v1.0
- CLI interface for all operations (7 command groups) — v1.0
- MCP server exposing tools for Claude (13 tools) — v1.0
- HOSE-based 13C shift prediction for solution ranking — v1.0
- NMRXiv dataset fetching — v1.0
- SQLite database for 928K compounds (COCONUT + NMRShiftDB) — v1.1
- Database-backed dereplication (~100x faster) — v1.1
- Database-backed 13C prediction with 7.9M HOSE statistics — v1.2
- MCP tool for checking prediction capability (get_hose_stats_info) — v1.2

### Active

- [ ] Audit all CLI/Python components -- identify what to simplify, remove, or keep
- [ ] Rewrite CASE skill with incremental HMBC strategy and error tolerance knowledge
- [ ] Multi-agent CASE architecture (CASE agent + supervisor + specialists)
- [ ] Supervisor agent rules for detecting and breaking unproductive loops
- [ ] Bake error tolerance into skill (close-shift detection, ambiguity handling, DEPT phase checks)

### Deferred

- [ ] Support for COSY correlations in LSD constraints -- notoriously difficult to analyze
- [ ] Stereochemistry handling (E/Z, R/S)
- [ ] Interactive CASE mode with user feedback loop

### Out of Scope

- NMR spectrum prediction from structures - use HOSE codes instead
- GUI or web visualization - purely programmatic interface
- Non-Bruker vendor formats (Varian, JEOL, etc.) - Bruker only for v1
- SENECA integration - requires Java GUI rebuild, deferred
- Natural products likeness scoring - later feature

## Constraints

- Python 3.10+ required
- Open source only - no proprietary dependencies
- Open data formats - no vendor lock-in
- Must interface with existing LSD/pyLSD CLI tools

## Context

### Background

Lucy was the original CASE software created by the project author and sold to Bruker. Lucy-ng represents a complete reimagining for the AI-agent era, prioritizing programmatic interfaces over GUI interactions.

### Problem

Existing NMR processing tools like nmrium are GUI-focused, making it difficult for AI agents to interact with them programmatically. An unattended system that can iterate through structure elucidation without human intervention requires a different architecture.

### Target Users

- Cheminformatics researchers
- Natural products chemists
- AI/ML researchers working on structure elucidation

### NMR Data Requirements

Minimum viable spectral data for v1:
- 1D: 1H and 13C spectra
- 2D: HSQC (direct C-H correlations) and HMBC (long-range correlations)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Hybrid CLI + MCP interface | MCP provides structured tools for agent iteration; CLI enables testing and scripting | Good |
| Bruker-only for v1 | Focus on most common format, expand vendor support later | Good |
| LSD/pyLSD as primary solvers | Established CASE tools with CLI interface | Good |
| nmrglue for NMR parsing | Most mature, BSD licensed, native Bruker support | Good |
| Pydantic v2 for models | Type safety, validation, JSON serialization | Good |
| DEPT-guided adaptive thresholding | Lower HSQC threshold until all DEPT carbons matched | Good |
| HMBC-guided peak picking | Filter by requiring C match in 13C/DEPT and H match in HSQC | Good |
| N:1 shift matching for ranking | Handles molecular symmetry correctly | Good |
| SQLite for dereplication DB | Portable, no server, formula-indexed for fast lookup | Good |
| HOSE codes for prediction | Pure Python, no external services, reasonable accuracy | Good |
| AI as intelligence layer | v2.0: Domain knowledge belongs in skill, not Python code | — Pending |
| Multi-agent CASE | v2.0: Supervisor prevents loops, specialists handle subtasks | — Pending |
| Error tolerance as skill knowledge | v2.0: Teach AI to detect close shifts, ambiguity -- not Python machinery | — Pending |

## Current State

**Version:** v1.2 (shipped 2026-01-18)
**Codebase:** ~17,500 lines Python, 642 tests
**Tech stack:** Python 3.10+, Pydantic v2, nmrglue, RDKit, SQLite, Click, FastMCP

**Capabilities:**
- 16 MCP tools for AI agent integration (including get_hose_stats_info)
- 7 CLI command groups (read, pick, analyze, dereplicate, predict, lsd, fetch)
- SQLite database with 928K compounds (COCONUT + NMRShiftDB)
- 7.9M HOSE statistics for database-backed 13C prediction
- Full CASE pipeline: peak picking → LSD generation → solving → ranking

---
*Last updated: 2026-02-06 after v2.0 milestone started*

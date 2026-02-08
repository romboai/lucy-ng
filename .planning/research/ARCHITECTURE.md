# Architecture Patterns: Multi-Agent CASE Orchestration

**Domain:** Multi-agent NMR structure elucidation system
**Researched:** 2026-02-08
**Focus:** Sub-command skill integration with existing lucy-ng architecture

## Executive Summary

The v2.1 architecture integrates GSD-pattern sub-command skills with the existing lucy-ng CLI system, replacing the monolithic `/lucy-ng` skill and paper-only agent definitions with working multi-agent orchestration. This is an **integration milestone**, not a rewrite — we're adding orchestration to a complete, working system (v2.0: thin CLI validated in Phase 26).

**Key architectural shift:** Supervisor logic dissolves from a separate agent (supervisor.md) into an orchestrator skill (case.md). Sub-command skills become the entry points, spawning worker agents with inlined skill content.

**Integration challenge:** Context management. skill/SKILL.md (1,079 lines) + skill/CASE/SKILL.md (~300 lines) must be accessible to spawned agents. Solution: hybrid inlining (critical workflow inlined in Task() instructions, detailed reference via file paths).

**Build order:** Sub-command skills → agent definitions → orchestration logic → diagnostic integration → validation.

---

## Recommended Architecture

### System Structure (v2.1)

```
~/.claude/commands/lucy-ng/          Sub-command skills (orchestrators)
    ├── case.md                       CASE orchestrator (spawns agents, monitors, intervenes)
    ├── sanitise.md                   AI-driven dataset sanitization
    ├── dereplicate.md                Thin wrapper for CLI dereplication
    ├── predict.md                    Thin wrapper for CLI prediction
    └── status.md                     System status checks

~/.claude/agents/                    Agent definitions (workers)
    ├── lucy-case-agent.md            Autonomous CASE worker
    └── lucy-diagnostic.md            LSD failure diagnosis specialist

/project/skill/                      Domain knowledge (referenced by agents)
    ├── SKILL.md                      Core NMR/CASE domain knowledge (1,079 lines)
    ├── CASE/SKILL.md                 CASE workflow procedures
    ├── supervisor/SKILL.md           Loop detection, intervention patterns (827 lines)
    ├── diagnostic/SKILL.md           LSD manual, diagnostic procedures (1,874 lines)
    ├── dereplicate/SKILL.md          Dereplication scoring rules
    └── sanitize/SKILL.md             Dataset sanitization patterns

/project/src/lucy_ng/cli/           Thin CLI commands (data access only)
    ├── read.py                       Read NMR spectra
    ├── pick.py                       Raw peak picking (no intelligence)
    ├── analyze.py                    Raw symmetry data
    ├── dereplicate.py                Database matching
    ├── predict.py                    13C shift prediction
    └── lsd.py                        LSD runner, solution ranking

/project/CLAUDE.md                   Project-level CLI reference only (305 lines)
```

### Architectural Principles

1. **Sub-command skills are orchestrators** — route requests, spawn agents, monitor progress, handle failures
2. **Agents are autonomous workers** — receive inlined skill content + compound data, execute workflows, write progress files
3. **Skill documents are referenced, not duplicated** — agents receive file paths to read OR critical sections inlined
4. **CLI commands are thin data pipes** — all intelligence lives in skills/agents, not Python (validated in v2.0 Phase 26)
5. **Progress files are the IPC mechanism** — CASE-PROGRESS.md and DIAGNOSTIC-REPORT.md enable orchestrator monitoring

---

## Component Boundaries

### Sub-Command Skills (Orchestrators)

| Skill | Responsibility | Spawns Agents | Writes Files |
|-------|---------------|---------------|--------------|
| `case.md` | CASE orchestration, progress monitoring, loop detection, intervention | lucy-case-agent, lucy-diagnostic | None (reads CASE-PROGRESS.md, DIAGNOSTIC-REPORT.md) |
| `sanitise.md` | AI-driven dataset sanitization (identify compound identifiers, remove/redact) | None (direct execution) | SANITIZATION-REPORT.md |
| `dereplicate.md` | Thin wrapper: `lucy dereplicate c13 <path> <formula>` | None (direct CLI) | None |
| `predict.md` | Thin wrapper: `lucy predict c13 <smiles>` | None (direct CLI) | None |
| `status.md` | System checks: lucy version, LSD availability, database presence | None (direct CLI) | None |

### Agent Definitions (Workers)

| Agent | Responsibility | Reads | Writes | Spawned By |
|-------|---------------|-------|--------|------------|
| `lucy-case-agent.md` | Autonomous CASE: peak picking → LSD writing → solving → ranking | skill/SKILL.md, skill/CASE/SKILL.md (via inlined content + file paths), compound spectra | CASE-PROGRESS.md (after each iteration), LSD files | case.md orchestrator |
| `lucy-diagnostic.md` | LSD failure diagnosis: systematic checks, root cause analysis, fix recommendations | skill/diagnostic/SKILL.md (via file path), CASE-PROGRESS.md, LSD files | DIAGNOSTIC-REPORT.md | case.md orchestrator |

### Skill Documents (Domain Knowledge)

| File | Lines | Purpose | Primary Consumer |
|------|-------|---------|------------------|
| skill/SKILL.md | 1,079 | Core NMR/CASE domain knowledge, peak picking, symmetry, LSD basics, HMBC strategy, ranking, confidence | lucy-case-agent (inlined excerpts + file path reference) |
| skill/CASE/SKILL.md | ~300 | CASE workflow step-by-step, CASE-PROGRESS.md format | lucy-case-agent (inlined in Task() instructions) |
| skill/supervisor/SKILL.md | 827 | Loop detection patterns, diagnostic procedures, intervention templates, convergence criteria | case.md orchestrator (read directly, not inlined) |
| skill/diagnostic/SKILL.md | 1,874 | LSD command reference, systematic diagnostic procedures, report template | lucy-diagnostic agent (file path reference) |
| skill/dereplicate/SKILL.md | ~100 | Dereplication scoring interpretation | dereplicate.md skill (read directly) |
| skill/sanitize/SKILL.md | ~200 | Dataset sanitization patterns (compound name/SMILES removal) | sanitise.md skill (read directly) |

**Note:** skill/ hierarchy is complete from v2.0. NO restructuring needed for v2.1.

### Existing Python CLI (Thin Tools)

**Status:** Complete from v2.0 Phase 26. All CLI commands are thin data-access wrappers with no embedded intelligence.

| CLI Group | Intelligence Level | Changes for v2.1 |
|-----------|-------------------|------------------|
| `lucy read 1d/2d` | None (pure data access) | No change |
| `lucy pick 1d/2d/hsqc/hmbc` | None (raw peaks above threshold) | No change |
| `lucy analyze symmetry` | None (raw carbon counts, intensity data) | No change |
| `lucy dereplicate c13` | Minimal (formula-indexed DB query, score calculation) | No change |
| `lucy predict c13` | Minimal (HOSE lookup, statistics) | No change |
| `lucy lsd run/rank` | None (LSD runner, 13C prediction for ranking) | No change |
| `lucy visualize correlations` | None (diagram generation) | No change |
| `lucy database info/download` | None (SQLite metadata, Figshare fetch) | No change |
| `lucy fetch nmrxiv` | None (API wrapper) | No change |

**Validation:** Phase 26-05 (Ibuprofen CASE) already validated that thin CLI + skill knowledge produces correct results.

---

## Data Flow Patterns

### Flow 1: Simple Sub-Commands (dereplicate, predict, status)

```
User invokes: /lucy-ng:dereplicate <path> C13H18O2

┌─────────────────────────────────────┐
│ ~/.claude/commands/lucy-ng/         │
│ dereplicate.md                       │
│ (orchestrator skill)                 │
└──────────────┬──────────────────────┘
               │
               │ Bash: lucy dereplicate c13 <path> <formula> --format json
               ▼
┌─────────────────────────────────────┐
│ src/lucy_ng/cli/dereplicate.py      │
│ (thin CLI wrapper)                   │
└──────────────┬──────────────────────┘
               │
               │ Query SQLite DB
               ▼
┌─────────────────────────────────────┐
│ data/reference/lucy-ng-derep.db     │
└──────────────┬──────────────────────┘
               │
               │ Return JSON: {is_match, top_matches, ...}
               ▼
┌─────────────────────────────────────┐
│ dereplicate.md interprets results    │
│ Uses skill/dereplicate/SKILL.md     │
│ Reports to user                      │
└─────────────────────────────────────┘
```

### Flow 2: CASE Orchestration (Multi-Agent)

```
User invokes: /lucy-ng:case <compound_path> C13H18O2

┌──────────────────────────────────────────────────────────────────┐
│ ~/.claude/commands/lucy-ng/case.md                                │
│ (orchestrator skill)                                               │
│ - Reads skill/supervisor/SKILL.md for loop detection patterns     │
│ - Prepares inlined content:                                        │
│   • NMR background (skill/SKILL.md Section 1)                     │
│   • CASE workflow (skill/CASE/SKILL.md)                           │
│   • LSD command syntax (skill/diagnostic/SKILL.md Section 1)      │
│   • CASE-PROGRESS.md format (skill/supervisor/SKILL.md Section 7) │
│ - Prepares file path references for detailed domain knowledge     │
│ - Provides compound context (path, formula, experiments)          │
└──────────────┬───────────────────────────────────────────────────┘
               │
               │ Task(instructions=<inlined content + file paths + compound context>)
               ▼
┌──────────────────────────────────────────────────────────────────┐
│ ~/.claude/agents/lucy-case-agent.md                               │
│ (autonomous CASE worker)                                           │
│ - Receives inlined skill content in Task() instructions           │
│ - Reads detailed reference via file paths (skill/SKILL.md full)   │
│ - Reads compound spectra via: lucy read 1d/2d, lucy pick ...      │
│ - Applies domain intelligence from skill content                  │
│ - Writes LSD files directly using LSD command knowledge           │
│ - Runs LSD: lucy lsd run <file>.lsd --format json                 │
│ - Ranks solutions: lucy lsd rank <solutions>.smi --spectrum ...   │
│ - Writes CASE-PROGRESS.md after each LSD iteration                │
└──────────────┬───────────────────────────────────────────────────┘
               │
               │ CASE-PROGRESS.md written (append-only)
               │ Contains: iteration N, solution count, constraints added/removed,
               │ effectiveness, confidence, sp2/H budget checks
               │
               ▼
┌──────────────────────────────────────────────────────────────────┐
│ case.md reads CASE-PROGRESS.md                                    │
│ Parses iterations to detect loop patterns:                        │
│ - ELIM thrashing (ELIM added 2+ times without diagnosis)          │
│ - Zero-solution loop (3+ consecutive 0 solutions)                 │
│ - Solution explosion (3+ iterations >100 solutions, <10% reduction)│
│ - Constraint churning (5+ iterations high add/remove, no converge)│
└──────────────┬───────────────────────────────────────────────────┘
               │
               ├─ NO LOOP DETECTED → Allow CASE agent to continue
               │
               └─ LOOP DETECTED → Diagnose root cause
                                   │
                                   ├─ Basic diagnosis sufficient?
                                   │  YES → Formulate advisory constraints
                                   │        Re-spawn CASE agent with advice
                                   │        Increment intervention_counts[pattern]
                                   │        If counts[pattern] >= 10: escalate to user
                                   │
                                   └─ Need deep LSD analysis?
                                      (After 2+ failed interventions with same pattern)
                                      │
                                      ▼
                  ┌───────────────────────────────────────────────────────┐
                  │ Task(agent_type="lucy-diagnostic")                     │
                  │ - Pass: compound path, LSD file, failure type          │
                  │ - Provide file path: skill/diagnostic/SKILL.md         │
                  │ - Diagnostic runs systematic checks:                   │
                  │   • sp2 count (must be even)                           │
                  │   • H budget (must match formula)                      │
                  │   • 1J artifacts (HMBC vs HSQC position check)         │
                  │   • Correlation order (HSQC before HMBC)               │
                  │   • Close carbon ambiguity (digital resolution)        │
                  │ - Identifies root cause with quantitative evidence     │
                  │ - Writes DIAGNOSTIC-REPORT.md                          │
                  └───────────────┬───────────────────────────────────────┘
                                  │
                                  │ DIAGNOSTIC-REPORT.md written
                                  │ Contains: findings, root cause, recommended fixes
                                  │ (with LSD command examples), confidence ratings
                                  │
                                  ▼
                  ┌───────────────────────────────────────────────────────┐
                  │ case.md reads DIAGNOSTIC-REPORT.md                     │
                  │ Extracts:                                              │
                  │ - Root cause (primary + contributing factors)          │
                  │ - Primary fix (specific LSD commands + verification)   │
                  │ Formulates diagnostic-informed advisory:               │
                  │ - Reference report for full analysis                   │
                  │ - Include specific fix action with commands            │
                  │ - Include verification steps                           │
                  │ Re-spawns CASE agent with diagnostic-informed advice   │
                  └───────────────────────────────────────────────────────┘
```

### Flow 3: AI-Driven Sanitization

```
User invokes: /lucy-ng:sanitise <dataset_path>

┌──────────────────────────────────────────────────────────────────┐
│ ~/.claude/commands/lucy-ng/sanitise.md                            │
│ (AI-driven skill, no CLI equivalent)                              │
│ - Reads skill/sanitize/SKILL.md for patterns                      │
│ - Reads dataset metadata files (nmr_parameters.json, etc.)        │
│ - Applies pattern matching:                                       │
│   • Compound names (e.g., "Ibuprofen", "Caffeine")               │
│   • SMILES strings (alphanumeric with brackets, @ signs)          │
│   • InChI strings ("InChI=...")                                   │
│   • Database IDs ("COCONUT_123456")                               │
│ - Redacts/removes identified content                              │
│ - Writes SANITIZATION-REPORT.md (redaction summary)               │
│ - Reports to user                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## Integration Points with Existing Components

### 1. Skill Documents (skill/*)

**Current state (v2.0):**
- skill/SKILL.md (1,079 lines) — core NMR/CASE knowledge
- skill/supervisor/SKILL.md (827 lines) — loop detection, intervention
- skill/diagnostic/SKILL.md (1,874 lines) — LSD manual, diagnostics
- skill/CASE/SKILL.md (~300 lines) — CASE workflow
- skill/dereplicate/SKILL.md, skill/sanitize/SKILL.md — specialized

**Integration approach for v2.1:**
- **NO restructuring needed** — existing hierarchy already supports sub-command pattern
- Sub-command skills REFERENCE these documents (file paths or inlined content)
- Agent definitions receive critical sections inlined in Task() instructions

**Inlining strategy (for case.md → lucy-case-agent):**

```python
# Conceptual structure (case.md orchestrator)

inlined_content = f"""
=== NMR Background (skill/SKILL.md Section 1) ===
{read_section('skill/SKILL.md', section=1, subsections=['Experiment Types', '13C Shift Regions', 'Common Pitfalls'])}

=== CASE Workflow (skill/CASE/SKILL.md) ===
{read_file('skill/CASE/SKILL.md')}  # ~300 lines, full inline

=== LSD Command Syntax (skill/diagnostic/SKILL.md Section 1 excerpt) ===
{read_section('skill/diagnostic/SKILL.md', section=1, commands=['MULT', 'HSQC', 'HMBC', 'BOND', 'LIST'])}

=== CASE-PROGRESS.md Format (skill/supervisor/SKILL.md Section 7) ===
{read_section('skill/supervisor/SKILL.md', section=7)}
"""

file_path_references = f"""
For detailed domain knowledge, read:
- {project_path}/skill/SKILL.md (Sections 2-11: peak picking, symmetry, HMBC strategy, ranking, confidence)
- {project_path}/skill/diagnostic/SKILL.md (full LSD manual with all commands)
"""

compound_context = f"""
Compound path: {compound_path}
Formula: {formula}
Available experiments: {auto_detected_experiments}
"""

Task(
  instructions=f"{inlined_content}\n\n{file_path_references}\n\n{compound_context}\n\nPerform CASE workflow. Write CASE-PROGRESS.md after EVERY LSD iteration."
)
```

**Rationale:**
- Critical workflow content (~500-700 lines) inlined for immediate access
- Detailed reference material (peak picking strategies, full LSD manual) via file paths
- Agent can Read tool to access full documents when needed
- Balances context window limits with completeness

### 2. Agent Definitions (.claude/agents/)

**Current state (v2.0):**
- supervisor.md (484 lines) — monolithic supervisor, spawns CASE agent generically
- diagnostic-specialist.md (455 lines) — LSD diagnostics

**Changes needed for v2.1:**

| File | Action | Rationale |
|------|--------|-----------|
| supervisor.md | **DELETE** | Supervisor logic dissolves into case.md orchestrator skill |
| diagnostic-specialist.md | **RENAME** to lucy-diagnostic.md, **UPDATE** frontmatter | Keep logic, update to be spawned by case.md (change agent_type reference) |
| lucy-case-agent.md | **CREATE** | New autonomous CASE worker definition |

**New agent frontmatter:**

```yaml
# ~/.claude/agents/lucy-case-agent.md
---
name: lucy-case-agent
description: >
  Autonomous CASE worker. Performs complete structure elucidation workflow:
  peak picking, symmetry analysis, LSD file writing, solving, ranking.
  Writes CASE-PROGRESS.md after each LSD iteration for orchestrator monitoring.
tools:
  - Read
  - Write
  - Bash
  - Glob
  - Grep
model: sonnet
---
```

```yaml
# ~/.claude/agents/lucy-diagnostic.md (updated from diagnostic-specialist.md)
---
name: lucy-diagnostic
description: >
  LSD failure diagnostic specialist. Systematic root cause analysis for
  zero-solution and solution-explosion failures. Produces structured
  diagnostic reports with findings, root cause, and recommended fixes.
tools:
  - Read
  - Bash
model: sonnet
---
```

**Key difference from v2.0:**
- v2.0: supervisor.md was a separate agent that spawned CASE agent
- v2.1: case.md skill IS the orchestrator (reads supervisor/SKILL.md for rules), spawns lucy-case-agent
- Supervisor logic is now in the skill, not a separate agent definition

### 3. CLAUDE.md (Project Instructions)

**Current state (v2.0):**
- 305 lines, CLI-only reference
- No MCP content (removed in Phase 26)
- Thin CLI command syntax and output formats
- References skill/SKILL.md for domain knowledge

**Changes needed for v2.1:**
- **Add section:** "Sub-Command Skills" with table of `/lucy-ng:*` commands
- **Update:** Entry point is now `/lucy-ng:case` for CASE workflows (not direct supervisor invocation)
- **NO other changes** — CLAUDE.md remains project-level CLI reference

**New section to add:**

```markdown
## Sub-Command Skills

lucy-ng provides specialized sub-commands for different workflows:

| Command | Purpose | Agent Spawning |
|---------|---------|----------------|
| /lucy-ng:case | Full CASE orchestration | Spawns lucy-case-agent, monitors progress, spawns lucy-diagnostic if needed |
| /lucy-ng:sanitise | AI-driven dataset sanitization | Direct execution (no agent spawning) |
| /lucy-ng:dereplicate | Database matching only | Direct CLI execution |
| /lucy-ng:predict | 13C shift prediction only | Direct CLI execution |
| /lucy-ng:status | System status checks | Direct CLI execution |

For CASE workflow: Use `/lucy-ng:case <compound_path> <formula>`. The orchestrator handles agent spawning, progress monitoring, loop detection, and intervention automatically.
```

### 4. CLI Commands (src/lucy_ng/cli/)

**Current state (v2.0 Phase 26):**
- 9 command groups, 22 commands
- All commands are thin data-access wrappers
- No embedded intelligence (DEPT-guided picking removed, HMBC cross-validation removed, LSD generator removed)
- Validated on Ibuprofen CASE (Phase 26-05)

**Changes needed for v2.1:**
- **NONE** — CLI is complete and thin as required
- v2.1 focuses on orchestration layer (skills + agents), not tool layer

**Architecture validation:**
- Phase 26-05 proved thin CLI + skill knowledge works (Ibuprofen correctly identified top-3)
- v2.1 builds on this validated foundation

### 5. Codebase Structure

**Current state (v2.0):**
```
src/lucy_ng/
├── models/          # Pydantic v2 data models (Spectrum1D, Spectrum2D, Peak1D, etc.)
├── readers/         # NMR file readers (BrukerReader)
├── processing/      # Peak picking, signal processing (thin, no DEPT guidance)
├── dereplication/   # Database matching (SpectrumMatcher, formula-indexed)
├── prediction/      # HOSE-based 13C prediction (C13Predictor)
├── solvers/         # LSD runner, solution parsing
├── database/        # SQLite schema, query API, DatabaseFinder
└── cli/             # Click CLI (thin wrappers, 9 groups, 22 commands)
```

**Changes needed for v2.1:**
- **NONE** — Code structure is stable post-Phase 26

**Integration stability:**
- Python codebase is mature (17,500 lines, 642 tests)
- All tests pass (verified in Phase 26)
- v2.1 is purely additive (orchestration layer on top)

---

## New Components Needed

### 1. Sub-Command Skills (5 files)

| File | Lines (Est.) | Content | Dependencies |
|------|--------------|---------|--------------|
| ~/.claude/commands/lucy-ng/case.md | ~400 | CASE orchestration: agent spawning with inlined content, progress monitoring (read CASE-PROGRESS.md), loop detection (4 patterns), basic diagnosis, intervention logic, diagnostic specialist spawning (after 2 failed interventions), escalation (after 10 cycles per pattern) | skill/SKILL.md, skill/CASE/SKILL.md, skill/supervisor/SKILL.md, skill/diagnostic/SKILL.md |
| ~/.claude/commands/lucy-ng/sanitise.md | ~200 | AI-driven sanitization: pattern matching for compound identifiers (names, SMILES, InChI, IDs), redaction logic, SANITIZATION-REPORT.md writing | skill/sanitize/SKILL.md |
| ~/.claude/commands/lucy-ng/dereplicate.md | ~100 | Thin wrapper: CLI execution (`lucy dereplicate c13 <path> <formula>`), JSON parsing, score interpretation (>= 0.95 match, 0.85-0.95 possible, < 0.65 no match), user reporting | skill/dereplicate/SKILL.md |
| ~/.claude/commands/lucy-ng/predict.md | ~80 | Thin wrapper: CLI execution (`lucy predict c13 <smiles>`), JSON parsing, result interpretation (MAE, prediction quality), user reporting | skill/SKILL.md Section 8 (ranking/prediction) |
| ~/.claude/commands/lucy-ng/status.md | ~60 | System checks: `lucy --version`, `lucy lsd check`, `lucy database info`, report availability, suggest setup steps if missing | CLAUDE.md (setup instructions) |

**Total:** ~840 lines of new orchestration logic

**Critical file:** case.md (~400 lines) is the most complex, containing loop detection, diagnostic delegation, and intervention tracking.

### 2. Agent Definition (1 new file)

| File | Lines (Est.) | Content | Dependencies |
|------|--------------|---------|--------------|
| ~/.claude/agents/lucy-case-agent.md | ~600 | Autonomous CASE worker: frontmatter (name, description, tools, model), instructions (receive inlined skill content in Task(), read reference files, perform CASE workflow, write CASE-PROGRESS.md checkpoints), workflow guidance (peak picking → symmetry → LSD writing → solving → ranking), error handling, convergence criteria | Inlined from skill/SKILL.md + skill/CASE/SKILL.md in Task() instructions |

**Note:** lucy-diagnostic.md already exists as diagnostic-specialist.md (455 lines). Rename and update frontmatter (~50 line change, primarily changing `agent_type` reference and description).

### 3. Progress File Formats (Already Specified in v2.0)

| File | Written By | Read By | Format Spec Location |
|------|-----------|---------|---------------------|
| CASE-PROGRESS.md | lucy-case-agent | case.md orchestrator | skill/supervisor/SKILL.md Section 7 |
| DIAGNOSTIC-REPORT.md | lucy-diagnostic | case.md orchestrator | skill/diagnostic/SKILL.md Section 3 |
| SANITIZATION-REPORT.md | sanitise.md skill | User (documentation) | skill/sanitize/SKILL.md (to be created in v2.1) |

**No new format design needed** — CASE-PROGRESS.md and DIAGNOSTIC-REPORT.md formats already fully specified in v2.0 Phases 24-25.

---

## Context Management Strategy

### Problem: Skill Content Size

| Document | Lines | Full Inline Feasible? |
|----------|-------|-----------------------|
| skill/SKILL.md | 1,079 | NO — too large |
| skill/CASE/SKILL.md | ~300 | YES — workflow is critical |
| skill/supervisor/SKILL.md | 827 | NO — but case.md reads it directly (not passed to agent) |
| skill/diagnostic/SKILL.md | 1,874 | NO — but diagnostic agent reads via file path |

### Solution: Hybrid Inlining Strategy

**For CASE agent spawning (case.md → lucy-case-agent):**

**Inline (~500-700 lines):**
1. **NMR background** (skill/SKILL.md Section 1): Experiment types, 13C shift regions, common pitfalls (~150 lines)
2. **CASE workflow** (skill/CASE/SKILL.md): Full step-by-step procedure (~300 lines)
3. **LSD command syntax** (skill/diagnostic/SKILL.md Section 1 excerpt): MULT, HSQC, HMBC, BOND, LIST syntax (~100 lines)
4. **CASE-PROGRESS.md format** (skill/supervisor/SKILL.md Section 7): Template with required fields, example (~50 lines)

**Provide file paths for reference:**
- {project_path}/skill/SKILL.md — for detailed domain knowledge (Sections 2-11: peak picking, symmetry, HMBC strategy, ranking, confidence)
- {project_path}/skill/diagnostic/SKILL.md — for full LSD manual if needed during LSD writing

**Provide compound context:**
- Compound path: {compound_path}
- Formula: {formula}
- Available experiments: [auto-detected list from `lucy read`]

**For diagnostic agent spawning (case.md → lucy-diagnostic):**

**Inline (~100 lines):**
1. **Failure context**: Failure type (0 solutions, 1000+ solutions), latest iteration summary from CASE-PROGRESS.md
2. **Diagnostic task**: Instructions for systematic checks, report writing

**Provide file paths:**
- {compound_path}/CASE-PROGRESS.md — iteration history
- {compound_path}/{lsd_file} — LSD file to diagnose
- {project_path}/skill/diagnostic/SKILL.md — full LSD manual and diagnostic procedures

**Rationale:**
- Task() instructions have practical size limits (~2000 lines max for readability)
- Critical workflow content must be inlined (agent can't assume project context loaded)
- Detailed reference material can be read by agent via Read tool (agents have Read in their tool list)
- Absolute file paths resolve context ambiguity

### Agent Context Loading Pattern (Pseudocode)

```python
# In case.md orchestrator skill

def spawn_case_agent(compound_path, formula):
    # 1. Prepare inlined content (critical workflow)
    inlined_content = (
        "=== NMR Background ===\n"
        + read_section('skill/SKILL.md', section=1)
        + "\n\n=== CASE Workflow ===\n"
        + read_file('skill/CASE/SKILL.md')
        + "\n\n=== LSD Command Syntax ===\n"
        + read_section('skill/diagnostic/SKILL.md', section=1, excerpt=True)
        + "\n\n=== CASE-PROGRESS.md Format ===\n"
        + read_section('skill/supervisor/SKILL.md', section=7)
    )

    # 2. Prepare reference paths
    project_path = os.getcwd()
    references = f"""
For detailed domain knowledge, read:
- {project_path}/skill/SKILL.md (Sections 2-11)
- {project_path}/skill/diagnostic/SKILL.md (full LSD manual)
"""

    # 3. Prepare compound context
    experiments = auto_detect_experiments(compound_path)
    compound_context = f"""
Compound path: {compound_path}
Formula: {formula}
Available experiments: {experiments}
"""

    # 4. Spawn agent
    Task(
        instructions=(
            f"{inlined_content}\n\n"
            f"{references}\n\n"
            f"{compound_context}\n\n"
            "Perform CASE workflow. Write CASE-PROGRESS.md after EVERY LSD iteration. Stop when solution count <= 10 or after ~20 iterations."
        )
    )
```

---

## Inter-Agent Communication

### CASE-PROGRESS.md (CASE Agent → Orchestrator)

**Purpose:** Enable orchestrator to monitor progress and detect loop patterns

**Format:** Append-only markdown with structured sections (human-readable, AI-parseable)

**Location:** {compound_path}/CASE-PROGRESS.md

**Written by:** lucy-case-agent after EVERY LSD iteration

**Read by:** case.md orchestrator

**Required fields per iteration:**
- Iteration N: brief description
- Time: timestamp
- LSD file: filename
- Solution count: number
- Constraints added: list with reasoning
- Constraints removed: list with reasoning (or "None")
- Why: natural language explanation of strategy
- Constraint effectiveness: % reduction or "baseline" or "over-constrained"
- Confidence: qualitative assessment (too many solutions / converging / stuck)
- HMBC correlations used: X/Y (running total)
- Notes: sp2 count (even/odd), H budget (matches/mismatch), observations

**Format specification:** skill/supervisor/SKILL.md Section 7 (complete with 3-iteration example)

**Example iteration:**
```markdown
## Iteration 3: Add quaternary carbon HMBC batch

**Time:** 2026-02-08 10:45:23
**LSD file:** ibuprofen-03.lsd
**Solution count:** 47

**Constraints added:**
- HMBC 1 8 (C172.4 to H7.2, quaternary carboxyl)
- HMBC 5 4 (C138.8 to H1.2, quaternary aromatic)
- HMBC 9 3 (C155.2 to H2.1, quaternary aromatic)

**Constraints removed:** None

**Why:** Target quaternary carbons to reduce solution space. Selected high-confidence correlations with unique proton assignments and strong intensities.

**Constraint effectiveness:** 96% reduction (1234 → 47 solutions)
**Confidence:** Converging, expect single-digit solutions after next batch
**HMBC correlations used:** 12/47

**Notes:**
- sp2 count: 8 (even) ✓
- H budget: 18 matches formula ✓
- All quaternary carbons now have at least 1 HMBC
```

### DIAGNOSTIC-REPORT.md (Diagnostic Agent → Orchestrator)

**Purpose:** Provide deep LSD failure analysis with root cause and fixes

**Format:** Structured markdown with sections (findings, root cause, fixes)

**Location:** {compound_path}/DIAGNOSTIC-REPORT.md

**Written by:** lucy-diagnostic agent when spawned for complex failures

**Read by:** case.md orchestrator (extracts root cause and primary fix)

**Required sections:**
1. **Summary** (executive overview, root cause one-liner, confidence)
2. **Findings** (2-5 findings with evidence, impact, confidence)
3. **Root Cause** (primary + contributing factors, mechanism explanation)
4. **Recommended Fixes** (1-3 fixes with LSD command examples, verification, priority, confidence)
5. **Supporting Data** (LSD file stats, iteration history, spectral quality)
6. **Next Steps** (immediate action, verification, follow-up)
7. **Diagnostic Methodology** (all systematic checks with PASS/FAIL)
8. **Metadata** (confidence breakdown)

**Format specification:** skill/diagnostic/SKILL.md Section 3 (complete template with examples)

**Orchestrator extraction pattern:**
```python
# In case.md orchestrator

def extract_diagnostic_guidance(report_path):
    report = read_file(report_path)

    # Extract root cause section
    root_cause = extract_section(report, "## Root Cause")

    # Extract primary fix
    fixes_section = extract_section(report, "## Recommended Fixes")
    primary_fix = [f for f in parse_fixes(fixes_section) if "PRIMARY" in f][0]

    # Format advisory for CASE agent
    advisory = f"""
DIAGNOSTIC GUIDANCE:

{root_cause}

{primary_fix}

See {report_path} for full analysis.
"""

    return advisory
```

### SANITIZATION-REPORT.md (Sanitize Skill → User)

**Purpose:** Document all redactions for dataset sanitization

**Format:** Structured markdown with redaction summary

**Location:** {dataset_path}/SANITIZATION-REPORT.md

**Written by:** sanitise.md skill

**Read by:** User (for documentation and validation)

**Required sections:**
1. **Summary** (files processed, identifiers removed, changes made)
2. **Redactions** (list of all redacted content with file:line references)
3. **Verification** (steps to confirm sanitization complete)

**Format specification:** skill/sanitize/SKILL.md (to be created in v2.1)

---

## Patterns to Follow

### Pattern 1: Orchestrator Skill with Agent Spawning (CASE)

**When:** Complex multi-iteration workflows requiring monitoring and intervention

**Structure:**
1. Validate inputs (compound path, formula)
2. Inline critical skill content (NMR background, CASE workflow, LSD basics, CASE-PROGRESS.md format)
3. Spawn CASE agent via Task() with inlined content + file path references + compound context
4. Monitor progress by reading CASE-PROGRESS.md after agent returns
5. Detect loop patterns using criteria from skill/supervisor/SKILL.md Section 4:
   - ELIM thrashing: ELIM added 2+ times without diagnosis
   - Zero-solution loop: 3+ consecutive iterations with 0 solutions
   - Solution explosion: 3+ iterations >100 solutions, <10% reduction each
   - Constraint churning: 5+ iterations high add/remove, no convergence
6. Diagnose root cause using pattern-specific procedure
7. If basic diagnosis insufficient (2+ failed interventions with same pattern):
   - Spawn diagnostic specialist via Task(agent_type="lucy-diagnostic")
   - Read DIAGNOSTIC-REPORT.md
   - Extract root cause and primary fix
8. Re-spawn CASE agent with advisory constraints (WHAT to fix, not HOW)
9. Track intervention_counts[pattern] separately for each pattern
10. Escalate to user after 10 failed interventions with same pattern

**Example:**
```markdown
# ~/.claude/commands/lucy-ng/case.md

## Orchestration Logic

When loop detected:
1. Read CASE-PROGRESS.md
2. Identify pattern (ELIM thrashing, zero-solution, explosion, churning)
3. Run basic diagnosis:
   - Check sp2 count (must be even)
   - Check H budget (must match formula)
   - Check for obvious issues (1J artifacts, close carbons)
4. If intervention_counts[pattern] >= 2:
   - Spawn diagnostic specialist
   - Wait for DIAGNOSTIC-REPORT.md
   - Extract root cause and fix
5. Formulate advisory:
   - WHAT is wrong (sp2 count odd, 1J artifact detected, etc.)
   - WHAT to check/fix (verify sp2, remove correlation, etc.)
   - NOT HOW to edit files (CASE agent decides)
6. Re-spawn CASE agent with advisory in instructions
7. Increment intervention_counts[pattern]
8. If intervention_counts[pattern] >= 10: escalate to user
```

### Pattern 2: Thin Wrapper Skill (Dereplicate, Predict)

**When:** Simple single-step operations with CLI tools

**Structure:**
1. Validate inputs
2. Execute CLI command: `lucy <command> <args> --format json`
3. Parse JSON result
4. Interpret using skill knowledge (score thresholds, result quality)
5. Report to user

**Example:**
```markdown
# ~/.claude/commands/lucy-ng/dereplicate.md

1. Validate: compound_path exists, formula is valid
2. Execute: `lucy dereplicate c13 {compound_path} {formula} --format json`
3. Parse JSON: {is_match, top_matches: [{name, smiles, score}, ...]}
4. Interpret (from skill/dereplicate/SKILL.md):
   - score >= 0.95: Match (report top hit, DONE)
   - score 0.85-0.95: Possible match (report, ask user)
   - score 0.65-0.85: Weak match (report, recommend CASE)
   - score < 0.65: No match (recommend CASE)
5. Report results to user
```

### Pattern 3: AI-Driven Skill (Sanitize)

**When:** Tasks requiring AI pattern recognition, no CLI tool exists

**Structure:**
1. Validate input (dataset path)
2. Read dataset files (metadata, NMR parameters, README, etc.)
3. Apply patterns from skill document (compound names, SMILES, InChI, IDs)
4. Identify all instances of compound identifiers
5. Redact/remove identified content
6. Write SANITIZATION-REPORT.md with summary
7. Report to user

**Example:**
```markdown
# ~/.claude/commands/lucy-ng/sanitise.md

1. Read skill/sanitize/SKILL.md for patterns
2. Scan dataset for files: *.json, *.md, *.txt
3. For each file, detect:
   - Compound names (capitalized chemistry terms, matched against known list)
   - SMILES (pattern: alphanumeric with brackets, parentheses, @, =, #)
   - InChI (pattern: "InChI=...")
   - Database IDs (pattern: "COCONUT_", "NPC", "CNP", followed by numbers)
4. For each detected identifier:
   - Record in redaction list (file, line, original text)
   - Replace/remove (compound name → "Unknown Compound", SMILES/InChI → delete field)
5. Write SANITIZATION-REPORT.md
6. Report summary to user
```

### Pattern 4: Progress File Monitoring (Loop Detection)

**When:** Orchestrator needs to detect patterns in agent behavior

**Implementation:**
```python
# In case.md orchestrator

def detect_loops(progress_file):
    iterations = parse_iterations(progress_file)

    # ELIM thrashing: ELIM added 2+ times
    if count_constraint_additions(iterations, "ELIM") >= 2:
        return "elim_thrashing"

    # Zero-solution loop: 3+ consecutive 0 solutions
    if all(i.solution_count == 0 for i in iterations[-3:]):
        return "zero_solution_loop"

    # Solution explosion: 3+ iterations >100, <10% reduction
    if len(iterations) >= 3:
        recent = iterations[-3:]
        if all(i.solution_count > 100 for i in recent):
            reductions = [
                (recent[j-1].solution_count - recent[j].solution_count) / recent[j-1].solution_count
                for j in range(1, 3)
            ]
            if all(r < 0.10 for r in reductions):
                return "solution_explosion"

    # Constraint churning: 5+ iterations, high add/remove, no convergence
    if len(iterations) >= 5:
        recent = iterations[-5:]
        if all(len(i.constraints_added) > 10 and len(i.constraints_removed) > 5 for i in recent):
            if recent[0].solution_count - recent[-1].solution_count < 10:
                return "constraint_churning"

    return None  # No loop detected
```

**Full detection criteria:** skill/supervisor/SKILL.md Section 4

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Duplicating Skill Content

**Wrong:** Copy entire skill documents into agent definitions

**Right:** Agent definitions reference skill documents; orchestrator inlines critical sections in Task() instructions

**Why:** Single source of truth prevents sync issues

### Anti-Pattern 2: Embedding Intelligence in CLI

**Wrong:** Add domain logic to Python CLI commands

**Right:** CLI returns raw data, agents apply intelligence from skills

**Why:** v2.0 Phase 26 established thin CLI architecture, don't regress

### Anti-Pattern 3: Global Intervention Counters

**Wrong:** Track total interventions across all patterns

**Right:** Track interventions per pattern separately

**Why:** Different patterns have different root causes, need targeted tracking

### Anti-Pattern 4: Directive Interventions

**Wrong:** Tell CASE agent exactly which file line to edit

**Right:** Tell CASE agent WHAT problem exists and WHAT needs checking

**Why:** CASE agent retains autonomy, supervisor provides constraints not commands

### Anti-Pattern 5: Spawning Diagnostic Specialist Too Early

**Wrong:** Spawn specialist on first loop detection

**Right:** Basic diagnosis first (1-2 interventions), specialist only if that fails

**Why:** Basic diagnosis often sufficient, specialist is for complex failures

---

## Build Order and Dependencies

### Phase Structure Recommendation

**v2.1 Milestone: Working Multi-Agent CASE**

**Phase 27: Sub-Command Skills Foundation** (3-4 hours)
- Create ~/.claude/commands/lucy-ng/ directory
- Implement simple skills: status.md, predict.md, dereplicate.md
- Test each skill executes CLI and reports correctly
- **Dependencies:** None (uses existing v2.0 CLI)
- **Validation:** `status.md` reports system state, `dereplicate.md` on test compound returns results

**Phase 28: CASE Agent Definition** (4-5 hours)
- Create ~/.claude/agents/lucy-case-agent.md
- Define frontmatter (name, description, tools, model)
- Write agent instructions (workflow overview, checkpoint writing)
- Test agent can be spawned with Task() and receives instructions
- **Dependencies:** Phase 27 (directory structure exists)
- **Validation:** Spawn agent with test instructions, verify it executes and writes CASE-PROGRESS.md

**Phase 29: CASE Orchestrator Skill** (6-8 hours)
- Create ~/.claude/commands/lucy-ng/case.md
- Implement agent spawning with inlined skill content (NMR background, CASE workflow, LSD basics, CASE-PROGRESS.md format)
- Implement progress monitoring (read CASE-PROGRESS.md after agent returns)
- Implement loop detection (4 patterns from skill/supervisor/SKILL.md Section 4)
- Implement basic diagnosis and advisory intervention
- Test spawn → monitor → detect loop → intervene workflow
- **Dependencies:** Phase 27 (directory), Phase 28 (agent exists)
- **Validation:** Run on test compound, verify loop detection triggers, advisory sent to agent

**Phase 30: Diagnostic Specialist Integration** (3-4 hours)
- Rename .claude/agents/diagnostic-specialist.md → lucy-diagnostic.md
- Update frontmatter (name, agent_type reference)
- Integrate diagnostic spawning in case.md (after 2 failed interventions with same pattern)
- Implement DIAGNOSTIC-REPORT.md reading and primary fix extraction
- Test loop → basic diagnosis fails → spawn specialist → read report → re-advise CASE agent
- **Dependencies:** Phase 29 (orchestrator exists)
- **Validation:** Force repeated failures with same pattern, verify specialist spawned, report generated

**Phase 31: Sanitization Skill** (2-3 hours)
- Create ~/.claude/commands/lucy-ng/sanitise.md
- Create skill/sanitize/SKILL.md (pattern definitions)
- Implement AI-driven pattern matching (compound names, SMILES, InChI, IDs)
- Implement redaction logic
- Write SANITIZATION-REPORT.md
- Test on dataset with known identifiers (e.g., Virgiline)
- **Dependencies:** Phase 27 (directory structure)
- **Validation:** Sanitize test dataset, verify compound name removed, report lists redactions

**Phase 32: End-to-End Validation** (2-3 hours)
- Test `/lucy-ng:case` on Ibuprofen de novo CASE (known working from Phase 26-05)
- Test `/lucy-ng:case` on Virgiline (known failure — should trigger diagnostics)
- Test `/lucy-ng:sanitise` on public dataset
- Test `/lucy-ng:dereplicate`, `/lucy-ng:predict`, `/lucy-ng:status`
- Update CLAUDE.md with sub-command reference section
- **Dependencies:** Phases 27-31 (all skills implemented)
- **Validation:** Ibuprofen top-3 ranked, Virgiline triggers diagnostic specialist, all simple skills work

**Phase 33: Documentation and Cleanup** (1-2 hours)
- Delete .claude/agents/supervisor.md (logic now in case.md)
- Update PROJECT.md decisions table (v2.1 architecture choices)
- Update STATE.md with v2.1 milestone completion
- Write v2.1 release notes
- **Dependencies:** Phase 32 (validation complete)
- **Validation:** Old supervisor.md deleted, documentation updated, no loose ends

### Dependency Graph

```
Phase 27 (Skills Foundation)
    ↓
    ├─→ Phase 28 (CASE Agent)
    │       ↓
    │   Phase 29 (CASE Orchestrator)
    │       ↓
    │   Phase 30 (Diagnostic Integration)
    │
    └─→ Phase 31 (Sanitization)

Phase 29, 30, 31 → Phase 32 (Validation) → Phase 33 (Cleanup)
```

### Critical Path

**Phases 27 → 28 → 29 → 30 → 32 → 33** (16-20 hours total)

Core CASE orchestration with diagnostics is the critical functionality.

**Phase 31 (Sanitization) can be parallelized** if multiple people are working on v2.1.

### Risk Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Task() context size limits | Medium | High | Hybrid inlining: ~500-700 lines inlined, rest via file paths |
| Agent doesn't write CASE-PROGRESS.md | Medium | High | Explicit instructions in inlined content, format template included, verification in Phase 32 |
| Loop detection too sensitive (false positives) | Low | Medium | Conservative thresholds (3+ iterations for zero-solution, 5+ for churning) |
| Loop detection too lenient (misses loops) | Low | Medium | Test on known failure cases (Virgiline) in Phase 32 |
| Diagnostic specialist spawning loops | Low | High | Track specialist spawning separately, escalate if called 3+ times without progress |
| Virgiline still fails after v2.1 | Medium | Low | Expected on first attempt — refine diagnostic procedures iteratively |
| Intervention count tracking bugs | Medium | Medium | Per-pattern tracking, clear increment/escalation logic, test in Phase 30 |

---

## Success Criteria

v2.1 Working Multi-Agent CASE is complete when:

**Infrastructure:**
- [ ] All 5 sub-command skills exist in ~/.claude/commands/lucy-ng/
- [ ] lucy-case-agent.md exists in ~/.claude/agents/
- [ ] lucy-diagnostic.md exists (renamed from diagnostic-specialist.md) in ~/.claude/agents/
- [ ] supervisor.md deleted (logic dissolved into case.md)

**Functionality:**
- [ ] `/lucy-ng:case` on Ibuprofen produces correct top-3 ranked solution (reproduces Phase 26-05 success)
- [ ] `/lucy-ng:case` on a failing compound triggers loop detection (verify on constructed test case)
- [ ] Loop detection correctly identifies all 4 patterns (ELIM thrashing, zero-solution, explosion, churning)
- [ ] After 2 failed interventions with same pattern, diagnostic specialist spawned
- [ ] CASE-PROGRESS.md written by CASE agent after each iteration with all required fields
- [ ] DIAGNOSTIC-REPORT.md written by diagnostic specialist with findings, root cause, fixes
- [ ] Orchestrator reads progress files and extracts information correctly
- [ ] Intervention tracking is per-pattern (not global), escalates after 10 cycles per pattern
- [ ] `/lucy-ng:sanitise` removes compound identifiers from test dataset
- [ ] `/lucy-ng:dereplicate`, `/lucy-ng:predict`, `/lucy-ng:status` execute CLI and report correctly

**Documentation:**
- [ ] CLAUDE.md updated with sub-command reference section
- [ ] PROJECT.md decisions table updated with v2.1 architecture
- [ ] STATE.md shows v2.1 milestone complete

**Regression:**
- [ ] All existing tests pass (no regression from v2.0)
- [ ] CLI commands still work standalone (backward compatibility)

---

## Integration Points Summary

| Component | Status | Changes Needed |
|-----------|--------|----------------|
| skill/*.md documents | Complete (v2.0) | None — reference as-is |
| src/lucy_ng/cli/*.py | Complete (v2.0 Phase 26) | None — thin CLI validated |
| CLAUDE.md | Needs minor update | Add sub-command section (~20 lines) |
| .claude/agents/supervisor.md | Delete | Logic moves to case.md orchestrator |
| .claude/agents/diagnostic-specialist.md | Rename/rework | → lucy-diagnostic.md (~50 line change) |
| .claude/agents/lucy-case-agent.md | Create new | Autonomous CASE worker (~600 lines) |
| ~/.claude/commands/lucy-ng/*.md | Create 5 new | Orchestrator skills (~840 lines total) |

**Total new code:** ~1,440 lines (skills + agent)
**Total modifications:** ~70 lines (CLAUDE.md update, diagnostic frontmatter)
**Total deletions:** ~484 lines (supervisor.md)
**Net addition:** ~1,000 lines of orchestration logic

---

## Sources

**Existing Architecture (v2.0):**
- .claude/agents/supervisor.md (484 lines) — Current supervisor approach
- .claude/agents/diagnostic-specialist.md (455 lines) — Diagnostic logic
- skill/SKILL.md (1,079 lines) — Core domain knowledge
- skill/supervisor/SKILL.md (827 lines) — Loop detection patterns
- skill/diagnostic/SKILL.md (1,874 lines) — LSD manual
- Phase 26 validation: .planning/phases/26-thin-tools/26-05-PLAN.md (Ibuprofen CASE success)

**GSD Pattern:**
- ~/.claude/commands/gsd/new-project.md — Sub-command structure reference

**Project Context:**
- .planning/PROJECT.md — v2.1 architecture decisions
- .planning/STATE.md — Current milestone status
- .planning/phases/26-thin-tools/26-CONTEXT.md — Thin CLI architecture rationale

**Confidence:** HIGH
- v2.0 provides complete foundation (thin CLI validated, skill documents complete)
- GSD pattern well-understood (existing /gsd:* commands as reference)
- Integration points clearly defined (no ambiguous dependencies)
- Build order considers existing dependencies (Phase 27 → 28 → 29 → 30 → 32)

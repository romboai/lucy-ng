# Technology Stack: Multi-Agent Skill Orchestration

**Project:** lucy-ng v2.1 Multi-Agent Working Orchestration
**Researched:** 2026-02-08
**Focus:** Stack additions/changes for Claude Code sub-command skills and agent orchestration

---

## Executive Summary

lucy-ng v2.0 created skill documents and agent definitions on paper but never wired up actual multi-agent orchestration. v2.1 makes it work by implementing Claude Code's native skill and subagent infrastructure.

**Core finding:** No new libraries needed. Claude Code provides all orchestration primitives natively (Task tool, skill registration, agent definitions). Integration is file-based, not code-based.

**Critical constraint:** Current infrastructure already proven in GSD workflow (40+ production skills, 11 agent types, cross-project usage). Copy patterns, don't reinvent.

---

## Required Stack (Zero New Dependencies)

### Claude Code Skill Format

| Component | Location | Purpose |
|-----------|----------|---------|
| **Skill files** | `~/.claude/commands/lucy-ng/*.md` | Sub-command registration (`/lucy-ng:case`, `/lucy-ng:sanitise`, etc.) |
| **Agent definitions** | `~/.claude/agents/lucy-*.md` | Subagent configurations (supervisor, diagnostic-specialist, case) |
| **Skill documents** | `skill/SKILL.md` (existing) | Domain knowledge referenced by agents |

**Why `~/.claude/commands/` not `.claude/skills/`:** GSD uses `commands/` for backward compatibility. Skills and commands merged in Claude Code 2.1.3. Both work identically. Use `commands/` to match GSD patterns.

**File format:** Markdown with YAML frontmatter
- Frontmatter: `name`, `description`, `allowed-tools`, `argument-hint`
- Body: Instructions (can reference skill documents via inline content, NOT `@` syntax)

**Version:** Claude Code 2.1.12+ (current as of 2026-02-08)
- Source: [Extend Claude with skills - Claude Code Docs](https://code.claude.com/docs/en/skills)
- Confidence: HIGH (official docs, active usage)

### Task Tool for Agent Spawning

| Parameter | Type | Purpose | Working Status |
|-----------|------|---------|----------------|
| `prompt` | string | Instructions for subagent | ✓ Working |
| `agent_type` | string | Which agent definition to use | ✓ Working |
| `model` | string | Model selection (`"haiku"`, `"sonnet"`, `"opus"`) | ⚠️ BROKEN (Issue #18873) |

**Critical bug (2026-02-08):** `model` parameter completely broken in 2.1.12+. Creates catch-22 that blocks cost-effective architectures.
- Short aliases rejected: `Task(model="haiku")` → validation error
- Full IDs rejected: `Task(model="claude-haiku-4-5-20251001")` → 404 error
- Workaround: Use `model: inherit` in agent definition, control at session level
- Source: [GitHub Issue #18873](https://github.com/anthropics/claude-code/issues/18873)
- Impact: Cannot route diagnostic work to cheaper models per-task
- Confidence: HIGH (reported bug with reproduction steps)

**Working syntax:**
```python
Task(
    prompt="<instructions with INLINED content>",
    agent_type="lucy-supervisor",
    # model parameter OMITTED due to bug
)
```

### Agent Definition Format

| Field | Required | Purpose | lucy-ng Usage |
|-------|----------|---------|---------------|
| `name` | Yes | Agent identifier | `lucy-supervisor`, `diagnostic-specialist` |
| `description` | Yes | When to spawn | Task delegation matching |
| `tools` | No | Tool allowlist | Restrict diagnostic to Read-only |
| `model` | No | Default model | Use `inherit` due to bug |
| `memory` | No | Persistent directory | NOT USED (file-based progress tracking sufficient) |

**Location:** `~/.claude/agents/lucy-*.md`
**Format:** YAML frontmatter + markdown body (system prompt)
**Discovery:** Loaded at session start; changes require restart or `/agents` reload

**Confidence:** HIGH (official docs, GSD production usage)

---

## Context Passing Architecture

### The @ Reference Limitation

**CRITICAL:** The `@` syntax for referencing files does NOT work across Task() boundaries.

**What doesn't work:**
```python
# BAD - supervisor spawning agent
Task(
    prompt="See @skill/SKILL.md for domain knowledge",  # ❌ Not loaded
    agent_type="diagnostic-specialist"
)
```

**Why:** Task tool spawns fresh context. `@` references are resolved at skill invocation time, not passed through Task() calls.

**Workaround (GSD pattern):**
```bash
# Read content BEFORE spawning
SKILL_CONTENT=$(cat skill/SKILL.md)
PLAN_CONTENT=$(cat .planning/phases/26-thin-tools/26-01-PLAN.md)

# Inline into prompt
Task(
    prompt="Domain knowledge:\n\n${SKILL_CONTENT}\n\nPlan:\n\n${PLAN_CONTENT}\n\nTask: ...",
    agent_type="gsd-executor"
)
```

**Source:** GSD `execute-phase.md` lines 256-276 (wave_execution section)
**Confidence:** HIGH (working implementation, documented in GSD workflows)

### File-Based Inter-Agent Communication

**Pattern:** Agents write structured files; supervisor reads and reacts.

| File | Writer | Reader | Purpose |
|------|--------|--------|---------|
| `CASE-PROGRESS.md` | CASE agent | Supervisor | Iteration history for loop detection |
| `DIAGNOSTIC-REPORT.md` | Diagnostic specialist | Supervisor | Root cause analysis results |
| `CASE-RESULT.md` | CASE agent | Supervisor (final return) | Top-ranked structures |

**Format:** Markdown with structured sections (human-readable, AI-parseable)
**Location:** Compound's working directory (e.g., `data/compound/virgiline/`)
**Polling:** No polling. Task tool BLOCKS until subagent completes. Supervisor reads file after return.

**Why not agent memory:** Memory is for cross-session learning, not inter-agent messaging. File-based is simpler, debuggable, version-controllable.

**Confidence:** MEDIUM (inferred from GSD SUMMARY.md pattern, not explicitly documented for subagents)

---

## Integration with Existing lucy-ng Stack

### No Changes Needed

| Component | Status | Notes |
|-----------|--------|-------|
| Python 3.10+ | Keep | CLI and library remain unchanged |
| Click CLI | Keep | Thin tools stay thin |
| Pydantic v2 | Keep | Data models unchanged |
| nmrglue, RDKit, SQLite | Keep | Core NMR/cheminformatics stack unchanged |

**Why:** Multi-agent orchestration is external to lucy-ng codebase. Skill files call existing CLI commands. No library modifications needed.

### New File Structure

```
lucy-ng/
├── skill/                          # Existing skill docs (v2.0)
│   ├── SKILL.md                    # Main CASE domain knowledge
│   ├── supervisor/SKILL.md         # Loop detection, diagnostics
│   └── diagnostic/SKILL.md         # LSD failure analysis
├── ~/.claude/commands/lucy-ng/     # NEW: Sub-command skills (v2.1)
│   ├── case.md                     # /lucy-ng:case
│   ├── sanitise.md                 # /lucy-ng:sanitise
│   └── dereplicate.md              # /lucy-ng:dereplicate
└── ~/.claude/agents/               # NEW: Agent definitions (v2.1)
    ├── lucy-supervisor.md          # Orchestrator + loop detection
    ├── lucy-case.md                # CASE workflow executor
    └── lucy-diagnostic.md          # LSD failure specialist
```

**Note:** Skill files are user-level (`~/.claude/`), not project-level (`.claude/`), because lucy-ng is a tool used across projects.

### Skill → CLI → Library Flow

```
User: "Solve structure for virgiline"
  ↓
/lucy-ng:case skill (Bash tool)
  ↓
lucy case data/compound/virgiline --formula C16H21N3O
  ↓
CLI parses args, loads config
  ↓
Python library (BrukerReader, LSDInputGenerator, SpectrumMatcher, etc.)
  ↓
LSD via subprocess
  ↓
CASE-PROGRESS.md written (iteration updates)
```

**Agent spawning happens within skills, not in Python code.**

---

## What NOT to Add (And Why)

### ❌ Python Agent Orchestration Libraries

**Options considered:**
- LangChain agents
- CrewAI
- AutoGen
- Custom Python orchestration with subprocess

**Why NOT:** Claude Code provides native orchestration via Task tool. Adding Python layer creates:
- Duplication (two orchestration systems)
- Context passing complexity (Python → Claude Code → subagent)
- Maintenance burden (library API changes)
- Loss of native features (hooks, permissions, context management)

**Decision:** Use Claude Code's native primitives. Skills call CLI commands via Bash tool.

**Confidence:** HIGH (GSD uses this pattern for 40+ skills, zero Python orchestration code)

### ❌ Message Queue Systems

**Options considered:**
- Redis pub/sub for agent messaging
- RabbitMQ for task queues
- ZeroMQ for IPC

**Why NOT:** Task tool is synchronous and blocking. Supervisor spawns CASE agent, waits for completion, reads result file. No async messaging needed.

**File-based communication sufficient:**
- CASE-PROGRESS.md written after each iteration
- Supervisor reads after Task() returns
- No race conditions (single-threaded spawn → execute → return)

**Decision:** File-based communication only.

**Confidence:** HIGH (Task tool blocks by design per official docs)

### ❌ Persistent State Databases

**Options considered:**
- SQLite for agent state
- Redis for shared state
- PostgreSQL for workflow history

**Why NOT:** Each CASE session is independent. State lives in:
- CASE-PROGRESS.md (iteration history)
- LSD files (constraint state)
- Solution files (results)

All files in compound directory. No cross-session state sharing needed.

**Decision:** Filesystem-only state. No database.

**Confidence:** MEDIUM (assumes CASE sessions don't need cross-session learning; may revisit if clustering/batch analysis added)

### ❌ Agent Memory System

**Claude Code provides:** `memory: user|project|local` in agent definitions
**lucy-ng decision:** Do NOT use agent memory

**Why:**
1. CASE knowledge is in skill documents (skill/SKILL.md, skill/supervisor/SKILL.md, skill/diagnostic/SKILL.md)
2. Compound-specific state is in CASE-PROGRESS.md (append-only log)
3. Agent memory is for cross-session learning; CASE is deterministic given inputs
4. Memory adds non-determinism (agent behavior changes based on past sessions)

**Exception:** May add memory to diagnostic specialist if recurring failure patterns emerge. NOT in initial implementation.

**Confidence:** MEDIUM (design decision, not technical constraint; may revisit based on usage data)

---

## Model Selection Strategy (Workaround for Bug #18873)

### Current Reality

Cannot specify model per Task() call due to bug. Must use `model: inherit` in agent definitions.

### Workaround Pattern

```yaml
# ~/.claude/agents/lucy-diagnostic.md
---
name: lucy-diagnostic
description: LSD failure diagnostic specialist
model: inherit  # Inherits from session
tools: Read, Bash
---
```

**Control at session level:**
```bash
# User launches Claude Code with chosen model
claude --model sonnet  # All agents inherit Sonnet
# OR
claude --model haiku   # All agents inherit Haiku
```

**Tradeoff:**
- Pro: Works around bug
- Con: Cannot mix models (e.g., Sonnet for supervisor, Haiku for diagnostic)
- Impact: Higher cost (diagnostic work billed at Sonnet rate even if Haiku sufficient)

**Future:** When bug fixed, add model selection to supervisor skill:
```python
# After bug fix
Task(
    prompt="...",
    agent_type="lucy-diagnostic",
    model="haiku"  # Cheaper model for deterministic checks
)
```

**Confidence:** HIGH (bug confirmed, workaround documented in GSD model lookup table)

---

## Skill Registration Details

### Skill File YAML Frontmatter

From official documentation, these fields are available:

| Field | Required | Purpose | lucy-ng Usage |
|-------|----------|---------|---------------|
| `name` | No (defaults to directory) | Slash command name | `case` → `/lucy-ng:case` |
| `description` | Recommended | When Claude should use skill | "Perform CASE workflow..." |
| `argument-hint` | No | Autocomplete hint | `"<compound-path> <formula>"` |
| `disable-model-invocation` | No | Prevent Claude from auto-loading | `true` for manual-only workflows |
| `user-invocable` | No | Hide from `/` menu | `false` for background knowledge |
| `allowed-tools` | No | Tool whitelist | `"Read, Bash"` for thin wrappers |
| `model` | No | Model override | Use `inherit` due to bug |
| `context` | No | Run in subagent | `"fork"` for isolation |
| `agent` | No | Which subagent type | `"lucy-supervisor"` |

**Source:** [Extend Claude with skills - Claude Code Docs](https://code.claude.com/docs/en/skills)

**lucy-ng pattern:**
```yaml
---
name: case
description: Perform Computer-Assisted Structure Elucidation (CASE) for organic natural products from NMR data
argument-hint: "<compound-path> <formula>"
disable-model-invocation: true  # User explicitly calls /lucy-ng:case
allowed-tools: Bash, Read, Write
---

Execute lucy-ng CASE workflow:
1. Run: lucy case $ARGUMENTS
2. Monitor progress
3. Report results
```

### Storage Location Hierarchy

| Location | Scope | Priority | lucy-ng Decision |
|----------|-------|----------|------------------|
| `--agents` CLI flag | Session-only | 1 (highest) | Not used |
| `.claude/commands/` | Project-level | 2 | Not used (project-specific) |
| `~/.claude/commands/` | User-level | 3 | ✓ USE THIS |
| Plugin's `commands/` | Plugin-enabled | 4 (lowest) | Future consideration |

**Rationale:** lucy-ng is a tool used across projects. User-level skills persist across all NMR datasets.

### Skill Discovery and Loading

**Discovery:** At session start or via `/agents` reload
**Loading:** Skill descriptions always in context; full content loads when invoked
**Context budget:** 2% of context window (~4K tokens for Opus 4.6) for all skill descriptions
**Override:** `SLASH_COMMAND_TOOL_CHAR_BUDGET` environment variable

**Implication:** Keep skill descriptions concise (<100 words). Move domain knowledge to skill/SKILL.md and inline when spawning agents.

---

## Agent Definition Details

### Complete Frontmatter Reference

From official documentation:

| Field | Required | Purpose | lucy-ng Usage |
|-------|----------|---------|---------------|
| `name` | Yes | Agent identifier | `lucy-supervisor` |
| `description` | Yes | When to spawn | "Orchestrates CASE workflow with loop detection" |
| `tools` | No | Tool allowlist | `["Task", "Read", "Bash"]` |
| `disallowedTools` | No | Tool denylist | Not used |
| `model` | No | Model selection | `"inherit"` (bug workaround) |
| `permissionMode` | No | Permission handling | `"default"` (standard prompts) |
| `maxTurns` | No | Iteration limit | Not used (CASE manages internally) |
| `skills` | No | Preload skill content | `["lucy-ng"]` to inline domain knowledge |
| `mcpServers` | No | MCP server access | Inherits from session |
| `hooks` | No | Lifecycle hooks | Not used initially |
| `memory` | No | Persistent directory | Not used (v2.1) |

**Source:** [Create custom subagents - Claude Code Docs](https://code.claude.com/docs/en/sub-agents)

### Permission Modes

| Mode | Behavior | lucy-ng Usage |
|------|----------|---------------|
| `default` | Standard permission prompts | ✓ Supervisor |
| `acceptEdits` | Auto-accept file edits | Not used (explicit control preferred) |
| `dontAsk` | Auto-deny unprompted | Not used |
| `delegate` | Team coordination only | Not applicable |
| `bypassPermissions` | Skip all prompts | Not used (security risk) |
| `plan` | Read-only exploration | Diagnostic specialist |

### Skills Preloading

**Pattern from official docs:**
```yaml
---
name: lucy-case
description: Executes CASE workflow with domain knowledge
skills:
  - lucy-ng  # Inlines full skill/SKILL.md content at startup
---

You are a CASE workflow executor. Follow the methodology from the preloaded lucy-ng skill.
Write CASE-PROGRESS.md after each iteration.
```

**How it works:**
1. Agent definition specifies `skills: [lucy-ng]`
2. Claude Code loads full content of `skill/SKILL.md`
3. Content injected into agent's context at spawn time
4. Agent has domain knowledge without needing to read files

**Advantage:** No file I/O during execution; knowledge is immediately available.

**Limitation:** Uses context budget (~5K tokens for skill/SKILL.md); must fit within agent's window.

---

## Verification Requirements

### Pre-Implementation Checklist

- [ ] Claude Code 2.1.12+ installed (check with `claude --version`)
- [ ] `~/.claude/commands/` directory exists
- [ ] `~/.claude/agents/` directory exists
- [ ] Task tool available (check with `claude --help | grep Task`)
- [ ] GSD workflow installed (reference implementation)

### Integration Tests

Each skill must be testable independently:

```bash
# Skill invocation test
/lucy-ng:case data/compound/test --formula C10H12O2

# Agent spawning test (manual)
# In supervisor skill:
Task(prompt="Test diagnostic agent", agent_type="lucy-diagnostic")

# File-based communication test
# After CASE agent run:
test -f data/compound/test/CASE-PROGRESS.md || echo "FAIL: Progress file missing"
```

### Known Failure Modes

| Failure | Detection | Recovery |
|---------|-----------|----------|
| Skill not found | "Unknown skill /lucy-ng:case" | Check `~/.claude/commands/lucy-ng/case.md` exists |
| Agent not found | "Unknown agent type lucy-supervisor" | Check `~/.claude/agents/lucy-supervisor.md` exists, restart session |
| Context too large | Skill truncated or fails to load | Reduce inlined content, increase SLASH_COMMAND_TOOL_CHAR_BUDGET |
| Model parameter error | "model parameter not supported" | Remove model parameter, use `model: inherit` |

---

## Migration Path (v2.0 → v2.1)

### Phase 1: File Structure (No Behavior Change)

1. Create `~/.claude/commands/lucy-ng/` directory
2. Create `~/.claude/agents/` directory
3. Copy existing agent definitions from `.claude/agents/` to `~/.claude/`
4. Create stub skill files (no Task() calls yet)
5. Test: `/lucy-ng:case` invokes skill, calls CLI directly (no agent spawning)

**Deliverable:** Skills work as thin CLI wrappers

### Phase 2: Agent Spawning (Supervisor Only)

1. Add Task() call to `/lucy-ng:case` skill
2. Supervisor spawns CASE agent (general-purpose Claude instance)
3. CASE agent writes CASE-PROGRESS.md
4. Supervisor reads, detects loops, advises
5. Test: End-to-end CASE with loop detection

**Deliverable:** Supervisor orchestration working

### Phase 3: Diagnostic Delegation

1. Create lucy-diagnostic agent definition
2. Supervisor spawns diagnostic specialist when stuck
3. Specialist writes DIAGNOSTIC-REPORT.md
4. Supervisor extracts root cause, re-advises CASE agent
5. Test: Zero-solution failure triggers diagnostic → fix → success

**Deliverable:** Full multi-agent workflow operational

---

## Performance Characteristics

### Context Window Usage

| Component | Estimated Tokens | Budget Allocation |
|-----------|------------------|-------------------|
| Skill descriptions (all lucy-ng skills) | ~500 | Skill discovery |
| skill/SKILL.md (inlined) | ~5,000 | CASE domain knowledge |
| skill/supervisor/SKILL.md (inlined) | ~4,000 | Loop detection patterns |
| skill/diagnostic/SKILL.md (inlined) | ~8,000 | Diagnostic procedures |
| CASE-PROGRESS.md (10 iterations) | ~2,000 | Iteration history |
| LSD file | ~500 | Current constraints |

**Total per CASE agent spawn:** ~20K tokens
**Opus 4.6 context window:** 200K tokens
**Headroom:** 10× safety margin (can inline all skill docs comfortably)

**Optimization:** If context pressure occurs, load skill sections on-demand (e.g., only load diagnostic/SKILL.md when spawning diagnostic specialist).

### Latency Profile

| Operation | Latency | Notes |
|-----------|---------|-------|
| Skill invocation | <100ms | File load + context injection |
| Task() spawn | 1-3s | Fresh context initialization |
| CASE iteration | 5-15s | LSD run + ranking + progress write |
| Diagnostic analysis | 10-30s | Systematic checks + report generation |
| Full CASE workflow | 2-10 min | 10-20 iterations typical |

**Bottleneck:** LSD solver runtime (external C binary, not optimizable)

**Parallelization:** Not applicable. CASE is sequential (iteration N depends on iteration N-1 results).

---

## Security Considerations

### Tool Restrictions

```yaml
# Diagnostic specialist: Read-only
---
name: lucy-diagnostic
tools: Read, Bash
---

# Supervisor: Read + Task spawning
---
name: lucy-supervisor
tools: Read, Write, Bash, Task
---

# CASE agent: Full access (needs to write LSD files, run solver)
---
name: lucy-case
tools: Read, Write, Bash, Glob, Grep
---
```

**Principle:** Minimal tool access per agent role.

### File Access

All agents restricted to:
- Project directory (cwd)
- `~/.claude/` (skill/agent definitions)
- `data/compound/<compound>/` (working directory)

No system-wide file access needed.

### External Process Execution

Only Bash tool can execute processes:
- `lucy` CLI commands (Python subprocess)
- `LSD` solver (C binary via subprocess)
- `outlsd` converter (C binary)

All subprocesses spawned by Bash tool, governed by Claude Code's permission system.

---

## Alternatives Considered

### Alternative 1: Python-Based Orchestration

**Approach:** Implement orchestration in Python using AgentExecutor pattern
**Rejected because:**
- Duplicates Claude Code's native capabilities
- Context management becomes manual (no `@` syntax, no skill discovery)
- Loses permission system integration
- Harder to debug (Python layer + Claude layer)

**GSD lesson:** Keep orchestration in Claude Code, keep Python library thin.

### Alternative 2: MCP Server for Agent Communication

**Approach:** Create MCP server exposing agent-to-agent messaging
**Rejected because:**
- Task tool already provides synchronous communication (spawn → execute → return)
- File-based messaging sufficient for sequential workflows
- Adds complexity without solving actual problem
- MCP overhead (server process, protocol, error handling)

**Decision:** File-based communication is simpler, debuggable, version-controllable.

### Alternative 3: Project-Level Skills (.claude/skills/)

**Approach:** Put skill files in project directory instead of user directory
**Rejected because:**
- lucy-ng is a tool, not a project
- Skills should work across all NMR datasets (different project directories)
- User-level skills persist across projects
- GSD uses user-level for general-purpose workflows

**Decision:** User-level skills (`~/.claude/commands/lucy-ng/`), not project-level.

---

## Sources

### Official Documentation

- [Extend Claude with skills - Claude Code Docs](https://code.claude.com/docs/en/skills)
- [Create custom subagents - Claude Code Docs](https://code.claude.com/docs/en/sub-agents)
- [Claude Code Slash Commands](https://code.claude.com/docs/en/slash-commands)
- [How Claude Code works - Claude Code Docs](https://code.claude.com/docs/en/how-claude-code-works)

### Production Reference Implementations

- GSD workflow (`.claude/commands/gsd/*.md`, `~/.claude/agents/gsd-*.md`)
  - 40+ skills, 11 agent types
  - Proven patterns: context inlining, wave-based execution, file-based communication
  - execute-phase.md lines 256-276: `@` reference workaround

### Known Issues

- [GitHub Issue #18873: Task tool model parameter returns 404](https://github.com/anthropics/claude-code/issues/18873) (2026-01-31)
- [GitHub Issue #20304: Feature Request for isolated context parameter](https://github.com/anthropics/claude-code/issues/20304)
- [GitHub Issue #4908: Feature Request for scoped context passing](https://github.com/anthropics/claude-code/issues/4908)

### Community Patterns

- [Claude Code Swarm Orchestration](https://gist.github.com/kieranklaassen/4f2aba89594a4aea4ad64d753984b2ea)
- [The Task Tool: Claude Code's Agent Orchestration System](https://dev.to/bhaidar/the-task-tool-claude-codes-agent-orchestration-system-4bf2)
- [Tracing Claude Code's LLM Traffic](https://medium.com/@georgesung/tracing-claude-codes-llm-traffic-agentic-loop-sub-agents-tool-use-prompts-7796941806f5)

---

## Confidence Assessment

| Topic | Confidence | Evidence |
|-------|-----------|----------|
| Skill file format | HIGH | Official docs + GSD implementation |
| Agent definition format | HIGH | Official docs + GSD implementation |
| Task tool API | HIGH | Official docs + working GSD usage |
| Model parameter bug | HIGH | Confirmed GitHub issue with reproduction |
| Context inlining pattern | HIGH | GSD execute-phase.md documented pattern |
| File-based communication | MEDIUM | Inferred from GSD SUMMARY.md pattern |
| Performance estimates | MEDIUM | Extrapolated from typical LLM latencies |
| Security constraints | MEDIUM | Logical analysis, not tested in production |

---

## Recommendations for Roadmap

### Phase Structure Implications

1. **Phase 27: Skill Registration**
   - File structure setup
   - Stub skills (CLI wrappers)
   - No agent spawning yet
   - **Rationale:** Establish foundation, verify skill discovery works

2. **Phase 28: Supervisor Agent**
   - Implement Task() spawning in `/lucy-ng:case`
   - CASE-PROGRESS.md format
   - Loop detection logic
   - **Rationale:** Core orchestration pattern, no diagnostic complexity yet

3. **Phase 29: Diagnostic Specialist**
   - Agent definition
   - DIAGNOSTIC-REPORT.md format
   - Delegation logic in supervisor
   - **Rationale:** Builds on Phase 28, adds deep diagnosis capability

**Avoid:** Implementing all three phases in parallel. Task() context passing has subtle gotchas (@ reference limitation, model parameter bug). Incremental validation prevents compounding issues.

### Research Flags

- **Phase 28:** May need to research performance optimization if CASE-PROGRESS.md grows large (>50 iterations). Consider truncation or summarization strategies.
- **Phase 29:** May need to research diagnostic accuracy metrics if LOW-confidence findings are common. Consider adding confidence calibration examples.

**No deep research expected:** All patterns proven in GSD. Adaptation, not invention.

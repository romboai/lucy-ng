# Project Research Summary

**Project:** lucy-ng v2.1 Working Multi-Agent CASE
**Domain:** AI-agent powered NMR structure elucidation
**Researched:** 2026-02-08
**Confidence:** HIGH

## Executive Summary

lucy-ng v2.0 created an elaborate paper-only architecture with extensive skill documents (3,780 lines total) and agent definitions that never spawned actual agents. The result was zero working orchestration. v2.1 makes multi-agent CASE work by implementing Claude Code's native orchestration primitives correctly.

**Core finding:** Zero new dependencies needed. Claude Code provides all orchestration via Task tool, skill files, and agent definitions. The critical mistake in v2.0 was documentation-first development without validation. v2.1 adopts validation-first: prove agent spawning works before expanding skills.

**Architecture shift:** Supervisor logic dissolves from a separate agent (supervisor.md) into orchestrator sub-command skills (case.md). Skills become entry points that spawn worker agents with inlined domain knowledge. The existing v2.0 Python CLI (validated in Phase 26) remains unchanged—orchestration is purely additive.

**Primary risk:** Repeating v2.0's paper architecture mistake. Mitigation is mandatory validation gates: prove Task() spawning works, prove progress monitoring works, prove loop detection works, THEN expand with full domain knowledge. Minimum 10 integration tests before declaring complete.

## Key Findings

### Recommended Stack

**No new dependencies.** Claude Code's native primitives (Task tool, skill files, agent definitions) provide all orchestration capabilities. Integration is file-based, not code-based.

**Core technologies:**
- **Claude Code 2.1.12+ Task tool** — Agent spawning with blocking semantics (no async messaging needed)
- **Skill files (~/.claude/commands/lucy-ng/)** — Sub-command orchestrators that spawn agents and monitor progress
- **Agent definitions (~/.claude/agents/)** — Worker agent configurations with domain knowledge
- **File-based IPC (CASE-PROGRESS.md)** — Sequential coordination via markdown progress files
- **Existing Python CLI** — Thin data-access tools (already validated in v2.0 Phase 26)

**Critical bug workaround:** Task tool's model parameter is completely broken (GitHub Issue #18873). Use `model: inherit` in agent definitions, control at session level. Cannot mix models per-task until bug fixed.

**Context management strategy:** Hybrid inlining. Critical workflow content (~500-700 lines) inlined in Task() instructions for immediate access. Detailed reference material (full LSD manual, advanced strategies) provided via file paths for on-demand reading.

### Expected Features

**Must have (table stakes):**
- **/lucy-ng:case orchestrator** — Spawn autonomous CASE agent, monitor progress via CASE-PROGRESS.md, detect 4 loop patterns, diagnose root cause, intervene with advisory constraints (WHAT to fix, not HOW)
- **Autonomous CASE agent** — Full workflow executor that writes CASE-PROGRESS.md after every iteration
- **Loop detection** — ELIM thrashing, zero-solution loop, solution explosion, constraint churning
- **Advisory intervention** — Maintain agent autonomy (supervisor constrains WHAT, agent decides HOW)
- **Per-pattern intervention counters** — Track failures separately for each loop type, escalate after 10 cycles per pattern
- **Termination guarantees** — Absolute cap at 10 spawn cycles prevents infinite loops

**Should have (competitive differentiators):**
- **Diagnostic specialist delegation** — Deep LSD failure analysis after 2 failed basic interventions
- **Autonomous workflow** — Agent runs to completion or reports stuck (no manual intervention mid-flight)
- **Progress transparency** — CASE-PROGRESS.md enables user observation without interrupting
- **/lucy-ng:sanitise** — AI-driven dataset sanitization for blind evaluation (requires semantic reasoning, cannot be CLI)

**Defer (v2+):**
- Interactive CASE mode with user feedback loop
- Cross-session learning via agent memory
- Advanced convergence strategies (plateau detection, strategy adaptation)

**Anti-features (explicitly DO NOT build):**
- Dereplication in CASE orchestrator (violates separation of concerns)
- CLI command for sanitization (chemical names require semantic understanding)
- Directive intervention (supervisor tells CASE agent exact edits to make)
- Global intervention counter (conflates different failure modes)
- One-shot CASE execution (CASE requires iterative refinement)

### Architecture Approach

v2.1 integrates GSD-pattern sub-command skills with existing thin CLI, replacing monolithic `/lucy-ng` skill with working multi-agent orchestration. This is integration, not rewrite—Python codebase (17,500 lines, 642 tests) remains stable.

**Major components:**

1. **Sub-command skills (orchestrators)** — 5 skills in ~/.claude/commands/lucy-ng/ that route requests, spawn agents, monitor progress, handle failures
2. **Agent definitions (workers)** — 2 agents in ~/.claude/agents/ (lucy-case-agent, lucy-diagnostic) that execute workflows and write structured progress files
3. **Skill documents (domain knowledge)** — Existing skill/ hierarchy (3,780 lines) referenced by agents via file paths or selective inlining
4. **Progress files (IPC mechanism)** — CASE-PROGRESS.md and DIAGNOSTIC-REPORT.md enable orchestrator monitoring of sequential agent execution
5. **Thin CLI commands** — Existing Python tools (validated Phase 26) for data access only, zero intelligence in CLI

**Data flow pattern:** User invokes /lucy-ng:case → case.md orchestrator reads skill documents → spawns lucy-case-agent via Task() with inlined critical content + file path references → agent executes CASE workflow → writes CASE-PROGRESS.md → orchestrator reads progress → detects loop → diagnoses → spawns agent again with advisory → repeat until convergence or escalation.

**Integration with v2.0:** skill/ documents unchanged, CLI unchanged, CLAUDE.md needs 20-line sub-command section, supervisor.md deleted (logic moves to case.md), diagnostic-specialist.md renamed to lucy-diagnostic.md (~50 line change).

### Critical Pitfalls

1. **Paper architecture without validation (v2.0's failure)** — Writing elaborate skill documents before testing if Task() spawning works creates 3,780 lines of non-working orchestration. Mitigation: Validation-first development with mandatory integration tests before skill expansion.

2. **Context window overflow in agent handoffs** — Inlining 3,780 lines of skill content in Task() instructions causes context overflow or degraded performance. Mitigation: Hybrid inlining (~500-700 lines critical workflow) + file path references for detailed docs.

3. **Iterative supervision loops without termination guarantees** — Supervisor spawns agent → detects failure → spawns again → infinite loop with no guaranteed stop. Mitigation: Per-pattern intervention counters with 10-cycle cap, multi-signal loop detection prevents false positives.

4. **Agent handoff state loss** — Fresh agent spawns have blank slate, repeat work already done (re-pick peaks, retry failed constraints). Mitigation: Explicit handoff protocol via progress.md, skip completed steps in retry instructions.

5. **Skill file authoring errors causing silent failures** — YAML frontmatter syntax errors prevent agent loading, orchestration fails with "agent not found" but no visible error. Mitigation: YAML validation checklist, test spawn immediately after edits.

6. **Smart orchestrator, dumb agent (inverted responsibility)** — Orchestrator does CASE domain reasoning, agent just executes commands, defeats purpose of autonomy. Mitigation: Orchestrator provides advisory constraints (WHAT to fix), agent applies domain expertise (HOW to fix).

7. **No end-to-end test for multi-agent orchestration** — Unit tests feel sufficient, integration failures discovered in production. Mitigation: Minimum 10 integration tests covering spawn → monitor → detect → intervene → retry → escalate.

8. **File-based inter-agent communication race conditions** — Supervisor reads progress.md while agent writes it, gets partial data. Mitigation: Atomic write pattern (write to temp file, atomic rename) + sequential agents (Task() blocks, no concurrent access).

## Implications for Roadmap

Based on research, v2.1 requires 7 phases structured for incremental validation.

### Phase 27: Sub-Command Skills Foundation (3-4 hours)

**Rationale:** Establish directory structure and prove simple skills work before complex orchestration. Thin wrappers for existing CLI validate pattern without multi-agent complexity.

**Delivers:**
- ~/.claude/commands/lucy-ng/ directory with 3 simple skills
- status.md (system checks)
- dereplicate.md (thin wrapper for lucy dereplicate c13)
- predict.md (thin wrapper for lucy predict c13)

**Addresses:** None yet (foundation phase)

**Avoids:** Paper architecture (all 3 skills tested individually before next phase)

**Research flag:** NO (standard CLI wrapper pattern, well-documented)

### Phase 28: CASE Agent Definition (4-5 hours)

**Rationale:** Prove Task() spawning works before writing orchestrator. Agent must be spawn-able and write progress before supervisor tries to coordinate.

**Delivers:**
- ~/.claude/agents/lucy-case-agent.md with YAML frontmatter
- Agent instructions with workflow overview
- CASE-PROGRESS.md checkpoint writing
- Integration test: spawn agent, verify progress file

**Addresses:** Autonomous CASE agent (table stakes from FEATURES.md)

**Avoids:** Paper architecture (must prove spawn before Phase 29), context overflow (test with minimal inlined content first)

**Research flag:** NO (Task tool well-documented, GSD reference pattern)

### Phase 29: CASE Orchestrator Skill (6-8 hours)

**Rationale:** Core orchestration logic—spawning with inlined content, progress monitoring, loop detection, advisory intervention. This is the critical path.

**Delivers:**
- ~/.claude/commands/lucy-ng/case.md orchestrator
- Agent spawning with hybrid inlining (critical workflow + file references)
- Progress monitoring (read CASE-PROGRESS.md after agent completes)
- 4 loop pattern detection (ELIM thrashing, zero-solution, explosion, churning)
- Basic diagnosis and advisory generation
- Per-pattern intervention counters with 10-cycle escalation

**Addresses:** CASE orchestrator, loop detection, advisory intervention, termination guarantees (all table stakes)

**Avoids:** Context overflow (hybrid inlining), infinite loops (termination guarantees), state loss (explicit handoff), inverted responsibility (advisory not directive)

**Research flag:** NO (patterns proven in GSD execute-phase.md, supervisor/SKILL.md already defines loop patterns)

### Phase 30: Diagnostic Specialist Integration (3-4 hours)

**Rationale:** Deep diagnosis for complex failures. Only spawned after basic interventions fail, so depends on Phase 29 orchestrator working.

**Delivers:**
- Rename .claude/agents/diagnostic-specialist.md → lucy-diagnostic.md
- Update frontmatter (agent name, tool permissions)
- Diagnostic spawning logic in case.md (after 2 failed interventions with same pattern)
- DIAGNOSTIC-REPORT.md reading and primary fix extraction
- Integration test: force repeated failure, verify specialist spawned

**Addresses:** Diagnostic specialist delegation (differentiator from FEATURES.md)

**Avoids:** Smart orchestrator (diagnostic agent does analysis, orchestrator just coordinates)

**Research flag:** NO (diagnostic/SKILL.md already defines systematic checks, report format)

### Phase 31: Sanitization Skill (2-3 hours)

**Rationale:** AI-driven dataset preparation for blind evaluation. Parallelizable with Phase 30 (independent functionality).

**Delivers:**
- ~/.claude/commands/lucy-ng/sanitise.md
- skill/sanitize/SKILL.md (pattern definitions)
- AI-driven compound identifier detection (names, SMILES, InChI, IDs)
- SANITIZATION-REPORT.md generation

**Addresses:** AI-driven sanitization (differentiator from FEATURES.md)

**Avoids:** CLI for sanitization (anti-feature, chemical names require semantic reasoning)

**Research flag:** NO (pattern matching well-understood, helpers already exist in skill/sanitize/)

### Phase 32: End-to-End Validation (2-3 hours)

**Rationale:** Mandatory validation gate. v2.1 ships ONLY after passing all integration tests—no repeat of v2.0's paper architecture.

**Delivers:**
- Integration tests (minimum 10):
  - Supervisor spawns CASE agent
  - CASE agent writes CASE-PROGRESS.md with required fields
  - Supervisor parses progress and detects loops
  - Advisory issued and agent re-spawned
  - Termination after 10 cycles
  - Diagnostic specialist invoked on complex failure
  - Full success path (Ibuprofen CASE)
  - Full intervention path (constructed failure case)
- Manual validation: /lucy-ng:case on Ibuprofen (reproduces Phase 26-05 success)
- CLAUDE.md update (sub-command reference section)

**Addresses:** End-to-end orchestration validation (prevents pitfall #7)

**Avoids:** All critical pitfalls (validation gates enforce prevention)

**Research flag:** NO (test patterns well-established)

### Phase 33: Documentation and Cleanup (1-2 hours)

**Rationale:** Remove deprecated components, update project documentation, prepare for milestone completion.

**Delivers:**
- Delete .claude/agents/supervisor.md (logic now in case.md)
- Update PROJECT.md decisions table (v2.1 architecture)
- Update STATE.md (milestone v2.1 complete)
- v2.1 release notes

**Addresses:** Project maintenance

**Avoids:** Technical debt (clean up deprecated files)

**Research flag:** NO (documentation task)

### Phase Ordering Rationale

**Critical path:** 27 → 28 → 29 → 30 → 32 → 33 (16-20 hours)

**Parallelizable:** Phase 31 (sanitization) can run in parallel with Phase 30 (diagnostic integration) if multiple contributors.

**Why this order:**
- Phase 27 establishes foundation without multi-agent complexity
- Phase 28 proves Task() spawning before orchestrator depends on it
- Phase 29 implements core orchestration (critical path)
- Phase 30 builds on working orchestrator
- Phase 31 is independent (can parallelize)
- Phase 32 is mandatory validation gate (nothing ships without passing)
- Phase 33 is cleanup after validation passes

**Dependency enforcement:**
- Each phase tested individually before next phase starts
- Phase 32 validation blocks completion (hard gate)
- No "almost ready to test" mentality—validation happens incrementally

**Pitfall avoidance structure:**
- Incremental validation prevents paper architecture (Phases 27-28-29 each validated)
- Integration tests required before Phase 33 (prevents pitfall #7)
- Context management tested in Phase 29 (prevents pitfall #2)
- Termination guarantees implemented in Phase 29 (prevents pitfall #3)
- Handoff protocol tested in Phase 29-30 (prevents pitfall #4)
- YAML validation in Phase 28 (prevents pitfall #5)
- Advisory constraints enforced in Phase 29 (prevents pitfall #6)

### Research Flags

**No deep research needed.** All phases implement patterns already proven in:
- GSD workflow (40+ skills, 11 agent types, Task tool usage)
- v2.0 skill documents (loop patterns, diagnostic procedures)
- v2.0 Phase 26 validation (thin CLI works)
- Claude Code official docs (Task tool, skill format, agent definitions)

**Standard patterns for all phases:**
- Phase 27: CLI wrapper pattern (GSD dereplicate/predict references)
- Phase 28: Agent definition pattern (GSD gsd-executor reference)
- Phase 29: Orchestration pattern (GSD execute-phase reference)
- Phase 30: Diagnostic delegation pattern (existing diagnostic-specialist.md)
- Phase 31: AI-driven pattern matching (existing sanitize helpers)
- Phase 32: Integration testing (standard pytest patterns)
- Phase 33: Documentation updates (standard GSD cleanup)

**If research becomes necessary during execution:**
- Phase 29 context management: If hybrid inlining proves insufficient, research progressive loading strategies
- Phase 29 loop detection: If false positives occur, research multi-signal suppression mechanisms
- Phase 30 diagnostic accuracy: If LOW-confidence findings common, research confidence calibration

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Claude Code official docs + GSD production reference + no new dependencies |
| Features | HIGH | Table stakes clear from multi-agent orchestration patterns + anti-features identified from v2.0 failure |
| Architecture | HIGH | Integration approach with stable v2.0 foundation + GSD sub-command pattern + file-based IPC proven |
| Pitfalls | HIGH | v2.0 provided real-world failure case (paper architecture) + community sources for other pitfalls + mitigation tested in GSD |

**Overall confidence:** HIGH

### Gaps to Address

**Potential gaps during execution:**

1. **Context management tuning** — Hybrid inlining sizes (~500-700 lines) are estimates based on LLM context limits. May need adjustment based on actual Task() spawn behavior. Mitigation: Start conservative (less inlined), expand if needed.

2. **Loop detection threshold sensitivity** — Multi-signal detection thresholds (3+ iterations zero-solution, 5+ iterations churning) may need tuning based on real compound failures. Mitigation: Test on Virgiline (known failure case), adjust if false positives/negatives.

3. **Diagnostic specialist accuracy** — v2.0 diagnostic/SKILL.md is comprehensive (1,874 lines) but untested. Specialist may miss root causes on first attempts. Mitigation: Iterative refinement after observing failure patterns in Phase 32 validation.

4. **Task tool model parameter bug timeline** — GitHub Issue #18873 may be fixed during v2.1 development, enabling per-task model selection. Mitigation: Use `model: inherit` initially, add per-task selection if bug fixed mid-development.

**No architectural unknowns.** All components either exist (v2.0 skills, CLI) or follow proven patterns (GSD orchestration). Gap handling is tuning, not discovery.

## Sources

### Primary (HIGH confidence)

**Claude Code official documentation:**
- [Extend Claude with skills - Claude Code Docs](https://code.claude.com/docs/en/skills) — Skill file format, frontmatter fields, context budget
- [Create custom subagents - Claude Code Docs](https://code.claude.com/docs/en/sub-agents) — Agent definition format, tool permissions, model selection
- [How Claude Code works - Claude Code Docs](https://code.claude.com/docs/en/how-claude-code-works) — Task tool blocking behavior, session lifecycle

**GSD production reference implementation:**
- ~/.claude/commands/gsd/execute-phase.md (lines 256-276) — Context inlining pattern, @ reference workaround
- ~/.claude/agents/gsd-executor.md — Agent definition reference
- 40+ skills, 11 agent types — Proven orchestration patterns

**lucy-ng v2.0 foundation:**
- skill/SKILL.md (1,079 lines) — Core domain knowledge
- skill/supervisor/SKILL.md (827 lines) — Loop detection patterns, CASE-PROGRESS.md format
- skill/diagnostic/SKILL.md (1,874 lines) — LSD manual, diagnostic procedures
- .planning/phases/26-thin-tools/26-05-PLAN.md — Thin CLI validation (Ibuprofen CASE success)

**Known issues:**
- [GitHub Issue #18873: Task tool model parameter returns 404](https://github.com/anthropics/claude-code/issues/18873) — Confirmed bug with workaround documented

### Secondary (MEDIUM confidence)

**Multi-agent orchestration patterns (2026):**
- [AI Agent Orchestration Guide - Patterns and Tools (2026) | Fast.io](https://fast.io/resources/ai-agent-orchestration/) — Hierarchical supervisor pattern
- [Choosing the right orchestration pattern for multi agent systems](https://www.kore.ai/blog/choosing-the-right-orchestration-pattern-for-multi-agent-systems) — Supervisor vs swarm tradeoffs
- [The Task Tool: Claude Code's Agent Orchestration System - DEV Community](https://dev.to/bhaidar/the-task-tool-claude-codes-agent-orchestration-system-4bf2) — Task tool usage patterns

**Context management:**
- [Context Window Overflow in 2026: Fix LLM Errors Fast](https://redis.io/blog/context-window-overflow/) — System prompt overhead calculation
- [Multi-agent orchestration for Claude Code in 2026](https://shipyard.build/blog/claude-code-multi-agent/) — Context depletion in subagent spawning

**Testing multi-agent systems:**
- [Evaluating LLM Agents in Multi-Step Workflows (2026 Guide)](https://www.codeant.ai/blogs/evaluate-llm-agentic-workflows) — Integration test patterns
- [Validating multi-agent AI systems](https://www.pwc.com/us/en/services/audit-assurance/library/validating-multi-agent-ai-systems.html) — Component-level then system-level validation

### Tertiary (LOW confidence)

**Community patterns (needs validation):**
- [Claude Code Swarm Orchestration](https://gist.github.com/kieranklaassen/4f2aba89594a4aea4ad64d753984b2ea) — Alternative orchestration approach (swarm vs supervisor)
- [Tracing Claude Code's LLM Traffic](https://medium.com/@georgesung/tracing-claude-codes-llm-traffic-agentic-loop-sub-agents-tool-use-prompts-7796941806f5) — Observability patterns (not validated in lucy-ng context)

**Agent communication alternatives (not pursued):**
- [Feature Request: Enable Agent-to-Agent Communication · Issue #4993](https://github.com/anthropics/claude-code/issues/4993) — Advanced messaging patterns (file-based sufficient for lucy-ng)

---
*Research completed: 2026-02-08*
*Ready for roadmap: yes*

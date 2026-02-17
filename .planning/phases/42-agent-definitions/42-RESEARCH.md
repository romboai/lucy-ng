---
phase: 42
status: complete
researched: 2026-02-17
---

# Phase 42: Agent Definitions with Knowledge Distribution - Research

## Research Question

"What do I need to know to create 4 specialist agent definitions by decomposing the 1280-line monolithic lucy-case-agent.md?"

## Source Analysis

### Monolithic Agent Structure (lucy-case-agent.md, 1280 lines)

The existing monolithic agent has these major sections:

| Section | Lines | Content |
|---------|-------|---------|
| YAML frontmatter + role + prohibitions | 1-33 | Agent identity, tools, prohibitions |
| Section 1: NMR Background | 34-209 | Experiment types, shift regions, Pitfalls 1-9 |
| Section 2: Spectral Quality | 210-259 | S/N, digital resolution, artifacts |
| Section 3: LSD Commands | 260-376 | MULT/HSQC/HMBC/BOND/LIST/PROP/ELEM, correlation order, hybridization, ELIM, outlsd, checklist, badlist |
| Section 3.5: Statistical Detection | 377-609 | 4 detection commands, interpretation, constraint translation examples, documentation |
| Section 3.6: Chemistry-First Hierarchy | 610-792 | Evidence priority, conflict resolution, worked examples, thresholds |
| Section 4: Incremental HMBC Strategy | 793-887 | Core principle, selection criteria, adaptive loop, stopping, recovery |
| Section 5: CASE Workflow | 888-978 | File organization, step-by-step workflow, ranking algorithm |
| Section 6: Error Tolerance | 979-1063 | Close carbons, DEPT conflicts, quaternary sparsity |
| Section 7: Confidence Scoring | 1064-1123 | Per-atom factors, downgrade rules, per-structure derivation |
| Section 8: CASE-PROGRESS.md | 1124-1217 | Format specification, required fields |
| Workflow + Advisory | 1218-1280 | Step-by-step execution, advisory handling, output format |

### Existing Stub Agent Files

Phase 41 created 4 stub files at `~/.claude/agents/`:
- `lucy-nmr-chemist.md` (25 lines, placeholder)
- `lucy-lsd-engineer.md` (25 lines, placeholder)
- `lucy-solution-analyst.md` (25 lines, placeholder)
- `lucy-devils-advocate.md` (25 lines, placeholder)

Each has YAML frontmatter (name, description, tools) and a placeholder `<role>` section. Phase 42 replaces the content while preserving the file locations.

### Agent Definition Patterns (from lucy-case-agent.md and lucy-diagnostic.md)

Both existing full agents use:
- YAML frontmatter: `name`, `description`, `tools`, `model`, `color`
- XML-tagged sections: `<role>`, `<inlined_critical_knowledge>`, `<detailed_references>`, `<workflow>`
- Inline knowledge rather than file references (agent can't reliably read external files at spawn time)
- `model: claude-opus-4-6` for the CASE agent

### Team Communication Pattern (from case.md orchestrator)

The orchestrator spawns agents with `Task(team_name="case-{compound}", subagent_type="lucy-{role}")`. Agents:
- Claim tasks from `TaskList`
- Report results via `SendMessage` to team lead and other agents
- Mark tasks completed via `TaskUpdate`
- Receive messages from team lead and peers

## Knowledge Distribution Analysis

### Distribution Map

Based on CONTEXT.md decisions, here is the exact section-to-agent mapping:

**NMR-Chemist (target: 200-280 lines)**
- Section 1: NMR Background (lines 34-209) -- 176 lines -- EXCLUSIVE
- Section 2: Spectral Quality (lines 210-259) -- 50 lines -- EXCLUSIVE
- Section 3.5: Statistical Detection Protocol (lines 377-609) -- 233 lines -- EXCLUSIVE
- Section 3.6: Chemistry-First Hierarchy (lines 610-792) -- 183 lines -- EXCLUSIVE
- Section 6: Error Tolerance (lines 979-1063) -- 85 lines -- EXCLUSIVE
- Section 7: Confidence Scoring (lines 1064-1123) -- 60 lines -- SHARED with solution-analyst

Total source: ~787 lines. Must be compressed to 200-280 lines. Key compression strategies:
- Pitfalls 1-9 can be condensed (remove worked examples, keep rules)
- Detection protocol keeps CLI syntax but condenses interpretation tables
- Chemistry-First hierarchy keeps decision tree, removes 3 worked examples (agent can reason through these)
- Error tolerance keeps rules, compresses resolution strategies

**LSD-Engineer (target: 200-280 lines)**
- Section 3: LSD Commands (lines 260-376) -- 117 lines -- EXCLUSIVE
- Section 4: Incremental HMBC Strategy (lines 793-887) -- 95 lines -- EXCLUSIVE
- Section 5: CASE Workflow file organization (lines 888-927) -- 40 lines -- EXCLUSIVE
- Section 8: CASE-PROGRESS.md format (lines 1124-1217) -- 94 lines -- SHARED (full version here)

Total source: ~346 lines. Already close to target. Key adjustments:
- LSD command reference kept nearly verbatim (critical syntax)
- HMBC strategy condensed slightly (remove "what NOT to do" examples)
- File organization kept verbatim (mandatory rules)
- CASE-PROGRESS format is the full specification (other agents get abbreviated version)

**Solution-Analyst (target: 150-200 lines)**
- Section 5 ranking algorithm (lines 969-977) -- 9 lines -- EXCLUSIVE
- Section 7: Confidence Scoring (lines 1064-1123) -- 60 lines -- SHARED with nmr-chemist
- `lucy lsd rank` CLI usage -- derived from monolith -- EXCLUSIVE
- `lucy predict c13` CLI usage -- from CLAUDE.md -- EXCLUSIVE

Total source: ~100 lines. The smallest agent. Key additions:
- Detailed ranking interpretation (what matched_count and MAE mean)
- Shift prediction for verification (not just ranking)
- Chemical plausibility assessment criteria (new content, derived from domain knowledge)
- Final results report format

**Devils-Advocate (target: 150-250 lines)**
- Section 3 hybridization rules (sp2 even count) -- reference from lsd-engineer -- SHARED
- Section 3 badlist filters (DEFF NOT) -- reference from lsd-engineer -- SHARED
- Section 6: Error Tolerance (close carbons, multiplicity conflicts) -- reference from nmr-chemist -- SHARED
- Diff protocol -- NEW content -- EXCLUSIVE
- Constraint persistence checklist -- NEW content -- EXCLUSIVE
- v3.0 UAT bug checks -- NEW content -- EXCLUSIVE

Total source: ~40 lines from monolith + ~150 lines new. Key content:
- 5 v3.0 UAT bugs as explicit checklist items
- Diff protocol: what to compare between iteration N and N-1
- Severity classification (CRITICAL/WARNING/INFO)
- Pre-run validation gate workflow

### Shared Knowledge Summary Template

Each agent needs a 5-10 line shared context section covering:
1. What the CASE team does (1-2 sentences)
2. What NMR experiments provide (experiment names, not details)
3. What LSD solver does (structure enumeration from constraints)
4. What the iteration workflow looks like (detect -> build -> validate -> solve -> rank)
5. Where files live (analysis/ directory structure)

### Inter-Agent Message Schemas

Plain text with structured markdown sections. Each agent's definition specifies:
- **OUTPUTS:** What it posts and the format
- **INPUTS:** What it reads from other agents

These are defined in CONTEXT.md and should be inlined in each agent definition.

## Key Findings

### 1. Compression Requirements

The monolithic agent is 1280 lines. The 4 specialists together should be 600-1000 lines total. This requires ~40-50% compression, achieved by:
- Removing duplication (each knowledge section lives in ONE agent)
- Compressing worked examples (keep rules, remove verbose walkthroughs)
- Using cross-references instead of duplicating content
- Removing the monolith's workflow section (replaced by team coordination)

### 2. Knowledge That MUST Stay Verbatim

Some content is too precise to paraphrase:
- LSD command syntax (MULT, HSQC, HMBC, BOND, LIST, ELEM, PROP, DEFF NOT)
- CLI command syntax (lucy detect, lucy pick, lucy lsd run, outlsd 5)
- Correlation order rule (HSQC before HMBC)
- File organization rules (analysis/iteration_NN/ structure)
- CASE-PROGRESS.md format specification

### 3. Content That Can Be Compressed

- Pitfall descriptions (keep rule, remove extended explanation)
- Worked conflict examples in Chemistry-First Hierarchy (keep decision tree, remove 3 full examples)
- Convergence stall and zero-solution recovery (keep algorithm, condense prose)

### 4. New Content Required

The devils-advocate agent needs entirely new content not in the monolith:
- Constraint diff protocol (compare iteration N vs N-1 LSD files)
- Constraint persistence checklist (5 items from v3.0 UAT findings)
- Severity classification system
- Pre-run validation gate workflow

### 5. Agent Definition Structure

Recommended structure for each agent:
```
---
YAML frontmatter (name, description, tools, model)
---

<role>
  Identity, team role, communication instructions
</role>

<shared_context>
  5-10 line CASE team overview
</shared_context>

<domain_knowledge>
  Agent-specific inlined knowledge (the bulk)
</domain_knowledge>

<message_interface>
  OUTPUTS: what this agent posts
  INPUTS: what this agent reads from others
</message_interface>

<workflow>
  Agent-specific step-by-step execution
</workflow>
```

### 6. Tool Assignments

From CONTEXT.md:
- **NMR-Chemist:** Read, Write, Bash, Glob, Grep (needs Bash for lucy CLI)
- **LSD-Engineer:** Read, Write, Bash, Glob, Grep (needs Bash for lucy lsd run, outlsd)
- **Solution-Analyst:** Read, Write, Bash, Glob, Grep (needs Bash for lucy lsd rank, lucy predict c13)
- **Devils-Advocate:** Read, Bash, Glob, Grep (reads LSD files, runs diff checks -- Write for logging only)

Note: Devils-Advocate gets Write removed from the stub's tool list. It should only read and validate, not modify LSD files.

### 7. Plan Structure Recommendation

Four plans, one per agent, all in Wave 1 (parallel, no inter-dependencies):
- Plan 42-01: NMR-Chemist full definition
- Plan 42-02: LSD-Engineer full definition
- Plan 42-03: Solution-Analyst full definition
- Plan 42-04: Devils-Advocate full definition

All 4 are independent (each reads from the monolith, writes to its own file). They can execute in parallel.

A 5th plan (Wave 2) for validation: verify coverage, check for knowledge gaps, confirm all sections from the monolith are covered by at least one agent.

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Knowledge gaps after decomposition | Agent fails on edge case | Plan 42-05 validates coverage systematically |
| Agent too large (> 400 lines) | Knowledge leaking across boundaries | Strict section assignment per CONTEXT.md |
| Agent too small (< 100 lines) | Insufficient domain knowledge | Solution-analyst is smallest; supplement with ranking interpretation |
| Devils-advocate missing UAT bug checks | v3.0 bugs recur | Explicit checklist from MEMORY.md findings |
| CLI syntax errors in compressed knowledge | Agent runs wrong commands | Keep CLI syntax verbatim, compress prose only |

---

*Phase: 42-agent-definitions*
*Research completed: 2026-02-17*

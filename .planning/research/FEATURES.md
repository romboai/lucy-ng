# Feature Landscape: Multi-Agent CASE Orchestration Skills

**Domain:** AI-powered NMR structure elucidation with multi-agent orchestration
**Researched:** 2026-02-08

---

## Executive Summary

This research defines the feature landscape for lucy-ng's v2.1 multi-agent CASE orchestration skills. The system replaces a monolithic `/lucy-ng` skill with GSD-pattern sub-command skills that follow modern agent orchestration patterns.

**Key findings:**
- **Table stakes**: Sub-commands must be single-purpose, spawn agents correctly, and maintain clean separation of concerns
- **Differentiators**: AI-driven sanitisation without CLI, autonomous CASE with supervision loop, diagnostic delegation pattern
- **Anti-features**: Dereplication in CASE orchestrator, CLI for sanitisation, directive intervention (vs advisory)

The feature set is informed by 2026 multi-agent orchestration patterns: hierarchical supervisor architectures, iterative agent spawning via Task tool, advisory intervention models, and transparent progress monitoring.

---

## Table Stakes

Features users expect. Missing = system feels broken or incomplete.

### 1. /lucy-ng:case — CASE Orchestrator

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Spawn autonomous CASE agent via Task tool | Core orchestrator responsibility in hierarchical pattern | Medium | Follow Claude Code 2.1 Task spawning pattern with clear instructions |
| Monitor CASE-PROGRESS.md after each iteration | Standard supervision loop pattern for iterative workflows | Low | Read-only, agent writes this file |
| Detect 4 unproductive loop patterns | Supervisor must prevent infinite loops in autonomous systems | Medium | ELIM thrashing, zero-solution loop, solution explosion, constraint churning |
| Diagnose root cause before intervention | Quality gate for supervision — intervention without diagnosis wastes tokens | Medium | Pattern-specific diagnostic procedures |
| Intervene with advisory constraints | Supervisor guides without directive control | Medium | "Check sp2 count" not "change line 15" |
| Track per-pattern intervention counts | Prevents infinite supervision loops | Low | Separate counters for each loop type |
| Escalate after 10 failed cycles | Hard safety cap for autonomous operation | Low | Return control to user with diagnostic report |
| NEVER attempt dereplication | Absolute separation of concerns | Low | Critical anti-pattern: CASE != dereplication |
| Spawn diagnostic specialist after 2 failures | Deep root cause analysis for persistent issues | Medium | Delegation pattern for specialized diagnosis |
| Support "skip dereplication" option | User control over workflow routing | Low | Default tries dereplication, user can override |

**Dependencies:**
- Existing: skill/SKILL.md (CASE workflow knowledge), skill/supervisor/SKILL.md (loop detection)
- Existing: CASE-PROGRESS.md format specification
- New: Autonomous CASE agent definition

### 2. /lucy-ng:sanitise — AI Dataset Sanitisation

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Extract all text content for AI review | AI needs complete context to identify identifiers | Low | Use existing lucy_text_extractor.py helper |
| Detect chemical names via reasoning | Cannot be pattern-matched — requires understanding | High | AI applies chemistry knowledge to recognize compound names |
| Detect SMILES/InChI/InChIKey patterns | Well-defined formats, pattern-matchable | Low | Regex for InChI/InChIKey, heuristics for SMILES |
| Detect CAS registry numbers | Standard format: up to 10 digits, hyphen-separated, check digit | Low | Pattern: `\d{2,7}-\d{2}-\d` with checksum validation |
| Detect MOL file structures | Binary structure files containing atom coordinates | Low | File extension and header signature |
| Detect dataset naming patterns | Paths/filenames may contain compound names | Medium | Example: "Caffeine/10" or "Ibuprofen_1H" |
| Generate redaction manifest | List of identifiers to remove | Low | One identifier per line, feed to bulk_sanitize.py |
| Execute bulk sanitisation | Apply text replacements safely | Low | Use existing lucy_bulk_sanitize.py helper |
| Verify sanitisation completeness | Re-extract and confirm no identifiers remain | Low | Run text extractor again, review output |
| NO CLI COMMAND | Requires AI reasoning — cannot be automated | N/A | Explicitly document: "This skill has no CLI command" |

**Dependencies:**
- Existing: skill/sanitize/lucy_text_extractor.py (extraction helper)
- Existing: skill/sanitize/lucy_bulk_sanitize.py (bulk replacement helper)
- New: AI reasoning about chemistry domain knowledge

**Critical design decision:** Sanitisation CANNOT be a simple CLI because identifying compound names requires semantic understanding. "Indigo" could be a dye, a company name, or background noise. Only AI with chemistry knowledge can distinguish.

### 3. /lucy-ng:dereplicate — Simple Dereplication

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Wrap `lucy dereplicate c13` CLI | Core function is database lookup | Low | Thin wrapper, all logic in CLI |
| Parse CLI JSON output | Programmatic result handling | Low | `--format json` flag |
| Report match quality tiers | User needs context: exact match vs possible vs no match | Low | ≥0.95 exact, 0.65-0.85 possible, <0.50 no match |
| Offer CASE escalation on no match | Natural workflow: dereplication → CASE if unknown | Low | "No match found. Run CASE? [Y/n]" |
| Support direct Bruker path input | Consistent with existing workflows | Low | Auto-detect experiment numbers |
| Support shift list input | Fallback when no spectrum available | Low | `--shifts "155.08,151.58,..."` |

**Dependencies:**
- Existing: `lucy dereplicate c13` CLI command
- Existing: Database with 928K compounds

### 4. /lucy-ng:predict — Standalone Prediction

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Wrap `lucy predict c13` CLI | Core function is HOSE lookup | Low | Thin wrapper, all logic in CLI |
| Parse prediction results | Programmatic access to shifts | Low | JSON output with atom indices, shifts, confidence |
| Validate SMILES input | Prevent crashes from invalid input | Low | Use RDKit validation |
| Report prediction confidence | User needs quality signal | Low | Based on HOSE stats count and std |
| Auto-detect database | Default to standard path | Low | data/reference/lucy-ng-derep.db |
| Support custom database path | Advanced users, testing | Low | --db option |

**Dependencies:**
- Existing: `lucy predict c13` CLI command
- Existing: Database with 7.9M HOSE statistics

### 5. /lucy-ng:status — Environment Readiness Check

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Check lucy-ng installation | Prerequisite for all operations | Low | `lucy --version` |
| Check LSD solver availability | Required for CASE | Low | `lucy lsd check` |
| Check database installation | Required for dereplication and prediction | Low | Verify data/reference/lucy-ng-derep.db exists |
| Report database statistics | User needs context about coverage | Low | Compound count, HOSE stats count |
| Check Python dependencies | Troubleshooting aid | Medium | nmrglue, rdkit, pydantic versions |
| Recommend fixes for missing components | Actionable guidance | Low | Download URLs, install commands |

**Dependencies:**
- Existing: All CLI commands for capability checking

### 6. /lucy-ng Landing Page (Replacement for Monolithic Skill)

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Route to sub-command skills | Discovery mechanism | Low | "For CASE: /lucy-ng:case" |
| Describe each sub-command's purpose | User needs to know which to invoke | Low | One-line description per skill |
| No direct functionality | Pure router/documentation | Low | All work delegated to sub-commands |
| Deprecation notice for old skill | Migration path for existing users | Low | "Old /lucy-ng skill replaced by sub-commands" |

**Dependencies:**
- All sub-command skills must exist first

---

## Differentiators

Features that set lucy-ng apart from other CASE systems. Not expected, but provide competitive advantage.

### 1. Autonomous CASE with Supervision Loop

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Full autonomy until stuck | Agent completes CASE without manual intervention | High | Option A architecture: run to completion or report stuck |
| Progress transparency via CASE-PROGRESS.md | User can observe reasoning without interrupting | Medium | Human-readable markdown, AI-parseable structure |
| Advisory intervention model | Maintains agent autonomy while preventing loops | Medium | Supervisor constrains WHAT to fix, not HOW |
| Diagnostic specialist delegation | Deep root cause analysis for complex failures | High | Separate agent with LSD manual knowledge |
| Escalation with diagnostic context | When stuck, provide actionable insights | Medium | Not just "failed" but "why failed" |

**Why differentiating:** Most CASE systems are either fully manual (user builds constraints) or black-box automated (no intervention). Lucy-ng's supervised autonomy combines the best of both.

**Complexity drivers:**
- Detecting loops requires pattern matching across iteration history
- Root cause diagnosis requires deep LSD domain knowledge
- Advisory guidance requires translating technical findings to actionable constraints

### 2. AI-Driven Dataset Sanitisation

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Semantic identifier detection | Recognizes compound names that patterns cannot | High | Requires chemistry domain knowledge |
| Multi-format identifier coverage | SMILES, InChI, CAS, MOL, chemical names | Medium | Hybrid pattern + reasoning approach |
| Blind evaluation workflow | Removes AI contamination for unbiased CASE | Medium | Critical for scientific validation |
| Verification loop | Confirms complete sanitisation | Low | Re-extract and review |
| NO CLI footgun | Explicitly prevents false security from automated approach | Low | Documents limitation clearly |

**Why differentiating:** No other CASE system addresses the AI contamination problem. Publishing blind evaluation results requires this capability.

**Complexity drivers:**
- Chemical name detection is NLP-hard: "Caffeine" vs "Indigo" vs "Classics_Indigo"
- Requires AI to apply chemistry knowledge to determine if text is a compound identifier
- Must balance thoroughness (catch everything) with false positives (don't redact legitimate text)

### 3. Iterative Agent Spawning with Convergence Monitoring

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Multi-iteration agent lifecycle | CASE agent continues across multiple spawns | Medium | Unlike one-shot GSD executors |
| Convergence criteria tracking | Automatic success detection | Medium | Solution count trends, MAE differentiation |
| Hard safety cap at ~20 iterations | Prevents runaway token consumption | Low | Report best available result |
| Plateau detection and strategy adaptation | Knows when to stop vs try different approach | Medium | Distinguish "good enough" from "stuck" |

**Why differentiating:** Most agent orchestrators are one-shot (plan → execute → done). CASE requires iterative refinement with dynamic strategy adjustment.

**Complexity drivers:**
- Supervisor must maintain state across multiple agent spawns
- Convergence is multi-signal: solution count, MAE spread, constraint effectiveness
- Plateau handling requires distinguishing "stuck" from "good enough"

---

## Anti-Features

Features to explicitly NOT build. Common mistakes or tempting additions that would harm the system.

### 1. Dereplication in CASE Orchestrator

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| CASE orchestrator attempts dereplication before spawning CASE agent | Violates separation of concerns, creates confusion about when dereplication happens | Dereplication is a separate sub-command. If user wants it, they invoke /lucy-ng:dereplicate explicitly |
| "Try dereplication first" logic in CASE skill | User already decided to run CASE by invoking the skill | Assume user has already tried dereplication if they wanted it |
| Automatic dereplication before CASE | Hidden behavior, wastes time for known unknowns | Make workflow explicit: dereplicate THEN case, or skip to case |

**Rationale:** The Virgiline (CASE7) failure revealed that mixing dereplication into CASE creates confusion and wasted iterations. User invokes CASE skill → user wants CASE, not dereplication.

**Design principle:** One sub-command, one purpose. If user wants both, they invoke both.

### 2. CLI Command for Sanitisation

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| `lucy sanitize <path>` CLI command | Gives false sense of security — patterns cannot detect semantic identifiers like "Caffeine" | No CLI. Skill explicitly documents: "There is no CLI for sanitisation. It requires AI reasoning." |
| Automated pattern-only sanitisation | Misses chemical names, creates undetected contamination | AI reviews extracted text, applies chemistry knowledge, generates manifest |
| "One-click" sanitisation promise | Impossible to deliver correctly, undermines scientific validity | Emphasize that sanitisation is thorough manual review with AI assistance |

**Rationale:** Chemical names are semantic, not syntactic. "Indigo" could be many things. Only AI with chemistry knowledge can identify it as a compound name. A CLI would make users think they're safe when they're not.

**Design principle:** If correctness requires reasoning, don't pretend automation works.

### 3. Directive Intervention in Supervision

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| "Change line 15 from X to Y" interventions | Removes CASE agent autonomy, creates brittle coupling | Advisory: "Check sp2 count is even before retrying" |
| Directly editing LSD files from supervisor | Supervisor becomes executor, defeats purpose of delegation | Supervisor diagnoses, advises; CASE agent implements fix |
| "Add this exact constraint" commands | Agent cannot learn or adapt strategy | Explain WHAT is wrong and WHY, let agent decide HOW to fix |

**Rationale:** The supervisor orchestrates, does not execute. Directive control creates tight coupling and removes agent autonomy. Advisory guidance maintains separation and allows agent to learn.

**Design principle:** Supervisor constrains WHAT must be addressed, agent retains autonomy for HOW.

### 4. Global Intervention Counter

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Single counter for all loop types | Prevents targeted diagnosis, escalates too early or too late | Per-pattern counters: count_elim, count_zero, count_explosion, count_churning |
| "10 interventions total" threshold | Different patterns have different root causes and fix strategies | Escalate after 10 cycles WITH THE SAME PATTERN |

**Rationale:** ELIM thrashing (sp2 count issue) is unrelated to solution explosion (need heteroatom constraints). Conflating them produces poor diagnostics.

**Design principle:** Track state relevant to the failure mode.

### 5. One-Shot CASE Execution

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| CASE agent spawned once, returns result | CASE requires iterative refinement, cannot complete in one shot | Multi-iteration lifecycle: spawn → monitor → intervene → re-spawn |
| No progress monitoring | Supervisor cannot detect loops or provide guidance | CASE-PROGRESS.md after every iteration |
| "Run until done" without safety cap | Token consumption runaway, stuck in unproductive loops | Hard cap at ~20 iterations, escalate if not converged |

**Rationale:** CASE is inherently iterative. Initial constraints (MULT + HSQC) produce hundreds of solutions. HMBC batches incrementally refine. Pretending it's one-shot ignores the domain.

**Design principle:** Match agent lifecycle to task structure.

### 6. Embedding Skill Knowledge in Orchestrator

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| CASE domain knowledge (HMBC strategy, LSD commands) in orchestrator skill | Duplication, drift, maintenance burden | Orchestrator references skill/SKILL.md, does not duplicate |
| Diagnostic procedures in orchestrator | Bloat, wrong level of abstraction | Supervisor has loop detection and basic diagnosis, delegates deep diagnosis to specialist |
| LSD manual in supervisor skill | Wrong specialist | Diagnostic specialist references skill/diagnostic/SKILL.md |

**Rationale:** Knowledge should live in one canonical place. Orchestrator coordinates; specialists hold domain expertise.

**Design principle:** Reference, don't duplicate. Separation of concerns applies to knowledge, not just code.

---

## Feature Dependencies

```
Dependency flow (features that require other features):

/lucy-ng:case orchestrator
├─ Autonomous CASE agent definition (NEW, critical path)
├─ CASE-PROGRESS.md format (EXISTING: skill/supervisor/SKILL.md Section 7)
├─ Loop detection patterns (EXISTING: skill/supervisor/SKILL.md Section 4)
├─ Diagnostic specialist agent (EXISTING: .claude/agents/diagnostic-specialist.md, needs orchestrator integration)
├─ skill/SKILL.md (EXISTING: CASE workflow knowledge)
└─ skill/supervisor/SKILL.md (EXISTING: supervisor knowledge)

/lucy-ng:sanitise orchestrator
├─ lucy_text_extractor.py (EXISTING: skill/sanitize/)
├─ lucy_bulk_sanitize.py (EXISTING: skill/sanitize/)
├─ Chemistry domain knowledge for identifier detection (EXISTING: in AI training)
└─ Sanitisation workflow documentation (NEW: how to use the helpers)

/lucy-ng:dereplicate
├─ lucy dereplicate c13 CLI (EXISTING)
└─ Database with 928K compounds (EXISTING)

/lucy-ng:predict
├─ lucy predict c13 CLI (EXISTING)
└─ Database with 7.9M HOSE stats (EXISTING)

/lucy-ng:status
├─ All lucy CLI commands (EXISTING)
└─ Environment check logic (NEW: minimal wrapper)

/lucy-ng landing page
└─ All sub-command skills exist (DEPENDENT on above)
```

**Critical path:** Autonomous CASE agent definition is the only truly new component. Everything else either exists or is thin orchestration wrappers.

---

## MVP Recommendation

For v2.1 MVP, prioritize in this order:

### Must Have (Core Value)

1. **/lucy-ng:case orchestrator** — Delivers the core value of autonomous supervised CASE
   - Spawn autonomous CASE agent via Task tool
   - Monitor CASE-PROGRESS.md
   - Detect 4 loop patterns
   - Basic diagnosis + advisory intervention
   - Per-pattern intervention counters
   - Escalation after 10 cycles
   - NEVER attempt dereplication (anti-pattern enforcement)

2. **Autonomous CASE agent definition** — The worker agent that CASE orchestrator spawns
   - Full CASE workflow implementation
   - Write CASE-PROGRESS.md after every iteration
   - Implement advisory constraints from supervisor
   - Follow skill/SKILL.md CASE methodology

3. **/lucy-ng landing page** — Discovery mechanism for new sub-command structure
   - Route to sub-commands
   - Deprecation notice for old skill

### Should Have (Quick Wins)

4. **/lucy-ng:dereplicate** — Simple, existing functionality (Low effort, high clarity)
5. **/lucy-ng:predict** — Simple, existing functionality (Low effort, high clarity)
6. **/lucy-ng:status** — Useful for troubleshooting (Low effort, prevents support burden)

### Could Have (Lower Priority)

7. **/lucy-ng:sanitise** — Important for blind evaluation, but not critical for basic CASE workflows
   - Can be deferred to v2.2 if timeline is tight
   - Users can manually sanitise for now

8. **Diagnostic specialist delegation** — Nice to have for deep failures, but basic diagnosis handles most cases
   - Can be deferred if autonomous CASE + basic supervision works well
   - Add when failure patterns reveal need

### Defer to Post-MVP

- Interactive CASE mode with user feedback loop
- COSY correlation support
- Stereochemistry handling
- Advanced convergence strategies

**Rationale for ordering:**
- MVP delivers core value: working autonomous supervised CASE (items 1-3)
- Quick wins add clarity with minimal effort (items 4-6)
- Lower priority items are nice-to-have but not critical for v2.1 goal (items 7-8)

**Timeline estimate:**
- Must Have: 2-3 phases (CASE orchestrator + agent definition + landing page)
- Should Have: 1 phase (3 simple wrappers in parallel)
- Could Have: 1-2 phases (sanitise is medium complexity, diagnostic delegation needs integration work)

**Success criteria for MVP:**
- User invokes `/lucy-ng:case` with compound path and formula
- Orchestrator spawns autonomous CASE agent
- Agent iterates through CASE workflow, writing CASE-PROGRESS.md
- Supervisor detects if stuck, diagnoses, intervenes with advisory
- Either converges to solution (≤10 candidates) or escalates with diagnostic context
- User receives ranked structures or clear escalation report

---

## Sources

**Multi-Agent Orchestration Patterns:**
- [AI Agent Orchestration Guide - Patterns and Tools (2026) | Fast.io](https://fast.io/resources/ai-agent-orchestration/)
- [AI Agent Orchestration in 2026: Coordination, Scale and Strategy](https://kanerika.com/blogs/ai-agent-orchestration/)
- [How to Build Multi-Agent Systems: Complete 2026 Guide - DEV Community](https://dev.to/eira-wexford/how-to-build-multi-agent-systems-complete-2026-guide-1io6)
- [Multi Agent Orchestration: The new Operating System powering Enterprise AI](https://www.kore.ai/blog/what-is-multi-agent-orchestration)
- [Choosing the right orchestration pattern for multi agent systems](https://www.kore.ai/blog/choosing-the-right-orchestration-pattern-for-multi-agent-systems)

**Agent Spawning and Supervision:**
- [2026 Agentic Coding Trends Report - Anthropic](https://resources.anthropic.com/hubfs/2026%20Agentic%20Coding%20Trends%20Report.pdf?hsLang=en)
- [The Task Tool: Claude Code's Agent Orchestration System - DEV Community](https://dev.to/bhaidar/the-task-tool-claude-codes-agent-orchestration-system-4bf2)
- [Top 10+ Agentic Orchestration Frameworks & Tools in 2026](https://aimultiple.com/agentic-orchestration)

**Research on Multi-Agent Systems:**
- [AgentOrchestra: A Hierarchical Multi-Agent Framework for General-Purpose Task Solving](https://arxiv.org/html/2506.12508v1)
- [Multi-Agent Collaboration via Evolving Orchestration](https://arxiv.org/html/2505.19591v1)

**GSD Pattern and Claude Code:**
- [GitHub - rokicool/gsd-opencode: Get-Shit-Done by TACHES for OpenCode](https://github.com/rokicool/gsd-opencode)
- [Claude Code Swarm Orchestration Skill - GitHub Gist](https://gist.github.com/kieranklaassen/4f2aba89594a4aea4ad64d753984b2ea)
- [Build Agent Skills Faster with Claude Code 2.1 Release | Medium](https://medium.com/@richardhightower/build-agent-skills-faster-with-claude-code-2-1-release-6d821d5b8179)
- [Create custom subagents - Claude Code Docs](https://code.claude.com/docs/en/sub-agents)

**Chemical Identifier Detection:**
- [How to crack a SMILES: automatic crosschecked chemical structure resolution | Journal of Cheminformatics](https://link.springer.com/article/10.1186/s13321-025-01064-7)
- [Regular Expressions for validating SMILES, InChi, InChiKey · GitHub](https://gist.github.com/lsauer/1312860/264ae813c2bd2c27a769d261c8c6b38da34e22fb)
- [Chemistry Regex: SMILES, InChi, InChiKey notation validated by regular expressions](https://www.ketikan.eu.org/2013/11/chemistry-regex-smiles-inchi-inchikey.html)
- [CAS Registry Number - Wikipedia](https://en.wikipedia.org/wiki/CAS_Registry_Number)
- [Extract the Names of Drugs & Chemicals | Healthcare NLP](https://nlp.johnsnowlabs.com/2021/11/04/ner_chemd_clinical_en.html)

**NMR Datasets and CASE Systems:**
- [Unraveling Molecular Structure: A Multimodal Spectroscopic Dataset for Chemistry](https://arxiv.org/html/2407.17492v2)
- [Blind trials of computer-assisted structure elucidation software - PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC3349476/)
- [COCONUT online: Collection of Open Natural Products database | Journal of Cheminformatics](https://jcheminf.biomedcentral.com/articles/10.1186/s13321-020-00478-9)
- [NMRShiftDB – compound identification and structure elucidation support - ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S003194220400408X)

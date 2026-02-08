# Domain Pitfalls: Adding Multi-Agent Orchestration to Existing AI Systems

**Domain:** Adding multi-agent orchestration to lucy-ng (subsequent milestone)
**Researched:** 2026-02-08
**Context:** v2.0 created paper-only multi-agent architecture that didn't work. v2.1 adds working orchestration.

---

## Overview

This document addresses pitfalls specific to **adding multi-agent orchestration to an existing AI-agent system**. These are integration pitfalls, not general multi-agent patterns.

**Critical context:** lucy-ng v2.0 defined elaborate agent definitions (supervisor.md, diagnostic-specialist.md) and extensive skill documents (827 lines supervisor skill, 1,874 lines diagnostic skill) but **never wired up actual agent spawning**. The result was a paper-only architecture that failed when tested.

v2.1's goal: Make multi-agent orchestration actually work by learning from v2.0's mistakes.

---

## Critical Pitfalls

Mistakes that cause rewrites or major issues when adding multi-agent to existing systems.

### Pitfall 1: Paper Architecture Without Validation (The v2.0 Failure)

**What goes wrong:** Defining elaborate agent architectures, skill documents, and coordination protocols without ever testing if agents can actually be spawned, communicate, or complete workflows.

**Why it happens:**
- **Documentation feels like progress** — writing 827-line supervisor skill gives illusion of completion
- **Testing deferred** — "We'll test the full flow once everything is defined"
- **Architectural purity over working code** — focus on design elegance, not functional validation
- **Missing the integration gap** — assuming Task tool works as imagined without trying it

**Consequences:**
- Months of work produces zero working orchestration
- Agent definitions don't match Claude Code's actual Task tool patterns
- Skills reference capabilities that don't exist (file-watching patterns, advanced messaging)
- Discovery of architectural problems delayed until attempted use
- User loses trust ("v2.0 says multi-agent but it doesn't work")

**Prevention:**

1. **Validation-first development:**
   ```markdown
   Phase 1: Prove agent spawning works
   - Write minimal supervisor.md (50 lines)
   - Write minimal case.md skill (100 lines)
   - Test: Spawn CASE agent via Task(), confirm it runs
   - Criterion: Agent completes one LSD iteration end-to-end

   Phase 2: Prove monitoring works
   - Add CASE-PROGRESS.md writing to CASE agent
   - Supervisor reads file after agent completes
   - Criterion: Supervisor can parse iteration data

   Phase 3: Prove iteration works
   - Spawn agent twice (initial + retry after advisory)
   - Criterion: Second spawn receives constraints from first

   THEN expand skills with full domain knowledge
   ```

2. **Minimum viable orchestration test:**
   ```bash
   # Test harness: tests/integration/test_orchestration.py
   def test_supervisor_spawns_case_agent():
       """Phase 1 validation: Can supervisor spawn CASE agent?"""
       # Simulate user request
       # Verify Task() call succeeds
       # Verify CASE agent receives instructions

   def test_case_agent_writes_progress():
       """Phase 2 validation: Does CASE agent write progress file?"""
       # Run CASE agent on test compound
       # Verify CASE-PROGRESS.md exists
       # Verify required fields present

   def test_supervisor_detects_loop():
       """Phase 3 validation: Can supervisor detect loop from progress?"""
       # Provide progress.md with loop pattern
       # Verify supervisor identifies pattern
       # Verify advisory constraint generated
   ```

3. **Incremental skill expansion:**
   ```markdown
   v2.1 milestone structure:

   Phase 1: Minimal working orchestration (100 lines total skill)
   - Supervisor spawns CASE agent
   - CASE agent runs one iteration
   - Progress written
   - VALIDATION: End-to-end test passes

   Phase 2: Add monitoring (add 200 lines skill)
   - Loop detection patterns
   - Progress parsing
   - VALIDATION: Supervisor detects ELIM thrashing

   Phase 3: Add intervention (add 300 lines skill)
   - Advisory constraint generation
   - Agent re-spawning with constraints
   - VALIDATION: Loop breaks after intervention

   Phase 4: Add domain knowledge (add 800 lines skill)
   - Full NMR reasoning
   - Diagnostic delegation
   - VALIDATION: Handles complex failure cases
   ```

4. **Red flags that you're building paper architecture:**
   - Writing agent skills before testing Task() spawning
   - Documenting coordination protocols without implementing them
   - Skill documents reference features not yet tested (file watching, advanced messaging)
   - No integration tests in test suite
   - "We'll test when it's complete" mentality

**Detection (early warning signs):**
- [ ] Agent definition files exist but no test that spawns them
- [ ] Skill documents >500 lines without working orchestration proof
- [ ] No integration test suite for multi-agent flows
- [ ] Task() call never appears in codebase or tests
- [ ] Coordination patterns documented but not validated
- [ ] "Almost ready to test" for multiple weeks

**Example from lucy-ng v2.0:**
```markdown
v2.0 deliverables (2026-02-08):
✓ supervisor.md (484 lines) — agent definition written
✓ diagnostic-specialist.md (455 lines) — agent definition written
✓ skill/supervisor/SKILL.md (827 lines) — coordination logic documented
✓ skill/diagnostic/SKILL.md (1,874 lines) — diagnostic procedures documented
✗ Test that supervisor spawns CASE agent — MISSING
✗ Test that CASE agent writes progress — MISSING
✗ Test that supervisor detects loops — MISSING
✗ Test that diagnostic specialist runs — MISSING

Result: 3,640 lines of multi-agent architecture that doesn't work.
```

**v2.1 approach:**
```markdown
Phase 1 deliverable:
✓ Minimal supervisor skill (50 lines)
✓ Minimal CASE skill (100 lines)
✓ Integration test: test_spawn_case_agent() — PASSES
✓ Integration test: test_case_writes_progress() — PASSES
✓ Validation: One end-to-end CASE run via supervisor — SUCCESS

THEN expand skills to full domain knowledge.
```

**References:**
- [Claude Code Tasks: Complete Guide to AI Agent Workflow](https://www.dplooy.com/blog/claude-code-tasks-complete-guide-to-ai-agent-workflow) — Task survival pattern requires disk persistence
- [Claude Code Todos to Tasks](https://medium.com/@richardhightower/claude-code-todos-to-tasks-5a1b0e351a1c) — Tasks saved to files survive session crashes
- [How Claude Code works](https://code.claude.com/docs/en/how-claude-code-works) — Understanding actual Task tool behavior

---

### Pitfall 2: Context Window Overflow in Agent Handoffs

**What goes wrong:** Passing 1,000+ lines of skill content to subagents via Task() instructions causes context overflow, degraded responses, or agent failures.

**Why it happens:**
- **System prompt overhead:** Each spawned agent carries system prompt + skill content + task instructions
- **Inlining temptation:** "Just include the entire skill in the spawn instruction"
- **Not understanding Task tool limits:** Assuming infinite context for subagent instructions
- **Skill bloat:** Domain knowledge documents grow to 1,000+ lines without structure

**Consequences:**
- Agent spawn fails with context limit error
- Agent receives truncated instructions (missing critical sections)
- Agent performance degrades (reasoning space squeezed by large prompt)
- Coordination overhead exceeds benefit (more tokens spent on spawning than execution)

**Context limits (2026):**
| Model | Total Context | Usable for Agent Instructions |
|-------|---------------|------------------------------|
| Sonnet 3.5 | 200K tokens | ~150K after system prompt (~100K words) |
| Opus 4.6 | 200K tokens | ~150K after system prompt (~100K words) |

**Rule of thumb:** If spawn instructions + referenced skill content > 50K tokens (~35K words), you're at risk.

**Prevention:**

1. **Skill reference pattern, not inlining:**
   ```python
   # WRONG - inlines entire skill
   Task(
       agent_type="general",
       instructions=f"""
       Perform CASE workflow.

       Here's the complete domain knowledge:
       {read_file('skill/SKILL.md')}  # 1,079 lines

       Here's the supervisor knowledge:
       {read_file('skill/supervisor/SKILL.md')}  # 827 lines

       Here's the diagnostic knowledge:
       {read_file('skill/diagnostic/SKILL.md')}  # 1,874 lines

       Now process compound X...
       """
   )
   # Total: ~3,780 lines in spawn instruction = OVERFLOW

   # RIGHT - references skills
   Task(
       agent_type="general",
       instructions="""
       Perform CASE workflow for compound at data/compound/X with formula C14H16.

       Follow workflow in skill/CASE/SKILL.md.
       Write CASE-PROGRESS.md after each LSD iteration.
       Include: iteration number, solution count, constraints added/removed, effectiveness.
       """
   )
   # Agent has access to skill files via Read tool, pulls on-demand
   ```

2. **Structured skill hierarchy:**
   ```
   skill/
   ├── SKILL.md              # Core domain knowledge (1,079 lines)
   │                         # Read on-demand by all agents
   ├── CASE/
   │   └── SKILL.md          # CASE workflow (200 lines)
   │                         # Referenced by CASE agent spawn
   ├── supervisor/
   │   └── SKILL.md          # Loop detection, intervention (827 lines)
   │                         # Used by orchestrator, NOT passed to CASE agent
   └── diagnostic/
       └── SKILL.md          # LSD diagnostics (1,874 lines)
                             # Only loaded when diagnostic specialist spawned
   ```

3. **Progressive skill loading pattern:**
   ```markdown
   In CASE agent spawn instructions:

   "Perform CASE workflow for compound X.

   Core workflow: skill/CASE/SKILL.md
   Domain knowledge: skill/SKILL.md (read sections as needed)

   Key sections you'll need:
   - Section 2 (NMR Interpretation)
   - Section 5 (HMBC Strategy)
   - Section 8 (LSD File Generation)
   - Section 10 (Ranking Solutions)

   Read other sections if you encounter issues not covered above."
   ```

4. **Skill content audit:**
   ```markdown
   For each skill file:

   [ ] Core concepts (keep) — what agent MUST know
   [ ] Reference tables (keep) — chemical shift ranges, multiplicities
   [ ] Workflow steps (keep) — what to do, in what order
   [ ] Examples (keep if <50 lines) — illustrate patterns
   [ ] Examples (move to separate file) — if >50 lines
   [ ] Redundant explanations (consolidate) — say it once clearly
   [ ] Edge case handling (move to appendix) — load on-demand

   Target: Core skill <500 lines, appendices referenced as needed
   ```

**Detection:**
- Task() spawn instruction >500 lines
- Agent spawn fails with "context limit" error
- Agent response quality degrades compared to main session
- Multiple skill files inlined in spawn instructions
- Skill files growing without structure (append-only)

**lucy-ng specific risks:**
```markdown
Current skill sizes:
- skill/SKILL.md: 1,079 lines
- skill/supervisor/SKILL.md: 827 lines
- skill/diagnostic/SKILL.md: 1,874 lines

If v2.1 tries to inline all three in diagnostic spawn:
1,079 + 827 + 1,874 = 3,780 lines (~15K tokens)

Plus spawn instruction (~500 lines = ~2K tokens)
Plus progress.md context (~200 lines = ~800 tokens)
Total spawn overhead: ~18K tokens

Risk level: MEDIUM (within limits but uses significant reasoning budget)

Mitigation: Reference pattern, not inline.
```

**References:**
- [Context Window Overflow in 2026: Fix LLM Errors Fast](https://redis.io/blog/context-window-overflow/) — System prompt overhead and tool output accumulation
- [Multi-agent orchestration for Claude Code in 2026](https://shipyard.build/blog/claude-code-multi-agent/) — Running subagents depletes context faster
- [Claude Code Multi-Agent Orchestration System](https://gist.github.com/kieranklaassen/d2b35569be2c7f1412c64861a219d51f) — Context management strategies

---

### Pitfall 3: Iterative Supervision Loops Without Termination Guarantees

**What goes wrong:** Supervisor spawns CASE agent → detects failure → spawns again → detects failure → infinite loop. No guaranteed termination.

**Why it happens:**
- **False positive detection** — supervisor sees legitimate iteration as "loop"
- **Ineffective interventions** — advisory constraints don't change agent behavior
- **No termination counter** — system never gives up
- **Ambiguous loop signals** — hard to distinguish productive iteration from unproductive thrashing

**Consequences:**
- System runs for hours without progress
- User cancels manually (supervisor never escalates)
- Cost explosion (hundreds of failed agent spawns)
- Trust erosion ("Multi-agent doesn't work")

**CASE-specific loop patterns:**

| Loop Type | Signal | False Positive Risk |
|-----------|--------|-------------------|
| ELIM thrashing | ELIM parameter changed 3+ times | LOW — clear signal |
| Zero-solution loop | 5+ consecutive iterations with 0 solutions | MEDIUM — may need exploration |
| Solution explosion | 3+ consecutive iterations with >10,000 solutions | LOW — clear signal |
| Constraint churning | Same HMBC added/removed 2+ times | MEDIUM — may be intentional hypothesis testing |
| sp2 parity oscillation | sp2 count corrected 3+ times without convergence | LOW — clear signal |

**Prevention:**

1. **Termination guarantees in orchestration logic:**
   ```python
   class CASEOrchestrator:
       MAX_SPAWN_CYCLES = 10  # Absolute limit
       MAX_PATTERN_RETRIES = 3  # Per loop pattern type

       def run_case(self, compound_path, formula):
           spawn_count = 0
           pattern_counters = {
               'elim_thrashing': 0,
               'zero_solution': 0,
               'solution_explosion': 0,
               'constraint_churning': 0,
               'sp2_oscillation': 0
           }

           while spawn_count < self.MAX_SPAWN_CYCLES:
               spawn_count += 1

               # Spawn CASE agent
               result = self.spawn_case_agent(compound_path, formula)

               if result.success:
                   return result  # SUCCESS PATH

               # Read progress, detect loop
               loop_pattern = self.detect_loop_pattern(progress_file)

               if loop_pattern:
                   pattern_counters[loop_pattern] += 1

                   if pattern_counters[loop_pattern] >= self.MAX_PATTERN_RETRIES:
                       # Pattern-specific termination
                       return self.escalate_to_user(
                           reason=f"Loop pattern '{loop_pattern}' persisted after {self.MAX_PATTERN_RETRIES} interventions",
                           progress=progress_file,
                           diagnostic_report=self.get_diagnostic_report()
                       )

                   # Intervene with advisory
                   advisory = self.generate_advisory(loop_pattern, progress_file)
                   # Retry with advisory
               else:
                   # No loop detected, legitimate failure
                   return result

           # Absolute termination after MAX_SPAWN_CYCLES
           return self.escalate_to_user(
               reason=f"CASE did not converge after {self.MAX_SPAWN_CYCLES} spawn cycles",
               progress=progress_file
           )
   ```

2. **False positive mitigation with multi-signal detection:**
   ```markdown
   Loop detection requires BOTH:
   1. Pattern signal (e.g., 3+ ELIM changes)
   2. Lack of progress signal (e.g., solution count unchanged OR all at extremes)

   Example:
   - 3 ELIM changes + solution counts (0, 0, 0) = LOOP
   - 3 ELIM changes + solution counts (0, 147, 3) = NOT LOOP (productive exploration)

   Suppression mechanism:
   CASE agent can write in progress.md:
   "SUPPRESSION: Exploring alternative sp2 assignments (need 2 more iterations)"

   Supervisor honors suppression for N iterations, then checks again.
   ```

3. **Intervention effectiveness tracking:**
   ```python
   class Advisory:
       pattern: str  # 'elim_thrashing', 'zero_solution', etc.
       constraint: str  # Specific guidance
       issued_at: int  # Iteration number

   def track_intervention_effectiveness(progress_file, advisories):
       """Did the advisory change behavior?"""
       for advisory in advisories:
           iterations_after = get_iterations_after(progress_file, advisory.issued_at)

           # Check if behavior changed
           pattern_repeated = any(
               detect_pattern(iteration) == advisory.pattern
               for iteration in iterations_after
           )

           if pattern_repeated:
               # Advisory ineffective
               return EffectivenessResult(
                   effective=False,
                   reason=f"Pattern '{advisory.pattern}' repeated after intervention"
               )

       return EffectivenessResult(effective=True)
   ```

4. **Escalation with diagnostic context:**
   ```markdown
   When escalating to user, provide:

   1. Loop pattern detected
   2. Number of intervention attempts
   3. Progress file showing iteration history
   4. Last advisory issued
   5. Diagnostic report (if specialist was called)
   6. Recommended next steps (manual intervention points)

   Example escalation:

   "CASE orchestration terminated after 10 spawn cycles without convergence.

   Loop pattern: ELIM thrashing
   Interventions attempted: 3
   Last advisory: 'Remove ELIM, verify sp2 count is even'

   Progress summary:
   - Iterations 1-3: 0 solutions, ELIM adjusted (1, 2, 3)
   - Iteration 4-6: Advisory issued, ELIM removed, still 0 solutions
   - Iterations 7-9: sp2 count corrected 3 times, oscillating even/odd

   Diagnostic report: data/compound/X/diagnostic-report.md

   Root cause hypothesis: Ambiguous hybridization for C5, C8.
   Chemical shifts (75.3, 88.1 ppm) are borderline sp2/sp3.

   Recommended action: Manual review of HSQC/HMBC for C5, C8.
   Consider chemical structure knowledge (does formula allow conjugation?)."
   ```

**Detection:**
- Supervisor spawns >5 agents without success or escalation
- Same loop pattern detected 3+ times consecutively
- Advisory issued but CASE agent behavior unchanged
- No termination condition in orchestrator code
- User has to cancel manually

**References:**
- [Our Agent Had A 4 Minute Loop. Here's How We Fixed It.](https://medium.com/data-science-collective/our-agent-had-a-4-minute-loop-heres-how-we-fixed-it-40a8142ef1a9) — Multi-signal detection prevents false positives
- [Ralph Wiggum AI Agents: The Coding Loop of 2026](https://www.leanware.co/insights/ralph-wiggum-ai-coding) — Termination guarantees in agentic systems
- [Agent Loop Definition: How AI Agents Use Iterative Processes](https://www.glean.com/ai-glossary/agent-loop) — Iterative refinement patterns with feedback

---

### Pitfall 4: File-Based Inter-Agent Communication Race Conditions

**What goes wrong:** Supervisor reads CASE-PROGRESS.md while CASE agent is writing it, getting partial/corrupted data. Coordination breaks down.

**Why it happens:**
- **Concurrent access** — both agents access same file simultaneously
- **No file locking** — standard Write tool doesn't prevent concurrent access
- **Timing assumptions** — "Agent will finish writing before I read"
- **Partial writes** — large progress files written non-atomically

**Consequences:**
- Supervisor parses incomplete progress.md, misses loop signals
- Agent sees old advisory constraints (stale read)
- Diagnostic specialist reads progress mid-update, gets inconsistent state
- Coordination failures appear non-deterministically (Heisenbug)

**File-based communication patterns in lucy-ng:**

| File | Writer | Reader | Race Condition Risk |
|------|--------|--------|-------------------|
| CASE-PROGRESS.md | CASE agent | Supervisor | HIGH — written after every iteration |
| advisory-constraints.md | Supervisor | CASE agent (re-spawn) | MEDIUM — written once per intervention |
| diagnostic-report.md | Diagnostic specialist | Supervisor | LOW — written once at end |
| compound.lsd | CASE agent | LSD solver (external) | NONE — agent waits for solver completion |

**Prevention:**

1. **Atomic write pattern:**
   ```python
   # WRONG - non-atomic write
   def write_progress(progress_data):
       with open('CASE-PROGRESS.md', 'w') as f:
           f.write(progress_data)  # Partial write visible to readers

   # RIGHT - atomic write via temp file
   import os
   import tempfile

   def write_progress_atomic(progress_data):
       # Write to temporary file first
       temp_fd, temp_path = tempfile.mkstemp(
           dir=os.path.dirname('CASE-PROGRESS.md'),
           prefix='.progress-',
           suffix='.tmp'
       )

       with os.fdopen(temp_fd, 'w') as f:
           f.write(progress_data)  # Write complete content
           f.flush()
           os.fsync(f.fileno())  # Force to disk

       # Atomic rename (replaces old file instantaneously)
       os.replace(temp_path, 'CASE-PROGRESS.md')
   ```

2. **Read-only coordination pattern:**
   ```markdown
   Coordination model:

   1. CASE agent writes CASE-PROGRESS.md
   2. CASE agent COMPLETES (Task returns)
   3. Supervisor reads CASE-PROGRESS.md (no concurrent access)
   4. Supervisor writes advisory-constraints.md
   5. Supervisor spawns NEW CASE agent with constraints

   Key: Agents never run concurrently.
   Supervisor acts as coordinator, agents are sequential workers.

   NO file locking needed — agents are serialized by Task() blocking.
   ```

3. **Skill instruction pattern:**
   ```markdown
   In CASE agent spawn instruction:

   "After completing ALL work for this iteration:
   1. Write complete CASE-PROGRESS.md with all fields
   2. Verify file is complete (all required sections present)
   3. Return control to supervisor

   DO NOT write partial progress during iteration.
   DO NOT update progress.md multiple times per iteration.
   Write once, write completely, at end of iteration."
   ```

4. **Format stability for parsing:**
   ```markdown
   CASE-PROGRESS.md format (MUST be stable for parsing):

   ## Iteration N: [Brief Description]

   **Timestamp:** YYYY-MM-DD HH:MM:SS
   **LSD File:** compound-iterN.lsd
   **Solution Count:** [number]

   **Constraints Added:**
   - [constraint 1]: [reasoning]
   - [constraint 2]: [reasoning]

   **Constraints Removed:**
   - [constraint]: [reasoning]

   **WHY:** [strategy explanation]

   **Effectiveness:** [percentage reduction / "baseline" / "over-constrained"]

   **HMBC Used:** X/Y correlations

   **Notes:**
   - sp2 count: [even/odd]
   - H budget: [matches/mismatch]
   - [other observations]

   ---

   Parser can rely on:
   - Each iteration starts with "## Iteration N:"
   - Fields use **FieldName:** format
   - Iterations separated by ---
   ```

**Detection:**
- Supervisor misses loop signals (progress file incomplete during read)
- Parsing errors ("Expected '## Iteration' but found partial line")
- Non-deterministic coordination failures (works sometimes, fails others)
- Agent receives stale advisory constraints from previous iteration
- Progress file looks correct when inspected manually (timing-dependent bug)

**lucy-ng orchestration model (no concurrent access):**

```markdown
Supervisor orchestration flow:

1. Spawn CASE agent via Task() → BLOCKS until agent completes
2. Agent writes CASE-PROGRESS.md at end
3. Agent returns
4. Supervisor reads CASE-PROGRESS.md (safe, agent finished)
5. Supervisor analyzes progress
6. If loop detected:
   - Write advisory-constraints.md
   - Spawn NEW CASE agent (includes constraints in instruction)
7. Return to step 1

Key insight: Task() is synchronous (blocking).
No concurrent file access because agents run sequentially.

Race condition risk: NONE (with blocking Task pattern)
```

**References:**
- [Feature Request: Enable Agent-to-Agent Communication for Collaborative Workflows · Issue #4993 · anthropics/claude-code](https://github.com/anthropics/claude-code/issues/4993) — File-based mailboxes are clunky and subject to race conditions
- [Race Conditions and Secure File Operations](https://developer.apple.com/library/archive/documentation/Security/Conceptual/SecureCodingGuide/Articles/RaceConditions.html) — Atomic file operations

---

### Pitfall 5: Skill File Authoring Errors Causing Silent Failures

**What goes wrong:** Agent definition YAML frontmatter has syntax errors, agent doesn't load, orchestration fails silently with "agent not found" or defaults to wrong agent type.

**Why it happens:**
- **Bad YAML = skill won't load** — small syntax errors break parsing
- **Tabs instead of spaces** — YAML rejects tabs
- **Unquoted strings with special characters** — YAML parser fails
- **Missing opening/closing `---`** — frontmatter not recognized
- **Tool permissions not declared** — agent can't use required tools
- **Agent spawning syntax errors** — Task() call malformed

**Consequences:**
- Agent definition ignored (file not loaded)
- Orchestrator spawns generic agent without domain knowledge
- Agent can't use tools (permission denied)
- Coordination logic doesn't execute (skill not active)
- Difficult to debug (no error message, just wrong behavior)

**Common YAML errors in agent definitions:**

| Error | Symptom | Fix |
|-------|---------|-----|
| Missing `---` markers | Frontmatter treated as markdown | Add `---` at start and end |
| Tabs instead of spaces | Parse error | Use spaces only (2 or 4 space indent) |
| Unquoted colon in description | Parse error | Quote entire description string |
| Tool name typo | Permission denied | Check exact tool name (case-sensitive) |
| Missing `tools:` array | Agent can't use any tools | Add `tools: [Tool1, Tool2]` |
| Wrong agent type in Task() | Spawns wrong agent | Check exact name from frontmatter |

**Prevention:**

1. **YAML validation checklist:**
   ```markdown
   Before committing agent definition:

   [ ] Frontmatter has opening `---` on line 1
   [ ] Frontmatter has closing `---` after YAML content
   [ ] No tabs (use spaces only)
   [ ] Description in quotes if contains : or special chars
   [ ] All required tools listed in `tools:` array
   [ ] Agent name matches Task() spawn calls
   [ ] YAML parses correctly (test with yamllint or parser)
   ```

2. **Minimal agent definition template:**
   ```yaml
   ---
   name: agent-name
   description: "Single-line description of agent role and when to use it"
   tools:
     - Task
     - Read
     - Write
     - Bash
   model: sonnet
   ---

   # Agent Name

   [Agent instructions and domain knowledge]
   ```

3. **Tool permission patterns for lucy-ng:**
   ```yaml
   # Orchestrator agent (supervisor):
   tools:
     - Task      # Spawn subagents
     - Read      # Read progress files
     - Write     # Write advisory constraints
     - Bash      # Run lucy CLI commands
     - Glob      # Find compound files

   # CASE agent (worker):
   tools:
     - Read      # Read spectra, progress
     - Write     # Write LSD files, progress
     - Bash      # Run lucy CLI, LSD solver
     - Glob      # Find experiment directories
     # NOT Task — CASE agent doesn't spawn subagents

   # Diagnostic specialist:
   tools:
     - Read      # Read LSD files, progress
     - Write     # Write diagnostic report
     - Bash      # Run lucy lsd analyze
     - Grep      # Search for patterns
     # NOT Task — diagnostic doesn't spawn subagents
   ```

4. **Agent spawning syntax validation:**
   ```python
   # WRONG - various syntax errors

   # 1. Wrong agent name (doesn't match definition)
   Task(
       agent_type="case-worker"  # Actual name: "case-agent"
   )

   # 2. Missing instructions
   Task(
       agent_type="case-agent"
       # No instructions field
   )

   # 3. Trying to pass complex data structures
   Task(
       agent_type="case-agent",
       instructions=instructions_dict  # Must be string
   )

   # RIGHT - correct syntax
   Task(
       agent_type="general",  # Or use custom agent name from .claude/agents/
       instructions="""
       Perform CASE workflow for compound at data/compound/X with formula C14H16.

       Follow workflow in skill/CASE/SKILL.md.
       Write CASE-PROGRESS.md after each LSD iteration.
       """
   )
   ```

5. **Agent hot-reload testing (Claude Code 2.1+):**
   ```markdown
   Development workflow:

   1. Edit .claude/agents/supervisor.md
   2. Save file (auto hot-reloads in Claude Code 2.1+)
   3. Test spawn immediately: "Spawn case agent for test compound"
   4. Observe behavior
   5. Iterate

   No need to restart session — changes take effect immediately.
   ```

**Detection:**
- Task() spawn fails with "agent type not found"
- Agent spawns but doesn't have domain knowledge (uses wrong skill)
- Permission denied errors when agent tries to use tools
- Agent behavior doesn't match definition (wrong agent loaded)
- YAML syntax error in file but no visible error message

**v2.1 validation plan:**
```markdown
Phase 1 validation includes YAML correctness:

[ ] Parse supervisor.md frontmatter with YAML library
[ ] Parse case-agent.md frontmatter with YAML library
[ ] Parse diagnostic-specialist.md frontmatter with YAML library
[ ] All parse successfully without errors
[ ] Tool names match available tools (Task, Read, Write, Bash, Glob, Grep)
[ ] Agent names match Task() spawn calls in supervisor
```

**References:**
- [Agent Skills - Claude Code Docs](https://code.claude.com/docs/en/skills) — Official skill file format
- [Build Agent Skills Faster with Claude Code 2.1 Release](https://medium.com/@richardhightower/build-agent-skills-faster-with-claude-code-2-1-release-6d821d5b8179) — Hot-reload and YAML syntax
- [Fix Common Claude Code Sub-Agent Setup Problems](https://www.arsturn.com/blog/fixing-common-claude-code-sub-agent-problems) — Common YAML errors

---

### Pitfall 6: Agent Handoff State Loss

**What goes wrong:** When spawning a fresh CASE agent for retry after intervention, the new agent doesn't remember context from previous attempt (spectra, peaks, constraints already tried).

**Why it happens:**
- **Fresh agent = blank slate** — new Task() spawn has no memory of previous agents
- **Implicit context assumption** — developer assumes "agent will remember"
- **Progress file incomplete** — doesn't capture all necessary state
- **No handoff protocol** — orchestrator doesn't explicitly pass state

**Consequences:**
- Agent repeats work already done (re-picks peaks, re-analyzes symmetry)
- Agent tries constraints already known to fail
- Efficiency loss (5x slowdown due to repeated work)
- Agent makes same mistakes (no learning across spawns)

**State categories for CASE handoff:**

| State Type | Where It Lives | Handoff Method |
|------------|----------------|----------------|
| Compound metadata | User input (path, formula) | Pass in spawn instruction |
| Spectra | Bruker files on disk | Reference path in instruction |
| Picked peaks | JSON files (hsqc_peaks.json, etc.) | Reference files OR re-pick |
| Symmetry analysis | progress.md | Parse from file |
| Constraints already tried | progress.md (iteration history) | Parse from file |
| Advisory constraints | advisory-constraints.md | Include in spawn instruction |
| Solution candidates | solutions.smi files | Reference files |

**Prevention:**

1. **Explicit handoff pattern in spawn instruction:**
   ```markdown
   Spawn instruction for retry after intervention:

   "Perform CASE workflow for compound at data/compound/X with formula C14H16.

   This is RETRY after intervention. Previous context:

   Iteration history: See CASE-PROGRESS.md (iterations 1-3)
   - Iteration 1: Baseline LSD, 0 solutions
   - Iteration 2: Added ELIM 1 0, still 0 solutions
   - Iteration 3: Added ELIM 2 0, still 0 solutions

   Loop detected: ELIM thrashing

   Advisory constraint: Remove ELIM. Verify sp2 count is even before retrying.

   DO NOT re-pick peaks (already done):
   - HSQC peaks: analysis/hsqc_peaks.json (89 peaks)
   - HMBC peaks: analysis/hmbc_peaks.json (247 peaks)

   DO NOT repeat symmetry analysis (already done):
   - Expected: 14 carbons
   - Observed: 14 peaks (no symmetry)
   - See CASE-PROGRESS.md iteration 1 for details

   Start from LSD generation with corrected constraints."
   ```

2. **Progress file as state repository:**
   ```markdown
   CASE-PROGRESS.md structure for handoff:

   ## Metadata

   **Compound:** data/compound/X
   **Formula:** C14H16
   **Started:** 2026-02-08 10:30:00

   ## Peak Picking (COMPLETED)

   **HSQC:** 89 peaks (analysis/hsqc_peaks.json)
   **HMBC:** 247 peaks → 89 validated (analysis/hmbc_peaks.json)
   **COSY:** Skipped (optional)

   ## Symmetry Analysis (COMPLETED)

   **Expected carbons:** 14
   **Observed peaks:** 14
   **Conclusion:** No molecular symmetry
   **Hydrogen budget:** 16 H assigned, matches formula

   ## LSD Iterations

   [Iteration history...]

   Key benefit: New agent can read progress.md to understand what's already done.
   ```

3. **Incremental work pattern (avoid re-work):**
   ```python
   class CASEOrchestrator:
       def spawn_case_agent(self, compound_path, formula, retry_context=None):
           if retry_context is None:
               # First spawn — full workflow
               instructions = f"""
               Perform complete CASE workflow for {compound_path} with formula {formula}.

               Steps:
               1. Peak picking (HSQC, HMBC)
               2. Symmetry analysis
               3. LSD generation and execution
               4. Solution ranking

               Write CASE-PROGRESS.md after each LSD iteration.
               """
           else:
               # Retry spawn — skip completed work
               instructions = f"""
               Continue CASE workflow for {compound_path} with formula {formula}.

               Previous context: See CASE-PROGRESS.md (iterations 1-{retry_context.last_iteration})

               Loop detected: {retry_context.loop_pattern}
               Advisory: {retry_context.advisory}

               Skip completed steps:
               - Peak picking: DONE (see progress.md)
               - Symmetry analysis: DONE (see progress.md)

               Start from: LSD generation with advisory constraints

               Constraints to avoid (already tried):
               {retry_context.failed_constraints}
               """

           return Task(
               agent_type="general",
               instructions=instructions
           )
   ```

4. **File-based state handoff:**
   ```markdown
   Handoff file structure:

   data/compound/X/
   ├── analysis/
   │   ├── hsqc_peaks.json          # Persistent state
   │   ├── hmbc_peaks.json          # Persistent state
   │   └── symmetry_analysis.json   # Persistent state
   ├── CASE-PROGRESS.md             # Iteration history
   ├── advisory-constraints.md      # From supervisor
   └── compound.lsd                 # Current LSD file

   New agent reads these files to reconstruct state.
   No implicit memory needed.
   ```

**Detection:**
- Agent re-picks peaks on retry (work already done)
- Agent re-analyzes symmetry on retry (work already done)
- Agent tries same constraint twice (no memory of failure)
- Iteration count restarts at 1 on retry (should continue from previous)
- Retry takes as long as initial attempt (no incremental benefit)

**References:**
- [The 4-Step Protocol That Fixes Claude Code Agent's Context Amnesia](https://medium.com/@ilyas.ibrahim/the-4-step-protocol-that-fixes-claude-codes-context-amnesia-c3937385561c) — Handoff artifact pattern
- [Claude Code Context: Never Lose Project State](https://claudefa.st/blog/guide/performance/context-preservation) — State preservation strategies
- [Continuous-Claude-v3: Context management for Claude Code](https://github.com/parcadei/Continuous-Claude-v3) — Ledger-based state tracking

---

### Pitfall 7: No End-to-End Test for Multi-Agent Orchestration

**What goes wrong:** Individual components tested in isolation, full orchestration never validated end-to-end, integration failures discovered in production.

**Why it happens:**
- **Unit tests feel sufficient** — "We tested each part"
- **Integration tests seen as optional** — "Too complex to set up"
- **Manual testing deferred** — "We'll test when users try it"
- **Orchestration logic not testable** — hard to mock Task() calls

**Consequences:**
- First user discovers orchestration doesn't work
- Bug reports are vague ("multi-agent failed") with no specifics
- Debugging requires full manual reproduction
- Confidence lost in multi-agent architecture

**lucy-ng v2.0 lesson:** Zero integration tests for multi-agent. Result: Paper-only architecture that didn't work when tested.

**Prevention:**

1. **Minimum viable integration test:**
   ```python
   # tests/integration/test_multi_agent_orchestration.py

   import pytest
   from pathlib import Path

   @pytest.mark.integration
   def test_case_orchestration_full_flow():
       """
       End-to-end test: Supervisor spawns CASE agent, monitors progress,
       detects loop, intervenes, retry succeeds.

       This is the MINIMUM test to prove multi-agent orchestration works.
       """
       # Setup test compound
       compound_path = "tests/data/test_compound"
       formula = "C10H14O"

       # Simulate supervisor orchestration
       orchestrator = CASEOrchestrator()

       # Run CASE (will spawn agent internally)
       result = orchestrator.run_case(compound_path, formula)

       # Assertions
       assert result.success, "CASE should complete successfully"
       assert Path(compound_path, "CASE-PROGRESS.md").exists(), "Progress file should exist"
       assert result.solution_count > 0, "Should find at least one solution"

       # Check progress file structure
       progress = read_progress_file(compound_path)
       assert "Iteration 1" in progress, "Should have baseline iteration"
       assert "HSQC peaks" in progress, "Should include peak picking"
       assert "sp2 count" in progress, "Should include checks"

   @pytest.mark.integration
   def test_loop_detection_and_intervention():
       """
       Test that supervisor detects loops and intervenes correctly.
       """
       # Setup compound that will trigger ELIM thrashing
       compound_path = "tests/data/elim_thrashing_case"
       formula = "C14H16"

       orchestrator = CASEOrchestrator()
       result = orchestrator.run_case(compound_path, formula)

       # Check intervention occurred
       progress = read_progress_file(compound_path)
       assert "Loop detected" in progress, "Should detect loop"
       assert "Advisory" in progress, "Should issue advisory"
       assert result.spawn_count > 1, "Should retry after intervention"
       assert result.spawn_count <= 10, "Should not exceed retry limit"

   @pytest.mark.integration
   def test_diagnostic_specialist_invocation():
       """
       Test that diagnostic specialist is invoked on complex failures.
       """
       compound_path = "tests/data/complex_failure_case"
       formula = "C12H10O2"

       orchestrator = CASEOrchestrator()
       result = orchestrator.run_case(compound_path, formula)

       # Check diagnostic report exists
       diagnostic_report = Path(compound_path, "diagnostic-report.md")
       assert diagnostic_report.exists(), "Diagnostic specialist should run"

       # Check report structure
       report_content = diagnostic_report.read_text()
       assert "Root Cause Analysis" in report_content
       assert "Recommendations" in report_content
   ```

2. **Integration test infrastructure:**
   ```python
   # tests/integration/orchestration_harness.py

   class OrchestrationTestHarness:
       """
       Test harness for multi-agent orchestration.
       Provides mocking and assertion utilities.
       """

       def __init__(self, test_data_dir):
           self.test_data_dir = Path(test_data_dir)
           self.spawn_log = []  # Track agent spawns

       def mock_task_spawn(self, agent_type, instructions):
           """Mock Task() call for testing"""
           self.spawn_log.append({
               'agent_type': agent_type,
               'instructions': instructions,
               'timestamp': datetime.now()
           })

           # Simulate agent execution
           return self.simulate_agent_run(agent_type, instructions)

       def assert_spawn_count(self, expected):
           """Assert number of agent spawns"""
           actual = len(self.spawn_log)
           assert actual == expected, f"Expected {expected} spawns, got {actual}"

       def assert_loop_detected(self, pattern):
           """Assert specific loop pattern was detected"""
           # Parse progress files, check for pattern detection
           pass

       def assert_advisory_issued(self, pattern):
           """Assert advisory constraint was issued"""
           # Check advisory-constraints.md exists and contains pattern-specific guidance
           pass
   ```

3. **Test data fixtures:**
   ```
   tests/data/
   ├── simple_case/           # Baseline case, should succeed in 1 iteration
   ├── elim_thrashing_case/   # Triggers ELIM thrashing loop
   ├── zero_solution_case/    # Triggers zero-solution loop
   ├── complex_failure_case/  # Requires diagnostic specialist
   └── solution_explosion_case/  # Triggers solution explosion

   Each fixture includes:
   - Bruker NMR files (realistic test data)
   - Expected outcomes (solution count, SMILES)
   - Orchestration expectations (spawn count, interventions)
   ```

4. **CI/CD integration test gate:**
   ```yaml
   # .github/workflows/test.yml

   jobs:
     unit-tests:
       # ... unit test job

     integration-tests:
       needs: unit-tests
       runs-on: ubuntu-latest
       steps:
         - name: Run integration tests
           run: pytest tests/integration/ -v --tb=short

         - name: Check orchestration coverage
           run: |
             # Verify these critical paths are tested:
             pytest tests/integration/test_multi_agent_orchestration.py::test_case_orchestration_full_flow
             pytest tests/integration/test_multi_agent_orchestration.py::test_loop_detection_and_intervention
             pytest tests/integration/test_multi_agent_orchestration.py::test_diagnostic_specialist_invocation
   ```

**Test coverage criteria for v2.1:**

```markdown
Integration tests MUST cover:

[ ] Supervisor spawns CASE agent successfully
[ ] CASE agent writes CASE-PROGRESS.md
[ ] Supervisor reads and parses progress file
[ ] Loop detection (ELIM thrashing)
[ ] Advisory constraint generation
[ ] Agent re-spawn with constraints
[ ] Termination after max retries
[ ] Diagnostic specialist invocation
[ ] Full end-to-end success path (simple case)
[ ] Full end-to-end intervention path (complex case)

Minimum 10 integration tests to prove orchestration works.
```

**Detection:**
- Test suite has unit tests but no integration tests
- No test that spawns agents via Task()
- Manual testing is the only validation
- First bug report is "orchestration doesn't work"
- No CI gate for multi-agent flows

**References:**
- [Evaluating LLM Agents in Multi-Step Workflows (2026 Guide)](https://www.codeant.ai/blogs/evaluate-llm-agentic-workflows) — Tracing and component-level validation
- [Validating multi-agent AI systems: From modular testing to system-level governance](https://www.pwc.com/us/en/services/audit-assurance/library/validating-multi-agent-ai-systems.html) — Individual validation then end-to-end testing
- [Multi-Agent Testing Systems: How Cooperative AI Agents Validate Complex Applications](https://www.virtuosoqa.com/post/multi-agent-testing-systems-cooperative-ai-validate-complex-applications) — Incremental testing strategy

---

### Pitfall 8: Smart Orchestrator, Dumb Agent (Inverted Responsibility)

**What goes wrong:** Orchestrator tries to do domain reasoning (CASE decision-making), reducing agent to passive command-executor. Loses benefit of multi-agent (agent autonomy).

**Why it happens:**
- **Control instinct** — orchestrator wants to "stay in charge"
- **Distrust of agents** — "Agent might make wrong decision"
- **Skill location confusion** — domain knowledge in orchestrator skill instead of agent skill
- **Incremental mission creep** — orchestrator "just handles this one edge case"

**Consequences:**
- Agent has no autonomy (just executes orchestrator commands)
- Orchestrator becomes complex CASE reasoner (defeats purpose of delegation)
- Hard to add new agents (orchestrator must understand their domain too)
- Coordination overhead high (orchestrator micromanages)
- System doesn't scale (orchestrator becomes bottleneck)

**Responsibility boundary for lucy-ng:**

| Responsibility | Orchestrator (Supervisor) | Worker (CASE Agent) |
|----------------|--------------------------|-------------------|
| Workflow routing | ✓ (dereplicate vs CASE) | — |
| Agent spawning | ✓ (Task() calls) | — |
| Progress monitoring | ✓ (read progress file) | — |
| Loop detection | ✓ (pattern recognition) | — |
| Advisory generation | ✓ (what to fix) | — |
| Escalation | ✓ (to user after retries) | — |
| **NMR interpretation** | **—** | **✓ (spectra, peaks)** |
| **Symmetry analysis** | **—** | **✓ (formula vs peaks)** |
| **HMBC strategy** | **—** | **✓ (which correlations)** |
| **LSD constraint building** | **—** | **✓ (atom types, bonds)** |
| **Solution ranking** | **—** | **✓ (shift prediction)** |

**Correct pattern:**
```
Orchestrator: "Loop detected (ELIM thrashing). Advisory: Remove ELIM, verify sp2 count is even."
Agent: *Understands NMR chemistry, applies knowledge to fix sp2 count, builds correct LSD file*

Orchestrator provides: WHAT is wrong (loop pattern, general guidance)
Agent provides: HOW to fix it (domain expertise, specific constraints)
```

**Antipattern:**
```
Orchestrator: "Change line 15 of compound.lsd from `MULT 5 C 2 1` to `MULT 5 C 3 1`."
Agent: *Just edits file as instructed, no reasoning applied*

Orchestrator is doing CASE domain reasoning (wrong)
Agent is reduced to text editor (wrong)
```

**Prevention:**

1. **Orchestrator skill focuses on coordination, not domain:**
   ```markdown
   skill/supervisor/SKILL.md contents:

   ✓ Loop detection patterns (ELIM thrashing, etc.)
   ✓ Advisory constraint generation (high-level guidance)
   ✓ Intervention thresholds (when to intervene)
   ✓ Escalation rules (when to give up)
   ✓ Diagnostic specialist delegation (when to call specialist)

   ✗ NMR chemical shift interpretation
   ✗ Hybridization determination
   ✗ HMBC correlation validation
   ✗ LSD file syntax details
   ✗ Solution ranking criteria

   Domain knowledge lives in skill/SKILL.md (CASE agent reads this).
   ```

2. **Agent skill contains domain expertise:**
   ```markdown
   skill/CASE/SKILL.md contents:

   ✓ NMR spectroscopy background
   ✓ Peak picking strategies (DEPT-guided, HMBC-guided)
   ✓ Symmetry analysis procedures
   ✓ Hybridization determination (shift ranges)
   ✓ LSD constraint building (atom types, bonds, correlations)
   ✓ HMBC correlation strategy
   ✓ Solution ranking with shift prediction
   ✓ Error tolerance and confidence scoring

   CASE agent is the domain expert.
   Orchestrator just monitors and intervenes when stuck.
   ```

3. **Advisory constraints are high-level, not prescriptive:**
   ```markdown
   GOOD advisories (WHAT, not HOW):

   "Loop detected: ELIM thrashing.
   Root cause: Likely constraint error masked by ELIM.
   Advisory: Remove ELIM. Verify sp2 count is even. Check H budget matches formula."

   "Loop detected: Zero solutions for 5 iterations.
   Advisory: Question one or more constraints. Consider:
   - Are all carbons correctly assigned sp2/sp3?
   - Are HMBC correlations validated against 13C positions?
   - Does molecular formula allow the proposed structure?"

   BAD advisories (HOW, too prescriptive):

   "Change C5 from sp2 (2) to sp3 (3) in MULT line."
   "Remove HMBC correlation between H at 7.2 ppm and C at 155 ppm."
   "Set ELIM parameter to 1 0."

   Agent should autonomously decide HOW to implement the advisory.
   ```

4. **Orchestrator code review checklist:**
   ```python
   # Code review for orchestrator implementation

   # RED FLAGS (orchestrator doing domain reasoning):
   if 'sp2' in advisory and any(digit in advisory for digit in '0123456789'):
       # Advisory specifies atom numbers — TOO PRESCRIPTIVE
       raise ValueError("Advisory should not specify atom numbers")

   if 'MULT' in advisory or 'HSQC' in advisory or 'HMBC' in advisory:
       # Advisory contains LSD syntax — WRONG LAYER
       raise ValueError("Advisory should not contain LSD syntax")

   if len(advisory) > 500:
       # Advisory is too long — probably contains HOW instead of WHAT
       raise ValueError("Advisory should be concise guidance, not detailed instructions")

   # GREEN FLAGS (orchestrator doing coordination):
   assert 'Loop detected' in advisory  # Pattern recognition
   assert 'Advisory:' in advisory      # High-level guidance
   assert len(advisory) < 300          # Concise
   ```

**Detection:**
- Orchestrator skill contains NMR domain knowledge (chemical shifts, hybridization)
- Advisory constraints include LSD syntax or atom numbers
- Advisory length >500 characters (too detailed)
- Agent skill is thin (just workflow steps, no domain knowledge)
- Agent doesn't exercise judgment (just follows orchestrator commands)

**Example from lucy-ng v2.1 architecture:**
```markdown
CORRECT division of responsibility:

Orchestrator (supervisor.md):
"Spawn CASE agent for compound X with formula C14H16.
Monitor progress via CASE-PROGRESS.md.
Detect loops: ELIM thrashing, zero solutions, solution explosion.
Intervene with advisory constraints when loop detected.
Escalate after 10 failed intervention cycles."

CASE Agent (spawned via Task):
Reads skill/SKILL.md (1,079 lines of domain knowledge)
Reads skill/CASE/SKILL.md (200 lines of workflow)
Applies NMR expertise to:
- Pick peaks with DEPT/HMBC guidance
- Analyze symmetry
- Determine hybridization from shifts
- Build LSD constraints
- Rank solutions with prediction

Orchestrator never sees chemical shifts or LSD syntax.
Agent never sees loop detection patterns or intervention thresholds.
```

**References:**
- [Why orchestrators become a bottleneck in multi-agent AI](https://dev.to/ablyblog/why-orchestrators-become-a-bottleneck-in-multi-agent-ai-published-4mgf) — Centralized orchestrators that do too much reasoning
- [Choosing the right orchestration pattern for multi agent systems](https://www.kore.ai/blog/choosing-the-right-orchestration-pattern-for-multi-agent-systems) — Supervisor pattern tradeoffs
- [AI Agent Orchestration Patterns - Azure Architecture Center](https://learn.microsoft.com/en-us/azure/architecture/ai-ml/guide/ai-agent-design-patterns) — Responsibility boundaries

---

## Moderate Pitfalls

Mistakes that cause delays or technical debt when adding multi-agent orchestration.

### Pitfall 9: No Incremental Migration Path

**What goes wrong:** Attempting to replace entire monolithic skill with multi-agent orchestration in one step, causing extended breakage period.

**Prevention:**
- Add orchestrator as **parallel path** initially
- Keep existing monolithic skill working
- Gradual migration: orchestrator calls existing tools first
- Feature flag for multi-agent vs monolithic mode
- Cut over once orchestration proven

### Pitfall 10: Unclear Orchestrator vs Agent Skill Boundary

**What goes wrong:** Domain knowledge duplicated between orchestrator skill and agent skill, causing inconsistencies.

**Prevention:**
- Orchestrator skill: Coordination patterns only
- Agent skill: Domain expertise only
- Shared skill: Common domain knowledge (NMR basics)
- Use skill inheritance (`skills: [lucy-ng]` in frontmatter)

### Pitfall 11: No Diagnostic Visibility

**What goes wrong:** When orchestration fails, no visibility into why (which agent failed, what was in progress file, what advisory was issued).

**Prevention:**
- Orchestrator logs all spawns, reads, advisories to orchestration.log
- Progress files persisted (not cleaned up after completion)
- Diagnostic report generated on escalation
- User can replay orchestration from logs

### Pitfall 12: Tight Coupling Between Orchestrator and Agent Format

**What goes wrong:** Orchestrator parses progress file with brittle regex, any format change in agent output breaks coordination.

**Prevention:**
- Define structured format (YAML or JSON sections in progress.md)
- Version progress file format (`version: 1.0` in header)
- Orchestrator gracefully handles missing fields (warns but continues)
- Schema validation for progress file

---

## Minor Pitfalls

Mistakes that cause annoyance but are fixable.

### Pitfall 13: Verbose Orchestration Messages

**What goes wrong:** Orchestrator logs every action to user, cluttering output with coordination details.

**Prevention:**
- Show user: "Running CASE workflow... (spawning agent)"
- Hide from user: Task() internals, progress file reads, loop detection logic
- Show user on intervention: "Loop detected, retrying with guidance"
- Show user on escalation: Full diagnostic context

### Pitfall 14: No Agent Performance Monitoring

**What goes wrong:** No visibility into agent efficiency (how long each spawn takes, token usage, retry rate).

**Prevention:**
- Log spawn time, completion time per agent
- Track token usage per spawn (if available)
- Monitor retry rate per loop pattern
- Report metrics on completion

### Pitfall 15: Hard-Coded Orchestration Constants

**What goes wrong:** MAX_SPAWN_CYCLES = 10 hard-coded in orchestrator, can't adjust without code change.

**Prevention:**
- Orchestration config file (orchestration-config.yaml)
- Environment variables for thresholds
- Documented tuning guide for production deployment

---

## Phase-Specific Warnings for v2.1

| Phase | Likely Pitfall | Mitigation |
|-------|---------------|------------|
| Sub-command skill creation | Paper architecture (writing skills before testing Task()) | Validation-first: Test spawn before expanding skills |
| Orchestrator implementation | Context overflow (inlining entire skills) | Reference pattern, not inline |
| Loop detection | False positives (intervening too early) | Multi-signal detection, suppression mechanism |
| Agent handoff | State loss across spawns | Explicit handoff, progress file as state repository |
| Integration | No end-to-end test | Minimum viable integration test suite |
| Skill authoring | YAML syntax errors | Validation checklist, hot-reload testing |
| Responsibility division | Smart orchestrator, dumb agent | Advisory constraints (WHAT not HOW) |

---

## Integration Pitfalls Summary

**Critical risks when adding multi-agent to lucy-ng v2.1:**

1. **Paper architecture** — Define-test-expand, not define-define-define
2. **Context overflow** — Reference skills, don't inline
3. **Infinite loops** — Termination guarantees, multi-signal detection
4. **Race conditions** — Atomic writes, sequential agents (blocking Task)
5. **YAML errors** — Validation checklist, hot-reload testing
6. **State loss** — Explicit handoff, progress as state repository
7. **No integration tests** — Minimum 10 tests proving orchestration works
8. **Inverted responsibility** — Orchestrator coordinates, agent reasons

**v2.1 validation gate (prevent v2.0 repeat):**

```markdown
Before declaring multi-agent orchestration complete:

[ ] Integration test: Supervisor spawns CASE agent
[ ] Integration test: CASE agent writes progress file
[ ] Integration test: Supervisor detects loop pattern
[ ] Integration test: Advisory issued and agent re-spawned
[ ] Integration test: Termination after max retries
[ ] Integration test: Full end-to-end success (simple case)
[ ] Integration test: Full end-to-end intervention (complex case)
[ ] Manual test: Run on real compound, supervisor coordinates correctly
[ ] Code review: Orchestrator doesn't contain domain reasoning
[ ] Documentation: User guide for multi-agent orchestration

ALL must pass before v2.1 ships.
```

---

## Sources

**Paper Architecture Prevention:**
- [Claude Code Tasks: Complete Guide to AI Agent Workflow](https://www.dplooy.com/blog/claude-code-tasks-complete-guide-to-ai-agent-workflow)
- [Claude Code Todos to Tasks](https://medium.com/@richardhightower/claude-code-todos-to-tasks-5a1b0e351a1c)
- [How Claude Code works](https://code.claude.com/docs/en/how-claude-code-works)

**Context Window Management:**
- [Context Window Overflow in 2026: Fix LLM Errors Fast](https://redis.io/blog/context-window-overflow/)
- [Multi-agent orchestration for Claude Code in 2026](https://shipyard.build/blog/claude-code-multi-agent/)
- [Claude Code Multi-Agent Orchestration System](https://gist.github.com/kieranklaassen/d2b35569be2c7f1412c64861a219d51f)

**Iterative Supervision:**
- [Our Agent Had A 4 Minute Loop. Here's How We Fixed It.](https://medium.com/data-science-collective/our-agent-had-a-4-minute-loop-heres-how-we-fixed-it-40a8142ef1a9)
- [Ralph Wiggum AI Agents: The Coding Loop of 2026](https://www.leanware.co/insights/ralph-wiggum-ai-coding)
- [Agent Loop Definition: How AI Agents Use Iterative Processes](https://www.glean.com/ai-glossary/agent-loop)

**File-Based Communication:**
- [Feature Request: Enable Agent-to-Agent Communication · Issue #4993](https://github.com/anthropics/claude-code/issues/4993)
- [Race Conditions and Secure File Operations](https://developer.apple.com/library/archive/documentation/Security/Conceptual/SecureCodingGuide/Articles/RaceConditions.html)

**Skill File Authoring:**
- [Agent Skills - Claude Code Docs](https://code.claude.com/docs/en/skills)
- [Build Agent Skills Faster with Claude Code 2.1 Release](https://medium.com/@richardhightower/build-agent-skills-faster-with-claude-code-2-1-release-6d821d5b8179)
- [Fix Common Claude Code Sub-Agent Setup Problems](https://www.arsturn.com/blog/fixing-common-claude-code-sub-agent-problems)

**Agent Handoff:**
- [The 4-Step Protocol That Fixes Claude Code Agent's Context Amnesia](https://medium.com/@ilyas.ibrahim/the-4-step-protocol-that-fixes-claude-codes-context-amnesia-c3937385561c)
- [Claude Code Context: Never Lose Project State](https://claudefa.st/blog/guide/performance/context-preservation)
- [Continuous-Claude-v3: Context management](https://github.com/parcadei/Continuous-Claude-v3)

**Testing Multi-Agent:**
- [Evaluating LLM Agents in Multi-Step Workflows (2026 Guide)](https://www.codeant.ai/blogs/evaluate-llm-agentic-workflows)
- [Validating multi-agent AI systems](https://www.pwc.com/us/en/services/audit-assurance/library/validating-multi-agent-ai-systems.html)
- [Multi-Agent Testing Systems](https://www.virtuosoqa.com/post/multi-agent-testing-systems-cooperative-ai-validate-complex-applications)

**Orchestration Patterns:**
- [Why orchestrators become a bottleneck in multi-agent AI](https://dev.to/ablyblog/why-orchestrators-become-a-bottleneck-in-multi-agent-ai-published-4mgf)
- [Choosing the right orchestration pattern](https://www.kore.ai/blog/choosing-the-right-orchestration-pattern-for-multi-agent-systems)
- [AI Agent Orchestration Patterns - Azure](https://learn.microsoft.com/en-us/azure/architecture/ai-ml/guide/ai-agent-design-patterns)

**Claude Code Agent Patterns:**
- [Create custom subagents - Claude Code Docs](https://code.claude.com/docs/en/sub-agents)
- [The Task Tool: Claude Code's Agent Orchestration System](https://dev.to/bhaidar/the-task-tool-claude-codes-agent-orchestration-system-4bf2)
- [Claude Code Swarm Orchestration Skill](https://gist.github.com/kieranklaassen/4f2aba89594a4aea4ad64d753984b2ea)

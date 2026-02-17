# Phase 44: CASE-PROGRESS.md Format - Research

**Researched:** 2026-02-17
**Domain:** Multi-agent journal format design and coordinator-as-sole-writer protocol
**Confidence:** HIGH (all findings grounded in Phase 42/43 shipped artifacts and existing orchestrator parsing logic)

---

## Summary

Phase 44 has a narrow scope: define the multi-agent CASE-PROGRESS.md format and establish who writes it, when, and how the orchestrator parses it. All prior context is already established by Phases 41-43.

The critical tension to resolve is **SC2 ("Coordinator is sole writer")** vs the current Phase 42 design where `lucy-lsd-engineer` is the de-facto CASE-PROGRESS.md writer (its job description says "write CASE-PROGRESS.md entries after every LSD run", Section 4 is the authoritative format spec, and it has Write tool access). The roadmap wants the coordinator (orchestrator skill) to be the sole writer, with agents posting results to the team via SendMessage. This is a deliberate protocol change — not a mistake in Phase 42 — and Phase 44 must specify it precisely.

The format itself is already 80% designed in ARCHITECTURE.md (Section 4) with concrete examples including per-agent sections, iteration headers, constraint inventory deltas, and diagnostic intervention blocks. Phase 44's job is to formalize this design as agent-executable instructions, not to design it from scratch.

Backward-compatibility (SC4) is a real constraint: the orchestrator's `monitor_progress` step parses CASE-PROGRESS.md to extract `solution count`, `constraints added/removed`, `sp2 checks`, `H budget status`, and `HMBC correlations used (X/Y)`. All of these fields already appear in the v3.0 format. The multi-agent format must preserve these field names and their positions within `## Iteration N:` sections.

**Primary recommendation:** Phase 44 is a documentation and protocol clarification phase. Write two plans: (1) specify the coordinator-as-sole-writer protocol and update agent instructions, (2) define the per-agent contribution format and update the orchestrator's parsing logic to handle multi-agent sections.

---

## What Was Shipped by Prior Phases (Critical Context)

### Phase 42: Agent Definitions (COMPLETE)

Agents created at `~/.claude/agents/`:
- `lucy-nmr-chemist.md` (224 lines) — has Write tool, does NOT write CASE-PROGRESS.md
- `lucy-lsd-engineer.md` (306 lines, extended to 394 in Phase 43) — has Write tool, IS the current CASE-PROGRESS.md writer
- `lucy-solution-analyst.md` (211 lines) — has Write tool
- `lucy-devils-advocate.md` (221 lines, extended to 299 in Phase 43) — NO Write tool (read-only)

Current lsd-engineer job description says: "write CASE-PROGRESS.md entries after every LSD run." Section 4 of lucy-lsd-engineer.md is the "Authoritative Specification" of CASE-PROGRESS.md format.

### Phase 43: Constraint Inventory System (COMPLETE)

- lsd-engineer writes JSON inventory block at top of every LSD file
- devils-advocate reads and validates the inventory block with three-check reconciliation
- Both files updated; constraint inventory is in LSD files, not in CASE-PROGRESS.md

### Phase 41: Orchestrator Skill (COMPLETE)

The orchestrator (`~/.claude/commands/lucy-ng/case.md`) parses CASE-PROGRESS.md by reading:
- `solution count` per iteration (for loop detection)
- `constraints added/removed` per iteration (for CONSTRAINT_CHURNING detection)
- `sp2 count` and `H budget` from Notes sections
- `HMBC correlations used: X/Y` (for SOLUTION_EXPLOSION check)
- Last `iteration number` (for safety cap)

These are parsed from Markdown fields in `## Iteration N:` sections. No regex or structured parse — the orchestrator (an LLM) reads the Markdown prose.

---

## Architecture Patterns

### Pattern 1: Coordinator-as-Sole-Writer

**What:** The orchestrator skill (coordinator) is the only agent that writes to `analysis/CASE-PROGRESS.md`. Specialist agents post structured results to the team via `SendMessage`, and the coordinator receives these messages and writes the corresponding CASE-PROGRESS.md entries.

**Why this pattern was chosen (from ARCHITECTURE.md Risk 3):**
> "Multiple agents appending concurrently may corrupt file. Fallback: Coordinator as sole writer, agents post to team only."

The roadmap SC2 makes this the primary approach, not the fallback.

**Implications for Phase 44:**
1. lsd-engineer Section 4 ("Authoritative Specification") must be relocated. The coordinator (orchestrator skill) is the authoritative writer.
2. lsd-engineer must be updated: instead of `Write` to CASE-PROGRESS.md, it sends a `SendMessage` with its iteration data.
3. nmr-chemist, solution-analyst similarly send results via `SendMessage`, not file writes.
4. The orchestrator's `deliver_advisory` step must also write to CASE-PROGRESS.md (diagnostic intervention sections).

**What agents still write:** Their own LSD files (lsd-engineer), solution files (solution-analyst). They do NOT write CASE-PROGRESS.md.

### Pattern 2: Structured SendMessage for CASE-PROGRESS Contribution

Each agent sends a structured message to the coordinator containing everything the coordinator needs to write that agent's section. The message format must be machine-parseable (the coordinator is an LLM, but a consistent template helps it extract fields correctly).

**Message template (confirmed by ARCHITECTURE.md Section 4):**

lsd-engineer → coordinator:
```
[ITERATION-COMPLETE] Iteration N
LSD file: analysis/iteration_NN/compound.lsd
Solution count: <N>
Constraints added: <list>
Constraints removed: <list or "None">
Constraint inventory delta: MULT=N, HSQC=N, HMBC=+N (total N), DEFF NOT=N, SYME=N, BOND=N
sp2 count: N (even/odd)
H budget: matches/mismatch
HMBC correlations used: X/Y
Why: <natural language reasoning>
```

nmr-chemist → coordinator:
```
[SETUP-COMPLETE] or [DETECTION-COMPLETE]
Spectra found: <list>
Peak counts: 13C: N, DEPT-135: N, HSQC: N, HMBC: N
Multiplicities: <summary>
Statistical detection: <per-shift results>
Symmetry: expected N, observed N, equivalent N
```

devils-advocate → coordinator:
```
[VALIDATION-PASSED] or [VALIDATION-BLOCKED] Iteration N
sp2 count: N (even)
H budget: N (matches formula)
DEFF NOT: N patterns (preserved/DROPPED)
SYME: N constraints (preserved/DROPPED)
Grouped notation: preserved/DROPPED
Concerns: <list or "None">
```

solution-analyst → coordinator:
```
[RANKING-COMPLETE] Iteration N
Solutions: N total
Top solution: Rank #1, SMILES: <smiles>, MAE: N ppm, Matched: N/N
Strained rings: None/found in <solutions>
Chemical plausibility: <summary>
Recommendation: <converge/continue/escalate>
```

### Pattern 3: Per-Agent Section Attribution

Each `## Iteration N:` block contains sub-sections `### <Agent-Name>` with that agent's contribution. The coordinator writes all sections sequentially as it receives messages.

**Section order within an iteration:**
1. `### Coordinator` — iteration header (time, phase, goal)
2. `### NMR-Chemist` — setup or HMBC selection (only in iteration 1 or when new batch selected)
3. `### LSD-Engineer` — constraints added, inventory delta
4. `### Devils-Advocate` — validation result, concerns
5. `### Coordinator` — LSD run result (solution count)
6. `### Solution-Analyst` — ranking, plausibility (only when solution_count <= 10 or as needed)

For diagnostic interventions, an additional block appears between iterations:
```markdown
## Diagnostic Intervention (After Iteration N)

### Orchestrator
**Pattern detected:** <name>
**Specialist spawned:** lucy-diagnostic at <timestamp>

### Diagnostic Specialist (External)
**Root cause:** <finding>
**Primary fix:** <action>

### Coordinator
**Advisory received:** <summary>
**Delegation:** <who does what>
```

### Pattern 4: Backward-Compatible Fields (SC4)

The orchestrator currently extracts these fields from CASE-PROGRESS.md:

| Field | v3.0 Location | v4.0 Location | Change? |
|-------|--------------|--------------|---------|
| `Solution count: N` | `## Iteration N:` body | `### Coordinator` sub-section | Field preserved, location slightly deeper |
| `Constraints added:` | `## Iteration N:` body | `### LSD-Engineer` sub-section | Field preserved, location in sub-section |
| `Constraints removed:` | `## Iteration N:` body | `### LSD-Engineer` sub-section | Field preserved |
| `sp2 count: N` | Notes section | `### Devils-Advocate` sub-section | Field preserved |
| `H budget: matches` | Notes section | `### Devils-Advocate` sub-section | Field preserved |
| `HMBC correlations used: X/Y` | `## Iteration N:` body | `### LSD-Engineer` sub-section | Field preserved |

**Backward-compatibility conclusion:** The orchestrator parses these fields via LLM reading, not regex. As long as the field names and values remain identical, their movement into sub-sections does not break parsing. The orchestrator's `monitor_progress` step instructions say "extract solution count", "extract constraints added/removed" — these work correctly whether fields are at the top level or inside a `### Agent` sub-section.

**Risk:** If the orchestrator's parsing instructions say "look for `Solution count:` directly under `## Iteration N:`" (level-specific), moving it to `### Coordinator` sub-section could break parsing. The current orchestrator instructions do NOT specify section depth — they say "parse the iteration history" generically. This is safe.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Concurrent write coordination | File locking, mutex, write queue | Coordinator-as-sole-writer pattern | Eliminates the problem entirely — no concurrent writes |
| CASE-PROGRESS.md parsing | Regex, JSON parser | LLM reading (existing pattern) | Orchestrator already reads Markdown with LLM; preserved in v4.0 |
| Agent contribution tracking | Separate log file, database | Sub-sections within existing `## Iteration N:` blocks | File already exists, attribution via `### Agent-Name` headers |
| Write sequencing | Message queue, timestamps | Sequential coordinator receipt + write | Messages arrive one at a time; coordinator writes after each |

---

## Common Pitfalls

### Pitfall 1: Dual-Write Conflict Between v3.0 Format and SC2

**What goes wrong:** lsd-engineer Section 4 says it writes CASE-PROGRESS.md; SC2 says coordinator is sole writer. If Phase 44 only defines the format without updating lsd-engineer's instructions, both patterns coexist and the agent will follow whichever it was trained on (Phase 42 wins — it writes the file).

**How to avoid:** Phase 44 MUST update `lucy-lsd-engineer.md` Section 4 to change the authoritative instruction from "write to CASE-PROGRESS.md" to "send structured message to coordinator". The CASE-PROGRESS.md format definition moves from lsd-engineer to the orchestrator skill.

**Warning signs:** If lsd-engineer still has `Write` to `analysis/CASE-PROGRESS.md` in its workflow steps, this pitfall is present.

### Pitfall 2: Message Format Too Loose for Coordinator to Parse

**What goes wrong:** Agents send free-form prose about their results. Coordinator can't reliably extract specific fields (solution count, sp2 count, etc.) to write correctly structured CASE-PROGRESS.md entries.

**How to avoid:** Define a structured message template for each agent (see Pattern 2 above). The template uses labeled fields (`Solution count: N`) matching what the orchestrator's detect_loops step expects.

**Warning signs:** If coordinator writes `Solution count: unknown` or leaves fields blank, the message template is too loose.

### Pitfall 3: Devils-Advocate Has No Write Tool (Already Correct)

**What goes wrong:** If Phase 44 assigns devils-advocate to write its own validation section to CASE-PROGRESS.md, this fails silently because `lucy-devils-advocate.md` has no Write tool in its frontmatter.

**How to avoid:** This is already handled. The design requires devils-advocate to `SendMessage` only. Do not add Write tool to devils-advocate — the read-only constraint is intentional (prevents it from writing LSD files).

**Confirmed from Phase 42 VERIFICATION.md:** "Devils-advocate: no Write tool — PASS"

### Pitfall 4: Coordinator Writes Section Before Agent Finishes

**What goes wrong:** Coordinator writes `### Devils-Advocate` section based on a preliminary validation message, then devils-advocate finds additional issues and sends a second message. The first entry is now wrong.

**How to avoid:** Define a single terminal message per agent per iteration. `[VALIDATION-PASSED]` and `[VALIDATION-BLOCKED]` are terminal — once sent, no follow-up within the same iteration. If devils-advocate needs to revise, it sends `[VALIDATION-REVISED]` and the coordinator appends a correction note.

### Pitfall 5: Setup Section Attribution Gap

**What goes wrong:** The v3.0 format has a `## Setup` section written by lsd-engineer with spectral data. Under the new design, nmr-chemist does the spectral analysis and sends results to coordinator. The coordinator must write the Setup section, but it does not know what to write until it receives nmr-chemist's message.

**How to avoid:** Setup section is written by coordinator AFTER receiving nmr-chemist's `[SETUP-COMPLETE]` message. The setup section attributes nmr-chemist contributions explicitly:

```markdown
## Setup

### NMR-Chemist
**DBE:** 4 (calculation: (2×13 + 2 - 18) / 2)
**Spectra found:** ...
...

### LSD-Engineer
**Constraint inventory (iteration 0):** MULT=0, HSQC=0, HMBC=0
**Plan:** Build from nmr-chemist assignments
```

---

## Code Examples

### Full Iteration Block Structure (v4.0)

```markdown
## Iteration 1: Baseline with first HMBC batch

### Coordinator
**Time:** 2026-02-17 10:24:12
**Iteration goal:** Establish baseline solution count with initial 5 HMBC correlations

### LSD-Engineer
**LSD file:** analysis/iteration_01/compound.lsd
**Constraints added:**
- HMBC C180.56-H2.45 (isolated carbon, unique proton, quaternary carbonyl)
- HMBC C132.1-H7.12 (aromatic, strong intensity)
- HMBC C44.90-H1.45 (CH2, top quartile intensity)
- HMBC C27.3-H1.05 (aliphatic, unique proton)
- HMBC C18.2-H0.89 (CH3, terminal methyl)
- BOND C1-O13 (carbonyl C=O from detection)
- DEFF NOT: 6 filters (cyclopropane, cyclobutane, aziridine, azetidine, thiirane, thietane)
**Constraints removed:** None
**Constraint inventory delta:** +15 MULT, +10 HSQC, +5 HMBC, +6 DEFF NOT, +1 BOND
**Why:** Starting with high-confidence correlations from isolated carbons

### Devils-Advocate
**Validation:** PASSED
**sp2 count:** 6 (even)
**H budget:** 18 (matches C13H18O2)
**DEFF NOT:** 6 patterns (present)
**Correlation order:** HSQC before HMBC (correct)
**Concerns:** Symmetric carbons (44.90/45.03 ppm) not encoded as SYME yet

### Coordinator
**Solution count:** 47
**HMBC correlations used:** 5/47

### Solution-Analyst
**Ranking:** 47 solutions converted and ranked
**Top solution:** Ibuprofen — MAE 2.23 ppm, 13/13 matched
**Strained rings:** None in top 10
**Recommendation:** Continue — correct structure at rank #1, add more HMBC to narrow field
```

### Orchestrator Parsing (unchanged logic, new section nesting)

The orchestrator's `monitor_progress` step extracts:
- `Solution count: 47` — appears in `### Coordinator` within `## Iteration 1:`
- `Constraints added:` — appears in `### LSD-Engineer`
- `sp2 count: 6 (even)` — appears in `### Devils-Advocate`
- `H budget: 18 (matches...)` — appears in `### Devils-Advocate`
- `HMBC correlations used: 5/47` — appears in `### Coordinator`

All fields preserved, nesting depth increases by 1 (`###` vs direct in `##`). LLM parser handles this transparently.

### Coordinator Writing Protocol (orchestrator case.md pseudocode)

```
On receive message from agent:
  1. Parse message type: [SETUP-COMPLETE] | [ITERATION-COMPLETE] | [VALIDATION-PASSED] |
     [VALIDATION-BLOCKED] | [RANKING-COMPLETE]
  2. Write corresponding section to analysis/CASE-PROGRESS.md (append)
  3. If [VALIDATION-PASSED]: proceed to run LSD (or signal lsd-engineer to run)
  4. If [VALIDATION-BLOCKED]: send message back to lsd-engineer with issues
  5. If [ITERATION-COMPLETE]: check solution count, detect loops, decide next action
```

---

## Architecture Decisions for Phase 44

### Decision 1: Format Definition Location

**Current state (Phase 42):** Format defined in `lucy-lsd-engineer.md` Section 4
**Phase 44 output:** Format defined in `~/.claude/commands/lucy-ng/case.md` (orchestrator)

The orchestrator is the writer, so the format spec lives with the writer. lsd-engineer Section 4 is replaced with: "Send structured [ITERATION-COMPLETE] message to coordinator. Do not write CASE-PROGRESS.md directly."

### Decision 2: Which Files Get Updated

| File | Change | Why |
|------|--------|-----|
| `~/.claude/agents/lucy-lsd-engineer.md` | Replace Section 4 write instructions with SendMessage instructions | lsd-engineer no longer writes CASE-PROGRESS.md |
| `~/.claude/agents/lucy-nmr-chemist.md` | Add [SETUP-COMPLETE] / [DETECTION-COMPLETE] message template | nmr-chemist sends structured results to coordinator |
| `~/.claude/agents/lucy-solution-analyst.md` | Add [RANKING-COMPLETE] message template | solution-analyst sends structured results |
| `~/.claude/agents/lucy-devils-advocate.md` | Add [VALIDATION-PASSED]/[VALIDATION-BLOCKED] message template | Already no Write tool; just needs message template |
| `~/.claude/commands/lucy-ng/case.md` | Add `write_progress` step with full format spec | Coordinator is sole writer; format spec lives here |

### Decision 3: Append Protocol

CASE-PROGRESS.md remains append-only. The coordinator writes entries in this order:
1. File header (on team start)
2. `## Setup` block (on [SETUP-COMPLETE] from nmr-chemist)
3. `## Iteration N:` block header (on starting iteration N)
4. `### LSD-Engineer` section (on [ITERATION-COMPLETE])
5. `### Devils-Advocate` section (on [VALIDATION-PASSED] or [VALIDATION-BLOCKED])
6. `### Coordinator` solution count (after LSD run)
7. `### Solution-Analyst` section (on [RANKING-COMPLETE])
8. Diagnostic intervention block (on specialist completion)

No writes happen out of this order. No agent writes CASE-PROGRESS.md directly.

---

## Standard Stack

| Component | Implementation | Notes |
|-----------|---------------|-------|
| File format | Markdown with `## Iteration N:` and `### Agent` headers | Existing pattern, backward-compatible |
| Write mechanism | `Write` tool in orchestrator skill | Case.md already has Write in allowed-tools |
| Agent output | `SendMessage` to coordinator | Already available in all agents |
| Parsing | LLM reading of Markdown (existing) | No structural parser needed |

---

## Open Questions

1. **NMR-Chemist writes setup section today?**
   - Current Phase 42 setup: nmr-chemist's job description says it documents spectral analysis. Does it currently write to CASE-PROGRESS.md directly?
   - Evidence: nmr-chemist has Write tool; its job description says "Document every detection override in CASE-PROGRESS.md under 'Conflicts with NMR evidence'"
   - **Resolution:** Phase 44 must decide whether nmr-chemist loses its Write-to-CASE-PROGRESS ability entirely (coordinator-only model) or retains it for the "Conflicts with NMR evidence" override documentation only. Recommend: coordinator-only for cleanliness.

2. **Solution-analyst writes final_results.md?**
   - The orchestrator's `present_results` step says "Read the latest iteration from CASE-PROGRESS.md and any solution files generated." Solution-analyst presumably writes `final_results.md`.
   - This is NOT CASE-PROGRESS.md — it's a separate file. Solution-analyst retains Write access for `final_results.md`. This is outside Phase 44 scope.

3. **When does coordinator write during validation failures?**
   - If [VALIDATION-BLOCKED] received, coordinator writes `### Devils-Advocate` with BLOCKED status, then sends fix request to lsd-engineer. After fix, does coordinator write a `### LSD-Engineer (revised)` section?
   - Recommend: Yes. Each validation cycle within an iteration appends a timestamped revision note.

---

## Sources

### Primary (HIGH confidence)

- `~/.planning/research/ARCHITECTURE.md` Section 4: "CASE-PROGRESS.md: Multi-Agent Journal Format" — Full proposed v4.0 format with concrete examples
- `/Users/steinbeck/.claude/agents/lucy-lsd-engineer.md` Section 4: Current authoritative format spec (v3.0 single-agent)
- `/Users/steinbeck/.claude/commands/lucy-ng/case.md` `monitor_progress` step: What fields orchestrator extracts
- `.planning/phases/42-agent-definitions/42-VERIFICATION.md`: Agent tool access confirmation (devils-advocate no Write tool)
- `.planning/phases/43-constraint-inventory-system/43-VERIFICATION.md`: Phase 43 deliverables confirmed
- `.planning/ROADMAP.md` Phase 44 success criteria (SC1-SC5)

### Secondary (MEDIUM confidence)

- `~/.planning/research/FEATURES.md` "Multi-agent CASE-PROGRESS.md" differentiator section
- `~/.planning/research/ARCHITECTURE.md` Risk 3 (file corruption) and Risk 3 fallback decision

---

## Metadata

**Confidence breakdown:**
- Format design: HIGH — ARCHITECTURE.md Section 4 has concrete examples; only needs formalization
- Coordinator-as-sole-writer protocol: HIGH — Roadmap SC2 is explicit; implications well-understood
- Agent message templates: HIGH — Field names dictated by orchestrator parsing requirements
- Backward-compatibility: HIGH — Orchestrator uses LLM reading, not regex; field names preserved
- File update scope: HIGH — Exactly 5 files; changes are incremental, not rewrites

**Research date:** 2026-02-17
**Valid until:** Until Phase 45 changes team coordination (may affect message protocol)

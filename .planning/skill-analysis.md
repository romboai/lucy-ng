# Lucy-ng Skill Set Review

Reviewed: 2026-03-10
Reviewer: Skill Creator analysis via Claude Opus 4.6
Scope: 6 sub-command skills (~1,300 lines), 6 agent definitions (~3,500 lines)

---

## Overall Impression

This is an impressively sophisticated skill set -- arguably one of the most complex multi-agent orchestrations in a Claude Code skill. The domain encoding (NMR spectroscopy, LSD solver constraints, iterative HMBC strategy) is deep and clearly battle-tested through multiple UAT rounds. The v3.0/v4.0 bug fixes show genuine learning from failures.

---

## Strengths

1. **Hard-won knowledge is inlined** -- The DEFF NOT persistence rule, 1J artifact detection, sp2 parity check, and H budget validation are all lessons from real failures, embedded exactly where agents need them.

2. **Constraint inventory system** (lsd-engineer + devils-advocate) -- The JSON-in-LSD-comments approach is clever. It gives the devils-advocate a machine-readable source of truth for regression detection.

3. **Clear role separation** -- The 4-agent team has well-defined boundaries with explicit "NEVER do X" prohibitions. This prevents overlap.

4. **Graduated intervention** -- Basic diagnosis -> specialist delegation -> user escalation is well-designed.

5. **Simpler skills are clean** -- `status.md`, `dereplicate.md`, `predict.md` are concise, well-structured, and do exactly what they should.

---

## Improvement Suggestions

### 1. Skill Descriptions Need Triggering Optimization

**Problem:** The descriptions are functional but don't help Claude trigger the skills from natural language. A user saying "I have some NMR data and need to figure out what compound this is" won't obviously match "Orchestrate 4-agent CASE team."

**Suggestions:**

| Skill | Current | Suggested |
|-------|---------|-----------|
| `lucy-ng` | "command listing" | "NMR structure elucidation toolkit. Use when user mentions NMR, chemical shifts, structure determination, HSQC, HMBC, or CASE." |
| `case` | "Orchestrate 4-agent CASE team..." | Add: "Use when user has Bruker NMR spectra and wants to determine molecular structure, solve an unknown compound, or run de novo structure elucidation." |
| `dereplicate` | "Match 13C NMR spectrum..." | Add: "Use when user wants to identify a known compound from its NMR spectrum, check if a spectrum matches any database entry." |
| `sanitise` | "Remove compound identifiers..." | Add: "Use when user wants to blind a dataset, prepare for blind testing, or remove chemical names before CASE evaluation." |

### 2. case.md Is Too Long (~1,100 lines)

**Problem:** At ~1,100 lines, `case.md` exceeds the recommended 500-line skill limit significantly. When loaded, it consumes a large fraction of the context window before any work begins.

**Suggestion:** Factor out reference material into bundled files:
- `references/progress-format.md` -- CASE-PROGRESS.md writing templates (lines 194-360, ~170 lines)
- `references/loop-patterns.md` -- Loop detection definitions (lines 906-963, ~60 lines)
- `references/advisory-templates.md` -- Intervention templates (lines 561-636, ~75 lines)

The main skill body would reference these: "For CASE-PROGRESS.md format, read `references/progress-format.md`." This keeps the orchestration flow in-context while deferring format details.

### 3. Agent Definitions Have Significant Duplication

**Problem:** Domain knowledge is duplicated across agents:
- LSD command reference appears in: `lucy-case-agent.md` (legacy), `lucy-lsd-engineer.md`, `lucy-diagnostic.md`
- NMR experiment reference appears in: `lucy-case-agent.md`, `lucy-nmr-chemist.md`
- Chemical shift regions appear in multiple agents
- The v3.0 bug checklist appears in both `lucy-devils-advocate.md` and `lucy-lsd-engineer.md`

**Suggestion:** Since each agent is spawned independently and needs self-contained knowledge, some duplication is unavoidable. However:
- `lucy-case-agent.md` (666 lines) appears to be the **legacy monolithic agent** from before the team architecture. If it's no longer spawned by `/lucy-ng:case`, consider archiving it or adding a clear deprecation header. Currently it could confuse: it's still registered as an agent type.
- Extract shared reference tables (shift regions, experiment types) into a `references/nmr-basics.md` that agents can read if needed, reducing each agent by ~30-50 lines.

### 4. Missing Error Recovery in Simpler Skills

**Problem:** `predict.md` and `dereplicate.md` have no guidance for common failure modes beyond "report the error."

**Suggestions:**
- `predict.md`: Add handling for "no predictions" (HOSE code miss) -- suggest trying a different SMILES representation or note that unusual environments may not have database coverage.
- `dereplicate.md`: Add guidance when 0 matches found -- suggest checking formula spelling, trying related formulas (e.g., with/without salt forms), or noting the compound may not be in the database.

### 5. The `sanitise.md` Skill Lacks a Dry-Run Mode

**Problem:** Sanitisation is destructive (deletes files, overwrites content in-place). There's no way to preview what would be changed before committing.

**Suggestion:** Add an optional `--dry-run` step that scans and reports findings without modifying files. The user can review the report, then confirm to proceed with actual redaction. This is especially important because the skill explicitly warns "Start a NEW AI session" -- a mistake is hard to undo.

### 6. Known Open Problems Not Reflected in Skills

**Problem:** MEMORY.md documents critical open problems from v4.0 UAT:
- 4J HMBC coupling through aromatic rings
- No aromatic ring sanity check on LSD solutions
- Solution analyst hallucinated structural claims

Yet only the solution-analyst has a partial "Check 6" for aromatic ring verification. The lsd-engineer and nmr-chemist have no awareness of 4J coupling risk.

**Suggestions:**
- **nmr-chemist**: Add a detection step for potential 4J couplings: "For aromatic systems (4+ carbons in 110-160 ppm), flag HMBC correlations between aromatic CH positions and benzylic/alpha positions as potential 4J couplings. Report these separately in [SETUP-COMPLETE] as 'Potential 4J' so lsd-engineer can defer them to later batches."
- **lsd-engineer**: Add to HMBC selection criteria: "Defer correlations flagged as potential 4J until later iterations. If these are the only remaining correlations and solutions already exist, skip them entirely."
- **solution-analyst**: The "Check 6" aromatic verification is good but should use `lucy predict c13` to verify aromatic ring presence structurally (check for aromatic carbons in predictions), not just rely on the `warnings` array.

### 7. Team Communication Could Be More Structured

**Problem:** The team relies on natural-language message passing via SendMessage with structured tags like `[SETUP-COMPLETE]`, `[ITERATION-COMPLETE]`, etc. But there's no schema validation -- an agent could send a malformed message that the orchestrator parses incorrectly.

**Suggestion:** Add a "message format validation" section to the orchestrator that explicitly lists required fields per message type. If a message is missing fields, the orchestrator should request the agent resend with complete information rather than silently proceeding with partial data. This is especially important for `[ITERATION-COMPLETE]` which the orchestrator depends on for loop detection.

### 8. The Routing Page (`lucy-ng.md`) Could Do More

**Problem:** The routing page is just a static table. It doesn't help the user choose the right workflow.

**Suggestion:** Add a decision tree:
```
Do you have a known compound and want to confirm it?
  -> /lucy-ng:dereplicate

Do you have an unknown compound and want to determine its structure?
  -> /lucy-ng:case

Do you have a SMILES and want to predict its NMR spectrum?
  -> /lucy-ng:predict

Do you want to prepare a dataset for blind evaluation?
  -> /lucy-ng:sanitise
```

### 9. No Version/Compatibility Tracking

**Problem:** Agent definitions reference specific versions (v3.0 bugs, v4.0 team architecture) but there's no mechanism to ensure the skills and agents are compatible with the installed `lucy-ng` CLI version.

**Suggestion:** Add to `status.md`: check `lucy --version` and compare against minimum required version. Report incompatibility clearly: "Your lucy-ng CLI is v0.X.Y but these skills require v0.Z.0+."

### 10. Testing Infrastructure

**Problem:** There's no way to validate these skills short of running full CASE on a real compound, which is expensive (spawns 4+ agents, takes many iterations).

**Suggestion:** Consider creating lightweight test cases:
- A pre-built `data/test/minimal/` with 2-3 Bruker experiments and known answers
- A "smoke test" mode for `/lucy-ng:case` that runs 1 iteration and verifies the pipeline works (team spawns, NMR-chemist picks peaks, LSD-engineer builds file, devils-advocate validates) without running to convergence

---

## Priority Ranking

If implementing these improvements as a milestone:

1. **Factor out case.md references** (highest impact on reliability -- context window management)
2. **Add 4J coupling awareness** (addresses the #1 known failure mode)
3. **Improve skill descriptions** (better triggering = better user experience)
4. **Archive legacy agent** (reduces confusion)
5. **Add dry-run to sanitise** (safety improvement)
6. **Missing error recovery in simpler skills** (better UX)
7. **Team communication validation** (reliability)
8. **Routing page decision tree** (UX)
9. **Version/compatibility tracking** (maintenance)
10. **Testing infrastructure** (long-term quality)

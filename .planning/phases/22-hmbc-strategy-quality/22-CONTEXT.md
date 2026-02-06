# Phase 22: HMBC Strategy and Spectral Quality - Context

**Gathered:** 2026-02-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Encode incremental HMBC constraint strategy and spectral quality assessment into SKILL.md so the AI agent builds LSD files iteratively rather than dumping all correlations at once. Also teach the agent to assess spectral quality before peak picking and adjust its strategy accordingly.

No new Python code or tools -- this phase is pure skill/knowledge authoring into existing SKILL.md.

</domain>

<decisions>
## Implementation Decisions

### Incremental HMBC strategy
- NOT a fixed 3-phase recipe -- the agent iterates continuously, adding small batches until a manageable solution set emerges
- High-confidence correlations defined by **unique carbon assignment** (no close shifts within tolerance that could cause ambiguity)
- Batch size: **3-5 HMBC correlations per iteration** -- observe solution count change before adding more
- Stopping condition: **≤10 solutions** triggers 13C prediction ranking and presentation to user
- If all HMBC correlations exhausted with >10 solutions: **rank anyway** and present top results with appropriate caveats
- "All correlations at once" approach is **strongly discouraged** but not absolutely prohibited (last resort if incremental yields nothing)
- Maximum **~10 LSD iterations** before the agent must stop and present whatever it has (prevents runaway loops before supervisor exists in Phase 24)

### Quality assessment criteria
- Agent assesses **S/N ratio, digital resolution, and artifacts** BEFORE peak picking
- Quality findings **actively modify the agent's strategy** (not just passive warnings) -- e.g., fewer correlations trusted, wider tolerances, more cautious constraint building
- Thresholds are **relative to the spectrum itself** (e.g., noise floor as % of tallest peak), not fixed absolute values
- Artifact types to teach: **Claude's discretion** on which are most relevant for automated CASE (1J leakage, t1 noise, baseline roll are candidates)

### Failure decision tree
- When ≤10 solutions but top-ranked has poor prediction quality (high MAE): **present with caveats** -- flag low confidence, let user decide plausibility
- When 0 solutions from first batch: **Claude's discretion** on whether to diagnose first or try ELIM (but ELIM should follow understanding, not be blind)
- Decision tree format: **Claude's discretion** -- choose whatever format (if/then rules, prose, or hybrid) the AI agent can follow most effectively
- Convergence strategy: **Claude's discretion** on when solution count reduction stalls vs keeps trending down
- Hard cap: **~10 LSD iterations maximum** before presenting results regardless

### Claude's Discretion
- Which HMBC artifacts to teach (1J leakage, t1 noise, baseline roll are candidates)
- Zero-solution recovery strategy (diagnose vs ELIM ordering)
- Decision tree encoding format (if/then rules vs prose vs hybrid)
- Convergence detection (when to stop adding constraints if solution count is decreasing but still >10)

</decisions>

<specifics>
## Specific Ideas

- The iterative approach emerged from the user's vision: "starts carefully and continues until no structure is found" -- this is not a rigid recipe but an adaptive loop
- ≤10 solutions as the ranking threshold was explicitly chosen by the user
- Small batches (3-5) were preferred over confidence-tier-based batching to give finer control over solution count changes

</specifics>

<deferred>
## Deferred Ideas

- No Virgiline/CASE7 case study reference in SKILL.md -- user explicitly excluded this (concerns about dataset quality)

</deferred>

---

*Phase: 22-hmbc-strategy-quality*
*Context gathered: 2026-02-06*

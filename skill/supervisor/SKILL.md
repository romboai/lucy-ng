---
name: lucy-ng:supervisor
description: >
  Orchestrates CASE workflow by selecting the right specialist skill.
  Routes between dereplication, full CASE, sanitize, and blind-case based on
  user intent. Detects unproductive loops and escalates to user.
---

# lucy-ng Supervisor

This supervisor skill orchestrates the CASE workflow by routing to the correct specialist skill and detecting unproductive loops.

**Note:** This is a foundation document. Phase 24 will significantly expand it with full supervisor agent implementation.

---

## Workflow Selection

Use this decision tree to route to the correct specialist skill:

```
Is this for blind CASE evaluation on public data?
    ├─ YES → /lucy-ng:sanitize (then fresh session)
    └─ NO → Continue

Do you want to check databases first?
    ├─ YES → /lucy-ng:dereplicate
    │         └─ Match found? → Done
    │         └─ No match? → /lucy-ng:CASE
    └─ NO (skip to full CASE) → /lucy-ng:CASE
```

**Default behavior:** The base `/lucy-ng` skill follows the full workflow: dereplication first, then CASE if no match found.

**Subskills:**
- `/lucy-ng:sanitize` - Remove compound identity from dataset (before blind CASE evaluation on public data)
- `/lucy-ng:dereplicate` - Database matching only (quick check if compound is known)
- `/lucy-ng:CASE` - Full structure elucidation (skip dereplication, for novel compounds or research evaluation)

---

## Loop Detection Patterns

These patterns detect unproductive loops and trigger interventions:

| Loop Type | Detection | Intervention |
|-----------|-----------|--------------|
| **0-solution loop** | 2+ LSD runs return 0 solutions with same approach | Invoke diagnostic: check sp2 count, H budget, correlation order (see skill/SKILL.md Section 5 LSD Reference) |
| **Solution explosion** | 2+ runs return >100 solutions | Check ELIM usage (remove if present), add more HMBC constraints |
| **ELIM thrashing** | ELIM added/removed 2+ times without diagnosing root cause | Stop and diagnose: verify sp2 count is even, verify H budget matches formula first (see skill/SKILL.md Section 5.3 Hybridization Rules) |

**Note:** Phase 24 will implement full loop detection with state tracking. This table provides the logic patterns.

---

## Escalation Criteria

Escalate to user when:

- **Conflicting data between experiments** (e.g., DEPT shows 10 carbons, 13C shows 13 carbons with no symmetry explanation)
- **Unusual chemical shifts outside normal ranges** (e.g., carbonyl at 50 ppm, aliphatic at 200 ppm)
- **Molecular formula does not match observed data** (e.g., formula indicates 13 carbons, only 8 signals observed, no symmetry detected)
- **3 failed intervention cycles with same pattern** (loop detection triggered 3 times with same root cause)
- **User requests interpretation beyond available data** (e.g., asks for stereochemistry determination without NOESY/ROESY)

---

## Routing Logic

1. **Check user intent**: blind CASE evaluation? Dereplication only? Full CASE?
2. **Route to specialist skill** based on decision tree
3. **Monitor for loops** during specialist execution (Phase 24)
4. **Apply interventions** if loop detected (Phase 24)
5. **Escalate if intervention fails** after 3 cycles

---

For CASE domain knowledge (NMR background, peak picking, symmetry, dereplication, LSD reference, ranking, workflow), see skill/SKILL.md.

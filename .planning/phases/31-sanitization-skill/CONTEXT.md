# Phase 31: Sanitization Skill — Discussion Context

**Date:** 2026-02-08
**Phase goal:** AI-driven compound identifier removal for blind dataset evaluation
**Requirements:** SCMD-03, SANT-01, SANT-02, SANT-03, SANT-04

---

## Key Decisions

### 1. Pure AI approach — no helper scripts

The sanitisation skill is entirely AI-driven. No Python helper scripts are used. The AI directly reads text files, identifies compound identifiers using semantic reasoning, and writes redacted files.

**Rationale:** This is fundamentally an AI reasoning task — identifying compound names, database IDs, and naming patterns requires semantic understanding, not regex. Scripts add complexity without value when the AI can read and write files directly.

### 2. Autonomous single-pass with report

The AI scans all text files and redacts autonomously in one pass, then presents a report of what was changed. No user approval step before redaction.

**Workflow:**
1. AI scans all text files in dataset, identifies compound identifiers
2. AI redacts identifiers (replaces with `[REDACTED]`)
3. AI presents report of all changes made
4. AI re-scans all files to verify no identifiers remain (full second pass)

### 3. Delete skill/sanitize/ directory

The existing `skill/sanitize/` directory (SKILL.md + lucy_text_extractor.py + lucy_bulk_sanitize.py) is deleted as part of this phase. The new `~/.claude/commands/lucy-ng/sanitise.md` sub-command replaces everything.

### 4. Replacement string: `[REDACTED]`

When redacting identifiers, replace with `[REDACTED]`. This is a clear marker that something was removed and is easy to search for during verification.

### 5. Verification is full re-scan

SANT-04 verification means the AI re-reads ALL text files in the dataset and confirms no identifiers remain. This is a full second pass, not just checking that specific manifest strings are gone. Catches anything missed in first pass.

### 6. SMILES/InChI detection is AI-only, best-effort

SMILES and InChI strings are not high-priority for detection because the CASE AI would need significant effort to exploit them. No regex patterns needed — rely on AI semantic recognition. If some are missed, it's acceptable.

### 7. Existing SKILL.md has useful content to preserve

The current `skill/sanitize/SKILL.md` has useful examples (compound name patterns, identifier types, dataset naming conventions) but also contains irrelevant content (instructions for CASE AI not to use compound info, which doesn't belong in a sanitisation skill). Clean up and incorporate the good parts.

---

## Existing Assets

| Asset | Location | Disposition |
|-------|----------|-------------|
| `skill/sanitize/SKILL.md` | 408 lines, workflow + examples | **DELETE** (content migrated to sanitise.md) |
| `skill/sanitize/lucy_text_extractor.py` | 301 lines, text extraction | **DELETE** (AI reads files directly) |
| `skill/sanitize/lucy_bulk_sanitize.py` | 351 lines, bulk redaction | **DELETE** (AI writes files directly) |

---

## Scope

**In scope:**
- Create `~/.claude/commands/lucy-ng/sanitise.md` sub-command skill
- Delete `skill/sanitize/` directory (SKILL.md + both scripts)
- Update routing page with sanitise command
- SANT-01: Explicit "no CLI" statement
- SANT-02: Identifier detection guidance (chemical names, CAS, SMILES, InChI, naming patterns)
- SANT-03: AI-driven redaction (no manifest file, no scripts — AI reads/writes directly)
- SANT-04: Full re-scan verification

**Out of scope:**
- Directory renaming (leave manual — noted in skill as limitation)
- Regex-based detection (pure AI reasoning)
- User approval workflow (autonomous with report)

---

## Requirements Mapping

| Requirement | How addressed |
|-------------|---------------|
| SCMD-03 | `~/.claude/commands/lucy-ng/sanitise.md` created |
| SANT-01 | Skill explicitly states "There is NO CLI command for sanitisation" |
| SANT-02 | Skill teaches identifier types: chemical names (IUPAC, common, trade), CAS numbers, SMILES, InChI/InChIKey, dataset naming patterns |
| SANT-03 | AI reads all text files, identifies identifiers, writes redacted versions with `[REDACTED]`, presents change report |
| SANT-04 | AI re-reads all text files in full second pass, confirms no identifiers remain |

---

*Captured: 2026-02-08 via /gsd:discuss-phase 31*

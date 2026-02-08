# Phase 31: Sanitization Skill - Research

**Researched:** 2026-02-08
**Domain:** AI-driven text analysis, identifier detection, file I/O at scale
**Confidence:** HIGH

## Summary

Sanitization is an AI-driven workflow for removing compound identifiers from Bruker NMR datasets to enable blind CASE evaluation. The core task is semantic pattern recognition across text files - identifying chemical names, database IDs, and metadata patterns that reveal compound identity.

The research confirms that this is fundamentally an AI reasoning task, not a regex problem. Chemical compound names vary enormously (IUPAC systematic, trivial, trade names), appear in diverse contexts (file paths, metadata, audit logs), and require semantic understanding to reliably detect without false positives.

**Primary recommendation:** Build the skill as a pure AI workflow using Claude's native Read/Write tools. The AI scans all text files, identifies identifiers using semantic reasoning, redacts in-place with `[REDACTED]`, presents a change report, then re-scans to verify completeness.

## Standard Stack

### Core Technologies
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Claude Read | native | Read text files with encoding detection | Built-in, handles UTF-8/Latin-1/CP1252 transparently |
| Claude Write | native | Overwrite files with redacted content | Built-in, atomic file operations |
| Claude Glob | native | Find text files in dataset tree | Built-in, efficient pattern matching |
| Claude Bash | native | Verify binary file patterns | For ls/find operations if needed |

### No External Dependencies
The sanitization skill requires **NO Python scripts, NO CLI commands, NO helper libraries**. This is pure AI-driven file analysis and redaction.

**Rationale:** AI semantic reasoning outperforms regex for this domain. Chemical names don't follow predictable patterns - "Ibuprofen" vs "2-(4-isobutylphenyl)propionic acid" vs "Brufen" are all the same compound. File paths contain identifiers embedded in folder names. Audit logs have free-text comments. Only AI can reliably distinguish "Unknown compound" (generic text) from "Indigo" (specific compound name).

## Architecture Patterns

### Recommended Workflow Structure

```
Phase 1: Discovery (Read-Only)
├── Find all text files (skip binary: fid, ser, 1r, 2rr, etc.)
├── Read each file's contents
├── Identify compound identifiers using semantic analysis
└── Compile redaction manifest (what to change, where)

Phase 2: Redaction (Write)
├── For each file with identifiers:
│   ├── Read current content
│   ├── Replace identifiers with [REDACTED]
│   └── Write redacted content (overwrite)
└── Present change report to user

Phase 3: Verification (Read-Only Re-Scan)
├── Re-read ALL text files (full second pass)
├── Confirm no identifiers remain
└── Report verification status
```

### Pattern 1: Text File Detection

**What:** Distinguish text files from binary NMR data files in Bruker datasets.

**When to use:** Before reading any file - must never attempt to read/modify binary spectral data.

**Example:**
```yaml
# Binary files to SKIP (never read or modify)
BINARY_PATTERNS:
  - fid, ser           # Raw FID data
  - 1r, 1i             # Processed 1D real/imaginary
  - 2rr, 2ri, 2ir, 2ii # Processed 2D data
  - 3rrr, 3rri, ...    # 3D data (8 variants)

BINARY_EXTENSIONS:
  - .pdf, .png, .jpg   # Images
  - .mol, .sdf, .cdx   # Structure files (DELETE, don't redact)

# Safe to read
TEXT_FILES:
  - title              # Experiment title (often contains compound name!)
  - acqus, acqu2s      # Acquisition parameters (file paths contain names)
  - procs, proc2s      # Processing parameters (file paths contain names)
  - *.xml              # Peak lists, metadata (may contain annotations)
  - audita.txt, auditp.txt  # Audit logs (DELETE - contain user info)
  - pulseprogram       # Pulse sequence code (safe, no compound info)
```

**Implementation:** Use Glob to find candidates, use file extension and filename pattern matching to classify. Never attempt to Read binary files.

### Pattern 2: Semantic Identifier Detection

**What:** AI reasoning to identify compound identifiers in text.

**When to use:** After reading a text file's contents - determine what needs redaction.

**Categories to detect:**

1. **Chemical names** (requires semantic understanding)
   - IUPAC systematic: "2-(4-isobutylphenyl)propionic acid"
   - Trivial names: "Ibuprofen", "Caffeine", "Indigo"
   - Trade names: "Advil", "Brufen"
   - Descriptor patterns: "Classics_Indigo", "nmrXiv_Caffeine_01"

2. **Database identifiers** (structured patterns)
   - CAS numbers: Format `xxxxxx-xx-x` (2-7 digits, 2 digits, 1 check digit)
     - Example: "482-89-3", "CAS 58-08-2"
   - InChI: Starts with "InChI=1S/" (layered structure notation)
   - InChIKey: Exactly 27 characters, format `XXXXXXXXXXXXXX-YYYYYYYYY-Z`
   - PubChem: "CID 12345", "CHEBI:12345"

3. **SMILES strings** (best-effort detection)
   - Patterns: `C`, `CC`, `c1ccccc1` (aromatic), `C(=O)O` (functional groups)
   - Caveat: Low priority - requires significant AI effort to exploit for CASE
   - Don't invest heavily in perfect SMILES detection

4. **File paths** (structural context)
   - Example: `Z:/Torsten/NMR/data/spek-vl_premium/nmr/Ibuprofen/1/pdata/1/procs`
   - Redact: "Ibuprofen" appears in path, replace in file content

5. **Dataset naming conventions**
   - nmrXiv pattern: "Classics_CompoundName"
   - Lab patterns: "JD_caffeine_01", "MC047_9" (may be coded)

**AI reasoning guide:**
- Context matters: "Unknown" is generic, "Ibuprofen" is specific
- Case variants: Search "Caffeine", "caffeine", "CAFFEINE"
- Partial matches: "Classics_Indigo" contains "Indigo"
- Negative space: Don't flag experiment types ("1H", "HSQC") or solvents ("CDCl3")

### Pattern 3: In-Place File Redaction

**What:** Overwrite files with redacted content using Write tool.

**When to use:** After identifying identifiers in a file's content.

**Example:**
```python
# Conceptual workflow (AI executes via Read/Write tools)
original_content = Read("data/Ibuprofen/1/pdata/1/procs")
# Contains: "Z:/Torsten/NMR/data/spek-vl_premium/nmr/Ibuprofen/1/pdata/1/procs"

redacted_content = original_content.replace("Ibuprofen", "[REDACTED]")
# Result: "Z:/Torsten/NMR/data/spek-vl_premium/nmr/[REDACTED]/1/pdata/1/procs"

Write("data/Ibuprofen/1/pdata/1/procs", redacted_content)
```

**Critical safety:** Claude's Write tool requires reading the file FIRST before writing (enforced by tool architecture). This prevents accidental overwrites.

### Anti-Patterns to Avoid

- **Regex-only detection:** Chemical names are too varied. "Ibuprofen" vs "ibuprofen" vs "Classics_Ibuprofen" vs file paths - semantic analysis required.
- **Interactive approval:** Don't ask "redact this file?" for each file. Autonomous single-pass with summary report.
- **Manifest files:** Don't create separate `identifiers.txt`. AI tracks findings internally, redacts immediately.
- **Helper scripts:** Don't invoke Python scripts. AI reads/writes files directly - simpler, more transparent.
- **Partial verification:** Verification must be full re-scan of ALL files, not spot-checking manifest entries.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Encoding detection | Manual UTF-8/Latin-1 logic | Claude Read (auto-detects) | Read tool handles UTF-8, Latin-1, CP1252 transparently |
| Recursive file finding | Custom directory traversal | Glob tool with `**/*` pattern | Built-in, tested, efficient |
| Binary file detection | Read-then-check logic | Filename pattern matching | Never attempt to read binary files - classify first |
| Chemical name dictionary | Hardcoded compound list | AI semantic reasoning | New compounds appear constantly, AI adapts |
| Regex pattern library | Collection of SMILES/InChI patterns | AI pattern recognition | Regex fails on naming variants, AI succeeds |

**Key insight:** This entire workflow could be implemented as Python scripts with regex (the existing `lucy_text_extractor.py` and `lucy_bulk_sanitize.py` do exactly that). But AI semantic reasoning is fundamentally superior for identifier detection, and Claude's native file I/O is simpler than maintaining scripts. Delete the scripts, use pure AI.

## Common Pitfalls

### Pitfall 1: Attempting to Redact Binary Files

**What goes wrong:** AI tries to Read a binary file (e.g., `fid`, `ser`, `2rr`), gets gibberish or errors, attempts to Write garbage back.

**Why it happens:** Not filtering files before reading. Glob returns all files, including binary data.

**How to avoid:**
1. Use filename patterns to classify BEFORE reading
2. Hardcode binary patterns: `fid`, `ser`, `1r`, `1i`, `2rr`, `2ri`, `2ir`, `2ii`, `3rrr`, etc.
3. Skip files with extensions: `.mol`, `.sdf`, `.pdf`, `.png`
4. Never attempt Read on classified binary files

**Warning signs:** Read tool returns non-text data, file sizes change after redaction, dataset becomes unreadable in NMR software.

### Pitfall 2: False Positives on Generic Terms

**What goes wrong:** Redacting "Unknown" or "Sample" or "Test" because they appear in text, even though they're generic placeholders, not compound identifiers.

**Why it happens:** Over-aggressive pattern matching without semantic context.

**How to avoid:**
- AI must distinguish generic ("Unknown compound", "Sample 1") from specific ("Ibuprofen", "CAS 58-08-2")
- Context clues: Is this a placeholder or an identifier?
- Don't redact: Experiment types (1H, 13C, HSQC), solvents (CDCl3, DMSO), generic terms

**Warning signs:** Redacted files have `[REDACTED]` in places that don't make sense ("13C NMR of [REDACTED]" where "Unknown" was generic).

### Pitfall 3: Incomplete Verification

**What goes wrong:** Verification only checks that specific manifest strings were replaced, misses identifiers that weren't detected in first pass.

**Why it happens:** Treating verification as "confirm replacements" instead of "re-scan for any remaining identifiers."

**How to avoid:**
- SANT-04 requires: "AI re-reads ALL text files and confirms no identifiers remain"
- Full second pass, not targeted checking
- AI applies same semantic reasoning as first pass
- Report: "Found 0 remaining identifiers" or "WARNING: Found X identifiers missed in first pass"

**Warning signs:** User discovers compound name in dataset after "sanitized" - verification was incomplete.

### Pitfall 4: Directory Name Leakage

**What goes wrong:** Dataset directory itself is named "Ibuprofen", AI redacts file contents but user must manually rename directory.

**Why it happens:** File I/O tools can't rename parent directories safely while working inside them.

**How to avoid:**
- Document as known limitation in skill
- Instruct user: "After sanitization, manually rename directory if needed"
- AI detects and warns: "Dataset directory name 'Ibuprofen' contains identifier - rename manually"

**Warning signs:** Clean file contents but obvious compound name in `ls` output.

### Pitfall 5: Encoding Corruption

**What goes wrong:** File contains Latin-1 or CP1252 special characters (degree symbol °, mu μ), AI reads as UTF-8, writes back with corruption.

**Why it happens:** NMR parameter files often use legacy encodings (Latin-1, Windows CP1252).

**How to avoid:**
- Claude Read tool auto-detects encoding (UTF-8, Latin-1, CP1252)
- Trust the tool - it handles this transparently
- If Read fails, skip the file (likely binary) rather than forcing UTF-8

**Warning signs:** After redaction, acqus/procs files show garbled characters where degree symbols or special characters were.

## Code Examples

Verified patterns from Claude's native tools:

### Finding All Text Files in Dataset

```bash
# Source: Claude Glob tool documentation
# Find all files recursively, then filter by patterns
Glob:
  pattern: "**/*"
  path: "/path/to/dataset"

# Returns all files - AI then filters:
# INCLUDE: title, acqus, procs, *.xml, *.txt
# EXCLUDE: fid, ser, 1r, 2rr, *.mol, *.pdf
```

### Reading Text Files with Encoding Detection

```yaml
# Source: Claude Read tool (built-in encoding detection)
# Tool automatically tries UTF-8, Latin-1, CP1252
Read:
  file_path: "/path/to/dataset/1/pdata/1/procs"

# Tool returns decoded text or error if truly binary
```

### Identifying Compound Names (AI Semantic Reasoning)

```markdown
# Example file content (procs parameter file)
##TITLE= Parameter file, TopSpin 4.1.0
$$ Z:/Torsten/NMR/data/spek-vl_premium/nmr/Ibuprofen/1/pdata/1/procs
##$SF= 499.870017809999
##$SREGLST= <1H.CDCl3>

# AI reasoning:
# - "TITLE", "SF", "SREGLST" → parameter names, not compound IDs
# - "TopSpin" → software name, not compound
# - "Ibuprofen" → COMPOUND NAME (trivial name for 2-(4-isobutylphenyl)propionic acid)
# - "CDCl3" → solvent, not compound being studied
# - "1H" → experiment type, not compound

# Action: Redact "Ibuprofen"
```

### In-Place Redaction

```yaml
# Source: Claude Write tool (requires Read first)
# Step 1: Read file (MANDATORY before Write)
Read:
  file_path: "/path/to/dataset/1/pdata/1/procs"

# Step 2: Perform replacement in content
# (AI internal operation - replace "Ibuprofen" with "[REDACTED]")

# Step 3: Write redacted content
Write:
  file_path: "/path/to/dataset/1/pdata/1/procs"
  content: |
    ##TITLE= Parameter file, TopSpin 4.1.0
    $$ Z:/Torsten/NMR/data/spek-vl_premium/nmr/[REDACTED]/1/pdata/1/procs
    ##$SF= 499.870017809999
    ##$SREGLST= <1H.CDCl3>
```

### Full Verification Re-Scan

```yaml
# Source: SANT-04 requirement - full second pass
# After redaction, re-scan ALL text files
Glob:
  pattern: "**/*"
  path: "/path/to/dataset"

# For each text file:
#   Read content
#   Apply same semantic reasoning as first pass
#   Check for ANY identifiers (not just previously found ones)
#   Report findings

# Expected result: 0 identifiers found
# Failure case: Report "Found identifiers missed in first pass: [list]"
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Helper scripts (lucy_text_extractor.py, lucy_bulk_sanitize.py) | Pure AI semantic reasoning with Read/Write | Phase 31 (2026-02-08) | Simpler workflow, better detection accuracy, no script maintenance |
| Regex-based identifier matching | AI semantic context analysis | Phase 31 | Handles naming variants, file path contexts, generic vs. specific |
| Interactive user approval per file | Autonomous single-pass with report | Phase 31 | Faster workflow, AI autonomy, user reviews summary |
| Manifest file tracking | AI internal tracking with summary | Phase 31 | Fewer files to manage, cleaner output |

**Deprecated/outdated:**
- `skill/sanitize/SKILL.md`: Replaced by `~/.claude/commands/lucy-ng/sanitise.md` (GSD sub-command pattern)
- `skill/sanitize/lucy_text_extractor.py`: Delete (AI uses Read directly)
- `skill/sanitize/lucy_bulk_sanitize.py`: Delete (AI uses Write directly)
- Regex pattern libraries for chemical identifiers: AI semantic reasoning is more reliable

**Current best practice (2026):**
- AI-driven file I/O using Claude's native Read/Write tools
- Semantic identifier detection (not regex)
- Autonomous workflow with summary reporting
- Full re-scan verification (SANT-04)

## Open Questions

Things that couldn't be fully resolved:

1. **Directory renaming during sanitization**
   - What we know: Claude can't safely rename a directory while working inside it
   - What's unclear: Should AI attempt to detect and warn, or assume user handles this?
   - Recommendation: Detect and warn with clear instruction: "Manually rename directory after sanitization"

2. **MOL/SDF file handling**
   - What we know: Structure files (.mol, .sdf, .cdx) contain compound structure, should be deleted
   - What's unclear: Should AI delete during redaction phase or instruct user to delete first?
   - Recommendation: AI deletes as part of redaction (simple Bash `rm` command), report in summary

3. **SMILES/InChI detection priority**
   - What we know: CONTEXT.md says "best-effort, not high priority"
   - What's unclear: Should skill explicitly teach SMILES/InChI patterns or leave to general AI knowledge?
   - Recommendation: Document patterns in skill for consistency, but flag as LOW priority detection

4. **Audit log handling**
   - What we know: `audita.txt`, `auditp.txt` contain timestamps, user info, possibly compound names
   - What's unclear: Redact or delete?
   - Recommendation: DELETE (align with existing SKILL.md practice) - user info is sensitive

## Sources

### Primary (HIGH confidence)
- Claude Read/Write/Glob tool documentation (official Anthropic docs)
- Bruker NMR file format structure from existing `lucy_text_extractor.py` analysis
- CONTEXT.md user decisions (locked requirements from `/gsd:discuss-phase`)

### Secondary (MEDIUM confidence)
- [5 Chemical Identifiers - Chemistry LibreTexts](https://chem.libretexts.org/Courses/University_of_Arkansas_Little_Rock/ChemInformatics_(2015):_Chem_4399_5399/Text/5_Chemical_Identifiers) - Identifier types overview
- [International Chemical Identifier - Wikipedia](https://en.wikipedia.org/wiki/International_Chemical_Identifier) - InChI format specification
- [CAS Registry Number - Wikipedia](https://en.wikipedia.org/wiki/CAS_Registry_Number) - CAS number format and validation
- [Simplified Molecular Input Line Entry System - Wikipedia](https://en.wikipedia.org/wiki/Simplified_Molecular_Input_Line_Entry_System) - SMILES format fundamentals
- [AI Redaction: Everything you need to know in 2026](https://www.redactable.com/blog/ai-redaction-everything-you-need-to-know) - AI redaction best practices
- [Claude Batch Processing - Claude API Docs](https://platform.claude.com/docs/en/build-with-claude/batch-processing) - File I/O patterns
- [GitHub - CHEMeDATA/bruker-nmr-acqus-files](https://github.com/CHEMeDATA/bruker-nmr-acqus-files) - Bruker metadata file structure
- [IUPAC nomenclature of organic chemistry - Wikipedia](https://en.wikipedia.org/wiki/IUPAC_nomenclature_of_organic_chemistry) - Chemical naming patterns

### Tertiary (LOW confidence)
- WebSearch results on encoding detection (general programming knowledge, not lucy-ng specific)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Claude native tools are authoritative, well-documented, tested
- Architecture: HIGH - Clear workflow phases, verified with existing helper scripts as reference
- Pitfalls: HIGH - Identified from real Bruker dataset analysis and CONTEXT.md decisions
- Identifier patterns: MEDIUM - Wikipedia sources verified, but AI semantic reasoning is more critical than pattern memorization

**Research date:** 2026-02-08
**Valid until:** 60 days (stable domain - chemical identifier formats don't change, AI file I/O is established)

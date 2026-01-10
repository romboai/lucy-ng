# lucy-ng State

## Current Position

**Milestone**: 1.0 — Core CASE Pipeline
**Phase**: 5.2 (Symmetry Detection from Spectroscopic Data) — COMPLETE
**Status**: Ready for Phase 6 (CLI Interface)

## Roadmap Evolution

- Phase 2.1 inserted after Phase 2: 1D Carbon Dereplication with nmrshiftdb (INSERTED)
  - Rationale: Validate pipeline works with 1D data before adding 2D complexity
- Phase 4.1 inserted after Phase 4: 2D Peak Picking Validation (INSERTED)
  - Rationale: Ensure 2D peak picking produces scientifically reasonable results
- Phase 4.2 inserted after Phase 4.1: DEPT-Guided Adaptive HSQC Peak Picking (INSERTED)
  - Rationale: DEPT provides ground truth for protonated carbons; HSQC must find all of them
- Phase 5.1 added: HMBC-Guided Peak Picking (COMPLETE)
  - Rationale: Filter HMBC noise by requiring correlation to known C and H positions
- Phase 5.2 inserted after Phase 5.1: Symmetry Detection from Spectroscopic Data (INSERTED)
  - Rationale: Molecular symmetry causes fewer NMR signals than atoms; must detect and handle for valid LSD input

## Recent Progress

- **Phase 5.2 Symmetry Detection complete**:
  - New `lucy_ng.analysis` module with AI-oriented convenience tools
  - `HydrogenBudgetAnalyzer`: Compare MF H count with observed carbon-assigned H
  - `IntensityReporter`: Report relative HSQC intensities, flag potential equivalents
  - `SymmetryAnalyzer`: Combined summary for AI-driven symmetry reasoning
  - Tools expose data with suggestions; AI makes final reasoning decisions
- Phase 5 LSD Integration complete and enhanced
- Added HMBCGuidedPicker for validated HMBC peak picking
- **Automatic spectroscopic constraint inference**:
  - Carbonyl carbons detected from chemical shift (165-185 ppm or 190-220 ppm)
  - BOND constraints auto-generated between carbonyl C and sp2 oxygen
  - Missing hydrogens (from MF vs carbon H count) assigned to sp3 oxygens
- 266 total tests passing (4 skipped when LSD not installed)

## Key Decisions

| Decision | Date | Context |
|----------|------|---------|
| Hybrid CLI + MCP interface | 2026-01-08 | MCP for agent iteration, CLI for testing |
| Bruker-only for v1 | 2026-01-08 | Focus on most common format |
| LSD/pyLSD as primary solvers | 2026-01-08 | Established CASE tools with CLI |
| nmrglue for NMR parsing | 2026-01-08 | Most mature, BSD licensed, native Bruker support |
| Pydantic v2 for models | 2026-01-08 | Type safety, validation, JSON serialization |
| hatch build system | 2026-01-08 | Modern Python packaging |
| Use processed data | 2026-01-08 | Read from pdata/1/ not raw FID |
| Multi-mode dereplication matching | 2026-01-09 | shifts_only, dept_enhanced modes for different data quality |
| Overlap-adjusted scoring | 2026-01-09 | Account for fewer peaks than expected carbons |
| Variable tolerance by region | 2026-01-09 | Tighter for aliphatic (0.8), looser for carbonyl (1.5) |
| RDKit for SD parsing | 2026-01-09 | Industry standard, handles MOL blocks and properties |
| inv4* long-range detection | 2026-01-10 | Distinguish HMBC from HSQC in inv4 pulse programs |
| nmrglue connected-region algorithm | 2026-01-10 | For 2D peak picking, handles overlapping peaks |
| Corner-based 2D noise estimation | 2026-01-10 | Corners rarely contain real peaks |
| Tolerance-based peak validation | 2026-01-10 | 0.5-1.0 ppm tolerance for 2D vs 1D matching |
| DEPT-guided adaptive thresholding | 2026-01-10 | Lower HSQC threshold until all DEPT carbons matched |
| Multiplicative threshold reduction | 2026-01-10 | ×0.5 factor gives logarithmic steps |
| HMBC-guided peak picking | 2026-01-10 | Filter HMBC by requiring C match in 13C/DEPT and H match in HSQC |
| LSD 2-param HMBC format | 2026-01-10 | LSD defaults to 2-3 bond distance; simpler than 4-param format |
| Real data over manual correlations | 2026-01-10 | Manual test correlations produced 900+ solutions; real data provides stronger constraints |
| Spectroscopic constraint inference | 2026-01-10 | Carbonyl C identified from shift; missing H assigned to O; derives BOND constraints automatically |

## Open Questions

- None at this time

## Resolved Questions

- **NMR parsing library**: nmrglue (2026-01-08) — Most mature, BSD licensed, native Bruker support, academic citations
- **Dereplication matching strategy**: Multi-mode with fuzzy tolerances (2026-01-09)
- **LSD vs pyLSD**: LSD first (2026-01-10) — Simpler (no Java), pyLSD builds on it, add ranking later
- **Symmetry detection**: (2026-01-10) — AI-driven approach with convenience tools exposing H budget + intensity data

## Session Continuity

**Last session**: 2026-01-10
**Completed**:
- **Phase 5.2 Symmetry Detection complete**
- New `lucy_ng.analysis` module with 3 convenience tools:
  - `HydrogenBudgetAnalyzer` - compare MF H vs observed carbon-assigned H
  - `IntensityReporter` - relative HSQC intensities with equivalence flagging
  - `SymmetryAnalyzer` - combined AI-readable summary
- Module exported from main `lucy_ng` package
- 21 new tests for symmetry analysis tools
- Verified with Ibuprofen data (correctly detects 5 missing carbons, aromatic pairs)
- 266 total tests passing

**Key technical insights**:
- AI-driven architecture: tools expose data, AI does reasoning
- H budget: compare MF H count with observed carbon-assigned H
- Intensity analysis: equivalent atoms show ~2× HSQC intensity
- Interpretation hints generated but AI makes final decisions
- Para-disubstituted benzene pattern correctly identified in Ibuprofen

**Next**: Phase 6 (CLI Interface)

---
*Last updated: 2026-01-10*

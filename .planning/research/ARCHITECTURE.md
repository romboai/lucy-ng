# Architecture Integration: Statistical Detection Features

**Domain:** NMR structure elucidation with statistical detection
**Researched:** 2026-02-10
**Overall confidence:** HIGH

## Executive Summary

Statistical detection features integrate cleanly into the existing lucy-ng architecture through three layers:

1. **Database layer**: Extend existing HOSE statistics schema with hybridisation and bond partner columns
2. **Statistics generation**: Extend existing `stats_generator.py` to compute additional aggregates during HOSE processing
3. **CLI layer**: Add new `detect` command group following existing Click pattern
4. **Agent integration**: CASE agent calls `lucy detect` CLI commands via Bash (same pattern as existing `lucy lsd rank`)

The architecture is additive, not invasive. Existing HOSE prediction infrastructure provides the foundation - statistical detection reuses the same database, the same HOSE code generator, and the same query patterns.

## 1. CLI Command Structure

### Current Pattern

lucy-ng uses Click multi-level command groups. Main entry point at `src/lucy_ng/cli/main.py`:

```python
@click.group()
def cli() -> None:
    """lucy-ng: AI-powered Computer-Assisted Structure Elucidation."""
    pass

# Command groups registered
cli.add_command(read)
cli.add_command(pick)
cli.add_command(analyze)
cli.add_command(dereplicate)
cli.add_command(predict)
cli.add_command(lsd)
cli.add_command(visualize)
cli.add_command(fetch)
cli.add_command(database)
```

Each command group is a separate module in `src/lucy_ng/cli/`:
- `read.py` - Read NMR spectra
- `pick.py` - Peak picking
- `analyze.py` - Analysis tools (symmetry detection)
- `dereplicate.py` - Database matching
- `predict.py` - 13C shift prediction
- `lsd.py` - LSD structure elucidation
- `visualize.py` - Correlation diagrams
- `fetch.py` - Fetch external data
- `database.py` - Database management

### Integration Point: New `detect.py` Module

**File:** `src/lucy_ng/cli/detect.py`

**Commands:**
```bash
lucy detect hybridisation <db_path> <shift>
lucy detect quaternary <db_path> <shift>
lucy detect bond-partners <db_path> <shift> <hose_code>
```

**Pattern to follow:**

```python
import click
from lucy_ng.detection import StatisticalDetector

@click.group()
def detect() -> None:
    """Statistical detection from HOSE database."""
    pass

@detect.command("hybridisation")
@click.argument("db_path", type=click.Path(exists=True))
@click.argument("shift", type=float)
@click.option("--format", type=click.Choice(["text", "json"]), default="text")
def detect_hybridisation(db_path: str, shift: float, format: str) -> None:
    """Detect hybridisation state from chemical shift statistics."""
    detector = StatisticalDetector.from_database(db_path)
    result = detector.detect_hybridisation(shift)

    if format == "json":
        click.echo(result.to_json())
    else:
        click.echo(result.summary())
```

**Registration:** Add to `main.py`:
```python
from lucy_ng.cli.detect import detect
cli.add_command(detect)
```

**Confidence:** HIGH - pattern is well-established, straightforward to replicate.

## 2. Database Layer Integration

### Current Schema

Database schema defined in `src/lucy_ng/database/schema.py`:

```sql
-- Existing compounds table (928K compounds)
CREATE TABLE compounds (
    id INTEGER PRIMARY KEY,
    name TEXT, smiles TEXT, formula TEXT,
    inchi TEXT, inchi_key TEXT,
    carbon_count INTEGER, source TEXT
);

-- Existing shifts table (13C NMR data)
CREATE TABLE shifts (
    id INTEGER PRIMARY KEY,
    compound_id INTEGER,
    atom_index INTEGER,
    shift_ppm REAL,
    hydrogen_count INTEGER
);

-- Existing HOSE statistics table (7.9M entries)
CREATE TABLE hose_stats (
    hose_code TEXT NOT NULL,
    radius INTEGER NOT NULL,
    mean REAL NOT NULL,
    std REAL NOT NULL,
    count INTEGER NOT NULL,
    m2 REAL NOT NULL,  -- For Welford's algorithm
    PRIMARY KEY (hose_code, radius)
);
```

### Extended Schema for Statistical Detection

**Option A: Extend hose_stats table (RECOMMENDED)**

Add columns to existing `hose_stats` table:

```sql
ALTER TABLE hose_stats ADD COLUMN sp2_fraction REAL DEFAULT NULL;
ALTER TABLE hose_stats ADD COLUMN sp3_fraction REAL DEFAULT NULL;
ALTER TABLE hose_stats ADD COLUMN quat_fraction REAL DEFAULT NULL;
ALTER TABLE hose_stats ADD COLUMN common_partners TEXT DEFAULT NULL;
```

**Rationale:**
- Statistics are HOSE-code specific, not compound-specific
- Computed during same pass as mean/std/count
- Same query pattern (lookup by hose_code + radius)
- No schema version bump needed (columns have defaults)

**Option B: Separate detection_stats table**

```sql
CREATE TABLE detection_stats (
    hose_code TEXT NOT NULL,
    radius INTEGER NOT NULL,
    sp2_fraction REAL NOT NULL,
    sp3_fraction REAL NOT NULL,
    quat_fraction REAL NOT NULL,
    common_partners TEXT,  -- JSON array
    PRIMARY KEY (hose_code, radius),
    FOREIGN KEY (hose_code, radius) REFERENCES hose_stats(hose_code, radius)
);
```

**Tradeoff:**
- Pro: Cleaner separation, easier to add/remove
- Con: Requires JOIN for queries, more complex schema management

**Recommendation:** Option A (extend hose_stats). The data is conceptually part of HOSE statistics, computed at the same time, queried together. Extending the table is simpler.

**Confidence:** HIGH - schema extension is straightforward, pattern exists (m2 column was added in schema v3).

### Database Manager Methods

**File:** `src/lucy_ng/database/manager.py`

Current pattern for HOSE stats queries:

```python
def get_hose_stats(self, hose_code: str, radius: int) -> HOSEStatsRecord | None:
    """Get statistics for a specific HOSE code at a given radius."""
    cursor.execute(
        """
        SELECT hose_code, radius, mean, std, count
        FROM hose_stats WHERE hose_code = ? AND radius = ?
        """,
        (hose_code, radius),
    )
    # Returns HOSEStatsRecord
```

**Extended query for detection:**

```python
def get_detection_stats(self, hose_code: str, radius: int) -> DetectionStatsRecord | None:
    """Get detection statistics for a HOSE code at a given radius."""
    cursor.execute(
        """
        SELECT hose_code, radius, mean, std, count,
               sp2_fraction, sp3_fraction, quat_fraction, common_partners
        FROM hose_stats WHERE hose_code = ? AND radius = ?
        """,
        (hose_code, radius),
    )
    # Returns DetectionStatsRecord with full detection info
```

**Confidence:** HIGH - follows existing pattern exactly.

## 3. HOSE Statistics Generation Pipeline

### Current Pipeline

**File:** `src/lucy_ng/prediction/stats_generator.py`

Three generator classes:
1. **HOSEStatsGenerator** - In-memory batch processing (original)
2. **ResumableHOSEStatsGenerator** - Checkpointed chunked processing (production)
3. **SDFHOSEStatsGenerator** - Direct SDF processing (COCONUT import)

**Core algorithm (simplified):**

```python
for compound_id, smiles, shifts in db.iter_compounds_with_shifts():
    mol = Chem.MolFromSmiles(smiles)

    for atom_idx, shift_ppm in shifts:
        for radius in range(1, max_radius + 1):
            hose_code = hose_gen.generate_for_atom(mol, atom_idx, radius)

            # Accumulate shift for statistics
            aggregates[(hose_code, radius)].append(shift_ppm)

# Compute statistics
for (hose_code, radius), shifts in aggregates.items():
    mean = statistics.mean(shifts)
    std = statistics.stdev(shifts)
    count = len(shifts)

    db.insert_hose_stats(hose_code, radius, mean, std, count)
```

**Uses Welford's online algorithm** for memory efficiency in `ResumableHOSEStatsGenerator`:
- O(1) memory per HOSE code
- Incremental updates (chunk by chunk)
- Parallel merge support

### Extended Pipeline for Detection Statistics

**Integration point:** Extend the accumulation phase to track hybridisation and bond partners.

**Proposed structure:**

```python
from collections import defaultdict
from lucy_ng.prediction.hose import HOSECodeGenerator

class DetectionStatsAccumulator:
    """Track hybridisation and bond partner statistics for a HOSE code."""

    def __init__(self):
        self.shifts = []
        self.sp2_count = 0
        self.sp3_count = 0
        self.quat_count = 0
        self.partner_symbols = defaultdict(int)  # {'C': 15, 'O': 3, 'N': 1}

    def update(self, shift_ppm, atom, mol):
        self.shifts.append(shift_ppm)

        # Determine hybridisation
        if atom.GetHybridization() == Chem.HybridizationType.SP2:
            self.sp2_count += 1
        elif atom.GetHybridization() == Chem.HybridizationType.SP3:
            self.sp3_count += 1

        # Quaternary check
        if atom.GetTotalNumHs() == 0:
            self.quat_count += 1

        # Bond partners
        for neighbor in atom.GetNeighbors():
            self.partner_symbols[neighbor.GetSymbol()] += 1

    def compute_stats(self):
        total = len(self.shifts)
        return {
            'sp2_fraction': self.sp2_count / total if total > 0 else 0.0,
            'sp3_fraction': self.sp3_count / total if total > 0 else 0.0,
            'quat_fraction': self.quat_count / total if total > 0 else 0.0,
            'common_partners': dict(self.partner_symbols)
        }
```

**Modified generation loop:**

```python
accumulators = defaultdict(DetectionStatsAccumulator)

for compound_id, smiles, shifts in db.iter_compounds_with_shifts():
    mol = Chem.MolFromSmiles(smiles)

    for atom_idx, shift_ppm in shifts:
        atom = mol.GetAtomWithIdx(atom_idx)

        for radius in range(1, max_radius + 1):
            hose_code = hose_gen.generate_for_atom(mol, atom_idx, radius)

            # Accumulate with detection info
            accumulators[(hose_code, radius)].update(shift_ppm, atom, mol)

# Compute statistics
for (hose_code, radius), acc in accumulators.items():
    stats = acc.compute_stats()
    mean = statistics.mean(acc.shifts)
    std = statistics.stdev(acc.shifts)

    db.insert_hose_stats(
        hose_code, radius, mean, std, len(acc.shifts),
        sp2_fraction=stats['sp2_fraction'],
        sp3_fraction=stats['sp3_fraction'],
        quat_fraction=stats['quat_fraction'],
        common_partners=json.dumps(stats['common_partners'])
    )
```

**For ResumableHOSEStatsGenerator:** Modify `WelfordAccumulator` dataclass to include detection counters:

```python
@dataclass
class WelfordAccumulator:
    count: int = 0
    mean: float = 0.0
    m2: float = 0.0
    # NEW: detection statistics
    sp2_count: int = 0
    sp3_count: int = 0
    quat_count: int = 0
    partner_counts: dict = field(default_factory=dict)  # {'C': 15, 'O': 3}
```

**Confidence:** MEDIUM - Extension is conceptually straightforward but requires:
- RDKit atom API familiarity (GetHybridization, GetTotalNumHs, GetNeighbors)
- Testing with actual COCONUT data to verify hybridisation detection accuracy
- Merge algorithm for Welford parallel processing (straightforward for counters)

## 4. Agent Integration Pattern

### Current Agent Architecture

**CASE agent:** `~/.claude/agents/lucy-case-agent.md` (666 lines)

**Agent spawning:** Claude Code Task tool with working directory set to compound directory

**CLI usage pattern:** Agent calls `lucy` commands via Bash tool:

```bash
# Symmetry analysis
lucy analyze symmetry C13H18O2 data/compound/2

# Peak picking
lucy pick 1d data/compound/2 --format json
lucy pick hsqc data/compound/6 --format json

# LSD workflow
cd analysis/iteration_01 && lucy lsd run compound.lsd
outlsd 5 < compound.sol > solutions.smi
lucy lsd rank solutions.smi --shifts "155.08,151.58,..."
```

**Key pattern:** Agent uses thin CLI commands, all domain knowledge is encoded in agent definition (inlined NMR/LSD knowledge).

### Statistical Detection Integration

**Agent workflow addition:**

```bash
# Step 1: Detect hybridisation for each carbon
lucy detect hybridisation data/reference/lucy-ng-derep.db 139.94 --format json
# Output: {"shift": 139.94, "prediction": "sp2", "confidence": 0.92, "sp2_fraction": 0.91}

# Step 2: Use detection to inform MULT command
# If sp2_fraction > 0.7 → MULT N C 2 H
# If sp3_fraction > 0.7 → MULT N C 3 H

# Step 3: Detect quaternary
lucy detect quaternary data/reference/lucy-ng-derep.db 155.08 --format json
# Output: {"shift": 155.08, "is_quaternary": true, "confidence": 0.88, "quat_fraction": 0.85}

# Step 4: Detect bond partners for heteroatom inference
lucy detect bond-partners data/reference/lucy-ng-derep.db 180.5 "C-4;C(//" --format json
# Output: {"common_partners": {"O": 0.95, "C": 0.82}, "interpretation": "Likely C=O"}
```

**Agent instruction addition (to `lucy-case-agent.md`):**

```markdown
## Statistical Detection Commands (Optional Enhancement)

Before writing MULT commands, optionally consult statistical detection:

**Hybridisation detection:**
```bash
lucy detect hybridisation <db_path> <shift> --format json
```
Returns sp2/sp3 prediction with confidence. Use when chemical shift region is ambiguous.

**Quaternary detection:**
```bash
lucy detect quaternary <db_path> <shift> --format json
```
Returns quaternary probability. Use for carbons appearing in 13C but absent from DEPT/HSQC.

**Bond partner detection:**
```bash
lucy detect bond-partners <db_path> <shift> <hose_code> --format json
```
Returns common heteroatom partners. Use for inferring O/N attachment from chemical shift.

**Integration example:**
1. Pick 13C peaks: 180.5, 139.0, 75.0, 30.0 ppm
2. Run detection for each: `lucy detect hybridisation db 180.5`
3. 180.5 → sp2 (0.95) → carbonyl carbon → MULT 1 C 2 0
4. 139.0 → sp2 (0.88) → aromatic CH → MULT 2 C 2 1
5. 75.0 → sp3 (0.92) → C-O CH → MULT 3 C 3 1
6. 30.0 → sp3 (0.98) → aliphatic CH2 → MULT 4 C 3 2
```

**Confidence:** HIGH - Follows exact same pattern as existing `lucy lsd rank`. Agent already uses JSON output parsing.

## 5. Ranking Integration: Two-Tier Approach

### Current Ranking Architecture

**File:** `src/lucy_ng/ranking/ranker.py`

**Algorithm:**
1. For each LSD solution (SMILES)
2. Predict 13C shifts using HOSE database
3. Match predicted to experimental shifts
4. Compute MAE (Mean Absolute Error)
5. Sort by MAE (lower is better)

**Output:** `RankedSolution` objects with MAE, quality label, deviations.

### Two-Tier Ranking Integration

**Tier 1: Hybridisation pre-filter**

Before HOSE-based ranking, check if solution's hybridisation matches statistical expectations:

```python
class HybridisationFilter:
    """Pre-filter solutions by hybridisation consistency."""

    def filter_solutions(
        self,
        solutions: list[LSDSolution],
        experimental_shifts: list[float],
        detector: StatisticalDetector,
    ) -> list[LSDSolution]:
        """Remove solutions with inconsistent hybridisation."""
        filtered = []

        for solution in solutions:
            mol = Chem.MolFromSmiles(solution.smiles)
            consistent = True

            for exp_shift in experimental_shifts:
                # Get expected hybridisation from statistics
                detection = detector.detect_hybridisation(exp_shift)

                # Find carbon in solution at similar shift
                carbon = self._find_carbon_at_shift(mol, exp_shift, tolerance=5.0)
                if carbon is None:
                    continue

                # Check consistency
                actual_hyb = carbon.GetHybridization()
                expected_hyb = detection.predicted_hybridisation

                if actual_hyb != expected_hyb and detection.confidence > 0.8:
                    consistent = False
                    break

            if consistent:
                filtered.append(solution)

        return filtered
```

**Tier 2: HOSE-based MAE ranking**

Unchanged - existing `SolutionRanker` class.

**Modified workflow:**

```python
# Current workflow
result = ranker.rank(solutions, experimental_shifts, top_n=10)

# Two-tier workflow
filtered_solutions = hyb_filter.filter_solutions(solutions, experimental_shifts, detector)
result = ranker.rank(filtered_solutions, experimental_shifts, top_n=10)
```

**CLI integration:**

```bash
# Option 1: Automatic (detect database presence)
lucy lsd rank solutions.smi --shifts "..." --use-detection

# Option 2: Explicit
lucy lsd rank solutions.smi --shifts "..." --filter-hybridisation --db data/reference/lucy-ng-derep.db
```

**Confidence:** MEDIUM - Concept is sound, but requires:
- Robust shift-to-carbon matching algorithm
- Tuning of confidence thresholds
- Validation with known structures to measure false positive rate

## 6. Build Order and Dependencies

### Phase 1: Database Schema Extension

**Dependencies:** None (extends existing schema)

**Files:**
- `src/lucy_ng/database/schema.py` - Add columns to hose_stats table
- `src/lucy_ng/database/models.py` - Add DetectionStatsRecord Pydantic model
- `src/lucy_ng/database/manager.py` - Add get_detection_stats() method

**Validation:** Schema migration, test queries

### Phase 2: Statistics Generation

**Dependencies:** Phase 1 (schema must exist)

**Files:**
- `src/lucy_ng/prediction/stats_generator.py` - Extend accumulators
- `src/lucy_ng/detection/accumulator.py` - NEW: DetectionStatsAccumulator class

**Validation:** Generate statistics from small test dataset, verify fractions

### Phase 3: Detection Module

**Dependencies:** Phase 2 (statistics must be generated)

**Files:**
- `src/lucy_ng/detection/__init__.py` - NEW module
- `src/lucy_ng/detection/detector.py` - StatisticalDetector class
- `src/lucy_ng/detection/models.py` - DetectionResult Pydantic models

**Validation:** Unit tests with known HOSE codes, verify predictions

### Phase 4: CLI Commands

**Dependencies:** Phase 3 (detector must exist)

**Files:**
- `src/lucy_ng/cli/detect.py` - NEW: detect command group
- `src/lucy_ng/cli/main.py` - Register detect command group

**Validation:** CLI smoke tests, JSON output validation

### Phase 5: Agent Integration

**Dependencies:** Phase 4 (CLI must work)

**Files:**
- `~/.claude/agents/lucy-case-agent.md` - Add detection command documentation
- Test with live CASE workflow

**Validation:** Run CASE on test compound with detection enabled

### Phase 6: Ranking Enhancement (Optional)

**Dependencies:** Phase 3 (detector must exist)

**Files:**
- `src/lucy_ng/ranking/filters.py` - NEW: HybridisationFilter class
- `src/lucy_ng/ranking/ranker.py` - Add two-tier ranking option
- `src/lucy_ng/cli/lsd.py` - Add --use-detection flag to rank command

**Validation:** Compare ranking with/without detection on known structures

### Dependency Chain Rationale

1. **Database first**: Schema must exist before any generation code can write to it
2. **Generation second**: Statistics must be computed before they can be queried
3. **Detection third**: Query interface must work before CLI can call it
4. **CLI fourth**: Commands must be stable before agent uses them
5. **Agent fifth**: Agent integration tests actual workflow end-to-end
6. **Ranking last**: Optional enhancement, doesn't block core detection features

## 7. Data Flow Summary

### Hybridisation Detection Flow

```
User: lucy detect hybridisation db.sqlite 139.94
  ↓
CLI: detect.py parses args, calls detector
  ↓
Detector: StatisticalDetector.detect_hybridisation(139.94)
  ↓
Detector: Generate HOSE codes at each radius for shift estimation
  ↓
Database: DatabaseManager.get_detection_stats(hose_code, radius)
  ↓
Database: SELECT sp2_fraction, sp3_fraction FROM hose_stats WHERE ...
  ↓
Detector: Compare sp2_fraction vs sp3_fraction
  ↓
Detector: Return DetectionResult(prediction="sp2", confidence=0.91)
  ↓
CLI: Format as JSON/text, print to stdout
  ↓
Agent: Parse JSON, use in MULT command generation
```

### Statistics Generation Flow

```
Admin: lucy database generate-detection-stats
  ↓
CLI: database.py calls ResumableHOSEStatsGenerator
  ↓
Generator: Iterate compounds from database
  ↓
For each compound:
  Generator: Parse SMILES → RDKit Mol
  Generator: For each carbon with shift:
    Generator: Generate HOSE code
    Generator: Get atom.GetHybridization()
    Generator: Get atom.GetTotalNumHs()
    Generator: Get atom.GetNeighbors()
    Generator: Accumulate in DetectionStatsAccumulator
  ↓
Generator: Compute fractions (sp2_count / total, etc.)
  ↓
Database: INSERT INTO hose_stats (sp2_fraction, ...) VALUES (...)
  ↓
Generator: Save checkpoint every 10K compounds
```

### Agent CASE Workflow with Detection

```
Agent: lucy detect hybridisation db 180.5
  ↓ (sp2, 0.95)
Agent: lucy detect quaternary db 180.5
  ↓ (true, 0.88)
Agent: Write LSD file
  MULT 1 C 2 0  ; sp2, quaternary → carbonyl
  ↓
Agent: lucy lsd run compound.lsd
  ↓ (10 solutions)
Agent: outlsd 5 < compound.sol > solutions.smi
  ↓
Agent: lucy lsd rank solutions.smi --shifts "..." --use-detection
  ↓ (Tier 1: filter by hybridisation)
  ↓ (Tier 2: rank by MAE)
Agent: Examine top solution
```

## 8. Integration Risks and Mitigations

### Risk 1: Hybridisation Detection Accuracy

**Issue:** RDKit's `GetHybridization()` may not always match NMR chemical shift expectations.

**Example:** Aromatic carbons are sp2, but some edge cases (e.g., pyrrole N-adjacent C) may have unexpected shifts.

**Mitigation:**
- Validate against known structures before deployment
- Report confidence scores, not absolute predictions
- Allow manual override in agent workflow

**Impact:** MEDIUM - Affects feature usefulness but not system stability

### Risk 2: Database Size Growth

**Issue:** Adding 4 columns to 7.9M row table increases storage.

**Estimate:**
- sp2_fraction: 4 bytes (REAL)
- sp3_fraction: 4 bytes (REAL)
- quat_fraction: 4 bytes (REAL)
- common_partners: ~50 bytes average (TEXT JSON)
- Total: ~62 bytes × 7.9M = ~490 MB additional storage

**Current database:** ~2.8 GB
**With detection:** ~3.3 GB (+18%)

**Mitigation:**
- Acceptable growth (modern systems have TB storage)
- Could compress common_partners JSON if needed
- Could make detection stats optional (separate table)

**Impact:** LOW - Storage is cheap, growth is reasonable

### Risk 3: Statistics Generation Time

**Issue:** Extending HOSE generation to compute detection stats may increase runtime.

**Analysis:**
- Current bottleneck: HOSE code generation (RDKit mol graph traversal)
- Detection stats: Additional atom property lookups (GetHybridization, GetNeighbors)
- Estimated overhead: +10-20% runtime (same mol object, just extra queries)

**Current generation time:** ~8-12 hours for 928K compounds (from project experience)
**With detection:** Estimated ~10-14 hours

**Mitigation:**
- Checkpointing already handles long runs
- Can run overnight or as background job
- Parallel processing possible (database upsert is atomic)

**Impact:** LOW - Runtime increase is acceptable for one-time generation

### Risk 4: Agent Complexity Creep

**Issue:** Adding detection commands to agent may make decision logic more complex.

**Mitigation:**
- Make detection OPTIONAL in agent workflow (not required)
- Provide clear heuristics (e.g., "use detection when shift is 50-90 ppm and DEPT is unclear")
- Fall back to existing DEPT-based multiplicity if detection unavailable

**Impact:** LOW - Agent already handles complex decision trees, detection is additive

## 9. Alternative Architectures Considered

### Alternative 1: Real-time Computation (No Database Extension)

**Idea:** Compute detection statistics on-the-fly by querying raw shifts table.

**Rejected because:**
- Query would scan millions of rows per lookup (too slow)
- Would require re-implementing HOSE aggregation logic
- No benefit over pre-computed statistics

### Alternative 2: Separate Detection Service

**Idea:** Build detection as microservice with its own database.

**Rejected because:**
- Over-engineering for single-user CLI tool
- lucy-ng is not a service architecture (no MCP server after v2.0)
- Adds deployment complexity

### Alternative 3: Machine Learning Model

**Idea:** Train ML model to predict hybridisation from shift + HOSE code.

**Rejected because:**
- Requires training data labeling (expensive)
- Requires model deployment (scikit-learn/TensorFlow dependency)
- Rule-based statistics are interpretable and sufficient

## 10. Open Questions for Implementation

1. **Hybridisation edge cases:** How to handle atoms with unusual hybridisation (e.g., carbocations, radicals)?
   - **Recommendation:** Filter to stable closed-shell molecules during database import

2. **Bond partner encoding:** JSON array vs delimited string for common_partners?
   - **Recommendation:** JSON for flexibility, SQLite has native JSON functions

3. **Confidence threshold tuning:** What sp2/sp3 fraction difference constitutes "high confidence"?
   - **Recommendation:** Start with 0.7 threshold, tune based on validation set

4. **Quaternary detection threshold:** What quat_fraction indicates "definitely quaternary"?
   - **Recommendation:** 0.8+ = very likely, 0.5-0.8 = uncertain, <0.5 = unlikely

5. **Agent decision logic:** When should agent prefer detection over DEPT?
   - **Recommendation:** Use DEPT as ground truth when available, detection for ambiguous cases or missing DEPT

## 11. Success Metrics

**Database generation:**
- Statistics computed for >95% of HOSE codes
- sp2_fraction + sp3_fraction approximately 1.0 (accounting for other hybridisations)

**Detection accuracy:**
- >90% agreement with DEPT-based multiplicity on test set
- Confidence scores correlate with accuracy (high confidence = high accuracy)

**Agent integration:**
- Agent successfully uses detection in at least 3 ambiguous cases per compound
- Detection-informed MULT commands reduce LSD solution count by 20-50%

**User impact:**
- Faster time to correct structure (fewer manual iterations)
- Higher confidence in LSD input file correctness
- Reduced reliance on trial-and-error for multiplicity assignment

## Conclusion

Statistical detection integrates cleanly into lucy-ng's existing architecture:

- **Database layer:** Extend hose_stats table with 4 columns (+18% storage)
- **Generation layer:** Extend existing stats_generator.py (+10-20% runtime)
- **CLI layer:** New detect.py module following established Click pattern
- **Agent layer:** Use via Bash tool, same as existing lucy lsd rank

**Critical success factors:**
1. RDKit hybridisation detection must be validated against real NMR data
2. Database schema migration must be tested on existing 2.8GB database
3. Agent decision logic must be clear and fall back gracefully

**Recommended build order:**
1. Schema extension (1 day)
2. Statistics generation (2-3 days)
3. Detection module (3-4 days)
4. CLI commands (2 days)
5. Agent integration (2-3 days)
6. Two-tier ranking (optional, 3-4 days)

Total: ~2-3 weeks for core features, +1 week for ranking enhancement.

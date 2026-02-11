"""Statistical detection of structural constraints from NMR shifts."""

from lucy_ng.detection.detector import StatisticalDetector
from lucy_ng.detection.models import HHBResult, HybridisationResult, NeighbourResult

__all__ = ["StatisticalDetector", "HHBResult", "HybridisationResult", "NeighbourResult"]

# UEHIS – Scoring Module
# 6-factor UEHI score computation, risk classification, and entropy weighting.
# water_availability formally investigated and excluded for Kothrud pilot.

from scoring.uehi_score import (
    compute_uehi_scores,
    classify_risk,
    load_config,
    get_factor_names,
    ScoringConfigError,
    RISK_THRESHOLDS,
)
from scoring.normalize import (
    min_max_scale,
    inverted_min_max_scale,
    normalise_factor,
)
from scoring.entropy import (
    entropy_weights,
    compute_factor_diagnostics,
    print_diagnostics_table,
    EntropyWeightError,
    MODAL_SHARE_THRESHOLD,
    DEGENERATE_WEIGHT_CAP,
    WEIGHT_SUM_TOLERANCE,
)

__all__ = [
    "compute_uehi_scores",
    "classify_risk",
    "load_config",
    "get_factor_names",
    "ScoringConfigError",
    "RISK_THRESHOLDS",
    "min_max_scale",
    "inverted_min_max_scale",
    "normalise_factor",
    "entropy_weights",
    "compute_factor_diagnostics",
    "print_diagnostics_table",
    "EntropyWeightError",
    "MODAL_SHARE_THRESHOLD",
    "DEGENERATE_WEIGHT_CAP",
    "WEIGHT_SUM_TOLERANCE",
]

# UEHIS – Scoring Module
# 8-factor UEHI score computation and risk classification.

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
]

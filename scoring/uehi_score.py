"""
scoring/uehi_score.py
─────────────────────
6-factor Urban Eco-Heat Island (UEHI) scoring engine.

Reads factor weights and directions from ``uehi_config.json``, normalises
each indicator column, computes the weighted sum, and scales to 0–100.

``water_availability`` was formally investigated and excluded for the
Kothrud pilot.  See the methodology report for details.

Score interpretation
--------------------
* **100** = maximum ecological health (cool, green, permeable)
* **0**  = severe heat-island conditions (hot, impervious, barren)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import geopandas as gpd
import pandas as pd

from scoring.normalize import normalise_factor

# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------

_DEFAULT_CONFIG = Path(__file__).parent / "uehi_config.json"


class ScoringConfigError(Exception):
    """Raised when the scoring configuration is invalid."""
    pass


def load_config(config_path: str | Path | None = None) -> dict[str, Any]:
    """
    Load and validate the UEHI scoring config.

    Parameters
    ----------
    config_path : str | Path | None
        Path to the JSON config.  ``None`` uses the built-in default.

    Returns
    -------
    dict
        Parsed config with a ``"factors"`` mapping.

    Raises
    ------
    ScoringConfigError
        If the file is missing, malformed, or weights do not sum to 1.
    """
    path = Path(config_path) if config_path else _DEFAULT_CONFIG

    if not path.exists():
        raise ScoringConfigError(f"Config file not found: {path}")

    with open(path, "r", encoding="utf-8") as fh:
        config = json.load(fh)

    factors = config.get("factors")
    if not factors or not isinstance(factors, dict):
        raise ScoringConfigError("Config must contain a 'factors' mapping.")

    total_weight = sum(f["weight"] for f in factors.values())
    if abs(total_weight - 1.0) > 1e-6:
        raise ScoringConfigError(
            f"Factor weights must sum to 1.0 (got {total_weight:.6f})."
        )

    for name, spec in factors.items():
        if spec.get("direction") not in ("positive", "negative"):
            raise ScoringConfigError(
                f"Factor '{name}' has invalid direction: {spec.get('direction')}. "
                "Must be 'positive' or 'negative'."
            )
        if not (0.0 <= spec["weight"] <= 1.0):
            raise ScoringConfigError(
                f"Factor '{name}' weight {spec['weight']} is out of [0, 1]."
            )

    return config


def get_factor_names(config: dict[str, Any] | None = None) -> list[str]:
    """Return the ordered list of factor column names from the config."""
    if config is None:
        config = load_config()
    return list(config["factors"].keys())


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def compute_uehi_scores(
    gdf: gpd.GeoDataFrame,
    config_path: str | Path | None = None,
    score_column: str = "uehi_score",
) -> gpd.GeoDataFrame:
    """
    Compute the UEHI score for each city block (row) in a GeoDataFrame.

    The GeoDataFrame must contain one column per factor listed in the config.
    Each column holds raw (un-normalised) indicator values.

    Parameters
    ----------
    gdf : geopandas.GeoDataFrame
        Input blocks.  Must include columns named after each factor in the
        config (e.g. ``ndvi``, ``temperature``, …).
    config_path : str | Path | None
        Custom config path (``None`` = built-in default).
    score_column : str
        Name of the new column that will hold the 0–100 score.

    Returns
    -------
    geopandas.GeoDataFrame
        A *copy* of *gdf* with an added ``score_column``.

    Raises
    ------
    ScoringConfigError
        If the config is invalid.
    KeyError
        If a required factor column is missing from *gdf*.
    """
    from scoring.entropy import entropy_weights

    config = load_config(config_path)
    factors = config["factors"]

    # Validate that all factor columns exist
    missing = [f for f in factors if f not in gdf.columns]
    if missing:
        raise KeyError(
            f"GeoDataFrame is missing required factor columns: {missing}"
        )

    result = gdf.copy()

    # Calculate entropy weights
    ew = entropy_weights(result, list(factors.keys()))

    # Normalise each factor and accumulate the weighted sum
    weighted_sum = pd.Series(0.0, index=result.index)

    for name, spec in factors.items():
        direction = spec["direction"]
        norm_col = f"_norm_{name}"
        result[norm_col] = normalise_factor(result[name], direction).fillna(0.0)
        weighted_sum += ew[name] * result[norm_col]

    base_score = (weighted_sum * 100).clip(0, 100)
    
    # Synergy: s(i) = α × N(NDVI) × N(Temperature) × 100
    ndvi_norm = normalise_factor(result["ndvi"], "positive").fillna(0.0)
    temp_norm = normalise_factor(result["temperature"], "negative").fillna(0.0)
    synergy = 0.1 * ndvi_norm * temp_norm * 100
    
    # Population multiplier: m(i) = 1 − β × N_positive(Pop_i)
    pop_norm = normalise_factor(result["population_exposure"], "positive").fillna(0.0)
    pop_multiplier = 1 - 0.3 * pop_norm

    # Scale to 0–100 and clamp for safety
    result[score_column] = ((base_score + synergy) * pop_multiplier).clip(0, 100).round(2)

    # Drop internal normalised columns
    norm_cols = [c for c in result.columns if c.startswith("_norm_")]
    result.drop(columns=norm_cols, inplace=True)

    _print_summary(result, score_column)
    return result


# ---------------------------------------------------------------------------
# Risk classification
# ---------------------------------------------------------------------------

RISK_THRESHOLDS = {
    (0, 25): "Critical",
    (25, 50): "High",
    (50, 75): "Moderate",
    (75, 101): "Low",
}


def classify_risk(
    gdf: gpd.GeoDataFrame,
    score_column: str = "uehi_score",
    risk_column: str = "risk_level",
) -> gpd.GeoDataFrame:
    """
    Bin UEHI scores into risk categories.

    Parameters
    ----------
    gdf : geopandas.GeoDataFrame
        Must contain *score_column*.
    score_column : str
        Column with 0–100 UEHI scores.
    risk_column : str
        Name of the new categorical risk column.

    Returns
    -------
    geopandas.GeoDataFrame
        A *copy* with an added *risk_column*.
    """
    result = gdf.copy()

    def _classify(score: float) -> str:
        for (lo, hi), label in RISK_THRESHOLDS.items():
            if lo <= score < hi:
                return label
        return "Unknown"

    result[risk_column] = result[score_column].apply(_classify)
    return result


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _print_summary(gdf: gpd.GeoDataFrame, col: str) -> None:
    scores = gdf[col]
    print(
        f"[UEHI] Score summary — "
        f"min={scores.min():.1f}  median={scores.median():.1f}  "
        f"max={scores.max():.1f}  mean={scores.mean():.1f}"
    )

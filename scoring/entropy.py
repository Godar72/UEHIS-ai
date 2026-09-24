"""
scoring/entropy.py
──────────────────
Entropy-based factor weighting with mathematical safeguards.

This module computes data-driven weights from the spatial variability
of each factor across city blocks using Shannon entropy.  Three levels
of safeguard are applied:

  **Safeguard A — Constant factor**
      Zero variance → weight = 0, excluded from entropy calculation.

  **Safeguard B — Degenerate distribution**
      >95% of blocks share the same exact value → raw entropy weight
      is calculated normally, then capped at 0.03.  Freed weight is
      redistributed proportionally among non-constant, non-degenerate
      factors.

  **Low-spatial-variation diagnostic**
      Factors with low coefficient of variation (CV) are flagged for
      reporting, but their entropy weight is NOT automatically altered
      unless they independently trigger Safeguard A or B.

IMPORTANT
---------
* The 95% modal-share threshold and 0.03 weight cap are **provisional
  mathematical guardrails** only.  They are NOT scientifically validated,
  literature-derived, or empirically calibrated.
* Entropy weights quantify cross-block information content.  They do
  NOT represent ecological importance.
"""

from __future__ import annotations

import math
import warnings
from collections import Counter
from typing import Any

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class EntropyWeightError(Exception):
    """Raised when entropy weight computation fails a validation check."""
    pass


# ---------------------------------------------------------------------------
# Configuration constants (provisional mathematical guardrails)
# ---------------------------------------------------------------------------

MODAL_SHARE_THRESHOLD = 0.95   # Safeguard B trigger
DEGENERATE_WEIGHT_CAP = 0.03  # Maximum weight for a degenerate factor
WEIGHT_SUM_TOLERANCE = 1e-9   # Acceptable deviation from 1.0


# ---------------------------------------------------------------------------
# Core entropy weight computation
# ---------------------------------------------------------------------------

def entropy_weights(
    df: pd.DataFrame,
    factor_cols: list[str],
) -> dict[str, float]:
    """
    Compute entropy-based weights with constant-factor and degenerate-
    distribution safeguards.

    Parameters
    ----------
    df : pd.DataFrame
        Block-level data with one column per factor.
    factor_cols : list[str]
        Names of the factor columns to weight.

    Returns
    -------
    dict[str, float]
        Factor name → final weight.  Guaranteed to sum to 1.0 within
        ``WEIGHT_SUM_TOLERANCE``.

    Raises
    ------
    EntropyWeightError
        If the final weights do not sum to 1.0 within tolerance.
    """
    n = len(df)
    if n <= 1:
        return {col: 1.0 / len(factor_cols) for col in factor_cols}

    # ------------------------------------------------------------------
    # Step 1: Handle constant factors and apply additive shift for zeros/negatives
    # ------------------------------------------------------------------
    shifted = pd.DataFrame()
    constant_factors: set[str] = set()
    eps = 1e-12

    for col in factor_cols:
        lo, hi = df[col].min(), df[col].max()
        if pd.isna(lo) or pd.isna(hi) or (hi - lo) == 0:
            shifted[col] = 0.0
            constant_factors.add(col)
        else:
            if lo < 0:
                shifted[col] = df[col] - lo + eps
            else:
                shifted[col] = df[col]

    variable_cols = [c for c in factor_cols if c not in constant_factors]

    # ------------------------------------------------------------------
    # Step 2: All-constant fallback
    # ------------------------------------------------------------------
    if not variable_cols:
        warnings.warn(
            "All factors are constant — using equal weights as safe fallback.",
            stacklevel=2,
        )
        return {col: 1.0 / len(factor_cols) for col in factor_cols}

    # ------------------------------------------------------------------
    # Step 3: Shannon entropy for variable factors
    # ------------------------------------------------------------------
    p = shifted[variable_cols].div(
        shifted[variable_cols].sum(axis=0), axis=1
    )

    k = 1.0 / math.log(n)  # normalisation constant
    entropy = {}
    for col in variable_cols:
        p_col = p[col].values
        p_safe = np.where(p_col > 0, p_col, 1.0)
        term = np.where(p_col > 0, p_col * np.log(p_safe), 0.0)
        entropy[col] = -k * term.sum()

    diversity = {col: max(1 - e, 0) for col, e in entropy.items()}
    total_d = sum(diversity.values()) or 1
    raw_weights = {col: d / total_d for col, d in diversity.items()}

    # ------------------------------------------------------------------
    # Step 4: Detect degenerate distributions (Safeguard B)
    # ------------------------------------------------------------------
    degenerate_factors: set[str] = set()

    for col in variable_cols:
        counts = Counter(df[col])
        most_common_count = counts.most_common(1)[0][1]
        modal_share = most_common_count / n
        if modal_share > MODAL_SHARE_THRESHOLD:
            degenerate_factors.add(col)

    # ------------------------------------------------------------------
    # Step 5: Cap degenerate weights, redistribute freed weight
    # ------------------------------------------------------------------
    final_weights: dict[str, float] = {}

    # Identify healthy (non-constant, non-degenerate) factors
    healthy_cols = [c for c in variable_cols if c not in degenerate_factors]

    if degenerate_factors and healthy_cols:
        # Pool the total weight freed by capping degenerate factors
        total_freed = 0.0
        for col in degenerate_factors:
            raw_w = raw_weights[col]
            capped_w = min(raw_w, DEGENERATE_WEIGHT_CAP)
            freed = raw_w - capped_w
            total_freed += freed
            final_weights[col] = capped_w

        # Redistribute freed weight proportionally among healthy factors
        healthy_raw_total = sum(raw_weights[c] for c in healthy_cols) or 1
        for col in healthy_cols:
            share = raw_weights[col] / healthy_raw_total
            final_weights[col] = raw_weights[col] + total_freed * share

    elif degenerate_factors and not healthy_cols:
        # All variable factors are degenerate — cap all, then renormalise
        for col in degenerate_factors:
            final_weights[col] = min(raw_weights[col], DEGENERATE_WEIGHT_CAP)
        # Renormalise so they sum to 1
        fw_total = sum(final_weights.values()) or 1
        for col in degenerate_factors:
            final_weights[col] /= fw_total
    else:
        # No degenerate factors — use raw weights directly
        for col in variable_cols:
            final_weights[col] = raw_weights[col]

    # ------------------------------------------------------------------
    # Step 6: Assign constant factors weight = 0
    # ------------------------------------------------------------------
    for col in constant_factors:
        final_weights[col] = 0.0

    # ------------------------------------------------------------------
    # Step 7: Validate weight sum
    # ------------------------------------------------------------------
    weight_sum = sum(final_weights.values())
    if abs(weight_sum - 1.0) > WEIGHT_SUM_TOLERANCE:
        raise EntropyWeightError(
            f"Final weights sum to {weight_sum:.12f}, expected 1.0 "
            f"(tolerance {WEIGHT_SUM_TOLERANCE}).  "
            f"Constant: {constant_factors}, Degenerate: {degenerate_factors}"
        )

    return final_weights


# ---------------------------------------------------------------------------
# Factor diagnostics
# ---------------------------------------------------------------------------

def compute_factor_diagnostics(
    df: pd.DataFrame,
    factor_cols: list[str],
    low_cv_threshold: float = 0.05,
) -> list[dict[str, Any]]:
    """
    Compute comprehensive per-factor diagnostics.

    Parameters
    ----------
    df : pd.DataFrame
        Block-level data.
    factor_cols : list[str]
        Factor column names.
    low_cv_threshold : float
        Coefficient of variation below which ``low_spatial_variation``
        is flagged.  This is a **reporting threshold only** and does
        NOT trigger any automatic weight adjustment.

    Returns
    -------
    list[dict]
        One dict per factor with keys:
        ``name``, ``min``, ``max``, ``mean``, ``median``, ``std``,
        ``cv``, ``n_unique``, ``modal_value``, ``modal_share_pct``,
        ``constant``, ``degenerate``, ``low_spatial_variation``,
        ``raw_entropy_weight``, ``final_weight``.
    """
    n = len(df)

    # Compute weights (to get raw and final)
    final_weights = entropy_weights(df, factor_cols)

    # Compute raw weights separately (without degenerate capping)
    # by running the core entropy computation
    raw_weights = _compute_raw_entropy_weights(df, factor_cols)

    diagnostics = []
    for col in factor_cols:
        series = df[col]
        lo = float(series.min())
        hi = float(series.max())
        mean_val = float(series.mean())
        median_val = float(series.median())
        std_val = float(series.std())
        cv = std_val / mean_val if mean_val != 0 else 0.0

        counts = Counter(series)
        modal_value, modal_count = counts.most_common(1)[0]
        modal_share_pct = (modal_count / n) * 100

        is_constant = (hi - lo) == 0
        is_degenerate = (not is_constant) and (modal_count / n > MODAL_SHARE_THRESHOLD)
        is_low_variation = (not is_constant) and (cv < low_cv_threshold)

        diagnostics.append({
            "name": col,
            "min": lo,
            "max": hi,
            "mean": mean_val,
            "median": median_val,
            "std": std_val,
            "cv": cv,
            "n_unique": int(series.nunique()),
            "modal_value": float(modal_value),
            "modal_share_pct": round(modal_share_pct, 2),
            "constant": is_constant,
            "degenerate": is_degenerate,
            "low_spatial_variation": is_low_variation,
            "raw_entropy_weight": raw_weights.get(col, 0.0),
            "final_weight": final_weights.get(col, 0.0),
        })

    return diagnostics


def _compute_raw_entropy_weights(
    df: pd.DataFrame,
    factor_cols: list[str],
) -> dict[str, float]:
    """
    Compute raw entropy weights WITHOUT degenerate-factor capping.

    This is used internally by diagnostics to report what the weight
    *would have been* before Safeguard B.
    """
    n = len(df)
    if n <= 1:
        return {col: 1.0 / len(factor_cols) for col in factor_cols}

    shifted = pd.DataFrame()
    constant_factors: set[str] = set()
    eps = 1e-12

    for col in factor_cols:
        lo, hi = df[col].min(), df[col].max()
        if pd.isna(lo) or pd.isna(hi) or (hi - lo) == 0:
            shifted[col] = 0.0
            constant_factors.add(col)
        else:
            if lo < 0:
                shifted[col] = df[col] - lo + eps
            else:
                shifted[col] = df[col]

    variable_cols = [c for c in factor_cols if c not in constant_factors]

    if not variable_cols:
        return {col: 1.0 / len(factor_cols) for col in factor_cols}

    p = shifted[variable_cols].div(
        shifted[variable_cols].sum(axis=0), axis=1
    )

    k = 1.0 / math.log(n)
    entropy = {}
    for col in variable_cols:
        p_col = p[col].values
        p_safe = np.where(p_col > 0, p_col, 1.0)
        term = np.where(p_col > 0, p_col * np.log(p_safe), 0.0)
        entropy[col] = -k * term.sum()

    diversity = {col: max(1 - e, 0) for col, e in entropy.items()}
    total_d = sum(diversity.values()) or 1
    raw_weights = {col: d / total_d for col, d in diversity.items()}

    for col in constant_factors:
        raw_weights[col] = 0.0

    return raw_weights


# ---------------------------------------------------------------------------
# Printing helpers
# ---------------------------------------------------------------------------

def print_diagnostics_table(diagnostics: list[dict[str, Any]]) -> None:
    """Print a formatted diagnostics table to stdout."""
    header = (
        f"{'Factor':<25s} {'Min':>10s} {'Max':>10s} {'Mean':>10s} "
        f"{'Median':>10s} {'Std':>10s} {'CV':>8s} {'Unique':>7s} "
        f"{'Modal':>10s} {'Modal%':>8s} {'Const':>6s} {'Degen':>6s} "
        f"{'LowVar':>7s} {'RawWt':>8s} {'FinalWt':>8s}"
    )
    print(header)
    print("-" * len(header))

    for d in diagnostics:
        print(
            f"{d['name']:<25s} "
            f"{d['min']:>10.4f} {d['max']:>10.4f} {d['mean']:>10.4f} "
            f"{d['median']:>10.4f} {d['std']:>10.4f} {d['cv']:>8.4f} "
            f"{d['n_unique']:>7d} {d['modal_value']:>10.4f} "
            f"{d['modal_share_pct']:>7.2f}% "
            f"{'YES' if d['constant'] else 'no':>6s} "
            f"{'YES' if d['degenerate'] else 'no':>6s} "
            f"{'YES' if d['low_spatial_variation'] else 'no':>7s} "
            f"{d['raw_entropy_weight']:>8.4f} {d['final_weight']:>8.4f}"
        )

    # Weight sum check
    total_raw = sum(d['raw_entropy_weight'] for d in diagnostics)
    total_final = sum(d['final_weight'] for d in diagnostics)
    print("-" * len(header))
    print(
        f"{'TOTAL':<25s} {'':>10s} {'':>10s} {'':>10s} "
        f"{'':>10s} {'':>10s} {'':>8s} {'':>7s} "
        f"{'':>10s} {'':>8s} {'':>6s} {'':>6s} {'':>7s} "
        f"{total_raw:>8.4f} {total_final:>8.4f}"
    )

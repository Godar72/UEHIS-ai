"""
scoring/normalize.py
────────────────────
Min-max normalisation functions for UEHI scoring factors.

* **Positive indicators** (higher raw value → better ecological health):
  standard min-max scaling  →  ``(x − min) / (max − min)``  →  1 = best.

* **Negative indicators** (higher raw value → worse ecological health):
  inverted min-max scaling  →  ``(max − x) / (max − min)``  →  1 = best.

Both functions map values to the closed interval [0, 1] and are safe for
constant-value columns (returns 0.0 when max == min).
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def min_max_scale(series: pd.Series) -> pd.Series:
    """
    Standard min-max normalisation to [0, 1].

    Higher raw value → higher normalised value.

    Parameters
    ----------
    series : pd.Series
        Raw indicator values.

    Returns
    -------
    pd.Series
        Normalised values in [0, 1].
    """
    lo, hi = series.min(), series.max()
    if hi - lo == 0:
        return pd.Series(0.0, index=series.index)
    return (series - lo) / (hi - lo)


def inverted_min_max_scale(series: pd.Series) -> pd.Series:
    """
    Inverted min-max normalisation to [0, 1].

    Higher raw value → *lower* normalised value.

    Parameters
    ----------
    series : pd.Series
        Raw indicator values.

    Returns
    -------
    pd.Series
        Normalised values in [0, 1].
    """
    lo, hi = series.min(), series.max()
    if hi - lo == 0:
        return pd.Series(0.0, index=series.index)
    return (hi - series) / (hi - lo)


def normalise_factor(
    series: pd.Series,
    direction: str,
) -> pd.Series:
    """
    Dispatch to the correct normaliser based on factor direction.

    Parameters
    ----------
    series : pd.Series
        Raw indicator values.
    direction : str
        ``"positive"`` or ``"negative"``.

    Returns
    -------
    pd.Series
        Normalised values in [0, 1].

    Raises
    ------
    ValueError
        If *direction* is not ``"positive"`` or ``"negative"``.
    """
    if direction == "positive":
        return min_max_scale(series)
    elif direction == "negative":
        return inverted_min_max_scale(series)
    else:
        raise ValueError(
            f"Unknown direction '{direction}'. Use 'positive' or 'negative'."
        )

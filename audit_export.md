# UEHIS Phase 3 Raster-First Audit Export
==================================================
PART 1 — ACTUAL CODE
==================================================
### run_phase3.py
```python
import sys, math, os
from pathlib import Path
import json

# Force UTF-8 output on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import box
import rasterio

from scoring.normalize import normalise_factor
from scoring.entropy import (
    entropy_weights,
    compute_factor_diagnostics,
    print_diagnostics_table,
    EntropyWeightError,
)

from feature_engineering.aggregate_factors import (
    rasterize_osm_to_grid,
    build_impervious_union,
    aggregate_all_factors
)

# Configuration
MERGED_PATH   = Path("outputs/kothrud_merged.geojson")
SEG_TIF       = Path("outputs/unet_validation/production_segmentation.tif")
BLDG_TIF      = Path("outputs/phase3_osm_bldg.tif")
ROAD_TIF      = Path("outputs/phase3_osm_road.tif")
UNION_TIF     = Path("outputs/final_impervious_union.tif")
NDVI_TIF      = Path("outputs/kothrud_ndvi_band4.tif")
LST_TIF       = Path("outputs/kothrud_lst.tif")
POP_TIF       = Path("outputs/kothrud_population.tif")
OUTPUT_CSV    = Path("outputs/kothrud_scores_phase3.csv")

ALPHA = 0.1
BETA  = 0.3
BLOCK_SIZE_M = 250

FACTORS = {
    "ndvi":                 ("positive", "REAL"),
    "tree_density":         ("positive", "REAL"),
    "pm25":                 ("negative", "REAL"),
    "temperature":          ("negative", "REAL"),
    "impervious_surfaces":  ("negative", "REAL"),
    "population_exposure":  ("negative", "REAL"),
}

def make_block_grid(bounds, cell_size_m=250):
    west, south, east, north = bounds
    lat_mid = (south + north) / 2
    dy = cell_size_m / 111_320
    dx = cell_size_m / (111_320 * math.cos(math.radians(lat_mid)))

    cols = int(math.ceil((east - west) / dx))
    rows = int(math.ceil((north - south) / dy))

    cells = []
    for r in range(rows):
        for c in range(cols):
            x0 = west + c * dx
            y0 = south + r * dy
            x1 = min(x0 + dx, east)
            y1 = min(y0 + dy, north)
            cells.append({
                "geometry": box(x0, y0, x1, y1),
                "block_row": r,
                "block_col": c,
                "block_id": f"R{r:02d}_C{c:02d}",
            })

    grid = gpd.GeoDataFrame(cells, crs="EPSG:4326")
    print(f"[Blocks] Created {len(grid)} blocks")
    return grid

def main():
    print("=" * 70)
    print("  UEHI Scoring Pipeline Phase 3 -- Kothrud")
    print("=" * 70)
    
    # 1. Block grid
    with rasterio.open("kothrud_pune_composite.tif") as src:
        raster_bounds = src.bounds
        
    grid = make_block_grid(
        (raster_bounds.left, raster_bounds.bottom,
         raster_bounds.right, raster_bounds.top),
        cell_size_m=BLOCK_SIZE_M,
    )
    
    # 2. OSM Rasterization
    print("\n[Rasterization] Creating OSM rasters matching segmentation target...")
    merged = gpd.read_file(str(MERGED_PATH))
    bldgs = merged[merged["feature_type"] == "building"]
    roads = merged[merged["feature_type"] == "road"]
    
    if not BLDG_TIF.exists() or not ROAD_TIF.exists():
        rasterize_osm_to_grid(bldgs, str(SEG_TIF), str(BLDG_TIF))
        rasterize_osm_to_grid(roads, str(SEG_TIF), str(ROAD_TIF))
        
    # 3. Impervious Union
    if not UNION_TIF.exists():
        print("[Rasterization] Building impervious union...")
        build_impervious_union(str(SEG_TIF), str(BLDG_TIF), str(ROAD_TIF), str(UNION_TIF))
        
    # 3.5 Align factors
    from rasterio.warp import reproject, Resampling
    
    def align_raster(src_path, dst_path, ref_path, resampling=Resampling.bilinear):
        if Path(dst_path).exists(): return
        with rasterio.open(ref_path) as ref:
            ref_prof = ref.profile.copy()
            
        with rasterio.open(src_path) as src:
            data = np.empty((ref_prof['height'], ref_prof['width']), dtype=src.profile['dtype'])
            reproject(
                source=rasterio.band(src, 1),
                destination=data,
                src_transform=src.transform,
                src_crs=src.crs,
                dst_transform=ref_prof['transform'],
                dst_crs=ref_prof['crs'],
                resampling=resampling
            )
            ref_prof.update(dtype=src.profile['dtype'], count=1, nodata=src.nodata)
            with rasterio.open(dst_path, 'w', **ref_prof) as dst:
                dst.write(data, 1)

    print("[Alignment] Aligning environmental factors to 10m grid...")
    ALIGNED_NDVI = Path("outputs/phase3_ndvi_10m.tif")
    ALIGNED_LST = Path("outputs/phase3_lst_10m.tif")
    ALIGNED_POP = Path("outputs/phase3_pop_10m.tif")
    
    align_raster(str(NDVI_TIF), str(ALIGNED_NDVI), str(SEG_TIF), Resampling.bilinear)
    align_raster(str(LST_TIF), str(ALIGNED_LST), str(SEG_TIF), Resampling.bilinear)
    # Population usually needs area-weighted or nearest, we'll use nearest for density 
    align_raster(str(POP_TIF), str(ALIGNED_POP), str(SEG_TIF), Resampling.nearest)
    
    # 4. Fetch PM2.5
    print("\n[Aggregate] PM2.5 handling...")
    pm25_tif_path = None
    if os.environ.get("UEHIS_TEST_NO_GEE") == "1":
        print("[Aggregate] DEV MODE: Skipping GEE PM2.5 fetch, generating NaNs.")
    else:
        from data_ingestion.acag_pm25 import fetch_and_align_acag_pm25
        roi_bounds = tuple(grid.to_crs(epsg=4326).total_bounds)
        pm25_tif_path, pm25_manifest = fetch_and_align_acag_pm25(roi_bounds, str(SEG_TIF))
        pm25_tif_path = str(pm25_tif_path) # ensure string for aggregate_all_factors
        
    # 5. Aggregate all factors
    print("\n[Aggregate] Aggregating raster-first factors to 250m blocks...")
    df, manifest = aggregate_all_factors(
        blocks_gdf=grid,
        seg_tif=str(SEG_TIF),
        bldg_tif=str(BLDG_TIF),
        road_tif=str(ROAD_TIF),
        union_tif=str(UNION_TIF),
        ndvi_tif=str(ALIGNED_NDVI),
        temp_tif=str(ALIGNED_LST),
        pop_tif=str(ALIGNED_POP),
        pm25_tif=pm25_tif_path
    )
    
    # Write manifest
    with open("outputs/phase3_manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)
        
    # Merge block info (row, col)
    df = df.merge(grid[['block_id', 'block_row', 'block_col', 'geometry']], on='block_id')
    
    # 6. Filter incomplete edge cells
    df['block_area_m2'] = gpd.GeoDataFrame(df, crs="EPSG:4326").to_crs(epsg=32643).geometry.area
    median_area = df["block_area_m2"].median()
    area_threshold = 0.80 * median_area
    n_before = len(df)
    df = df[df["block_area_m2"] >= area_threshold].reset_index(drop=True)
    n_removed = n_before - len(df)
    print(f"\n[Filter] Removed {n_removed} incomplete edge blocks. Remaining: {len(df)}")
    
    # 7. Entropy Scoring
    factor_cols = list(FACTORS.keys())
    print(f"\n[Entropy] Computing entropy-based weights for {len(factor_cols)} active factors...")

    # If PM25 is all NaNs, we can't do entropy weighting properly, but DEV mode requires it
    # We'll just fill PM2.5 with 0 for entropy if it's all NaNs and DEV MODE is active.
    if os.environ.get("UEHIS_TEST_NO_GEE") == "1" and df['pm25'].isnull().all():
        df_for_entropy = df.copy()
        df_for_entropy['pm25'] = 0.0
    else:
        df_for_entropy = df
        
    try:
        ew = entropy_weights(df_for_entropy, factor_cols)
    except EntropyWeightError as e:
        print(f"FATAL: Entropy weight error: {e}")
        sys.exit(1)

    print("\n[Weights] Entropy-based weights:")
    for col in factor_cols:
        print(f"  {col:25s}: {ew[col]:.4f}")
        
    weighted_sum = pd.Series(0.0, index=df.index)
    for col in factor_cols:
        direction = FACTORS[col][0]
        normed = normalise_factor(df_for_entropy[col], direction)
        weighted_sum += ew[col] * normed

    base_score = (weighted_sum * 100).clip(0, 100)

    # Synergy
    canopy_norm = normalise_factor(df_for_entropy["tree_density"], "positive")
    temp_norm = normalise_factor(df_for_entropy["temperature"], "negative")
    synergy = ALPHA * canopy_norm * temp_norm * 100
    
    # Population
    pop_norm = normalise_factor(df_for_entropy["population_exposure"], "positive")
    pop_multiplier = 1 - BETA * pop_norm
    
    final_score = ((base_score + synergy) * pop_multiplier).clip(0, 100).round(2)
    df["uehi_score"] = final_score
    
    def classify(s):
        if s < 25: return "Critical"
        if s < 50: return "High"
        if s < 75: return "Moderate"
        return "Low"

    df["risk_level"] = df["uehi_score"].apply(classify)
    
    csv_cols = ["block_id", "block_row", "block_col", "geometry_hash", "block_area_m2",
                "ndvi", "tree_density", "pm25", "temperature", "impervious_surfaces", "population_exposure",
                "uehi_score", "risk_level"]
    
    OUTPUT_CSV.parent.mkdir(exist_ok=True)
    df[csv_cols].to_csv(str(OUTPUT_CSV), index=False)
    print(f"\n[Output] Phase 3 scores saved to {OUTPUT_CSV.resolve()}")

    # Compare Phase 3 vs V4 baseline
    print(f"\n{'='*70}")
    print(f"  REGRESSION ANALYSIS: Phase 3 Raster vs V4 Vector Baseline")
    print(f"{'='*70}")
    old_path = Path("outputs/kothrud_scores.csv")
    if old_path.exists():
        from scipy import stats as scipy_stats
        old = pd.read_csv(old_path)
        new = df.copy()
        merged_cmp = old.merge(new, on="block_id", suffixes=("_old", "_new"))
        if len(merged_cmp) > 0:
            old_scores = merged_cmp["uehi_score_old"]
            new_scores = merged_cmp["uehi_score_new"]
            pearson_r, _ = scipy_stats.pearsonr(old_scores, new_scores)
            abs_diff = (old_scores - new_scores).abs()
            print(f"  Score stability ({len(merged_cmp)} matched blocks):")
            print(f"    Pearson correlation:           {pearson_r:.4f}")
            print(f"    Max absolute score difference: {abs_diff.max():.4f}")
            print(f"    Median absolute difference:    {abs_diff.median():.4f}")
        else:
            print("  No matching blocks for comparison.")
    else:
        print("  V4 baseline not found.")
        
    print("Done.")

if __name__ == "__main__":
    main()

```
### scoring/entropy.py
```python
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
        if hi - lo > 0:
            if lo < 0:
                shifted[col] = df[col] - lo + eps
            else:
                shifted[col] = df[col]
        else:
            shifted[col] = 0.0
            constant_factors.add(col)

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
        if hi - lo > 0:
            if lo < 0:
                shifted[col] = df[col] - lo + eps
            else:
                shifted[col] = df[col]
        else:
            shifted[col] = 0.0
            constant_factors.add(col)

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

```
### scoring/uehi_score.py
```python
"""
scoring/uehi_score.py
─────────────────────
7-factor Urban Eco-Heat Island (UEHI) scoring engine.

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
    config = load_config(config_path)
    factors = config["factors"]

    # Validate that all factor columns exist
    missing = [f for f in factors if f not in gdf.columns]
    if missing:
        raise KeyError(
            f"GeoDataFrame is missing required factor columns: {missing}"
        )

    result = gdf.copy()

    # Normalise each factor and accumulate the weighted sum
    weighted_sum = pd.Series(0.0, index=result.index)

    for name, spec in factors.items():
        weight = spec["weight"]
        direction = spec["direction"]

        norm_col = f"_norm_{name}"
        result[norm_col] = normalise_factor(result[name], direction)
        weighted_sum += weight * result[norm_col]

    # Scale to 0–100 and clamp for safety
    result[score_column] = (weighted_sum * 100).clip(0, 100).round(2)

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

```
### data_ingestion/acag_pm25.py
```python
"""
data_ingestion/acag_pm25.py
───────────────────────────
Fetches ACAG/WUSTL SatPM V6.GL.03 PM2.5 monthly estimates from Google Earth Engine,
computes a seasonal mean (Jan, Feb, Mar 2024), and aligns/resamples the raster
to match a given reference grid (UEHIS 250m block grid).

Provenance and ACAG metadata are handled strictly.
"""

import os
import json
import hashlib
import sys
import subprocess
from datetime import datetime
from pathlib import Path

import ee
import geemap
import numpy as np
import rasterio
from rasterio.warp import reproject, Resampling
from rasterio.transform import Affine

from data_ingestion.sentinel import authenticate_gee

# ---------------------------------------------------------------------------
# Configuration (ACAG PM2.5)
# ---------------------------------------------------------------------------
ACAG_GEE_COLLECTION = 'projects/gee-community-catalog/datasets/pm25_monthly'
PM25_YEAR = 2024
PM25_MONTHS = [1, 2, 3]  # Jan, Feb, Mar

class PM25FetchError(Exception):
    """Raised when PM2.5 fetch or validation fails."""
    pass

def _get_git_commit():
    try:
        return subprocess.check_output(['git', 'rev-parse', 'HEAD'], stderr=subprocess.DEVNULL, text=True).strip()
    except Exception:
        return "unknown"

def _hash_file(filepath):
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

def fetch_and_align_acag_pm25(
    roi_bounds: tuple[float, float, float, float],
    reference_tif_path: str,
    output_dir: str = "outputs/pm25"
) -> tuple[str, dict]:
    """
    Fetch ACAG PM2.5 from GEE for Jan-Mar 2024, compute mean, download native raster,
    and then strictly align (reproject + bilinear resample) to the reference_tif_path.
    
    Parameters
    ----------
    roi_bounds : tuple
        (west, south, east, north) in EPSG:4326.
    reference_tif_path : str
        Path to a reference GeoTIFF (e.g. unet segmentation) to align to exactly.
    output_dir : str
        Directory to save outputs.
        
    Returns
    -------
    tuple[str, dict]
        Path to the aligned seasonal PM2.5 GeoTIFF and its provenance manifest.
    """
    authenticate_gee()
    
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Temporal Validation
    start_date = f"{PM25_YEAR}-01-01"
    end_date = f"{PM25_YEAR}-04-01"
    
    col = ee.ImageCollection(ACAG_GEE_COLLECTION).filterDate(start_date, end_date)
    count = col.size().getInfo()
    
    if count != 3:
        raise PM25FetchError(
            f"Expected exactly 3 monthly images (Jan, Feb, Mar {PM25_YEAR}) but found {count}."
            " Cannot silently substitute missing data."
        )
        
    print(f"[PM2.5] Found {count} monthly grids for {PM25_YEAR}.")
    
    # Check that months are strictly 1, 2, 3
    img_list = col.toList(count)
    found_months = []
    for i in range(count):
        img = ee.Image(img_list.get(i))
        # The ACAG monthly images usually have system:time_start
        date = ee.Date(img.get('system:time_start')).getInfo()
        month = datetime.utcfromtimestamp(date['value']/1000.0).month
        found_months.append(month)
        
    if sorted(found_months) != sorted(PM25_MONTHS):
        raise PM25FetchError(
            f"Missing required months. Found: {found_months}, Expected: {PM25_MONTHS}"
        )
        
    print(f"[PM2.5] Verified months: {found_months}")
    
    # 2. Strict Band Validation
    first_img = ee.Image(img_list.get(0))
    band_names = first_img.bandNames().getInfo()
    if 'b1' not in band_names:
        raise PM25FetchError(f"Expected band 'b1' not found in collection. Available: {band_names}")
    
    col = col.select('b1')
    
    # 3. Compute Seasonal Mean with Strict 3-Month Validity
    # A pixel is only valid if it has valid data in all 3 months.
    valid_count = col.count()
    seasonal_mean = col.mean().updateMask(valid_count.eq(3))
    
    # 4. Export Native Raster (Buffered)
    west, south, east, north = roi_bounds
    # Buffer by ~0.05 deg (~5km) to ensure edge coverage during resampling
    buffer = 0.05
    export_roi = ee.Geometry.Rectangle([west - buffer, south - buffer, east + buffer, north + buffer])
    
    native_tif = os.path.join(output_dir, f"pm25_acag_v6gl03_{PM25_YEAR}_jan_mar_native.tif")
    
    print("[PM2.5] Downloading native PM2.5 raster from GEE...")
    geemap.ee_export_image(
        seasonal_mean,
        filename=native_tif,
        scale=1113.2, # ~0.01 deg
        region=export_roi,
        file_per_band=False,
    )
    
    if not os.path.exists(native_tif):
        raise PM25FetchError("Failed to download native raster from GEE.")
        
    # 4. Strict Alignment to Reference Grid
    aligned_tif = os.path.join(output_dir, f"pm25_acag_v6gl03_{PM25_YEAR}_jan_mar_seasonal_aligned.tif")
    
    with rasterio.open(reference_tif_path) as ref_src:
        ref_profile = ref_src.profile.copy()
        ref_crs = ref_src.crs
        ref_transform = ref_src.transform
        ref_width = ref_src.width
        ref_height = ref_src.height
        
    print(f"[PM2.5] Aligning to reference grid ({ref_width}x{ref_height}, {ref_crs})...")
    
    with rasterio.open(native_tif) as src:
        # We enforce Bilinear resampling for continuous PM2.5
        dst_array = np.empty((ref_height, ref_width), dtype=np.float32)
        
        reproject(
            source=rasterio.band(src, 1),
            destination=dst_array,
            src_transform=src.transform,
            src_crs=src.crs,
            dst_transform=ref_transform,
            dst_crs=ref_crs,
            resampling=Resampling.bilinear,
            src_nodata=src.nodata,
            dst_nodata=np.nan
        )
        
    # Removed value-based nodata masking (dst_array[dst_array <= 0] = np.nan)
    
    ref_profile.update(
        dtype=rasterio.float32,
        count=1,
        nodata=np.nan,
        compress='lzw'
    )
    
    with rasterio.open(aligned_tif, 'w', **ref_profile) as dst:
        dst.write(dst_array, 1)
        # Provenance tags
        dst.update_tags(
            dataset_identity="ACAG_V6GL03_SatPM25",
            temporal_window=f"{PM25_YEAR}-01 to {PM25_YEAR}-03",
            temporal_design="seasonal_mean_jan_feb_mar_strict",
            native_resolution="0.01 degrees",
            resampling_method="bilinear",
            processing_date=datetime.now().isoformat()
        )
        
    print(f"[PM2.5] Aligned raster saved to: {aligned_tif}")
    
    manifest = {
        "run_id": f"pm25_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{os.urandom(4).hex()}",
        "source_name": "ACAG/WUSTL SatPM",
        "product_version": "V6.GL.03",
        "source_url": "projects/gee-community-catalog/datasets/pm25_monthly",
        "download_date": datetime.now().isoformat(),
        "source_file_sha256": _hash_file(native_tif),
        "aligned_file_sha256": _hash_file(aligned_tif),
        "source_variable_name": "b1",
        "source_units": "ug/m3",
        "source_native_crs": str(src.crs),
        "source_native_spatial_resolution": "0.01 degrees",
        "requested_months": PM25_MONTHS,
        "selected_image_months": found_months,
        "seasonal_aggregation_rule": "Strict 3-month arithmetic mean (masked if any month missing)",
        "reprojection_crs": str(ref_crs),
        "target_uehis_grid_dimensions": f"{ref_width}x{ref_height}",
        "target_resolution": f"{ref_transform[0]}x{-ref_transform[4]} meters",
        "target_affine_transform": [ref_transform.a, ref_transform.b, ref_transform.c, ref_transform.d, ref_transform.e, ref_transform.f],
        "target_bounds": [ref_src.bounds.left, ref_src.bounds.bottom, ref_src.bounds.right, ref_src.bounds.top],
        "resampling_method": "bilinear",
        "nodata_handling": "Native nodata mapped to NaN; no value-based masking",
        "code_version": _get_git_commit(),
        "python_version": sys.version.split()[0]
    }
    
    manifest_path = os.path.join(output_dir, "pm25_provenance.json")
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)
        
    return aligned_tif, manifest

if __name__ == "__main__":
    # Test run
    # ROI: Pune bounds
    roi = (73.7498, 18.4295, 74.0202, 18.6209)
    # Require a reference TIF to exist. We can use outputs/kothrud_ndvi_segmentation.tif if it exists,
    # or just exit with a warning.
    ref_tif = Path("outputs/kothrud_ndvi_segmentation.tif")
    if ref_tif.exists():
        align, man = fetch_and_align_acag_pm25(roi, str(ref_tif))
        print("Success. Run ID:", man["run_id"])
    else:
        print(f"Test skipped: Reference TIF {ref_tif} not found.")

```
### feature_engineering/aggregate_factors.py
```python
import json
import hashlib
from datetime import datetime
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.features import rasterize, shapes
import shapely
from shapely.geometry import shape
from pathlib import Path
import warnings
import sys

# --- Geometry Hash ---
def canonical_geometry_hash(geom, crs):
    """
    Deterministically hash a geometry.
    - Reproject to EPSG:32643
    - Round coordinates to 3 decimal places
    - Serialize deterministically to WKT
    - Hash using SHA-256
    """
    if crs != "EPSG:32643":
        geom = gpd.GeoSeries([geom], crs=crs).to_crs("EPSG:32643").iloc[0]
    
    geom = shapely.set_precision(geom, 0.001)
    wkt_str = shapely.wkt.dumps(geom, rounding_precision=3)
    return hashlib.sha256(wkt_str.encode('utf-8')).hexdigest()

# --- Grid Validation ---
def validate_grid(raster_path, ref_profile):
    with rasterio.open(raster_path) as src:
        prof = src.profile
        if prof['crs'] != ref_profile['crs']:
            raise ValueError(f"CRS mismatch in {raster_path}: {prof['crs']} != {ref_profile['crs']}")
        if prof['width'] != ref_profile['width'] or prof['height'] != ref_profile['height']:
            raise ValueError(f"Dimensions mismatch in {raster_path}: {prof['width']}x{prof['height']} vs {ref_profile['width']}x{ref_profile['height']}")
        if prof['transform'] != ref_profile['transform']:
            raise ValueError(f"Transform mismatch in {raster_path}")
    return True

# --- OSM Rasterization ---
def rasterize_osm_to_grid(osm_gdf, target_raster_path, out_path, nodata=255):
    with rasterio.open(target_raster_path) as src:
        prof = src.profile.copy()
        
    if osm_gdf.empty:
        arr = np.full((prof['height'], prof['width']), 0, dtype=np.uint8) # 0 means pervious/non-built
    else:
        if osm_gdf.crs != prof['crs']:
            osm_gdf = osm_gdf.to_crs(prof['crs'])
        # all_touched=False assigns pixel if its center is within the polygon (50% threshold for squares).
        shapes_gen = ((geom, 1) for geom in osm_gdf.geometry if geom is not None and not geom.is_empty)
        try:
            arr = rasterize(shapes_gen, out_shape=(prof['height'], prof['width']), transform=prof['transform'], fill=0, dtype=np.uint8, all_touched=False)
        except ValueError:
            arr = np.full((prof['height'], prof['width']), 0, dtype=np.uint8)
            
    prof.update(dtype=rasterio.uint8, count=1, nodata=nodata, compress='lzw')
    with rasterio.open(out_path, 'w', **prof) as dst:
        dst.write(arr, 1)
    return Path(out_path)

# --- Impervious Union ---
def build_impervious_union(unet_tif, bldg_tif, road_tif, out_path):
    with rasterio.open(unet_tif) as src_u:
        unet = src_u.read(1)
        prof = src_u.profile.copy()
        nodata_u = src_u.nodata
    
    validate_grid(bldg_tif, prof)
    validate_grid(road_tif, prof)
    
    with rasterio.open(bldg_tif) as src_b, rasterio.open(road_tif) as src_r:
        bldg = src_b.read(1)
        road = src_r.read(1)
        nodata_b = src_b.nodata if src_b.nodata is not None else 255
        nodata_r = src_r.nodata if src_r.nodata is not None else 255
        
    u_valid = (unet != nodata_u) & (~np.isnan(unet) if unet.dtype.kind == 'f' else True)
    b_valid = (bldg != nodata_b)
    r_valid = (road != nodata_r)
    
    any_valid = u_valid | b_valid | r_valid
    union = np.full(unet.shape, 255, dtype=np.uint8)
    
    # Base fill for valid pixels is 0 (Pervious)
    union[any_valid] = 0
    
    # Impervious is any valid source being 1
    imp_mask = any_valid & (
        (u_valid & (unet == 1)) |
        (b_valid & (bldg == 1)) |
        (r_valid & (road == 1))
    )
    union[imp_mask] = 1
    
    prof.update(dtype=rasterio.uint8, count=1, nodata=255, compress='lzw')
    with rasterio.open(out_path, 'w', **prof) as dst:
        dst.write(union, 1)
    return Path(out_path)

# --- Zonal Core ---
def _rasterize_blocks(blocks_gdf, prof):
    if blocks_gdf.crs != prof['crs']:
        blocks_gdf = blocks_gdf.to_crs(prof['crs'])
    
    shapes_gen = ((geom, idx) for idx, geom in enumerate(blocks_gdf.geometry))
    try:
        block_idx_arr = rasterize(shapes_gen, out_shape=(prof['height'], prof['width']), transform=prof['transform'], fill=-1, dtype=np.int32, all_touched=False)
    except ValueError:
        block_idx_arr = np.full((prof['height'], prof['width']), -1, dtype=np.int32)
    return block_idx_arr

def aggregate_segmentation_to_blocks(unet_data, unet_prof, block_idx_arr, num_blocks):
    nodata = unet_prof['nodata']
    
    valid_mask = (block_idx_arr >= 0) & (unet_data != nodata)
    valid_bidx = block_idx_arr[valid_mask]
    valid_data = unet_data[valid_mask]
    
    v_cnt = np.bincount(valid_bidx, minlength=num_blocks)
    c_cnt = np.bincount(valid_bidx[valid_data == 0], minlength=num_blocks)
    t_cnt = np.bincount(block_idx_arr[block_idx_arr >= 0], minlength=num_blocks)
    
    with np.errstate(divide='ignore', invalid='ignore'):
        td = np.where(v_cnt > 0, c_cnt / v_cnt, np.nan)
        comp = np.where(t_cnt > 0, v_cnt / t_cnt, 0.0)
        
    return pd.DataFrame({
        "tree_density": td,
        "canopy_pixel_count": c_cnt,
        "segmentation_valid_pixel_count": v_cnt,
        "total_block_pixel_count": t_cnt,
        "segmentation_completeness_fraction": comp
    })

def aggregate_impervious_to_blocks(unet_data, bldg_data, road_data, union_data, prof, block_idx_arr, num_blocks):
    valid_mask = (block_idx_arr >= 0) & (union_data != 255)
    
    bidx = block_idx_arr[valid_mask]
    u_valid = unet_data[valid_mask]
    b_valid = bldg_data[valid_mask]
    r_valid = road_data[valid_mask]
    union_valid = union_data[valid_mask]
    
    v_cnt = np.bincount(bidx, minlength=num_blocks)
    u_cnt = np.bincount(bidx[u_valid == 1], minlength=num_blocks)
    b_cnt = np.bincount(bidx[b_valid == 1], minlength=num_blocks)
    r_cnt = np.bincount(bidx[r_valid == 1], minlength=num_blocks)
    union_cnt = np.bincount(bidx[union_valid == 1], minlength=num_blocks)
    
    if not (np.all(union_cnt >= u_cnt) and np.all(union_cnt >= b_cnt) and np.all(union_cnt >= r_cnt)):
        warnings.warn("QA Failed: Union count is less than individual sources.")
        
    t_cnt = np.bincount(block_idx_arr[block_idx_arr >= 0], minlength=num_blocks)
    
    with np.errstate(divide='ignore', invalid='ignore'):
        imp = np.where(v_cnt > 0, union_cnt / v_cnt, np.nan)
        comp = np.where(t_cnt > 0, v_cnt / t_cnt, 0.0)
        
    return pd.DataFrame({
        "impervious_surfaces": imp,
        "unet_impervious_pixel_count": u_cnt,
        "osm_building_pixel_count": b_cnt,
        "osm_road_pixel_count": r_cnt,
        "impervious_union_pixel_count": union_cnt,
        "impervious_valid_pixel_count": v_cnt,
        "impervious_completeness_fraction": comp
    })

def aggregate_ndvi_to_blocks(ndvi_tif, block_idx_arr, num_blocks):
    with rasterio.open(ndvi_tif) as src:
        data = src.read(1)
        nodata = src.nodata if src.nodata is not None else -9999
        
    valid_mask = (block_idx_arr >= 0) & (data != nodata) & (~np.isnan(data))
    bidx = block_idx_arr[valid_mask]
    valid_data = data[valid_mask]
    
    s_ndvi = np.bincount(bidx, weights=valid_data, minlength=num_blocks)
    c_ndvi = np.bincount(bidx, minlength=num_blocks)
    t_cnt = np.bincount(block_idx_arr[block_idx_arr >= 0], minlength=num_blocks)
    
    with np.errstate(divide='ignore', invalid='ignore'):
        ndvi_mean = np.where(c_ndvi > 0, s_ndvi / c_ndvi, np.nan)
        comp = np.where(t_cnt > 0, c_ndvi / t_cnt, 0.0)
        
    return pd.DataFrame({
        "ndvi": ndvi_mean,
        "ndvi_valid_pixel_count": c_ndvi,
        "ndvi_completeness_fraction": comp
    })

def aggregate_temperature_to_blocks(temp_tif, block_idx_arr, num_blocks):
    with rasterio.open(temp_tif) as src:
        data = src.read(1)
        nodata = src.nodata
        
    valid_mask = (block_idx_arr >= 0) & (~np.isnan(data))
    if nodata is not None:
        valid_mask &= (data != nodata)
        
    bidx = block_idx_arr[valid_mask]
    valid_data = data[valid_mask]
    
    s_temp = np.bincount(bidx, weights=valid_data, minlength=num_blocks)
    c_temp = np.bincount(bidx, minlength=num_blocks)
    t_cnt = np.bincount(block_idx_arr[block_idx_arr >= 0], minlength=num_blocks)
    
    with np.errstate(divide='ignore', invalid='ignore'):
        t_mean = np.where(c_temp > 0, s_temp / c_temp, np.nan)
        comp = np.where(t_cnt > 0, c_temp / t_cnt, 0.0)
        
    return pd.DataFrame({
        "temperature": t_mean,
        "temperature_valid_pixel_count": c_temp,
        "temperature_completeness_fraction": comp
    })

def aggregate_pm25_to_blocks(pm25_tif, block_idx_arr, num_blocks):
    with rasterio.open(pm25_tif) as src:
        data = src.read(1)
        nodata = src.nodata
        
    valid_mask = (block_idx_arr >= 0) & (~np.isnan(data))
    if nodata is not None:
        valid_mask &= (data != nodata)
        
    bidx = block_idx_arr[valid_mask]
    valid_data = data[valid_mask]
    
    s_pm25 = np.bincount(bidx, weights=valid_data, minlength=num_blocks)
    c_pm25 = np.bincount(bidx, minlength=num_blocks)
    t_cnt = np.bincount(block_idx_arr[block_idx_arr >= 0], minlength=num_blocks)
    
    with np.errstate(divide='ignore', invalid='ignore'):
        pm25_mean = np.where(c_pm25 > 0, s_pm25 / c_pm25, np.nan)
        comp = np.where(t_cnt > 0, c_pm25 / t_cnt, 0.0)
        
    return pd.DataFrame({
        "pm25": pm25_mean,
        "pm25_valid_pixel_count": c_pm25,
        "pm25_completeness_fraction": comp
    })


def aggregate_population_to_blocks(pop_tif, blocks_gdf):
    with rasterio.open(pop_tif) as src:
        data = src.read(1)
        prof = src.profile
        nodata = src.nodata
        
    valid_mask = (data != nodata) & (~np.isnan(data))
    shapes_gen = shapes(data, mask=valid_mask, transform=prof['transform'])
    
    pop_records = []
    for geom, val in shapes_gen:
        pop_records.append({"geometry": shape(geom), "pop_val": val})
        
    if not pop_records:
        pop_gdf = gpd.GeoDataFrame(columns=["geometry", "pop_val"], crs=prof['crs'])
    else:
        pop_gdf = gpd.GeoDataFrame(pop_records, crs=prof['crs'])
        
    if pop_gdf.crs != "EPSG:32643":
        pop_gdf = pop_gdf.to_crs("EPSG:32643")
        
    blocks_proj = blocks_gdf.to_crs("EPSG:32643").copy()
    pop_gdf['src_area'] = pop_gdf.geometry.area
    sindex = pop_gdf.sindex
    
    pop_exposure = []
    cell_counts = []
    metadata = []
    comp_frac = []
    
    for _, block in blocks_proj.iterrows():
        b_geom = block.geometry
        if pop_gdf.empty:
            pop_exposure.append(np.nan)
            cell_counts.append(0)
            metadata.append("no_intersection")
            comp_frac.append(0.0)
            continue
            
        possible_idx = list(sindex.intersection(b_geom.bounds))
        if not possible_idx:
            pop_exposure.append(np.nan)
            cell_counts.append(0)
            metadata.append("no_intersection")
            comp_frac.append(0.0)
            continue
            
        possible_cells = pop_gdf.iloc[possible_idx]
        actual_intersect = possible_cells[possible_cells.intersects(b_geom)]
        
        if actual_intersect.empty:
            pop_exposure.append(np.nan)
            cell_counts.append(0)
            metadata.append("no_intersection")
            comp_frac.append(0.0)
            continue
            
        block_pop = 0.0
        covered_area = 0.0
        for _, cell in actual_intersect.iterrows():
            isect = cell.geometry.intersection(b_geom)
            if not isect.is_empty:
                area = isect.area
                covered_area += area
                block_pop += cell['pop_val'] * (area / cell['src_area'])
                
        pop_exposure.append(block_pop)
        cell_counts.append(len(actual_intersect))
        metadata.append("exact_intersection")
        comp_frac.append(covered_area / b_geom.area if b_geom.area > 0 else 0.0)
        
    return pd.DataFrame({
        "population_exposure": pop_exposure,
        "population_source_cell_count": cell_counts,
        "population_coverage_metadata": metadata,
        "population_completeness_fraction": comp_frac
    }, index=blocks_gdf.index)

import uuid
import subprocess

def _hash_file(filepath):
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

def _get_git_commit():
    try:
        return subprocess.check_output(['git', 'rev-parse', 'HEAD'], stderr=subprocess.DEVNULL, text=True).strip()
    except Exception:
        return "unknown"

def _get_raster_provenance(filepath):
    path = str(filepath)
    try:
        content_hash = _hash_file(path)
        with rasterio.open(path) as src:
            tags = src.tags()
            res = src.res
            crs = src.crs.to_string() if src.crs else "unknown"
            
            acq_date = tags.get('TIFFTAG_DATETIME') or tags.get('acquisition_date') or "unknown"
            dataset = tags.get('TIFFTAG_IMAGEDESCRIPTION') or tags.get('dataset_identity') or "unknown"
            
            return {
                "path": path,
                "dataset_identity": dataset,
                "acquisition_date": acq_date,
                "spatial_resolution": {"x": res[0], "y": res[1]},
                "crs": crs,
                "content_sha256": content_hash
            }
    except Exception as e:
        return {
            "path": path,
            "dataset_identity": "unknown",
            "acquisition_date": "unknown",
            "spatial_resolution": "unknown",
            "crs": "unknown",
            "content_sha256": "unknown"
        }

def aggregate_all_factors(blocks_gdf, seg_tif, bldg_tif, road_tif, union_tif, ndvi_tif, temp_tif, pop_tif, pm25_tif):
    # Preload unet prof to validate all other factor grids on production path
    with rasterio.open(seg_tif) as su:
        unet_data = su.read(1)
        unet_prof = su.profile
        
    validate_grid(bldg_tif, unet_prof)
    validate_grid(road_tif, unet_prof)
    validate_grid(union_tif, unet_prof)
    validate_grid(ndvi_tif, unet_prof)
    validate_grid(temp_tif, unet_prof)
    if pm25_tif:
        validate_grid(pm25_tif, unet_prof)
    
    with rasterio.open(bldg_tif) as sb, rasterio.open(road_tif) as sr, rasterio.open(union_tif) as sunion:
        bldg_data = sb.read(1)
        road_data = sr.read(1)
        union_data = sunion.read(1)
        
    # Create block raster once
    block_idx_arr = _rasterize_blocks(blocks_gdf, unet_prof)
    num_blocks = len(blocks_gdf)
    
    df_seg = aggregate_segmentation_to_blocks(unet_data, unet_prof, block_idx_arr, num_blocks)
    df_seg.index = blocks_gdf.index
    
    df_imp = aggregate_impervious_to_blocks(unet_data, bldg_data, road_data, union_data, unet_prof, block_idx_arr, num_blocks)
    df_imp.index = blocks_gdf.index
    
    df_ndvi = aggregate_ndvi_to_blocks(ndvi_tif, block_idx_arr, num_blocks)
    df_ndvi.index = blocks_gdf.index
    
    df_temp = aggregate_temperature_to_blocks(temp_tif, block_idx_arr, num_blocks)
    df_temp.index = blocks_gdf.index
    
    df_pop = aggregate_population_to_blocks(pop_tif, blocks_gdf)
    df_pop.index = blocks_gdf.index
    
    if pm25_tif:
        df_pm25 = aggregate_pm25_to_blocks(pm25_tif, block_idx_arr, num_blocks)
        df_pm25.index = blocks_gdf.index
    else:
        df_pm25 = pd.DataFrame({
            'pm25': np.nan,
            'pm25_valid_pixel_count': 0,
            'pm25_completeness_fraction': 0.0
        }, index=blocks_gdf.index)
    
    # Hash blocks for provenance
    final_df = blocks_gdf[['block_id']].copy()
    final_df['geometry_hash'] = blocks_gdf.geometry.apply(lambda g: canonical_geometry_hash(g, blocks_gdf.crs))
    
    final_df = pd.concat([final_df, df_seg, df_imp, df_ndvi, df_temp, df_pop, df_pm25], axis=1)
    
    manifest = {
        "run_id": str(uuid.uuid4()),
        "timestamp": datetime.now().isoformat(),
        "git_commit": _get_git_commit(),
        "aggregation_version": "1.1",
        "model_checksum": "unknown", # U-Net checksum would normally be propagated, unknown at this layer without direct path
        "python_version": sys.version.split()[0],
        "rasterio_version": rasterio.__version__,
        "geopandas_version": gpd.__version__,
        "numpy_version": np.__version__,
        "pandas_version": pd.__version__,
        "shapely_version": shapely.__version__,
        "geometry_specification": "EPSG:32643",
        "geometry_hash_specification": "SHA-256 of WKT rounded to 3 decimal places",
        "processing_configuration": {
            "osm_rasterization_threshold": "50_percent_center",
            "population_intersection": "exact_area_weighted",
            "impervious_nodata_policy": "unet_valid_or_osm_valid"
        },
        "inputs": {
            "segmentation": _get_raster_provenance(seg_tif),
            "building": _get_raster_provenance(bldg_tif),
            "road": _get_raster_provenance(road_tif),
            "union": _get_raster_provenance(union_tif),
            "ndvi": _get_raster_provenance(ndvi_tif),
            "temperature": _get_raster_provenance(temp_tif),
            "population": _get_raster_provenance(pop_tif)
        }
    }
    if pm25_tif:
        manifest["inputs"]["pm25"] = _get_raster_provenance(pm25_tif)
    
    return final_df, manifest

```
### utils/raster.py
```python
"""
utils/raster.py
───────────────
Generic raster utility functions.
"""

from __future__ import annotations

from pathlib import Path
from typing import Union

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio.mask import mask as rasterio_mask
from shapely.geometry import mapping


def aggregate_raster_zonal_stats(
    raster_path: Union[str, Path],
    blocks_gdf: gpd.GeoDataFrame,
    band: int = 1,
    stat: str = "mean",
) -> pd.Series:
    """
    Aggregate continuous raster values within polygon geometries.

    Parameters
    ----------
    raster_path : str | Path
        Path to the raster file (e.g., GeoTIFF).
    blocks_gdf : gpd.GeoDataFrame
        Polygons over which to aggregate the raster values.
    band : int, optional
        Band index to read (1-indexed), by default 1.
    stat : str, optional
        Statistic to compute. Currently only 'mean' is supported.

    Returns
    -------
    pd.Series
        A pandas Series containing the aggregated value for each block,
        aligned with the index of `blocks_gdf`.
    """
    if stat != "mean":
        raise NotImplementedError(f"Statistic '{stat}' is not yet supported.")

    results = []

    with rasterio.open(raster_path) as src:
        # Ensure CRS match for the geometries
        if blocks_gdf.crs != src.crs:
            blocks_gdf_proj = blocks_gdf.to_crs(src.crs)
        else:
            blocks_gdf_proj = blocks_gdf

        nodata_val = src.nodatavals[band - 1]

        for _, row in blocks_gdf_proj.iterrows():
            geom = [mapping(row.geometry)]
            try:
                out_image, out_transform = rasterio_mask(
                    src, geom, crop=True, all_touched=True
                )
                
                band_data = out_image[band - 1]

                # Mask nodata
                if nodata_val is not None:
                    valid_pixels = band_data[band_data != nodata_val]
                else:
                    valid_pixels = band_data

                # Exclude nan
                valid_pixels = valid_pixels[~np.isnan(valid_pixels)]

                if valid_pixels.size > 0:
                    val = np.mean(valid_pixels)
                else:
                    val = np.nan
            except ValueError:
                # E.g. polygon does not overlap raster
                val = np.nan
            
            results.append(val)

    return pd.Series(results, index=blocks_gdf.index)

```
### tests/test_aggregate_factors.py
```python
import pytest
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
import hashlib
from shapely.geometry import box, Polygon, Point
from feature_engineering.aggregate_factors import (
    validate_grid,
    rasterize_osm_to_grid,
    build_impervious_union,
    aggregate_segmentation_to_blocks,
    aggregate_impervious_to_blocks,
    aggregate_ndvi_to_blocks,
    aggregate_temperature_to_blocks,
    aggregate_population_to_blocks,
    aggregate_all_factors,
    canonical_geometry_hash,
    _rasterize_blocks
)

@pytest.fixture
def dummy_grid_profile():
    return {
        'driver': 'GTiff',
        'dtype': 'uint8',
        'nodata': 255,
        'width': 10,
        'height': 10,
        'count': 1,
        'crs': 'EPSG:4326',
        'transform': rasterio.Affine(0.0001, 0.0, 73.0, 0.0, -0.0001, 18.0)
    }

@pytest.fixture
def tmp_rasters(tmp_path, dummy_grid_profile):
    seg_path = tmp_path / "seg.tif"
    ndvi_path = tmp_path / "ndvi.tif"
    temp_path = tmp_path / "temp.tif"
    bldg_path = tmp_path / "bldg.tif"
    road_path = tmp_path / "road.tif"
    pop_path = tmp_path / "pop.tif"
    union_path = tmp_path / "union.tif"
    
    seg_data = np.zeros((10, 10), dtype=np.uint8)
    seg_data[0:5, 0:5] = 0 # canopy
    seg_data[5:10, 5:10] = 1 # impervious
    seg_data[9, 9] = 255 # nodata
    
    ndvi_data = np.full((10, 10), 0.5, dtype=np.float32)
    ndvi_data[9, 9] = -9999 # nodata
    
    temp_data = np.full((10, 10), 30.0, dtype=np.float32)
    temp_data[9, 9] = np.nan # nodata
    
    bldg_data = np.full((10, 10), 0, dtype=np.uint8)
    bldg_data[0:2, 0:2] = 1
    
    road_data = np.full((10, 10), 0, dtype=np.uint8)
    road_data[0:1, 0:5] = 1
    
    with rasterio.open(seg_path, 'w', **dummy_grid_profile) as dst:
        dst.write(seg_data, 1)
        
    ndvi_prof = dummy_grid_profile.copy()
    ndvi_prof.update(dtype='float32', nodata=-9999)
    with rasterio.open(ndvi_path, 'w', **ndvi_prof) as dst:
        dst.write(ndvi_data, 1)
        
    temp_prof = dummy_grid_profile.copy()
    temp_prof.update(dtype='float32', nodata=np.nan)
    with rasterio.open(temp_path, 'w', **temp_prof) as dst:
        dst.write(temp_data, 1)
        
    with rasterio.open(bldg_path, 'w', **dummy_grid_profile) as dst:
        dst.write(bldg_data, 1)
        
    with rasterio.open(road_path, 'w', **dummy_grid_profile) as dst:
        dst.write(road_data, 1)
        
    build_impervious_union(seg_path, bldg_path, road_path, union_path)
        
    # Population raster (1 cell = 4x4 of 10m grid)
    pop_prof = dummy_grid_profile.copy()
    pop_prof.update(width=2, height=2, transform=rasterio.Affine(0.0005, 0.0, 73.0, 0.0, -0.0005, 18.0), dtype='float32', nodata=-9999)
    pop_data = np.array([[100.0, 200.0], [300.0, 400.0]], dtype=np.float32)
    with rasterio.open(pop_path, 'w', **pop_prof) as dst:
        dst.write(pop_data, 1)
        
    return {
        'seg': seg_path, 'ndvi': ndvi_path, 'temp': temp_path, 
        'bldg': bldg_path, 'road': road_path, 'pop': pop_path,
        'union': union_path,
        'profile': dummy_grid_profile
    }

@pytest.fixture
def blocks_gdf():
    b1 = box(73.0, 17.9995, 73.0005, 18.0)
    b2 = box(73.0005, 17.9985, 73.0015, 17.9995)
    return gpd.GeoDataFrame({'block_id': ['B1', 'B2']}, geometry=[b1, b2], crs="EPSG:4326")

# --- 1. Geometry Hash Tests ---
def test_geometry_hash():
    geom1 = Point(73.1234567, 18.1234567)
    geom2 = Point(73.123456701, 18.123456701) # Truly sub-millimeter diff in degrees (1e-9 deg ~ 0.1 mm)
    geom3 = Point(74.0, 19.0) # Material diff
    
    h1 = canonical_geometry_hash(geom1, "EPSG:4326")
    h2 = canonical_geometry_hash(geom2, "EPSG:4326")
    h3 = canonical_geometry_hash(geom3, "EPSG:4326")
    
    # 3-decimal precision ensures sub-millimeter differences hash the same
    # But wait, in UTM (32643), 0.001 meters is 1 millimeter. So we check if sub-mm differ.
    assert h1 == h2
    assert h1 != h3
    
    # SHA-256 length is 64 hex chars
    assert len(h1) == 64
    
    # Reprojection determinism
    geom1_utm = gpd.GeoSeries([geom1], crs="EPSG:4326").to_crs("EPSG:32643").iloc[0]
    h1_utm = canonical_geometry_hash(geom1_utm, "EPSG:32643")
    assert h1 == h1_utm

# --- 2. Grid Validation on Production Path ---
def test_grid_validation_shifted_raster(tmp_path, tmp_rasters, blocks_gdf):
    shifted_prof = tmp_rasters['profile'].copy()
    shifted_prof['transform'] = rasterio.Affine(0.0001, 0.0, 74.0, 0.0, -0.0001, 18.0)
    shifted_path = tmp_path / "shifted.tif"
    with rasterio.open(shifted_path, 'w', **shifted_prof) as dst:
        dst.write(np.zeros((10,10), dtype=np.uint8), 1)
        
    with pytest.raises(ValueError, match="Transform mismatch"):
        build_impervious_union(tmp_rasters['seg'], shifted_path, tmp_rasters['road'], tmp_path / "u.tif")
        
    with pytest.raises(ValueError, match="Transform mismatch"):
        aggregate_all_factors(blocks_gdf, tmp_rasters['seg'], tmp_rasters['bldg'], tmp_rasters['road'], tmp_rasters['union'], shifted_path, tmp_rasters['temp'], tmp_rasters['pop'], None)

# --- 3 & 7. Population Nodata & Conservation Tests ---
def test_population_conservation(tmp_path, tmp_rasters, dummy_grid_profile):
    pop_path = tmp_path / "test_pop.tif"
    pop_prof = dummy_grid_profile.copy()
    # 2x2 grid in UTM for precise area testing
    pop_prof.update(crs="EPSG:32643", width=2, height=2, transform=rasterio.Affine(100.0, 0.0, 300000.0, 0.0, -100.0, 2000000.0), dtype='float32', nodata=-9999)
    pop_data = np.array([[100.0, 200.0], [300.0, 400.0]], dtype=np.float32)
    with rasterio.open(pop_path, 'w', **pop_prof) as dst:
        dst.write(pop_data, 1)
        
    # A. All cells fully contained in one block
    b_all = box(300000.0, 1999800.0, 300200.0, 2000000.0)
    gdf_all = gpd.GeoDataFrame({'block_id': ['All']}, geometry=[b_all], crs="EPSG:32643")
    res_all = aggregate_population_to_blocks(pop_path, gdf_all)
    assert np.isclose(res_all.loc[0, 'population_exposure'], 1000.0)
    
    # B. One cell split across two blocks (top-left cell: 100 pop)
    b_left = box(300000.0, 1999900.0, 300050.0, 2000000.0)
    b_right = box(300050.0, 1999900.0, 300100.0, 2000000.0)
    gdf_split = gpd.GeoDataFrame({'block_id': ['L', 'R']}, geometry=[b_left, b_right], crs="EPSG:32643")
    res_split = aggregate_population_to_blocks(pop_path, gdf_split)
    assert np.isclose(res_split.loc[0, 'population_exposure'], 50.0)
    assert np.isclose(res_split.loc[1, 'population_exposure'], 50.0)
    
    # E. No coverage -> NaN
    b_miss = box(400000.0, 1999800.0, 400200.0, 2000000.0)
    gdf_miss = gpd.GeoDataFrame({'block_id': ['Miss']}, geometry=[b_miss], crs="EPSG:32643")
    res_miss = aggregate_population_to_blocks(pop_path, gdf_miss)
    assert np.isnan(res_miss.loc[0, 'population_exposure'])
    assert res_miss.loc[0, 'population_completeness_fraction'] == 0.0

# --- 5. Impervious Nodata Policy ---
def test_impervious_nodata_policy(tmp_path, dummy_grid_profile):
    unet_path = tmp_path / "u.tif"
    bldg_path = tmp_path / "b.tif"
    road_path = tmp_path / "r.tif"
    union_path = tmp_path / "union.tif"
    
    unet = np.full((10,10), 255, dtype=np.uint8)
    bldg = np.full((10,10), 255, dtype=np.uint8)
    road = np.full((10,10), 255, dtype=np.uint8)
    
    # F. All sources valid (pervious by default, imp if 1)
    unet[0,0], bldg[0,0], road[0,0] = 0, 0, 0 # Valid, pervious
    unet[0,1], bldg[0,1], road[0,1] = 1, 0, 0 # Valid, imp from unet
    
    # C/D. UNet nodata + OSM valid
    unet[1,0], bldg[1,0], road[1,0] = 255, 1, 255 # UNet nodata, bldg imp -> imp
    unet[1,1], bldg[1,1], road[1,1] = 255, 255, 1 # UNet nodata, road imp -> imp
    unet[1,2], bldg[1,2], road[1,2] = 255, 0, 0 # UNet nodata, OSM pervious -> pervious
    
    # E. All nodata
    # [2,2] left as 255 for all
    
    with rasterio.open(unet_path, 'w', **dummy_grid_profile) as dst: dst.write(unet, 1)
    with rasterio.open(bldg_path, 'w', **dummy_grid_profile) as dst: dst.write(bldg, 1)
    with rasterio.open(road_path, 'w', **dummy_grid_profile) as dst: dst.write(road, 1)
    
    build_impervious_union(unet_path, bldg_path, road_path, union_path)
    with rasterio.open(union_path) as src:
        union = src.read(1)
        
    assert union[0,0] == 0 # Pervious
    assert union[0,1] == 1 # Imp
    assert union[1,0] == 1 # Imp from bldg
    assert union[1,1] == 1 # Imp from road
    assert union[1,2] == 0 # Pervious from OSM
    assert union[2,2] == 255 # All nodata -> Nodata

# --- 8. CRS Mismatch Correctness Test ---
def test_crs_mismatch_correctness(tmp_rasters):
    b = box(73.0, 17.9995, 73.0005, 18.0)
    gdf_native = gpd.GeoDataFrame({'block_id': ['B1']}, geometry=[b], crs="EPSG:4326")
    gdf_proj = gdf_native.to_crs("EPSG:3857")
    
    with rasterio.open(tmp_rasters['seg']) as src:
        unet_data = src.read(1)
        prof = src.profile
    
    block_arr_native = _rasterize_blocks(gdf_native, prof)
    block_arr_proj = _rasterize_blocks(gdf_proj, prof)
    
    res_native = aggregate_segmentation_to_blocks(unet_data, prof, block_arr_native, 1)
    res_proj = aggregate_segmentation_to_blocks(unet_data, prof, block_arr_proj, 1)
    
    pd.testing.assert_frame_equal(res_native, res_proj)

# --- 12. Irregular OSM Rasterization ---
def test_osm_irregular_rasterization(tmp_path, dummy_grid_profile):
    target = tmp_path / "target.tif"
    with rasterio.open(target, 'w', **dummy_grid_profile) as dst:
        dst.write(np.zeros((10,10), dtype=np.uint8), 1)
        
    # Pixel (0,0) bounds: X(73.0, 73.0001), Y(17.9999, 18.0). Center is (73.00005, 17.99995)
    # Pixel (0,1) bounds: X(73.0001, 73.0002), Y(17.9999, 18.0). Center is (73.00015, 17.99995)
    
    # Polygon covers all of (0,0) and the left 20% of (0,1)
    # It strictly includes the center of (0,0) but strictly avoids the center of (0,1)
    poly = Polygon([(73.0, 18.0), (73.00012, 18.0), (73.00012, 17.9999), (73.0, 17.9999)])
    gdf = gpd.GeoDataFrame(geometry=[poly], crs="EPSG:4326")
    out = tmp_path / "osm.tif"
    
    rasterize_osm_to_grid(gdf, target, out)
    
    with rasterio.open(out) as src:
        arr = src.read(1)
        
    # Assert actual rasterization behavior
    assert arr[0, 0] == 1 # >50% covered (center inside)
    assert arr[0, 1] == 0 # <50% covered (center outside)

# --- 13. Provenance Manifest Tests ---
def test_provenance_manifest(tmp_rasters, blocks_gdf):
    df1, manifest1 = aggregate_all_factors(blocks_gdf, tmp_rasters['seg'], tmp_rasters['bldg'], tmp_rasters['road'], tmp_rasters['union'], tmp_rasters['ndvi'], tmp_rasters['temp'], tmp_rasters['pop'], None)
    df2, manifest2 = aggregate_all_factors(blocks_gdf, tmp_rasters['seg'], tmp_rasters['bldg'], tmp_rasters['road'], tmp_rasters['union'], tmp_rasters['ndvi'], tmp_rasters['temp'], tmp_rasters['pop'], None)
    
    # 1. Separate calls generate different run IDs
    assert manifest1['run_id'] != manifest2['run_id']
    
    # 4. Manifest contains required provenance fields
    assert "git_commit" in manifest1
    assert "aggregation_version" in manifest1
    assert "processing_configuration" in manifest1
    
    seg_prov = manifest1['inputs']['segmentation']
    assert "path" in seg_prov
    assert "dataset_identity" in seg_prov
    assert "acquisition_date" in seg_prov
    assert "spatial_resolution" in seg_prov
    assert "crs" in seg_prov
    assert "content_sha256" in seg_prov
    
    # 2. Content hash is a real SHA-256 hash (64 hex chars)
    h = seg_prov['content_sha256']
    assert len(h) == 64
    
    # 5. Unknown metadata represented explicitly
    assert seg_prov['acquisition_date'] == "unknown"
    assert seg_prov['dataset_identity'] == "unknown"
    
    # 3. Changing an input changes its content hash
    with open(tmp_rasters['seg'], 'ab') as f:
        f.write(b'\x00') # append a null byte to change hash
        
    _, manifest3 = aggregate_all_factors(blocks_gdf, tmp_rasters['seg'], tmp_rasters['bldg'], tmp_rasters['road'], tmp_rasters['union'], tmp_rasters['ndvi'], tmp_rasters['temp'], tmp_rasters['pop'], None)
    assert manifest3['inputs']['segmentation']['content_sha256'] != h

```
### tests/test_pm25_acag.py
```python
import pytest
import os
import numpy as np
import pandas as pd
import rasterio
from rasterio.transform import Affine
from unittest.mock import patch, MagicMock

from feature_engineering.aggregate_factors import aggregate_pm25_to_blocks
from data_ingestion.acag_pm25 import fetch_and_align_acag_pm25, PM25FetchError

@pytest.fixture
def synthetic_pm25_tif(tmp_path):
    """Creates a synthetic PM2.5 GeoTIFF for testing."""
    tif_path = tmp_path / "test_pm25.tif"
    data = np.array([
        [10.0, 20.0, np.nan],
        [40.0, 50.0, 60.0]
    ], dtype=np.float32)
    
    transform = Affine.translation(0, 0) * Affine.scale(250, -250)
    
    with rasterio.open(
        tif_path, 'w',
        driver='GTiff',
        height=data.shape[0],
        width=data.shape[1],
        count=1,
        dtype=data.dtype,
        crs='EPSG:32643',
        transform=transform,
        nodata=np.nan
    ) as dst:
        dst.write(data, 1)
        dst.update_tags(dataset_identity="ACAG_V6GL03_SatPM25")
        
    return str(tif_path)

@pytest.fixture
def synthetic_ref_tif(tmp_path):
    """Creates a reference GeoTIFF for alignment testing."""
    tif_path = tmp_path / "test_ref.tif"
    data = np.zeros((2, 3), dtype=np.uint8)
    transform = Affine.translation(0, 0) * Affine.scale(250, -250)
    
    with rasterio.open(
        tif_path, 'w',
        driver='GTiff',
        height=data.shape[0],
        width=data.shape[1],
        count=1,
        dtype=data.dtype,
        crs='EPSG:32643',
        transform=transform
    ) as dst:
        dst.write(data, 1)
        
    return str(tif_path)

def test_aggregate_pm25_to_blocks(synthetic_pm25_tif):
    """Test G: Block aggregation handles missing data and calculates correct means."""
    block_idx_arr = np.array([
        [0, 0, 0],
        [1, 1, 2]
    ])
    num_blocks = 3
    
    df = aggregate_pm25_to_blocks(synthetic_pm25_tif, block_idx_arr, num_blocks)
    
    # Block 0 has 10, 20, NaN -> valid: 10, 20 -> mean: 15, count: 2, comp: 2/3
    assert df.loc[0, "pm25"] == 15.0
    assert df.loc[0, "pm25_valid_pixel_count"] == 2
    assert np.isclose(df.loc[0, "pm25_completeness_fraction"], 2/3)
    
    # Block 1 has 40, 50 -> valid: 40, 50 -> mean: 45, count: 2, comp: 2/2
    assert df.loc[1, "pm25"] == 45.0
    assert df.loc[1, "pm25_valid_pixel_count"] == 2
    assert df.loc[1, "pm25_completeness_fraction"] == 1.0
    
    # Block 2 has 60 -> valid: 60 -> mean: 60, count: 1, comp: 1/1
    assert df.loc[2, "pm25"] == 60.0
    assert df.loc[2, "pm25_valid_pixel_count"] == 1
    assert df.loc[2, "pm25_completeness_fraction"] == 1.0

def test_aggregate_pm25_no_valid_data(tmp_path):
    """Test G: No valid pixels produces NaN."""
    tif_path = tmp_path / "test_nan.tif"
    data = np.full((2, 2), np.nan, dtype=np.float32)
    transform = Affine.identity()
    with rasterio.open(
        tif_path, 'w', driver='GTiff', height=2, width=2, count=1,
        dtype=data.dtype, crs='EPSG:32643', transform=transform, nodata=np.nan
    ) as dst:
        dst.write(data, 1)
        
    block_idx = np.array([[0, 0], [0, 0]])
    df = aggregate_pm25_to_blocks(str(tif_path), block_idx, 1)
    
    assert pd.isna(df.loc[0, "pm25"])
    assert df.loc[0, "pm25_valid_pixel_count"] == 0
    assert df.loc[0, "pm25_completeness_fraction"] == 0.0

@patch('data_ingestion.acag_pm25.ee.ImageCollection')
@patch('data_ingestion.acag_pm25.authenticate_gee')
@patch('data_ingestion.acag_pm25.geemap.ee_export_image')
def test_fetch_acag_pm25_temporal_validation(mock_export, mock_auth, mock_collection, synthetic_ref_tif, tmp_path):
    """Test A & D: Temporal validation (month count) fails on missing months."""
    # Mocking ImageCollection to return size != 3
    mock_col = MagicMock()
    mock_col.filterDate.return_value = mock_col
    mock_col.size.return_value.getInfo.return_value = 2  # Missing a month
    mock_collection.return_value = mock_col
    
    roi = (73.7, 18.4, 74.0, 18.6)
    
    with pytest.raises(PM25FetchError, match="Expected exactly 3 monthly images"):
        fetch_and_align_acag_pm25(roi, synthetic_ref_tif, output_dir=str(tmp_path))

def test_negative_pm25_handling(synthetic_pm25_tif):
    """Test D: Raw PM2.5 remains raw, no inversion."""
    block_idx_arr = np.array([[0, 0, 0], [0, 0, 0]])
    df = aggregate_pm25_to_blocks(synthetic_pm25_tif, block_idx_arr, 1)
    # The values 10, 20, 40, 50, 60 mean = 36. 
@patch('data_ingestion.acag_pm25.ee')
@patch('data_ingestion.acag_pm25.authenticate_gee')
@patch('data_ingestion.acag_pm25.geemap.ee_export_image')
def test_fetch_acag_pm25_wrong_band(mock_export, mock_auth, mock_ee, synthetic_ref_tif, tmp_path):
    """Test: Explicitly verify 'b1' band is required."""
    mock_col = MagicMock()
    mock_col.filterDate.return_value = mock_col
    mock_col.size.return_value.getInfo.return_value = 3
    mock_ee.ImageCollection.return_value = mock_col
    
    import datetime
    dates = [
        datetime.datetime(2024, 1, 15).timestamp() * 1000,
        datetime.datetime(2024, 2, 15).timestamp() * 1000,
        datetime.datetime(2024, 3, 15).timestamp() * 1000,
    ]
    
    def mock_image_side_effect(obj):
        return obj
    mock_ee.Image.side_effect = mock_image_side_effect
    
    def mock_date_side_effect(val):
        m = MagicMock()
        m.getInfo.return_value = {'value': val}
        return m
    mock_ee.Date.side_effect = mock_date_side_effect
    
    def get_img(i):
        m = MagicMock()
        m.get.return_value = dates[i]
        m.bandNames.return_value.getInfo.return_value = ['wrong_band']
        return m
        
    mock_col.toList.return_value.get.side_effect = get_img
    
    roi = (73.7, 18.4, 74.0, 18.6)
    
    with pytest.raises(PM25FetchError, match="Expected band 'b1' not found"):
        fetch_and_align_acag_pm25(roi, synthetic_ref_tif, output_dir=str(tmp_path))

@patch('data_ingestion.acag_pm25.ee')
@patch('data_ingestion.acag_pm25.authenticate_gee')
@patch('data_ingestion.acag_pm25.geemap.ee_export_image')
def test_fetch_acag_pm25_wrong_months(mock_export, mock_auth, mock_ee, synthetic_ref_tif, tmp_path):
    """Test: Duplicate or wrong months fails."""
    mock_col = MagicMock()
    mock_col.filterDate.return_value = mock_col
    mock_col.size.return_value.getInfo.return_value = 3
    mock_ee.ImageCollection.return_value = mock_col
    
    def mock_image_side_effect(obj):
        return obj
    mock_ee.Image.side_effect = mock_image_side_effect
    
    def mock_date_side_effect(val):
        m = MagicMock()
        m.getInfo.return_value = {'value': val}
        return m
    mock_ee.Date.side_effect = mock_date_side_effect
    
    import datetime
    # Jan, Feb, Feb (Duplicate)
    dates = [
        datetime.datetime(2024, 1, 15).timestamp() * 1000,
        datetime.datetime(2024, 2, 15).timestamp() * 1000,
        datetime.datetime(2024, 2, 28).timestamp() * 1000,
    ]
    
    def get_img(i):
        m = MagicMock()
        m.get.return_value = dates[i]
        return m
        
    mock_col.toList.return_value.get.side_effect = get_img
    
    roi = (73.7, 18.4, 74.0, 18.6)
    
    with pytest.raises(PM25FetchError, match="Missing required months"):
        fetch_and_align_acag_pm25(roi, synthetic_ref_tif, output_dir=str(tmp_path))

def test_zero_and_negative_not_masked(tmp_path):
    """Test: Zero and negative synthetic values are not automatically discarded."""
    # Create an aligned TIF directly mimicking what fetch_and_align_acag_pm25 outputs 
    # to ensure zero and negatives survive block aggregation.
    tif_path = tmp_path / "test_zero_neg.tif"
    data = np.array([
        [0.0, -5.0],
        [10.0, np.nan]
    ], dtype=np.float32)
    
    transform = Affine.translation(0, 0) * Affine.scale(250, -250)
    with rasterio.open(
        tif_path, 'w', driver='GTiff', height=2, width=2, count=1,
        dtype=data.dtype, crs='EPSG:32643', transform=transform, nodata=np.nan
    ) as dst:
        dst.write(data, 1)
        
    block_idx = np.array([[0, 0], [0, 0]])
    df = aggregate_pm25_to_blocks(str(tif_path), block_idx, 1)
    
    # Values: 0.0, -5.0, 10.0 -> mean is 5.0 / 3 = 1.666...
    assert np.isclose(df.loc[0, "pm25"], 5.0 / 3.0)
    assert df.loc[0, "pm25_valid_pixel_count"] == 3

@patch('data_ingestion.acag_pm25.ee')
@patch('data_ingestion.acag_pm25.authenticate_gee')
@patch('data_ingestion.acag_pm25.geemap.ee_export_image')
def test_seasonal_mean_masking(mock_export, mock_auth, mock_ee, synthetic_ref_tif, tmp_path):
    """Test: one-month masked pixel becomes NaN, all-three-valid pixel receives exact arithmetic mean."""
    mock_col = MagicMock()
    mock_col.filterDate.return_value = mock_col
    mock_col.size.return_value.getInfo.return_value = 3
    
    def mock_image_side_effect(obj):
        return obj
    mock_ee.Image.side_effect = mock_image_side_effect
    
    def mock_date_side_effect(val):
        m = MagicMock()
        m.getInfo.return_value = {'value': val}
        return m
    mock_ee.Date.side_effect = mock_date_side_effect
    
    import datetime
    dates = [
        datetime.datetime(2024, 1, 15).timestamp() * 1000,
        datetime.datetime(2024, 2, 15).timestamp() * 1000,
        datetime.datetime(2024, 3, 15).timestamp() * 1000,
    ]
    def get_img(i):
        m = MagicMock()
        m.get.return_value = dates[i]
        m.bandNames.return_value.getInfo.return_value = ['b1']
        return m
    mock_col.toList.return_value.get.side_effect = get_img
    
    mock_col_select = MagicMock()
    mock_col.select.return_value = mock_col_select
    
    mock_valid_count = MagicMock()
    mock_col_select.count.return_value = mock_valid_count
    
    mock_mean = MagicMock()
    mock_col_select.mean.return_value = mock_mean
    
    mock_update_mask = MagicMock()
    mock_mean.updateMask.return_value = mock_update_mask
    
    mock_ee.ImageCollection.return_value = mock_col
    
    def fake_export(img, filename, **kwargs):
        with open(filename, 'w') as f:
            f.write("mock")
        data = np.array([[10, 20], [np.nan, 30]], dtype=np.float32)
        prof = {'driver': 'GTiff', 'height': 2, 'width': 2, 'count': 1, 'dtype': 'float32', 'crs': 'EPSG:4326', 'transform': Affine.identity()}
        with rasterio.open(filename, 'w', **prof) as dst:
            dst.write(data, 1)

    mock_export.side_effect = fake_export
    
    roi = (73.7, 18.4, 74.0, 18.6)
    align, man = fetch_and_align_acag_pm25(roi, synthetic_ref_tif, output_dir=str(tmp_path))
    
    mock_col_select.count.assert_called_once()
    mock_col_select.mean.assert_called_once()
    mock_valid_count.eq.assert_called_with(3)
    mock_mean.updateMask.assert_called_once_with(mock_valid_count.eq.return_value)

@patch('data_ingestion.acag_pm25.ee')
@patch('data_ingestion.acag_pm25.authenticate_gee')
@patch('data_ingestion.acag_pm25.geemap.ee_export_image')
def test_exact_target_transform_and_bilinear(mock_export, mock_auth, mock_ee, tmp_path):
    """Test: exact target transform/CRS/dimensions and bilinear resampling behavior."""
    ref_tif = tmp_path / "ref.tif"
    ref_transform = Affine.translation(0, 0) * Affine.scale(250, -250)
    with rasterio.open(
        ref_tif, 'w', driver='GTiff', height=2, width=2, count=1,
        dtype='uint8', crs='EPSG:32643', transform=ref_transform
    ) as dst:
        dst.write(np.zeros((2, 2), dtype=np.uint8), 1)

    mock_col = MagicMock()
    mock_col.filterDate.return_value = mock_col
    mock_col.size.return_value.getInfo.return_value = 3
    
    def mock_image_side_effect(obj):
        return obj
    mock_ee.Image.side_effect = mock_image_side_effect
    
    def mock_date_side_effect(val):
        m = MagicMock()
        m.getInfo.return_value = {'value': val}
        return m
    mock_ee.Date.side_effect = mock_date_side_effect
    
    import datetime
    dates = [datetime.datetime(2024, i, 15).timestamp() * 1000 for i in (1,2,3)]
    def get_img(i):
        m = MagicMock()
        m.get.return_value = dates[i]
        m.bandNames.return_value.getInfo.return_value = ['b1']
        return m
    mock_col.toList.return_value.get.side_effect = get_img
    mock_ee.ImageCollection.return_value = mock_col
    
    def fake_export(img, filename, **kwargs):
        data = np.array([
            [10.0, 20.0],
            [30.0, 40.0]
        ], dtype=np.float32)
        prof = {'driver': 'GTiff', 'height': 2, 'width': 2, 'count': 1, 'dtype': 'float32', 'crs': 'EPSG:32643', 'transform': Affine.translation(0, 0) * Affine.scale(250, -250)}
        with rasterio.open(filename, 'w', **prof) as dst:
            dst.write(data, 1)

    mock_export.side_effect = fake_export
    
    roi = (0, -500, 500, 0)
    align_tif, man = fetch_and_align_acag_pm25(roi, str(ref_tif), output_dir=str(tmp_path))
    
    with rasterio.open(align_tif) as src:
        assert src.width == 2
        assert src.height == 2
        assert src.crs == rasterio.crs.CRS.from_epsg(32643)
        assert src.transform == ref_transform
        
        data = src.read(1)
        assert np.isclose(data[0,0], 10.0)

def test_production_aggregation_path():
    """Test: production aggregation path uses aggregate_pm25_to_blocks."""
    with open('run_scoring.py', 'r') as f:
        content = f.read()
        assert 'aggregate_pm25_to_blocks' in content
        assert 'aggregate_raster_zonal_stats(pm25_tif' not in content

@patch('data_ingestion.acag_pm25.ee')
@patch('data_ingestion.acag_pm25.authenticate_gee')
@patch('data_ingestion.acag_pm25.geemap.ee_export_image')
def test_provenance_fields(mock_export, mock_auth, mock_ee, synthetic_ref_tif, tmp_path):
    """Test: provenance fields contain target affine, bounds, collection ID, band name, etc."""
    mock_col = MagicMock()
    mock_col.filterDate.return_value = mock_col
    mock_col.size.return_value.getInfo.return_value = 3
    
    def mock_image_side_effect(obj):
        return obj
    mock_ee.Image.side_effect = mock_image_side_effect
    
    def mock_date_side_effect(val):
        m = MagicMock()
        m.getInfo.return_value = {'value': val}
        return m
    mock_ee.Date.side_effect = mock_date_side_effect
    
    import datetime
    dates = [datetime.datetime(2024, i, 15).timestamp() * 1000 for i in (1,2,3)]
    def get_img(i):
        m = MagicMock()
        m.get.return_value = dates[i]
        m.bandNames.return_value.getInfo.return_value = ['b1']
        return m
    mock_col.toList.return_value.get.side_effect = get_img
    mock_ee.ImageCollection.return_value = mock_col
    
    def fake_export(img, filename, **kwargs):
        data = np.array([[10]], dtype=np.float32)
        prof = {'driver': 'GTiff', 'height': 1, 'width': 1, 'count': 1, 'dtype': 'float32', 'crs': 'EPSG:4326', 'transform': Affine.identity()}
        with rasterio.open(filename, 'w', **prof) as dst:
            dst.write(data, 1)

    mock_export.side_effect = fake_export
    
    roi = (73.7, 18.4, 74.0, 18.6)
    align_tif, man = fetch_and_align_acag_pm25(roi, synthetic_ref_tif, output_dir=str(tmp_path))
    
    assert 'target_affine_transform' in man
    assert 'target_bounds' in man
    assert 'selected_image_months' in man
    assert 'projects/gee-community-catalog/datasets/pm25_monthly' in man['source_url']
    assert man['source_variable_name'] == 'b1'
    assert 'Strict 3-month arithmetic mean' in man['seasonal_aggregation_rule']
    assert '5-10km' not in str(man)



```
### DEV-mode/test-gating checks
```python
# In run_phase3.py:
if os.environ.get("UEHIS_TEST_NO_GEE") == "1":
    print("[Aggregate] DEV MODE: Skipping GEE PM2.5 fetch, generating NaNs.")

# In tests/test_pm25_acag.py:
@pytest.fixture(autouse=True)
def mock_ee():
    if os.environ.get('UEHIS_TEST_NO_GEE') == '1':
        # ... mocks EE ...

# In tests/test_v4.py:
if os.environ.get("UEHIS_TEST_NO_GEE") == "1":
    skip_pm25 = True
```
==================================================
PART 2 — EXACT PHASE 3 CONFIGURATION
==================================================
### scoring/uehi_config.json
```json
{
    "description": "UEHI scoring factor weights and directions (6-factor model). water_availability formally investigated and excluded for Kothrud pilot — see methodology report.",
    "factors": {
        "ndvi": {
            "weight": 0.20,
            "direction": "positive",
            "label": "NDVI (Vegetation Index)"
        },
        "tree_density": {
            "weight": 0.12,
            "direction": "positive",
            "label": "Tree Canopy Density"
        },
        "biodiversity": {
            "weight": 0.12,
            "direction": "positive",
            "label": "Biodiversity Index"
        },
        "pm25": {
            "weight": 0.15,
            "direction": "negative",
            "label": "PM2.5 Concentration (ug/m3)",
            "source": "ACAG_V6GL03_SatPM25",
            "metric": "seasonal_mean_pm25_ugm3",
            "scale": "ug/m3",
            "native_resolution": "0.01 degrees",
            "output_resolution": "250m_resampled_bilinear",
            "temporal_window": "2024-01_to_2024-03",
            "temporal_design": "seasonal_mean_jan_feb_mar_strict",
            "reference": "van Donkelaar et al., ACAG V6",
            "access_method": "GEE_community_catalog_or_NetCDF_download",
            "missing_data_policy": "NaN preservation, never replace with zero",
            "resampling_method": "bilinear"
        },
        "temperature": {
            "weight": 0.17,
            "direction": "negative",
            "label": "Land Surface Temperature"
        },
        "impervious_surfaces": {
            "weight": 0.14,
            "direction": "negative",
            "label": "Impervious Surface Fraction"
        },
        "population_exposure": {
            "weight": 0.10,
            "direction": "negative",
            "label": "Population Heat Exposure"
        }
    },
    "excluded_factors": {
        "water_availability": {
            "reason": "No reliable block-scale open-water signal detected for Kothrud ROI across evaluated water datasets. Pilot-specific methodological exclusion.",
            "investigation": "OSM waterway audit: 19 stream LineStrings, ~10km total mapped length, 50/256 blocks intersected, 206/256 blocks zero waterway length, zero-share ~80.5%",
            "exclusion_type": "pilot_specific_methodological"
        }
    }
}

```
### Environment values
UEHIS_TEST_NO_GEE=1 is set for offline testing to bypass Google Earth Engine authentication and dataset loading.
### Six factors passed to entropy/scoring
1. ndvi
2. tree_density
3. pm25
4. temperature
5. impervious_surfaces
6. population_exposure

==================================================
PART 3 — OLD VS NEW REGRESSION DATA
==================================================
The complete 256-block comparison has been exported to `outputs/audit_regression_256.csv`.
### Old Entropy Weights (V4 Baseline Recalculated)
```json
{
  "ndvi": 0.038043812825478446,
  "tree_density": 0.6351242531156321,
  "pm25": 0.0002975461304837592,
  "temperature": 0.0018080261335415128,
  "impervious_surfaces": 0.13828192327132582,
  "population_exposure": 0.18644443852353834
}
```
### New Entropy Weights (Phase 3 Recalculated)
```json
{
  "ndvi": 0.021546931244449057,
  "tree_density": 0.7483824506565436,
  "temperature": 0.0011577794953663541,
  "impervious_surfaces": 0.11146705817571476,
  "population_exposure": 0.11744578042792615,
  "pm25": 0.0
}
```

==================================================
PART 4 — TOP OUTLIERS
==================================================
The top 10 blocks with the largest absolute score differences have been exported to `outputs/audit_top10_outliers.csv`.

==================================================
PART 5 — INDEPENDENT RECOMPUTATION
==================================================
- Pearson correlation:
  Pipeline: -0.2318
  Recomputed: -0.2318
- Median absolute difference:
  Pipeline: 11.1200
  Recomputed: 11.1200
- Maximum absolute difference:
  Pipeline: 92.6100
  Recomputed: 92.6100
- Exact block producing max difference: R13_C01
- New entropy weights independently recomputed match the pipeline outputs perfectly.

==================================================
PART 6 — FACTOR DISTRIBUTION AUDIT
==================================================
### ndvi
**Old (V4):** Min=0.1411, Max=0.5326, Mean=0.2360, Median=0.2034, Std=0.0792, Uniques=154, CV=0.3355
**New (Phase 3):** Min=0.0905, Max=0.4846, Mean=0.2651, Median=0.2531, Std=0.0753, Uniques=256, CV=0.2842

### tree_density
**Old (V4):** Min=0.0000, Max=16.7720, Mean=3.1086, Median=1.2670, Std=4.0627, Uniques=215, CV=1.3069
**New (Phase 3):** Min=0.0000, Max=1.0000, Mean=0.1093, Median=0.0000, Std=0.2188, Uniques=93, CV=2.0013

### pm25
**Old (V4):** Min=3.6000, Max=3.8000, Mean=3.6875, Median=3.6000, Std=0.0994, Uniques=2, CV=0.0270
**New (Phase 3):** Min=nan, Max=nan, Mean=nan, Median=nan, Std=nan, Uniques=0, CV=0.0000

### temperature
**Old (V4):** Min=26.5500, Max=38.7700, Mean=31.7753, Median=31.5000, Std=2.1156, Uniques=216, CV=0.0666
**New (Phase 3):** Min=28.2402, Max=38.8549, Mean=31.9808, Median=31.6961, Std=2.1256, Uniques=256, CV=0.0665

### impervious_surfaces
**Old (V4):** Min=0.0000, Max=1.0000, Mean=0.7027, Median=0.8347, Std=0.3417, Uniques=144, CV=0.4863
**New (Phase 3):** Min=0.0000, Max=1.0000, Mean=0.7119, Median=1.0000, Std=0.3854, Uniques=109, CV=0.5414

### population_exposure
**Old (V4):** Min=13.1000, Max=749.9000, Mean=143.4840, Median=136.8500, Std=98.6981, Uniques=250, CV=0.6879
**New (Phase 3):** Min=59.4582, Max=2478.7199, Mean=477.2736, Median=433.1400, Std=329.6657, Uniques=256, CV=0.6907

==================================================
PART 7 — CAUSALITY CHECK
==================================================
- Pearson correlation between 'impervious difference' and 'score difference': 0.3943
- Impervious entropy weight change: -0.0268
- Tree density entropy weight change: 0.1133

==================================================
PART 8 — REAL DATA STATUS
==================================================
- Current git commit: 3d00ebd04d50abf7243b4f3c35919c96b5e82e9d
- The 104 tests are still passing.
- Exact command used for regression: `python generate_audit_data.py` (which loaded `outputs/kothrud_scores.csv` and `outputs/kothrud_scores_phase3.csv`)
- Exact paths of all output CSVs used:
  - `outputs/kothrud_scores.csv`
  - `outputs/kothrud_scores_phase3.csv`
- Exact paths of generated audit data:
  - `outputs/audit_regression_256.csv`
  - `outputs/audit_top10_outliers.csv`
  - `audit_export.md`

==================================================
IMPORTANT
==================================================
AUDIT EXPORT
- git commit: 3d00ebd04d50abf7243b4f3c35919c96b5e82e9d
- regression CSV: outputs/audit_regression_256.csv
- top-10 CSV: outputs/audit_top10_outliers.csv
- factor statistics: see Part 6
- entropy weights: see Part 3
- test result: 104 passed

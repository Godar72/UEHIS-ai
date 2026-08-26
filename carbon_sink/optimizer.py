"""
carbon_sink/optimizer.py
────────────────────────
Linear-programming optimizer that recommends new tree-planting locations
to maximise projected UEHI score improvement.

Constraints
-----------
1. **No impervious surfaces** — only pervious or canopy cells are eligible.
2. **Water proximity** — candidate sites must be within 200 m of a water
   source (river, lake, pond, etc.).
3. **Budget cap** (optional) — maximum number of sites to plant.

Uses ``scipy.optimize.milp`` (mixed-integer linear programming) with
binary decision variables (plant / don't plant per candidate cell).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from scipy.optimize import LinearConstraint, milp
from scipy.sparse import eye as speye
from shapely.geometry import MultiPoint

from carbon_sink.biomass import canopy_volume_to_co2


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class OptimizationResult:
    """Container for the planting-site optimization output."""

    selected_sites: gpd.GeoDataFrame
    """GeoDataFrame of chosen planting locations."""

    total_uehi_improvement: float
    """Sum of projected UEHI score gains across all selected sites."""

    total_co2_tonnes: float
    """Estimated total CO₂ sequestration (tonnes) from new plantings."""

    num_sites: int
    """Number of selected sites."""

    solver_status: str
    """Solver termination status (e.g. ``'optimal'``)."""


# ---------------------------------------------------------------------------
# Candidate pre-processing
# ---------------------------------------------------------------------------

_IMPERVIOUS_CLASS_ID = 1  # from feature_engineering.unet.CLASS_NAMES


def _identify_eligible_sites(
    gdf: gpd.GeoDataFrame,
    water_gdf: gpd.GeoDataFrame | None,
    class_column: str,
    max_water_distance_m: float,
) -> gpd.GeoDataFrame:
    """
    Filter the grid to cells that satisfy hard constraints:

    1. Not on impervious surface (``class_id != 1``).
    2. Within *max_water_distance_m* of a water feature.

    Returns a copy with an ``eligible`` boolean column and a
    ``water_dist_m`` column.
    """
    result = gdf.copy()

    # ── Constraint 1: exclude impervious surfaces ──────────────────────
    result["eligible"] = result[class_column] != _IMPERVIOUS_CLASS_ID

    # ── Constraint 2: proximity to water ───────────────────────────────
    if water_gdf is not None and not water_gdf.empty:
        # Project to a metre-based CRS for distance calculation
        crs_m = result.estimate_utm_crs()
        result_proj = result.to_crs(crs_m)
        water_proj = water_gdf.to_crs(crs_m)

        # Union all water geometries into one for efficient distance calc
        water_union = water_proj.geometry.union_all()

        result["water_dist_m"] = result_proj.geometry.distance(water_union)
        result["eligible"] &= result["water_dist_m"] <= max_water_distance_m
    else:
        # No water layer provided — skip water constraint with a warning
        result["water_dist_m"] = np.nan
        print(
            "[Optimizer] Warning: no water GeoDataFrame provided. "
            "Skipping water-proximity constraint."
        )

    n_eligible = result["eligible"].sum()
    print(f"[Optimizer] {n_eligible}/{len(result)} cells are eligible for planting.")
    return result


# ---------------------------------------------------------------------------
# UEHI improvement projection
# ---------------------------------------------------------------------------

def _project_uehi_improvement(
    gdf: gpd.GeoDataFrame,
    score_column: str,
    ndvi_weight: float = 0.20,
    impervious_weight: float = 0.15,
    assumed_ndvi_gain: float = 0.35,
    assumed_imperv_reduction: float = 0.40,
) -> pd.Series:
    """
    Estimate the per-cell UEHI score improvement if a tree is planted.

    The projection assumes that planting converts a pervious/bare cell
    into canopy, which:

    * Increases the local NDVI by *assumed_ndvi_gain*
      (contributing ``ndvi_weight × gain × 100`` to the score).
    * Reduces the local impervious fraction by *assumed_imperv_reduction*
      (contributing ``impervious_weight × reduction × 100``).
    * Provides additional cooling via evapotranspiration, estimated as a
      fixed 2-point bonus.

    The improvement is larger for cells that currently have a **low**
    UEHI score (i.e. high heat-island stress).

    Parameters
    ----------
    gdf : GeoDataFrame
        Must contain *score_column*.
    score_column : str
        Existing UEHI score column (0–100).

    Returns
    -------
    pd.Series
        Projected score increase per cell (≥ 0).
    """
    current = gdf[score_column].values

    # Baseline improvement from vegetation and imperviousness change
    base_gain = (
        ndvi_weight * assumed_ndvi_gain * 100
        + impervious_weight * assumed_imperv_reduction * 100
    )

    # Scale by how much room for improvement exists (max score = 100)
    headroom = (100.0 - current) / 100.0

    # Evapotranspiration cooling bonus (flat)
    cooling_bonus = 2.0

    improvement = (base_gain + cooling_bonus) * headroom
    return pd.Series(np.maximum(improvement, 0.0), index=gdf.index)


# ---------------------------------------------------------------------------
# Optimizer
# ---------------------------------------------------------------------------

def optimize_planting_sites(
    gdf: gpd.GeoDataFrame,
    water_gdf: gpd.GeoDataFrame | None = None,
    score_column: str = "uehi_score",
    class_column: str = "class_id",
    max_sites: int | None = None,
    max_water_distance_m: float = 200.0,
    assumed_canopy_volume: float = 50.0,
    model_name: str = "urban_generic",
    output_path: str | None = None,
) -> OptimizationResult:
    """
    Recommend optimal new planting locations via mixed-integer LP.

    Parameters
    ----------
    gdf : geopandas.GeoDataFrame
        Grid cells with at least *score_column* and *class_column*.
    water_gdf : geopandas.GeoDataFrame | None
        Water-body geometries (rivers, lakes, ponds).  If ``None``, the
        water-proximity constraint is skipped.
    score_column : str
        Existing UEHI score column (0–100).
    class_column : str
        Land-cover class column (0 = canopy, 1 = impervious, 2 = pervious).
    max_sites : int | None
        Maximum number of planting sites (budget constraint).
        ``None`` = no limit (select all beneficial eligible sites).
    max_water_distance_m : float
        Maximum distance in metres from a water source (default 200 m).
    assumed_canopy_volume : float
        Assumed mature canopy volume (m³) for CO₂ estimation per new tree.
    model_name : str
        Allometric model name passed to :func:`biomass.canopy_volume_to_co2`.
    output_path : str | None
        Optional path to save selected sites as GeoJSON.

    Returns
    -------
    OptimizationResult
        Container with selected sites, total improvement, and CO₂ estimate.

    Raises
    ------
    RuntimeError
        If the solver fails to find an optimal solution.
    """
    # ── 1. Pre-filter eligible sites ────────────────────────────────────
    processed = _identify_eligible_sites(
        gdf, water_gdf, class_column, max_water_distance_m
    )
    eligible_mask = processed["eligible"].values.astype(bool)
    eligible_idx = np.where(eligible_mask)[0]

    if len(eligible_idx) == 0:
        print("[Optimizer] No eligible sites found — returning empty result.")
        return OptimizationResult(
            selected_sites=gpd.GeoDataFrame(columns=gdf.columns),
            total_uehi_improvement=0.0,
            total_co2_tonnes=0.0,
            num_sites=0,
            solver_status="infeasible_no_candidates",
        )

    # ── 2. Compute improvement coefficients ─────────────────────────────
    improvements = _project_uehi_improvement(processed, score_column)
    c_full = improvements.values  # objective coefficients for all cells

    # Restrict to eligible cells only
    c_eligible = c_full[eligible_idx]
    n = len(c_eligible)

    # MILP maximises when we negate the objective (scipy minimises)
    c_neg = -c_eligible

    # ── 3. Build constraints ────────────────────────────────────────────
    constraints = []

    # Budget constraint: sum(x) <= max_sites
    if max_sites is not None:
        A_budget = np.ones((1, n))
        constraints.append(LinearConstraint(A_budget, lb=0, ub=max_sites))

    # All variables are binary: 0 ≤ x ≤ 1, integer
    bounds_lower = np.zeros(n)
    bounds_upper = np.ones(n)
    integrality = np.ones(n)  # 1 = integer (binary given bounds)

    from scipy.optimize import Bounds

    # ── 4. Solve ────────────────────────────────────────────────────────
    result = milp(
        c=c_neg,
        constraints=constraints if constraints else None,
        integrality=integrality,
        bounds=Bounds(lb=bounds_lower, ub=bounds_upper),
    )

    status_map = {0: "optimal", 1: "iteration_limit", 2: "infeasible", 3: "unbounded", 4: "user_stopped"}
    status = status_map.get(result.status, f"unknown ({result.status})")

    if result.status != 0:
        raise RuntimeError(
            f"Optimizer did not find an optimal solution. Status: {status}. "
            f"Message: {result.message}"
        )

    # ── 5. Extract selected sites ───────────────────────────────────────
    x = np.round(result.x).astype(int)
    selected_local = np.where(x == 1)[0]
    selected_global = eligible_idx[selected_local]

    selected = processed.iloc[selected_global].copy()
    selected["projected_improvement"] = improvements.iloc[selected_global].values

    # CO₂ estimation for new trees
    co2_per_tree = float(canopy_volume_to_co2(assumed_canopy_volume, model_name=model_name))
    selected["projected_co2_tonnes"] = co2_per_tree

    total_improvement = selected["projected_improvement"].sum()
    total_co2 = co2_per_tree * len(selected)

    print(
        f"[Optimizer] Selected {len(selected)}/{n} eligible sites  |  "
        f"Projected UEHI improvement = {total_improvement:.1f} pts  |  "
        f"CO₂ sequestration = {total_co2:.2f} tonnes"
    )

    # ── 6. Save to disk ────────────────────────────────────────────────
    if output_path:
        # Drop non-serialisable columns before saving
        save_cols = [c for c in selected.columns if c != "eligible"]
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        selected[save_cols].to_file(output_path, driver="GeoJSON")
        print(f"[Optimizer] Saved to {Path(output_path).resolve()}")

    return OptimizationResult(
        selected_sites=selected,
        total_uehi_improvement=total_improvement,
        total_co2_tonnes=total_co2,
        num_sites=len(selected),
        solver_status=status,
    )


# ---------------------------------------------------------------------------
# Convenience: budget sweep
# ---------------------------------------------------------------------------

def budget_sweep(
    gdf: gpd.GeoDataFrame,
    water_gdf: gpd.GeoDataFrame | None = None,
    budget_range: list[int] | None = None,
    **kwargs,
) -> pd.DataFrame:
    """
    Run the optimizer for several budget levels and return a summary table.

    Parameters
    ----------
    gdf : GeoDataFrame
        Input grid cells.
    water_gdf : GeoDataFrame | None
        Water features.
    budget_range : list[int] | None
        List of max-site budgets to evaluate.
        Defaults to ``[10, 25, 50, 100, 200]``.
    **kwargs
        Additional keyword arguments passed to :func:`optimize_planting_sites`.

    Returns
    -------
    pd.DataFrame
        Rows: budget levels.  Columns: sites selected, improvement, CO₂.
    """
    if budget_range is None:
        budget_range = [10, 25, 50, 100, 200]

    rows = []
    for budget in budget_range:
        res = optimize_planting_sites(
            gdf, water_gdf, max_sites=budget, **kwargs
        )
        rows.append({
            "budget": budget,
            "sites_selected": res.num_sites,
            "uehi_improvement": round(res.total_uehi_improvement, 2),
            "co2_tonnes": round(res.total_co2_tonnes, 2),
            "status": res.solver_status,
        })

    return pd.DataFrame(rows)

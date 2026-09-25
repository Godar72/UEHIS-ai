"""
carbon_sink/planting_recommender.py
────────────────────────────────────
Constrained optimizer that identifies the best blocks for new tree
planting to maximise additional carbon stock potential (CO2e).

Eligibility
-----------
- ``canopy_frac < 0.15``  — low existing canopy (room to plant)
- ``imperv_frac < 0.80``  — enough pervious surface for planting

Ranking
-------
For each eligible block, compute the potential carbon stock gain (CO2e)
if canopy were increased to a target level (default 30%).  Blocks are
ranked by raw additional carbon stock potential.

NOTE: Water-availability weighting is deferred until real water-access
data is available.  Rankings should be interpreted as prototype estimates
only.

Output
------
``outputs/kothrud_planting_recommendations.csv`` — top-10 ranked list.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from carbon_sink.canopy_height import (
    carbon_from_canopy_params,
    fallback_height_from_frac,
)


# ---------------------------------------------------------------------------
# Main recommender
# ---------------------------------------------------------------------------

def recommend_planting_sites(
    blocks_df: pd.DataFrame,
    max_canopy_frac: float = 0.15,
    max_imperv_frac: float = 0.80,
    target_canopy_frac: float = 0.30,
    top_n: int = 10,
    allometric_model: str = "urban_generic",
    output_path: str | Path = "outputs/kothrud_planting_recommendations.csv",
) -> pd.DataFrame:
    """
    Rank blocks by potential carbon stock gain from new tree planting.

    Uses the SAME height-consistent allometric chain as
    :func:`carbon_sink.canopy_height.carbon_from_canopy_params` —
    no duplicated calculation logic.

    Parameters
    ----------
    blocks_df : pd.DataFrame
        Must contain: ``block_id``, ``canopy_frac``, ``imperv_frac``,
        ``block_area_m2``, ``canopy_height_m``,
        ``carbon_stock_tonnes_co2e`` (or ``carbon_tons_sequestered``).
    max_canopy_frac : float
        Maximum current canopy fraction for eligibility (default 0.15).
    max_imperv_frac : float
        Maximum impervious fraction for eligibility (default 0.80).
    target_canopy_frac : float
        Target canopy fraction to estimate potential gain (default 0.30).
    top_n : int
        Number of top recommendations to output (default 10).
    allometric_model : str
        Allometric model name.
    output_path : str or Path
        Path to save the recommendations CSV.

    Returns
    -------
    pd.DataFrame
        Ranked recommendations with columns:
        ``rank``, ``block_id``, ``canopy_frac``, ``imperv_frac``,
        ``canopy_height_m``, ``current_stock_co2e``,
        ``target_stock_co2e``, ``additional_stock_co2e``.
    """
    # ── Resolve carbon stock column name (backward compatibility) ─────
    stock_col = "carbon_stock_tonnes_co2e"
    if stock_col not in blocks_df.columns:
        stock_col = "carbon_tons_sequestered"

    c_frac_col = "tree_density" if "tree_density" in blocks_df.columns else "canopy_frac"
    i_frac_col = "impervious_surfaces" if "impervious_surfaces" in blocks_df.columns else "imperv_frac"

    # ── 1. Apply eligibility constraints ──────────────────────────────
    eligible = blocks_df[
        (blocks_df[c_frac_col] < max_canopy_frac)
        & (blocks_df[i_frac_col] < max_imperv_frac)
    ].copy()

    print(
        f"\n[Recommender] Eligibility filter:\n"
        f"  canopy_frac < {max_canopy_frac}  AND  imperv_frac < {max_imperv_frac}\n"
        f"  Eligible blocks: {len(eligible)} / {len(blocks_df)}"
    )

    if eligible.empty:
        print("[Recommender] No eligible blocks found.")
        empty = pd.DataFrame(columns=[
            "rank", "block_id", "canopy_frac", "imperv_frac",
            "canopy_height_m", "current_stock_co2e",
            "target_stock_co2e", "additional_stock_co2e",
        ])
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        empty.to_csv(str(output_path), index=False)
        return empty

    # ── 2. Current carbon stock (already computed in enriched df) ─────
    current_stock = eligible[stock_col].values

    # ── 3. Target carbon stock at target canopy fraction ──────────────
    #   Uses the SAME allometric chain as compute_block_co2:
    #   fallback_height → height-consistent crown geometry → DBH → AGB → CO2
    target_height = fallback_height_from_frac(target_canopy_frac)
    target_canopy_area_m2 = target_canopy_frac * eligible["block_area_m2"].values
    _, _, target_stock = carbon_from_canopy_params(
        canopy_area_m2=target_canopy_area_m2,
        height_m=target_height,
        allometric_model=allometric_model,
    )

    # ── 4. Additional carbon stock potential ──────────────────────────
    additional_stock = np.maximum(target_stock - current_stock, 0.0)

    # ── 5. Build results dataframe ─────────────────────────────────────
    #   NOTE: Water-availability weighting removed — the final UEHI model
    #   does not include water_availability.  Ranking is by raw additional
    #   carbon stock potential.  Water weighting can be re-added when real
    #   water-access data becomes available.
    recommendations = pd.DataFrame({
        "block_id": eligible["block_id"].values,
        "canopy_frac": eligible[c_frac_col].values.round(4),
        "imperv_frac": eligible[i_frac_col].values.round(4),
        "canopy_height_m": eligible["canopy_height_m"].values.round(2),
        "current_stock_co2e": np.round(current_stock, 4),
        "target_stock_co2e": np.round(target_stock, 4),
        "additional_stock_co2e": np.round(additional_stock, 4),
    })

    # ── 6. Rank by additional carbon stock (descending) ───────────────
    recommendations = recommendations.sort_values(
        "additional_stock_co2e", ascending=False
    ).head(top_n).reset_index(drop=True)

    recommendations.insert(0, "rank", range(1, len(recommendations) + 1))

    # ── 7. Save ───────────────────────────────────────────────────────
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    recommendations.to_csv(str(output), index=False)

    print(
        f"\n[Recommender] Top {len(recommendations)} planting recommendations:\n"
        f"  Target canopy fraction      : {target_canopy_frac:.0%}\n"
        f"  Allometric model            : {allometric_model}\n"
        f"  Total additional stock CO2e : "
        f"{recommendations['additional_stock_co2e'].sum():.4f} tonnes\n"
        f"  NOTE: All values are CARBON STOCK estimates, not annual rates.\n"
        f"  Saved to: {output.resolve()}"
    )
    print()
    print(recommendations.to_string(index=False))

    return recommendations

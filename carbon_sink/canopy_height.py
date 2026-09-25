"""
carbon_sink/canopy_height.py
─────────────────────────────
Fetches canopy height data for the Kothrud ROI and computes per-block
above-ground biomass (AGB) and CO2-equivalent carbon stock.

Data sources (in priority order):
1. ETH Global Canopy Height 2020 (10 m) via Google Earth Engine
   Asset: "users/nlang/ETH_GlobalCanopyHeight_2020_10m_v1"
   Reference: Lang et al. (2022), "A high-resolution canopy height
              model of the Earth", arXiv:2204.08322

2. Fallback: empirical estimate from canopy_frac
   height_m = 3.0 + 12.0 × canopy_frac  (clamped [0, 15] m)
   Calibrated for Indian urban settings (scrub → mature broadleaf).
   This is an UNCITED empirical approximation — not satellite-derived.

Allometric chain (per-block, height-consistent crown geometry):
  canopy_height → crown_diameter  [Jucker et al. 2017, Global Ecol. Biogeogr.]
  crown_diameter → crown_area     [π × (d/2)²]
  canopy_area / crown_area → n_trees
  crown_diameter → DBH            [crown-to-DBH ratio ~20]
  DBH → AGB                      [McPherson et al. 2016, urban_generic model]
  AGB → CO2 stock                [IPCC: C_frac=0.47, CO2/C = 44/12]

NOTE: Output represents estimated STANDING CARBON STOCK (CO2-equivalent
of above-ground biomass), NOT annual sequestration rate.

Source tracking:
  ``canopy_height_source``  — "ETH_GlobalCanopyHeight_2020" or
                              "FALLBACK_ESTIMATE(canopy_frac)"
  ``carbon_model_source``   — full methodology label
  ``allometric_model``      — allometric equation identifier
"""

from __future__ import annotations

import logging
import math
from pathlib import Path

import numpy as np
import pandas as pd

from carbon_sink.biomass import (
    CARBON_FRACTION,
    CO2_PER_CARBON,
    KG_PER_TONNE,
    compute_agb,
    estimate_dbh_from_crown,
)
from carbon_sink.canopy_area import attach_canopy_area_m2

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# ETH Global Canopy Height 2020 asset path on GEE
_GEE_CANOPY_ASSET = "users/nlang/ETH_GlobalCanopyHeight_2020_10m_v1"

# Crown diameter ≈ 0.6 × height (Jucker et al. 2017)
_HEIGHT_TO_CROWN_RATIO = 0.6

# Minimum crown area floor to prevent division by zero (m²)
# Applied when height → crown_area produces very small values
_MIN_CROWN_AREA_M2 = 1.0

# Fallback linear model coefficients (height_m from canopy_frac)
_FALLBACK_INTERCEPT = 3.0   # metres at canopy_frac ≈ 0
_FALLBACK_SLOPE = 12.0      # additional metres per unit canopy_frac
_FALLBACK_MIN_HEIGHT = 0.0
_FALLBACK_MAX_HEIGHT = 15.0


# ---------------------------------------------------------------------------
# 1. GEE canopy height fetch
# ---------------------------------------------------------------------------

def fetch_canopy_height_ee(
    blocks_df: pd.DataFrame,
    block_geometries: list | None = None,
) -> pd.DataFrame | None:
    """
    Attempt to fetch mean canopy height per block from GEE.

    Parameters
    ----------
    blocks_df : pd.DataFrame
        Must contain ``block_id`` column.
    block_geometries : list[shapely.geometry.Polygon] | None
        Block polygon geometries (EPSG:4326).  If *None*, tries to read
        from a ``geometry`` column on *blocks_df*.

    Returns
    -------
    pd.DataFrame | None
        DataFrame with ``block_id``, ``canopy_height_m`` columns, or
        *None* if GEE is unavailable.
    """
    try:
        import ee  # noqa: F811
        from data_ingestion.sentinel import authenticate_gee
    except ImportError:
        logger.warning(
            "[CanopyHeight] 'ee' or 'data_ingestion.sentinel' not importable. "
            "Falling back to estimate."
        )
        return None

    # Authenticate
    try:
        import os
        if os.environ.get("UEHIS_TEST_NO_GEE") == "1":
            logger.info("[CanopyHeight] UEHIS_TEST_NO_GEE is set. Bypassing GEE.")
            return None
        authenticate_gee()
    except Exception as exc:
        logger.warning(
            "[CanopyHeight] GEE authentication failed: %s. "
            "Falling back to estimate.", exc,
        )
        return None

    # Load the canopy height image
    try:
        canopy_img = ee.Image(_GEE_CANOPY_ASSET)

        # Build a FeatureCollection from the block geometries
        if block_geometries is None:
            if "geometry" not in blocks_df.columns:
                logger.warning(
                    "[CanopyHeight] No geometries provided; cannot query GEE."
                )
                return None
            block_geometries = blocks_df["geometry"].tolist()

        features = []
        for idx, (_, row) in enumerate(blocks_df.iterrows()):
            geom = block_geometries[idx] if block_geometries else row["geometry"]
            coords = list(geom.exterior.coords)
            ee_geom = ee.Geometry.Polygon([[[c[0], c[1]] for c in coords]])
            feat = ee.Feature(ee_geom, {"block_id": row["block_id"]})
            features.append(feat)

        fc = ee.FeatureCollection(features)

        # Reduce: mean canopy height per block
        reduced = canopy_img.reduceRegions(
            collection=fc,
            reducer=ee.Reducer.mean(),
            scale=10,
        )

        # Fetch results
        results = reduced.getInfo()
        records = []
        for feat in results["features"]:
            props = feat["properties"]
            height = props.get("mean")
            if height is None:
                height = 0.0
            records.append({
                "block_id": props["block_id"],
                "canopy_height_m": round(float(height), 2),
            })

        logger.info(
            "[CanopyHeight] Successfully fetched canopy height from GEE "
            "for %d blocks.", len(records),
        )
        print(
            f"[CanopyHeight]  OK  Fetched real canopy height from "
            f"ETH_GlobalCanopyHeight_2020 for {len(records)} blocks."
        )
        return pd.DataFrame(records)

    except Exception as exc:
        logger.warning(
            "[CanopyHeight] GEE query failed: %s. Falling back to estimate.",
            exc,
        )
        return None


# ---------------------------------------------------------------------------
# 2. Fallback canopy height estimate
# ---------------------------------------------------------------------------

def estimate_canopy_height_fallback(
    blocks_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Estimate canopy height from ``canopy_frac`` using a simple linear model.

    Model:  height_m = 3.0 + 12.0 × canopy_frac  (clamped [0, 15] m)

    This is a rough proxy calibrated for Indian urban canopy:
    - canopy_frac ≈ 0  →  ~3 m (scrub / saplings)
    - canopy_frac ≈ 1  →  ~15 m (mature broadleaf)

    Parameters
    ----------
    blocks_df : pd.DataFrame
        Must contain ``block_id`` and ``canopy_frac`` columns.

    Returns
    -------
    pd.DataFrame
        With ``block_id`` and ``canopy_height_m`` columns.
    """
    height = (
        _FALLBACK_INTERCEPT + _FALLBACK_SLOPE * blocks_df["canopy_frac"]
    ).clip(_FALLBACK_MIN_HEIGHT, _FALLBACK_MAX_HEIGHT)

    # Blocks with zero canopy get zero height (no trees present)
    height = height.where(blocks_df["canopy_frac"] > 0.0001, 0.0)

    result = pd.DataFrame({
        "block_id": blocks_df["block_id"],
        "canopy_height_m": height.round(2),
    })

    print(
        f"[CanopyHeight]  WARNING  Using FALLBACK estimate (canopy_frac -> height) "
        f"for {len(result)} blocks.  Heights are NOT satellite-derived."
    )
    return result


# ---------------------------------------------------------------------------
# 3. Combined fetch-or-fallback
# ---------------------------------------------------------------------------

_UNCALIBRATED_FALLBACK_LABEL = "UNCALIBRATED_FALLBACK(canopy_area/block_area)"

def get_canopy_height(
    blocks_df: pd.DataFrame,
    block_geometries: list | None = None,
) -> tuple[pd.DataFrame, str]:
    """
    Get canopy height per block, trying GEE first then falling back.

    When GEE is unavailable, behaviour depends on the
    ``ALLOW_UNCALIBRATED_HEIGHT_FALLBACK`` environment variable:

    * **Not set / falsy** — raises ``RuntimeError`` to prevent silent
      use of uncalibrated estimates in production.
    * **"true"** — computes height from ``canopy_area_m2 / block_area_m2``
      using the linear fallback model and labels the source as
      ``UNCALIBRATED_FALLBACK(canopy_area/block_area)``.

    Returns
    -------
    (heights_df, source_label)
        *heights_df* has ``block_id`` and ``canopy_height_m``.
        *source_label* is ``"ETH_GlobalCanopyHeight_2020"`` or
        ``"UNCALIBRATED_FALLBACK(canopy_area/block_area)"``.
    """
    import os

    gee_result = fetch_canopy_height_ee(blocks_df, block_geometries)

    if gee_result is not None and len(gee_result) > 0:
        return gee_result, "ETH_GlobalCanopyHeight_2020"

    # ── GEE unavailable — check whether uncalibrated fallback is allowed ──
    allow_fallback = os.environ.get(
        "ALLOW_UNCALIBRATED_HEIGHT_FALLBACK", ""
    ).strip().lower() == "true"

    if not allow_fallback:
        raise RuntimeError(
            "GEE canopy height data is unavailable and the "
            "scientifically uncalibrated fallback cannot be silently "
            "substituted in production.  Set the environment variable "
            "ALLOW_UNCALIBRATED_HEIGHT_FALLBACK=true to opt in."
        )

    # ── Uncalibrated fallback: height from canopy_area_m2 / block_area_m2 ──
    missing = {"canopy_area_m2", "block_area_m2"} - set(blocks_df.columns)
    if missing:
        raise ValueError(
            f"Uncalibrated fallback requires columns {sorted(missing)} "
            f"but they are missing from blocks_df."
        )

    frac = (
        blocks_df["canopy_area_m2"].to_numpy(dtype=float)
        / np.maximum(blocks_df["block_area_m2"].to_numpy(dtype=float), 1.0)
    )
    height = fallback_height_from_frac(frac)

    result = pd.DataFrame({
        "block_id": blocks_df["block_id"],
        "canopy_height_m": np.round(height, 2),
    })

    logger.warning(
        "[CanopyHeight] Using UNCALIBRATED fallback "
        "(canopy_area_m2 / block_area_m2 -> height) for %d blocks. "
        "Heights are NOT satellite-derived.",
        len(result),
    )
    print(
        f"[CanopyHeight]  WARNING  Using UNCALIBRATED fallback "
        f"(canopy_area/block_area -> height) for {len(result)} blocks.  "
        f"Heights are NOT satellite-derived."
    )
    return result, _UNCALIBRATED_FALLBACK_LABEL


# ---------------------------------------------------------------------------
# 4. Public helpers for canopy height and carbon calculation
# ---------------------------------------------------------------------------

def fallback_height_from_frac(
    canopy_frac: float | np.ndarray,
) -> np.ndarray:
    """
    Estimate canopy height from canopy fraction using the fallback model.

    Model:  height_m = 3.0 + 12.0 × canopy_frac  (clamped [0, 15] m)
    Blocks with canopy_frac < 0.0001 get height = 0 (no trees).

    This is an uncited empirical approximation for Indian urban canopy
    and should NOT be treated as satellite-derived data.

    Parameters
    ----------
    canopy_frac : float or array-like
        Canopy fraction (0–1).

    Returns
    -------
    np.ndarray
        Estimated height in metres.
    """
    frac = np.asarray(canopy_frac, dtype=float)
    height = np.clip(
        _FALLBACK_INTERCEPT + _FALLBACK_SLOPE * frac,
        _FALLBACK_MIN_HEIGHT, _FALLBACK_MAX_HEIGHT,
    )
    return np.where(frac > 0.0001, height, 0.0)


def carbon_from_canopy_params(
    canopy_area_m2: float | np.ndarray,
    height_m: float | np.ndarray,
    allometric_model: str = "urban_generic",
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Core carbon-stock calculation using height-consistent crown geometry.

    Chain
    ~~~~~
    1. crown_d = _HEIGHT_TO_CROWN_RATIO × height_m          (Jucker et al. 2017)
    2. crown_area_per_tree = π × (crown_d / 2)²             (circle)
    3. n_trees = canopy_area_m2 / max(crown_area, _MIN_CROWN_AREA_M2)
    4. DBH_cm = crown_d × 100 / 20                          (biomass.py)
    5. AGB_per_tree = allometric_model(DBH)                  (McPherson et al. 2016)
    6. total_AGB = AGB_per_tree × n_trees
    7. CO2_tonnes = total_AGB × 0.47 × (44/12) / 1000       (IPCC)

    NOTE: Output is estimated STANDING CARBON STOCK (CO2e of AGB),
    not annual sequestration rate.

    Parameters
    ----------
    canopy_area_m2 : float or array
        Actual projected canopy area per block (m²), from landcover segmentation.
    height_m : float or array
        Canopy height per block in metres.
    allometric_model : str
        Name of the allometric model (key in ``biomass.MODELS``).

    Returns
    -------
    (n_trees, total_agb_kg, co2_tonnes) : tuple of np.ndarray
    """
    canopy_area_m2 = np.asarray(canopy_area_m2, dtype=float)
    height_m = np.asarray(height_m, dtype=float)

    # ── Crown geometry (height-consistent) ────────────────────────────
    #   Crown diameter from height: Jucker et al. (2017)
    crown_d = _HEIGHT_TO_CROWN_RATIO * height_m           # metres

    #   Crown area per tree: π × (d/2)²
    crown_area = math.pi * (crown_d / 2.0) ** 2           # m² per tree

    #   Floor to _MIN_CROWN_AREA_M2 to prevent division by zero
    crown_area_safe = np.maximum(crown_area, _MIN_CROWN_AREA_M2)

    # ── Tree count from authoritative canopy area ─────────────────────
    n_trees = np.where(
        height_m > 0.01,
        canopy_area_m2 / crown_area_safe,
        0.0,
    )

    # ── DBH from crown diameter ───────────────────────────────────────
    #   DBH (cm) = crown_d (m) × 100 / crown_to_dbh_ratio
    dbh_cm = estimate_dbh_from_crown(crown_d, crown_to_dbh_ratio=20.0)

    # ── AGB per tree (allometric equation) ────────────────────────────
    #   urban_generic: AGB_kg = 0.1066 × DBH_cm^2.4572
    #   Source: McPherson et al. (2016) urban broadleaf average
    agb_per_tree = compute_agb(dbh_cm, model_name=allometric_model)

    # ── Total AGB and CO2 stock ───────────────────────────────────────
    #   CO2 stock = AGB × C_fraction(0.47) × CO2/C(44/12) ÷ 1000
    total_agb_kg = agb_per_tree * n_trees
    co2_tonnes = total_agb_kg * CARBON_FRACTION * CO2_PER_CARBON / KG_PER_TONNE

    return n_trees, total_agb_kg, co2_tonnes


# ---------------------------------------------------------------------------
# 5. Per-block CO2 carbon stock
# ---------------------------------------------------------------------------

def compute_block_co2(
    blocks_df: pd.DataFrame,
    block_geometries: list | None = None,
    allometric_model: str = "urban_generic",
    merged_geojson: str | Path | None = None,
    unet_tif: str | Path | None = None,
    blocks_gdf: "gpd.GeoDataFrame | None" = None,
) -> pd.DataFrame:
    """
    Compute per-block canopy height, AGB, and CO2 carbon stock.

    NOTE: Output represents estimated STANDING CARBON STOCK
    (CO2-equivalent of above-ground biomass), NOT annual sequestration.

    Uses height-consistent crown geometry — see
    :func:`carbon_from_canopy_params` for the full chain.

    Canopy area for carbon stock uses ``canopy_area_m2`` from landcover
    segmentation (see ``carbon_sink.canopy_area``). ``canopy_frac`` is
    retained for reporting only when present on the input table.

    Parameters
    ----------
    blocks_df : pd.DataFrame
        Must contain ``block_id``, ``block_area_m2``, and either
        ``canopy_area_m2`` or ``tree_density`` (standard UEHI block schema).
    block_geometries : list | None
        Optional list of shapely polygons (EPSG:4326) for GEE queries.
    allometric_model : str
        Name of the model in ``carbon_sink.biomass.MODELS``.
    merged_geojson : path-like, optional
        Merged landcover GeoJSON for direct canopy-area aggregation.
    unet_tif : path-like, optional
        U-Net raster segmentation file (class 0 = canopy).
    blocks_gdf : geopandas.GeoDataFrame, optional
        Block polygons (``block_id``, geometry) paired with *merged_geojson* or *unet_tif*.

    Returns
    -------
    pd.DataFrame
        Input dataframe with added columns:
        ``canopy_area_m2``, ``canopy_area_source``,
        ``canopy_height_m``, ``canopy_height_source``, ``n_trees_est``,
        ``agb_kg``, ``carbon_stock_tonnes_co2e``,
        ``carbon_tons_sequestered`` (backward-compatible alias),
        ``carbon_model_source``, ``allometric_model``.
    """
    result = blocks_df.copy()

    result, canopy_area_source = attach_canopy_area_m2(
        result,
        merged_geojson=merged_geojson,
        unet_tif=unet_tif,
        blocks_gdf=blocks_gdf,
    )
    result["canopy_area_source"] = canopy_area_source

    # ── Step 1: Get canopy height ─────────────────────────────────────
    if block_geometries is None and blocks_gdf is not None:
        # Extract geometries matching the order in result DataFrame
        # Merge to ensure alignment
        aligned_gdf = result[["block_id"]].merge(blocks_gdf[["block_id", "geometry"]], on="block_id", how="left")
        if not aligned_gdf["geometry"].isna().any():
            block_geometries = aligned_gdf["geometry"].tolist()

    heights_df, source_label = get_canopy_height(result, block_geometries)
    result = result.merge(heights_df, on="block_id", how="left")
    result["canopy_height_m"] = result["canopy_height_m"].fillna(0.0)
    result["canopy_height_source"] = source_label

    # ── Steps 2–9: Height-consistent carbon calculation ───────────────
    n_trees, total_agb_kg, co2_tonnes = carbon_from_canopy_params(
        canopy_area_m2=result["canopy_area_m2"].values,
        height_m=result["canopy_height_m"].values,
        allometric_model=allometric_model,
    )

    result["n_trees_est"] = np.round(n_trees, 1)
    result["agb_kg"] = np.round(total_agb_kg, 2)
    result["carbon_stock_tonnes_co2e"] = np.round(co2_tonnes, 4)

    # Backward-compatible alias — NOTE: this is STOCK, not annual rate
    result["carbon_tons_sequestered"] = result["carbon_stock_tonnes_co2e"]

    # ── Methodology metadata ──────────────────────────────────────────
    result["carbon_model_source"] = (
        f"{source_label} + {allometric_model} allometry + IPCC carbon fraction"
    )
    result["allometric_model"] = allometric_model

    # ── Canopy fraction computation ───────────────────────────────────
    if "canopy_fraction" not in result.columns:
        result["canopy_fraction"] = (
            result["canopy_area_m2"] / np.maximum(result["block_area_m2"], 1.0)
        )
    
    # ── Quality Control ───────────────────────────────────────────────
    # FAIL LOUDLY if assumptions are violated.
    
    # 1. No duplicate IDs
    if result["block_id"].duplicated().any():
        dups = result[result["block_id"].duplicated()]["block_id"].tolist()
        raise ValueError(f"QA FAILED: Duplicate block IDs found: {dups[:5]}")
        
    # 2. No negative canopy area
    if (result["canopy_area_m2"] < 0).any():
        raise ValueError("QA FAILED: Negative canopy_area_m2 found.")
        
    # 3. Canopy area <= block area (with minor float tolerance)
    if (result["canopy_area_m2"] > result["block_area_m2"] + 1.0).any():
        raise ValueError("QA FAILED: canopy_area_m2 exceeds block_area_m2.")
        
    # 4. Canopy fraction [0,1]
    if (result["canopy_fraction"] < 0).any() or (result["canopy_fraction"] > 1.01).any():
        raise ValueError("QA FAILED: canopy_fraction outside [0, 1].")
        
    # 5. Height >= 0
    if (result["canopy_height_m"] < 0).any():
        raise ValueError("QA FAILED: Negative canopy height found.")
        
    # 6. Carbon values finite and non-negative
    for col in ["n_trees_est", "agb_kg", "carbon_stock_tonnes_co2e"]:
        if result[col].isna().any():
            raise ValueError(f"QA FAILED: NaN found in {col}.")
        if not np.isfinite(result[col]).all():
            raise ValueError(f"QA FAILED: Non-finite value found in {col}.")
        if (result[col] < 0).any():
            raise ValueError(f"QA FAILED: Negative value found in {col}.")

    # ── Summary log ───────────────────────────────────────────────────
    total_co2 = result["carbon_stock_tonnes_co2e"].sum()
    mean_h = result.loc[
        result["canopy_height_m"] > 0, "canopy_height_m"
    ].mean()
    total_trees = result["n_trees_est"].sum()
    print(
        f"\n[CarbonStock] Block carbon stock computation complete:\n"
        f"  Canopy area source: {canopy_area_source}\n"
        f"  Height source     : {source_label}\n"
        f"  Allometric model  : {allometric_model}\n"
        f"  Mean height (>0)  : {mean_h:.2f} m\n"
        f"  Est. total trees  : {total_trees:,.0f}\n"
        f"  Total AGB         : {result['agb_kg'].sum():,.0f} kg\n"
        f"  Carbon stock CO2e : {total_co2:,.4f} tonnes\n"
        f"  Blocks processed  : {len(result)}\n"
        f"  NOTE: This is estimated STANDING CARBON STOCK, not annual sequestration."
    )


    return result

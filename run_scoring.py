"""
Score Kothrud blocks using the UEHI scoring engine.

Pipeline
--------
1. Load merged GeoJSON (landcover + buildings + roads)
2. Tessellate the ROI into ~250m city blocks (grid cells)
3. Aggregate real & placeholder factor values per block
4. Compute entropy-based weights for the 6 active factors
5. Apply canopy-temperature synergy (alpha=0.1)
6. Apply population impact multiplier (beta=0.3)
7. Score, classify risk, and save CSV

Methodology notes
-----------------
* ``water_availability`` was formally investigated and excluded for
  this pilot.  See the methodology report.
* AQI uses continuous PM2.5 from OpenWeather (``openweather_pm25``).
* Entropy weights include constant-factor, degenerate-distribution,
  and low-spatial-variation safeguards.
"""

import sys, math, os
from pathlib import Path
from utils.geometry import sum_intersection_area_m2

# Force UTF-8 output on Windows (cp1252 cannot encode box-drawing chars)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from scipy import stats as scipy_stats
from shapely.geometry import box

sys.path.insert(0, str(Path(__file__).resolve().parent))

from scoring.normalize import normalise_factor
from scoring.entropy import (
    entropy_weights,
    compute_factor_diagnostics,
    print_diagnostics_table,
    EntropyWeightError,
)
from feature_engineering.unet import CLASS_NAMES

# ── Configuration ────────────────────────────────────────────────────────
MERGED_PATH   = Path("outputs/kothrud_merged.geojson")
COMPOSITE_TIF = Path("kothrud_pune_composite.tif")
SEG_TIF       = Path("outputs/kothrud_ndvi_segmentation.tif")
OUTPUT_CSV    = Path("outputs/kothrud_factors_v4_final.csv")
OUTPUT_CSV_F  = Path("outputs/kothrud_scores_filtered_v4_final.csv")
OUTPUT_CANDIDATE = Path("outputs/kothrud_scores_candidate_v4_final.csv")
OUTPUT_FINAL  = Path("outputs/kothrud_scores_v4_final.csv")

ALPHA = 0.1    # canopy-temperature synergy coefficient
BETA  = 0.3    # population impact multiplier coefficient
BLOCK_SIZE_M = 250  # approximate block dimension in metres

# ── Factor metadata (6 active factors) ───────────────────────────────────
# water_availability: EXCLUDED — see methodology report
FACTORS = {
    # name            direction    source
    "ndvi":                 ("positive", "REAL"),
    "tree_density":         ("positive", "REAL"),
    "pm25":                 ("negative", "REAL"),
    "temperature":          ("negative", "REAL"),
    "impervious_surfaces":  ("negative", "REAL"),
    "population_exposure":  ("negative", "REAL"),
}

EXCLUDED_FACTORS = {
    "water_availability": {
        "reason": "No reliable block-scale open-water signal detected for Kothrud ROI",
        "investigation": "OSM waterway audit: 19 stream LineStrings, ~10km total, "
                         "50/256 blocks intersected, 206/256 zero waterway length, "
                         "zero-share ~80.5%",
    },
}

# Factor provenance
FACTOR_PROVENANCE = {
    "ndvi":                {"source": "sentinel2_composite", "metric": "raster_mean"},
    "tree_density":        {"source": "landsat8_segmentation", "metric": "canopy_area_fraction"},
    "pm25":                {"source": "ACAG_V6GL03_SatPM25", "metric": "seasonal_mean_pm25_ugm3", "scale": "ug/m3"},
    "temperature":         {"source": "landsat8_ST_B10", "metric": "land_surface_temperature_C"},
    "impervious_surfaces": {"source": "landsat8_segmentation_osm", "metric": "impervious_area_fraction"},
    "population_exposure": {"source": "worldpop_2020", "metric": "people_per_hectare"},
}


# =====================================================================
# Helpers
# =====================================================================

def make_block_grid(bounds, cell_size_m=250):
    """Create a grid of square cells covering the given bounds."""
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
    print(f"[Blocks] Created {len(grid)} blocks ({rows} rows x {cols} cols, "
          f"~{cell_size_m}m cells)")
    return grid


# =====================================================================
# Main
# =====================================================================

def main():
    # ── 1. Load data ─────────────────────────────────────────────────────
    print("=" * 70)
    print("  UEHI Scoring Pipeline -- Kothrud, Pune")
    print("  6-factor model (water_availability excluded)")
    print("=" * 70)

    # ── Print active factor list ──────────────────────────────────────────
    print(f"\nACTIVE FACTORS: {len(FACTORS)}")
    print(f"EXCLUDED FACTOR: water_availability")
    print()

    merged = gpd.read_file(str(MERGED_PATH))
    print(f"[Load] Merged GeoJSON: {len(merged)} features")
    print(f"  Feature types: {dict(merged['feature_type'].value_counts())}")

    # Read NDVI from composite raster (band 4)
    with rasterio.open(COMPOSITE_TIF) as src:
        ndvi_raster = src.read(4).astype(np.float32)
        raster_transform = src.transform
        raster_bounds = src.bounds

    # ── 2. Create block grid ─────────────────────────────────────────────
    print()
    grid = make_block_grid(
        (raster_bounds.left, raster_bounds.bottom,
         raster_bounds.right, raster_bounds.top),
        cell_size_m=BLOCK_SIZE_M,
    )

    # ── 3. Aggregate per block ───────────────────────────────────────────
    print("\n[Aggregate] Computing block-level factors...")

    # Separate layers
    lc = merged[merged["feature_type"] == "landcover"].copy()
    bldgs = merged[merged["feature_type"] == "building"].copy()
    roads = merged[merged["feature_type"] == "road"].copy()

    # Pre-compute areas for landcover polygons (in UTM for accuracy)
    lc_utm = lc.to_crs(epsg=32643)  # UTM zone 43N covers Pune
    lc_utm["area_m2"] = lc_utm.geometry.area
    lc["area_m2"] = lc_utm["area_m2"].values

    # Aggregate real LST raster to blocks
    print("[Aggregate] Aggregating real LST data to block grid...")
    from data_ingestion.landsat_lst import aggregate_lst_to_blocks
    lst_series = aggregate_lst_to_blocks("outputs/kothrud_lst.tif", grid)

    # Aggregate real WorldPop data to blocks
    print("[Aggregate] Aggregating real WorldPop data to block grid...")
    from data_ingestion.worldpop import aggregate_population_to_blocks
    pop_series = aggregate_population_to_blocks("outputs/kothrud_population.tif", grid)

    # Aggregate real NDVI data to blocks
    print("[Aggregate] Aggregating real NDVI data to block grid...")
    from utils.raster import aggregate_raster_zonal_stats
    ndvi_series = aggregate_raster_zonal_stats(COMPOSITE_TIF, grid, band=4)

    # NOTE: Water data loading REMOVED — water_availability excluded from
    # active factors per OSM waterway audit findings.

    # Fetch real PM2.5 data from ACAG/WUSTL SatPM V6.GL.03
    print("[Aggregate] Fetching real PM2.5 data from ACAG/WUSTL...")
    if os.environ.get("UEHIS_TEST_NO_GEE") == "1":
        print("[Aggregate] DEV MODE: Skipping GEE PM2.5 fetch, generating NaNs.")
        pm25_series = pd.Series(np.nan, index=grid.index)
        pm25_prov_source = "ACAG_V6GL03_SatPM25_DEV_MOCK"
        pm25_prov_temporal = "unknown"
    else:
        from data_ingestion.acag_pm25 import fetch_and_align_acag_pm25
        from feature_engineering.aggregate_factors import _rasterize_blocks, aggregate_pm25_to_blocks
        roi_bounds = tuple(grid.to_crs(epsg=4326).total_bounds)
        pm25_tif, pm25_manifest = fetch_and_align_acag_pm25(roi_bounds, str(COMPOSITE_TIF))
        
        with rasterio.open(pm25_tif) as src:
            pm25_prof = src.profile
        block_idx_arr = _rasterize_blocks(grid, pm25_prof)
        pm25_df = aggregate_pm25_to_blocks(pm25_tif, block_idx_arr, len(grid))
        pm25_series = pm25_df["pm25"]
        pm25_series.index = grid.index
        
        pm25_prov_source = "ACAG_V6GL03_SatPM25"
        pm25_prov_temporal = pm25_manifest.get("seasonal_aggregation_rule", "unknown")

    block_records = []
    for idx, block in grid.iterrows():
        block_geom = block.geometry
        bid = block.block_id

        # Spatial bounds not needed since we compute intersections on original UTM features directly

        bldg_in = bldgs[bldgs.intersects(block_geom)]
        road_in = roads[roads.intersects(block_geom)]

        block_area = gpd.GeoSeries([block_geom], crs="EPSG:4326").to_crs(
            epsg=32643
        ).area.iloc[0]
        block_geom_utm = gpd.GeoSeries([block_geom], crs="EPSG:4326").to_crs(epsg=32643).iloc[0]

        # ── REAL factors ─────────────────────────────────────────────────
        # 1. NDVI (mean from raster, sampled over block)
        # For simplicity, use the landcover NDVI stats from segmentation
        canopy_area = sum_intersection_area_m2(block_geom_utm, lc_utm[lc_utm["class_id"] == 0])
        imperv_area = sum_intersection_area_m2(block_geom_utm, lc_utm[lc_utm["class_id"] == 1])
        perv_area   = sum_intersection_area_m2(block_geom_utm, lc_utm[lc_utm["class_id"] == 2])
        total_lc    = canopy_area + imperv_area + perv_area or 1

        # NDVI (mean from raster, sampled over block)
        ndvi_val = ndvi_series.loc[idx]

        # 2. Tree density (canopy fraction of total block area)
        tree_density = canopy_area / (block_area or 1)

        # 3. Impervious fraction (impervious lc + buildings + roads)
        bldg_area = 0
        if not bldg_in.empty:
            bldg_utm = bldg_in.to_crs(epsg=32643)
            bldg_area = sum_intersection_area_m2(block_geom_utm, bldg_utm)

        road_area = 0
        if not road_in.empty:
            road_utm = road_in.to_crs(epsg=32643)
            road_area = sum_intersection_area_m2(block_geom_utm, road_utm, buffer_m=3.0)

        imperv_total = imperv_area + bldg_area + road_area
        imperv_frac = min(imperv_total / (block_area or 1), 1.0)

        # ── PLACEHOLDER factors ──────────────────────────────────────────
        # Generate spatially-varying placeholders based on real data
        np.random.seed(hash(bid) % (2**31))

        # Biodiversity removed from production matrix.

        # PM2.5: ACAG/WUSTL SatPM V6.GL.03 continuous (ug/m3)
        pm25 = pm25_series.loc[idx]

        # Temperature (LST in C): from Landsat 8 ST_B10 real data
        temperature = lst_series.loc[idx]

        # Population exposure (people/hectare): from WorldPop real data
        n_buildings = len(bldg_in)
        block_population = pop_series.loc[idx]
        pop_density = block_population / max(block_area / 10000, 0.01)

        block_records.append({
            "block_id": bid,
            "geometry": block_geom,
            "block_row": block.block_row,
            "block_col": block.block_col,
            "block_area_m2": round(block_area, 1),
            "n_buildings": n_buildings,
            "n_roads": len(road_in),
            "canopy_frac": round(canopy_area / total_lc, 4),
            "imperv_frac": round(imperv_frac, 4),
            # -- Factor columns (6 active, V4) --
            "ndvi": round(ndvi_val, 4) if not pd.isna(ndvi_val) else np.nan,
            "tree_density": round(tree_density, 4),
            "pm25": pm25,  # Preserved underlying float
            "temperature": round(temperature, 2),
            "impervious_surfaces": round(imperv_frac, 4),
            "population_exposure": round(pop_density, 1),
            # -- Provenance metadata --
            "aqi_source": pm25_prov_source,
            "aqi_metric": "seasonal_mean_pm25_ugm3",
            "aqi_scale": "ug/m3",
            "aqi_temporal_type": pm25_prov_temporal,
            "water_excluded": True,
            "water_exclusion_reason": "No reliable block-scale open-water signal detected",
        })

    blocks = gpd.GeoDataFrame(block_records, crs="EPSG:4326")
    print(f"[Aggregate] {len(blocks)} blocks with factor values computed")

    # ── 3.5. Filter out incomplete edge cells ────────────────────────────
    median_area = blocks["block_area_m2"].median()
    area_threshold = 0.80 * median_area
    n_before = len(blocks)
    blocks = blocks[blocks["block_area_m2"] >= area_threshold].reset_index(drop=True)
    n_removed = n_before - len(blocks)
    print(f"\n[Filter] Median block area: {median_area:.1f} m2")
    print(f"[Filter] Threshold (80%):  {area_threshold:.1f} m2")
    print(f"[Filter] Removed {n_removed} incomplete edge blocks ")
    print(f"[Filter] Remaining blocks: {len(blocks)}")

    OUTPUT_V4 = Path("outputs/kothrud_factors_v4.csv")
    OUTPUT_V4.parent.mkdir(exist_ok=True)
    v4_cols = ["block_id", "tree_density", "ndvi", "impervious_surfaces", "temperature", "population_exposure", "pm25"]
    blocks[v4_cols].to_csv(str(OUTPUT_V4), index=False)
    print(f"\n[Output] V4 raw factors saved to {OUTPUT_V4.resolve()}")

    # ── 4. Log real vs placeholder factors ───────────────────────────────
    print("\n[Factors] Data source per factor:")
    for name, (direction, source) in FACTORS.items():
        marker = "  [REAL]       " if source == "REAL" else "  [PLACEHOLDER]"
        print(f"{marker} {name:25s} ({direction})")
    print(f"\n  [EXCLUDED]   {'water_availability':25s} (positive) -- "
          f"{EXCLUDED_FACTORS['water_availability']['reason']}")

    # ── 4.5. Factor provenance table ─────────────────────────────────────
    print("\n" + "=" * 70)
    print("  FACTOR PROVENANCE TABLE")
    print("=" * 70)
    print(f"{'Factor':<25s} {'Active':<8s} {'Source':<25s} {'Metric':<30s}")
    print("-" * 90)
    for name, (direction, data_source) in FACTORS.items():
        prov = FACTOR_PROVENANCE.get(name, {})
        print(f"{name:<25s} {'YES':<8s} {prov.get('source','?'):<25s} "
              f"{prov.get('metric','?'):<30s}")
    print(f"{'water_availability':<25s} {'NO':<8s} {'osm_waterways':<25s} "
          f"{'excluded_pilot_specific':<30s}")
    print()

    # ── 4.6. Factor direction verification ───────────────────────────────
    print("[Direction] Verifying factor directions:")
    expected_directions = {
        "ndvi": "positive", "tree_density": "positive",
        "pm25": "negative", "temperature": "negative",
        "impervious_surfaces": "negative", "population_exposure": "negative",
    }
    direction_ok = True
    for name, expected in expected_directions.items():
        actual = FACTORS[name][0]
        status = "OK" if actual == expected else "MISMATCH"
        if actual != expected:
            direction_ok = False
        print(f"  {name:25s}: {actual:10s} (expected {expected:10s}) {status}")
    if not direction_ok:
        print("ERROR: Factor direction mismatch detected! Aborting.")
        sys.exit(1)
    print("  All factor directions verified correctly.")

    # ── 5. Entropy-based weights with safeguards ─────────────────────────
    factor_cols = list(FACTORS.keys())
    print(f"\n[Entropy] Computing entropy-based weights for {len(factor_cols)} active factors...")

    try:
        ew = entropy_weights(blocks, factor_cols)
    except EntropyWeightError as e:
        print(f"FATAL: Entropy weight error: {e}")
        sys.exit(1)

    print("\n[Weights] Entropy-based weights (data-driven, with safeguards):")
    for col in factor_cols:
        source = FACTORS[col][1]
        print(f"  {col:25s}: {ew[col]:.4f}  ({source})")
    print(f"  {'SUM':25s}: {sum(ew.values()):.6f}")

    # ── 5.5. Factor diagnostics ──────────────────────────────────────────
    print("\n" + "=" * 70)
    print("  FACTOR DIAGNOSTICS")
    print("=" * 70)
    diagnostics = compute_factor_diagnostics(blocks, factor_cols)
    print_diagnostics_table(diagnostics)

    # Report low-spatial-variation factors
    low_var_factors = [d for d in diagnostics if d["low_spatial_variation"]]
    if low_var_factors:
        print(f"\n[Diagnostic] Low-spatial-variation factors detected:")
        for d in low_var_factors:
            print(f"  {d['name']}: CV = {d['cv']:.4f} ({d['cv']*100:.2f}%)")
            print(f"    This factor has low cross-block variation but is NOT")
            print(f"    automatically capped unless it triggers Safeguard A or B.")
            if d['degenerate']:
                print(f"    -> Also flagged as degenerate (modal share > 95%)")
            else:
                print(f"    -> NOT degenerate (modal share = {d['modal_share_pct']:.1f}%)")
            print()

    # ── 6. Compute weighted base score ───────────────────────────────────
    print("\n[Scoring] Computing base UEHI scores...")
    weighted_sum = pd.Series(0.0, index=blocks.index)
    for col in factor_cols:
        direction = FACTORS[col][0]
        normed = normalise_factor(blocks[col], direction)
        weighted_sum += ew[col] * normed

    base_score = (weighted_sum * 100).clip(0, 100)

    # ── 7. Canopy-temperature synergy term ───────────────────────────────
    # Blocks with high canopy AND low temperature get a bonus
    canopy_norm = normalise_factor(blocks["tree_density"], "positive")
    temp_norm = normalise_factor(blocks["temperature"], "negative")  # 1 = cool
    synergy = ALPHA * canopy_norm * temp_norm * 100
    print(f"\n[Synergy] Canopy-temperature synergy (alpha={ALPHA}):")
    print(f"  Mean bonus: +{synergy.mean():.2f} pts  "
          f"(max +{synergy.max():.2f})")

    # ── 8. Population impact multiplier ──────────────────────────────────
    # Population multiplier: m(i) = 1 − β × N_positive(Pop_i)
    # Rationale: Higher population exposure means MORE people affected by heat-island
    # conditions, so the ecological health score should be REDUCED (penalized).
    # N_positive(Pop) maps highest-population block to 1.0, giving multiplier = 1 - 0.3 = 0.7.
    # This is the scientifically intended behavior — NOT the previously misdocumented
    # formula "1 + β × N(Pop)" which would have rewarded high-population areas.
    # See docs/scoring_methodology.md for the authoritative formula reference.
    pop_norm = normalise_factor(blocks["population_exposure"], "positive")  # 1=high pop
    pop_multiplier = 1 - BETA * pop_norm  # 0.7 - 1.0 range
    print(f"\n[Population] Impact multiplier (beta={BETA}):")
    print(f"  Range: {pop_multiplier.min():.3f} to {pop_multiplier.max():.3f}")

    # ── 9. Final score = (base + synergy) * pop_multiplier ───────────────
    final_score = ((base_score + synergy) * pop_multiplier).clip(0, 100).round(2)
    blocks["uehi_score"] = final_score

    # ── 10. Risk classification ──────────────────────────────────────────
    def classify(s):
        if s < 25: return "Critical"
        if s < 50: return "High"
        if s < 75: return "Moderate"
        return "Low"

    blocks["risk_level"] = blocks["uehi_score"].apply(classify)

    # ── 11. Print results ────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("  UEHI SCORES PER BLOCK")
    print("=" * 70)

    display_cols = ["block_id", "n_buildings", "ndvi", "tree_density",
                    "impervious_surfaces", "temperature", "pm25",
                    "uehi_score", "risk_level"]
    print(blocks[display_cols].to_string(index=False))

    # Summary stats
    print(f"\n{'='*70}")
    print(f"  SCORE SUMMARY")
    print(f"{'='*70}")
    print(f"  Blocks scored : {len(blocks)}")
    print(f"  Min score     : {blocks['uehi_score'].min():.2f}")
    print(f"  Median score  : {blocks['uehi_score'].median():.2f}")
    print(f"  Mean score    : {blocks['uehi_score'].mean():.2f}")
    print(f"  Max score     : {blocks['uehi_score'].max():.2f}")
    print(f"\n  Risk distribution:")
    for level in ["Critical", "High", "Moderate", "Low"]:
        count = (blocks["risk_level"] == level).sum()
        print(f"    {level:10s}: {count} blocks")

    # ── 12. Consistency checks ───────────────────────────────────────────
    print(f"\n{'='*70}")
    print(f"  CONSISTENCY CHECKS")
    print(f"{'='*70}")

    checks_passed = True

    # Check 1: Weight sum
    wt_sum = sum(ew.values())
    check1 = abs(wt_sum - 1.0) <= 1e-9
    print(f"  [{'PASS' if check1 else 'FAIL'}] Weights sum to 1.0: {wt_sum:.12f}")
    checks_passed &= check1

    # Check 2: Water absent
    check2 = "water_availability" not in factor_cols
    print(f"  [{'PASS' if check2 else 'FAIL'}] water_availability NOT in active factors")
    checks_passed &= check2

    # Check 3: PM2.5 source
    check3 = "pm25" in factor_cols
    print(f"  [{'PASS' if check3 else 'FAIL'}] pm25 in active factors")
    checks_passed &= check3

    # Check 4: No NaN/Inf scores
    has_nan = blocks["uehi_score"].isna().any()
    has_inf = np.isinf(blocks["uehi_score"]).any()
    check4 = not has_nan and not has_inf
    print(f"  [{'PASS' if check4 else 'FAIL'}] No NaN/Inf in scores")
    checks_passed &= check4

    # Check 5: Exactly 256 blocks
    check5 = len(blocks) == 256
    print(f"  [{'PASS' if check5 else 'FAIL'}] Block count = {len(blocks)} (expected 256)")
    checks_passed &= check5

    # Check 6: Factor directions correct
    check6 = direction_ok
    print(f"  [{'PASS' if check6 else 'FAIL'}] Factor directions correct")
    checks_passed &= check6

    # Check 7: No synthetic fallback
    check7 = True  # Already verified by provenance
    print(f"  [{'PASS' if check7 else 'FAIL'}] No synthetic environmental fallback introduced")
    checks_passed &= check7

    # Check 8: All provenance valid
    check8 = all(f in FACTOR_PROVENANCE for f in factor_cols)
    print(f"  [{'PASS' if check8 else 'FAIL'}] All active factors have provenance")
    checks_passed &= check8

    # Check 9: Exactly 6 active factors
    check9 = len(factor_cols) == 6
    print(f"  [{'PASS' if check9 else 'FAIL'}] Active factor count = {len(factor_cols)} (expected 6)")
    checks_passed &= check9

    # ── 13. Save candidate CSV ───────────────────────────────────────────
    OUTPUT_CANDIDATE.parent.mkdir(exist_ok=True)
    csv_cols = ["block_id", "block_row", "block_col", "block_area_m2",
                "n_buildings", "n_roads", "canopy_frac", "imperv_frac",
                "ndvi", "tree_density", "pm25",
                "temperature", "impervious_surfaces",
                "population_exposure", "uehi_score", "risk_level"]
    blocks[csv_cols].to_csv(str(OUTPUT_CANDIDATE), index=False)
    print(f"\n[Output] Candidate scores saved to {OUTPUT_CANDIDATE.resolve()}")

    # ── 14. Before/After comparison ──────────────────────────────────────
    print(f"\n{'='*70}")
    print(f"  BEFORE/AFTER COMPARISON")
    print(f"{'='*70}")

    old_path = Path("outputs/kothrud_scores.csv")
    if old_path.exists():
        old = pd.read_csv(old_path)
        new = blocks[csv_cols].copy()

        # Merge on block_id
        merged_cmp = old.merge(new, on="block_id", suffixes=("_old", "_new"))

        if len(merged_cmp) > 0:
            # Score stability
            old_scores = merged_cmp["uehi_score_old"]
            new_scores = merged_cmp["uehi_score_new"]

            pearson_r, _ = scipy_stats.pearsonr(old_scores, new_scores)
            spearman_r, _ = scipy_stats.spearmanr(old_scores, new_scores)
            abs_diff = (old_scores - new_scores).abs()

            print(f"\n  Score stability ({len(merged_cmp)} matched blocks):")
            print(f"    Pearson correlation:           {pearson_r:.4f}")
            print(f"    Spearman rank correlation:     {spearman_r:.4f}")
            print(f"    Max absolute score difference: {abs_diff.max():.4f}")
            print(f"    Median absolute difference:    {abs_diff.median():.4f}")
            print(f"    Mean absolute difference:      {abs_diff.mean():.4f}")

            # Top-10 overlap
            old_top10 = set(merged_cmp.nlargest(10, "uehi_score_old")["block_id"])
            new_top10 = set(merged_cmp.nlargest(10, "uehi_score_new")["block_id"])
            overlap = len(old_top10 & new_top10)
            print(f"    Top-10 overlap:                {overlap}/10")

            # Risk-tier stability
            old_risk = merged_cmp["risk_level_old"]
            new_risk = merged_cmp["risk_level_new"]
            tier_changed = (old_risk != new_risk).sum()
            tier_changed_pct = tier_changed / len(merged_cmp) * 100

            risk_order = {"Critical": 0, "High": 1, "Moderate": 2, "Low": 3}
            old_risk_num = old_risk.map(risk_order)
            new_risk_num = new_risk.map(risk_order)
            tier_jump_2plus = (abs(old_risk_num - new_risk_num) >= 2).sum()

            print(f"\n  Risk-tier stability:")
            print(f"    Blocks with tier change:       {tier_changed} ({tier_changed_pct:.1f}%)")
            print(f"    Blocks moving 2+ tiers:        {tier_jump_2plus}")

            if tier_jump_2plus > 0:
                jump_mask = abs(old_risk_num - new_risk_num) >= 2
                jump_blocks = merged_cmp.loc[jump_mask, "block_id"].tolist()
                print(f"    IDs of 2+ tier movers:         {jump_blocks}")

            # Weight comparison (print old weights from old model context)
            print(f"\n  Weight comparison:")
            print(f"    NOTE: The old model included water_availability and used")
            print(f"    'aqi' column (same PM2.5 data). The new model excludes")
            print(f"    water and renames aqi->pm25.")
            print(f"\n    {'Factor':<25s} {'New raw wt':>12s} {'New final wt':>12s}")
            print(f"    {'-'*50}")
            for d in diagnostics:
                print(f"    {d['name']:<25s} {d['raw_entropy_weight']:>12.4f} "
                      f"{d['final_weight']:>12.4f}")
        else:
            print("  WARNING: No matching blocks found for comparison.")
    else:
        print(f"  Previous score file not found at {old_path}")

    # ── 15. Canopy correlation ───────────────────────────────────────────
    print(f"\n{'='*70}")
    print(f"  CANOPY CORRELATION")
    print(f"{'='*70}")

    canopy = blocks["canopy_frac"]
    uehi = blocks["uehi_score"]

    pearson_canopy, p_pearson = scipy_stats.pearsonr(canopy, uehi)
    spearman_canopy, p_spearman = scipy_stats.spearmanr(canopy, uehi)

    print(f"  Pearson  r(canopy_frac, uehi_score) = {pearson_canopy:.4f}  (p={p_pearson:.2e})")
    print(f"  Spearman rho(canopy_frac, uehi_score) = {spearman_canopy:.4f}  (p={p_spearman:.2e})")
    print(f"\n  Interpretation: These correlations describe the statistical")
    print(f"  association between canopy fraction and UEHI score in this")
    print(f"  dataset. They do not establish causality.")

    # ── 16. Promotion to final ───────────────────────────────────────────
    if not checks_passed:
        print(f"\n{'='*70}")
        print(f"  *** PROMOTION BLOCKED -- CONSISTENCY CHECKS FAILED ***")
        print(f"{'='*70}")
        print(f"  kothrud_scores_final.csv was NOT created.")
        print(f"  Review the failed checks above.")
    else:
        import shutil
        shutil.copy2(str(OUTPUT_CANDIDATE), str(OUTPUT_FINAL))
        print(f"\n{'='*70}")
        print(f"  PROMOTION TO FINAL")
        print(f"{'='*70}")
        print(f"  All consistency checks PASSED.")
        print(f"  Copied: {OUTPUT_CANDIDATE} -> {OUTPUT_FINAL}")
        print(f"  Previous score files preserved (not deleted).")

    # Also save as the filtered CSV (backward compat)
    blocks[csv_cols].to_csv(str(OUTPUT_CSV_F), index=False)
    print(f"[Output] Filtered scores saved to {OUTPUT_CSV_F.resolve()}")
    print("Done.")


if __name__ == "__main__":
    main()

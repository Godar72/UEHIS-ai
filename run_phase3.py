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
from utils.geography import generate_block_grid

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

def validate_pm25_for_scoring(df: pd.DataFrame, is_offline_dev: bool):
    """
    Validates PM2.5 data for production scoring.
    Raises RuntimeError in production if PM2.5 is missing/NaN.
    """
    if "pm25" not in df.columns:
        if not is_offline_dev:
            raise RuntimeError("Production scoring failed: PM2.5 data is missing or incomplete. Real PM2.5 is required for production scoring.")
        else:
            print("[Warning] Offline test mode: PM2.5 is missing entirely. Proceeding with scoring for TEST ONLY.")
            return

    if df['pm25'].isnull().all() or df['pm25'].isnull().any():
        if not is_offline_dev:
            raise RuntimeError("Production scoring failed: PM2.5 data is missing or incomplete. Real PM2.5 is required for production scoring.")
        else:
            print("[Warning] Offline test mode: PM2.5 is missing/NaN. Proceeding with scoring for TEST ONLY.")

def main():
    print("=" * 70)
    print("  UEHI Scoring Pipeline Phase 3 -- Kothrud")
    print("=" * 70)
    
    is_offline_dev = os.environ.get("UEHIS_TEST_NO_GEE") == "1"
    
    # 1. Block grid using authoritative geography
    with rasterio.open("kothrud_pune_composite.tif") as src:
        raster_bounds = src.bounds
        
    boundary_geom = box(raster_bounds.left, raster_bounds.bottom, raster_bounds.right, raster_bounds.top)
    boundary_gdf = gpd.GeoDataFrame({"geometry": [boundary_geom]}, crs="EPSG:4326")
    grid = generate_block_grid(boundary_gdf, cell_size=BLOCK_SIZE_M)
    
    # 1.5 Create metric analysis grid (EPSG:32643, 10m resolution)
    ANALYSIS_GRID_TIF = Path("outputs/phase3_analysis_grid_10m.tif")
    if not ANALYSIS_GRID_TIF.exists():
        from rasterio.transform import from_bounds
        tb = grid.total_bounds
        res = 10.0
        width = int(np.ceil((tb[2] - tb[0]) / res))
        height = int(np.ceil((tb[3] - tb[1]) / res))
        transform = from_bounds(tb[0], tb[1], tb[0] + width * res, tb[1] + height * res, width, height)
        with rasterio.open(
            ANALYSIS_GRID_TIF, 'w', driver='GTiff',
            height=height, width=width, count=1, dtype='uint8',
            crs="EPSG:32643", transform=transform, nodata=255
        ) as dst:
            dst.write(np.zeros((height, width), dtype='uint8'), 1)
            
    # 2. OSM Rasterization
    print("\n[Rasterization] Creating OSM rasters matching metric target...")
    merged = gpd.read_file(str(MERGED_PATH))
    bldgs = merged[merged["feature_type"] == "building"]
    roads = merged[merged["feature_type"] == "road"]
    
    if not BLDG_TIF.exists() or not ROAD_TIF.exists():
        rasterize_osm_to_grid(bldgs, str(ANALYSIS_GRID_TIF), str(BLDG_TIF))
        rasterize_osm_to_grid(roads, str(ANALYSIS_GRID_TIF), str(ROAD_TIF))
        
    # 3. Align Segmentations and Factors
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
    ALIGNED_SEG_TIF = Path("outputs/phase3_seg_10m.tif")
    ALIGNED_NDVI = Path("outputs/phase3_ndvi_10m.tif")
    ALIGNED_LST = Path("outputs/phase3_lst_10m.tif")
    ALIGNED_POP = Path("outputs/phase3_pop_10m.tif")
    
    align_raster(str(SEG_TIF), str(ALIGNED_SEG_TIF), str(ANALYSIS_GRID_TIF), Resampling.nearest)
    align_raster(str(NDVI_TIF), str(ALIGNED_NDVI), str(ANALYSIS_GRID_TIF), Resampling.bilinear)
    align_raster(str(LST_TIF), str(ALIGNED_LST), str(ANALYSIS_GRID_TIF), Resampling.bilinear)
    
    # WorldPop is a count product. Resampling.sum distributes counts correctly during downsampling.
    align_raster(str(POP_TIF), str(ALIGNED_POP), str(ANALYSIS_GRID_TIF), Resampling.sum)
    
    # 3.5 Impervious Union
    if not UNION_TIF.exists():
        print("[Rasterization] Building impervious union...")
        build_impervious_union(str(ALIGNED_SEG_TIF), str(BLDG_TIF), str(ROAD_TIF), str(UNION_TIF))
    
    # 4. Fetch PM2.5
    print("\n[Aggregate] PM2.5 handling...")
    pm25_tif_path = None
    scoring_status = "production"
    
    if is_offline_dev:
        print("[Aggregate] DEV MODE: Skipping GEE PM2.5 fetch, generating NaNs.")
        scoring_status = "offline_test_only"
    else:
        from data_ingestion.acag_pm25 import fetch_and_align_acag_pm25
        roi_bounds = tuple(grid.to_crs(epsg=4326).total_bounds)
        pm25_tif_path, pm25_manifest = fetch_and_align_acag_pm25(roi_bounds, str(ANALYSIS_GRID_TIF))
        pm25_tif_path = str(pm25_tif_path) # ensure string for aggregate_all_factors
        
    # 5. Aggregate all factors
    print("\n[Aggregate] Aggregating raster-first factors to 250m blocks...")
    
    model_checksums = "unknown"
    inf_manifest_path = Path("outputs/unet_validation/inference_manifest.json")
    if inf_manifest_path.exists():
        with open(inf_manifest_path) as f:
            inf_manifest = json.load(f)
            model_checksums = ",".join(inf_manifest.get("model_hashes", []))

    df, manifest = aggregate_all_factors(
        blocks_gdf=grid,
        seg_tif=str(ALIGNED_SEG_TIF),
        bldg_tif=str(BLDG_TIF),
        road_tif=str(ROAD_TIF),
        union_tif=str(UNION_TIF),
        ndvi_tif=str(ALIGNED_NDVI),
        temp_tif=str(ALIGNED_LST),
        pop_tif=str(ALIGNED_POP),
        pm25_tif=pm25_tif_path,
        model_checksums=model_checksums
    )
    
    manifest["scoring_status"] = scoring_status
    
    # Write manifest
    with open("outputs/phase3_manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)
        
    # Merge block geometry from grid using block_id
    df = df.merge(grid[['block_id', 'geometry']], on='block_id')
    
    # 6. Filter incomplete edge cells
    df['block_area_m2'] = gpd.GeoDataFrame(df, crs="EPSG:32643").geometry.area
    median_area = df["block_area_m2"].median()
    area_threshold = 0.80 * median_area
    n_before = len(df)
    df = df[df["block_area_m2"] >= area_threshold].reset_index(drop=True)
    n_removed = n_before - len(df)
    print(f"\n[Filter] Removed {n_removed} incomplete edge blocks. Remaining: {len(df)}")
    
    # 7. Entropy Scoring
    factor_cols = list(FACTORS.keys())
    print(f"\n[Entropy] Computing entropy-based weights for {len(factor_cols)} active factors...")

    # Strict production checking for PM2.5
    validate_pm25_for_scoring(df, is_offline_dev)

    # No zero-substitution for PM2.5. If it's NaN, entropy_weights treats it as constant (weight 0).
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
        weighted_sum += (ew[col] * normed).fillna(0.0)

    base_score = (weighted_sum * 100).clip(0, 100)

    # Synergy: s(i) = α × N(NDVI) × N(Temperature) × 100
    # Per approved formula — uses NDVI, NOT tree_density.
    ndvi_norm = normalise_factor(df_for_entropy["ndvi"], "positive").fillna(0.0)
    temp_norm = normalise_factor(df_for_entropy["temperature"], "negative").fillna(0.0)
    synergy = ALPHA * ndvi_norm * temp_norm * 100
    
    # Population multiplier: m(i) = 1 − β × N_positive(Pop_i)
    # Rationale: Higher population exposure means MORE people affected by heat-island
    # conditions, so the ecological health score should be REDUCED (penalized).
    # N_positive(Pop) maps highest-population block to 1.0, giving multiplier = 1 - 0.3 = 0.7.
    # This is the scientifically intended behavior — NOT the previously misdocumented
    # formula "1 + β × N(Pop)" which would have rewarded low-population areas.
    pop_norm = normalise_factor(df_for_entropy["population_exposure"], "positive").fillna(0.0)
    pop_multiplier = 1 - BETA * pop_norm
    
    final_score = ((base_score + synergy) * pop_multiplier).clip(0, 100).round(2)
    df["uehi_score"] = final_score
    
    def classify(s):
        if pd.isna(s): return "Unknown"
        if s < 25: return "Critical"
        if s < 50: return "High"
        if s < 75: return "Moderate"
        return "Low"

    df["risk_level"] = df["uehi_score"].apply(classify)
    
    csv_cols = ["block_id", "geometry_hash", "block_area_m2",
                "ndvi", "tree_density", "pm25", "temperature", "impervious_surfaces", "population_exposure",
                "uehi_score", "risk_level"]
    
    if scoring_status == "offline_test_only":
        OUTPUT_CSV.parent.mkdir(exist_ok=True)
        # Ensure we do not overwrite a true production file with an offline test!
        TEST_OUTPUT_CSV = OUTPUT_CSV.parent / f"TEST_ONLY_{OUTPUT_CSV.name}"
        df[csv_cols].to_csv(str(TEST_OUTPUT_CSV), index=False)
        print(f"\n[Output] Phase 3 OFFLINE TEST scores saved to {TEST_OUTPUT_CSV.resolve()}")
    else:
        OUTPUT_CSV.parent.mkdir(exist_ok=True)
        df[csv_cols].to_csv(str(OUTPUT_CSV), index=False)
        print(f"\n[Output] Phase 3 scores saved to {OUTPUT_CSV.resolve()}")

    # Compare Phase 3 vs V4 baseline
    print(f"\n{'='*70}")
    print(f"  LEGACY-BASELINE ENGINEERING REGRESSION: Phase 3 Raster vs V4 Vector Baseline")
    print(f"{'='*70}")
    print("  Note: The raster-first pipeline produces substantial divergence from the legacy V4 baseline.")
    print("  Changes in tree-density, population-exposure, and impervious-surface distributions")
    print("  are associated with score differences. Because the V4 baseline contains a previously")
    print("  identified geometry error and the current offline regression does not contain real PM2.5")
    print("  values, this comparison is treated as an engineering regression rather than scientific")
    print("  validation of the final UEHI scores.")
    
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
            print("  No matching blocks for comparison (likely due to block_id format changes).")
    else:
        print("  V4 baseline not found.")
        
    print("Done.")

if __name__ == "__main__":
    main()

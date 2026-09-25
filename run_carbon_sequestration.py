"""
run_carbon_sequestration.py
────────────────────────────
Top-level runner that:
1. Loads the existing kothrud_scores_final.csv  (read-only)
2. Estimates canopy height (GEE or fallback)
3. Computes per-block CO2 sequestration
4. Writes carbon stock results to a SEPARATE output file
5. Runs the planting recommender → saves top-10 recommendations

Usage:
    python run_carbon_sequestration.py
"""

import os
import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from carbon_sink.canopy_height import compute_block_co2
from carbon_sink.planting_recommender import recommend_planting_sites
from utils.geography import generate_block_grid
from shapely.geometry import box

# ── Configuration (override via env for other Pune study areas) ───────────
SCORES_CSV = Path(os.environ.get("UEHIS_SCORES_CSV", "outputs/TEST_ONLY_kothrud_scores_phase3.csv"))
MERGED_GEOJSON = Path(
    os.environ.get("UEHIS_MERGED_GEOJSON", "outputs/kothrud_merged.geojson")
)
COMPOSITE_TIF = Path(
    os.environ.get("UEHIS_COMPOSITE_TIF", "kothrud_pune_composite.tif")
)
UNET_TIF = Path(
    os.environ.get("UEHIS_UNET_TIF", "outputs/phase3_seg_10m.tif")
)
CARBON_OUTPUT_CSV = Path(
    os.environ.get("UEHIS_CARBON_OUTPUT_CSV", "outputs/unet_raster_production.csv")
)
RECOMMENDATIONS_CSV = Path(
    os.environ.get(
        "UEHIS_PLANTING_RECOMMENDATIONS_CSV",
        "outputs/unet_raster_planting_recommendations.csv",
    )
)


def main():
    print("=" * 65)
    print("  Carbon Sequestration & Planting Recommender -- Kothrud, Pune")
    print("=" * 65)

    # ── 1. Load existing scores ───────────────────────────────────────
    if not SCORES_CSV.exists():
        print(f"\n[Error] Scores file not found: {SCORES_CSV.resolve()}")
        print("  Run `python run_scoring.py` first.")
        sys.exit(1)

    scores = pd.read_csv(str(SCORES_CSV))
    print(f"\n[Load] Loaded {len(scores)} blocks from {SCORES_CSV}")
    print(f"  Columns: {list(scores.columns)}")

    # ── 2. Compute canopy height + CO2 ───────────────────────────────
    print("\n" + "-" * 65)
    print("  Step 1: Canopy Height & CO2 Carbon Stock")
    print("-" * 65)

    # Columns that compute_block_co2 will produce
    new_cols = [
        "canopy_area_m2", "canopy_area_source",
        "canopy_height_m", "canopy_height_source", "n_trees_est",
        "agb_kg", "carbon_stock_tonnes_co2e", "carbon_tons_sequestered",
        "carbon_model_source", "allometric_model",
    ]

    # Drop any pre-existing columns to avoid merge conflicts on re-runs
    for col in new_cols:
        if col in scores.columns:
            scores = scores.drop(columns=[col])

    blocks_gdf = None
    merged_path = MERGED_GEOJSON if MERGED_GEOJSON.exists() else None
    unet_path = UNET_TIF if UNET_TIF.exists() else None
    
    if COMPOSITE_TIF.exists():
        import rasterio

        with rasterio.open(str(COMPOSITE_TIF)) as src:
            raster_bounds = src.bounds
            
        boundary_geom = box(raster_bounds.left, raster_bounds.bottom, raster_bounds.right, raster_bounds.top)
        boundary_gdf = gpd.GeoDataFrame({"geometry": [boundary_geom]}, crs="EPSG:4326")
        
        grid = generate_block_grid(boundary_gdf)
        blocks_gdf = grid.merge(scores[["block_id"]], on="block_id", how="inner")

    enriched = compute_block_co2(
        scores,
        unet_tif=unet_path,
        merged_geojson=merged_path,
        blocks_gdf=blocks_gdf,
    )

    # ── 3. Merge back into scores CSV ─────────────────────────────────
    # Merge on block_id
    merged = scores.merge(
        enriched[["block_id"] + new_cols],
        on="block_id",
        how="left",
    )

    # Save carbon stock results to a SEPARATE file (do not overwrite UEHI scores)
    merged.to_csv(str(CARBON_OUTPUT_CSV), index=False)
    print(f"\n[Output] Carbon stock results saved to {CARBON_OUTPUT_CSV.resolve()}")
    print(f"  New columns added: {new_cols}")
    print(f"  NOTE: UEHI score files are NOT modified.")

    # Write provenance
    import hashlib
    import json
    from datetime import datetime
    import subprocess
    
    # Attempt to get git commit
    git_commit = "unknown"
    try:
        git_commit = subprocess.check_output(["git", "rev-parse", "HEAD"]).decode("utf-8").strip()
    except Exception:
        pass
        
    # Get height source info
    height_source_val = merged['canopy_height_source'].iloc[0] if not merged.empty else "unknown"
    is_fallback = "FALLBACK" in height_source_val

    provenance = {
        "pipeline_version": "Phase 4 Stage 1",
        "git_commit": git_commit,
        "processing_timestamp": datetime.utcnow().isoformat(),
        "canopy_class_id": 0,
        "block_grid_specification": "EPSG:32643",
        "grid_origin": "E=300000, N=2000000",
        "grid_size": "16x16 blocks (example)",
        "block_size": "250m x 250m",
        "unet_model_checksums": [
            "f6a1c4f266ec53e3b7203c105aa7da8245e96046cee500e8d3f536c2d5df7c22",
            "47709658f8ebc1d4582ec8604db5e65f38526ef9075ca254a6e92f9987fd3a40",
            "74275566a429ea81eec62194a8db84241e806ea8e11f2120dd077a56f13cfa15"
        ],
        "height_source": height_source_val,
        "height_source_mode": "production" if not is_fallback else "development/research",
        "fallback_status": is_fallback
    }
    
    if unet_path and unet_path.exists():
        import rasterio
        with rasterio.open(unet_path) as src:
            provenance["segmentation_raster_path"] = str(unet_path)
            provenance["crs"] = str(src.crs)
            provenance["spatial_resolution"] = src.res
            # grid size approximation from raster if needed, but keeping simple above
        
        with open(unet_path, "rb") as f:
            provenance["segmentation_raster_sha256"] = hashlib.sha256(f.read()).hexdigest()
            
    manifest_path = CARBON_OUTPUT_CSV.with_suffix('.json')
    with open(manifest_path, 'w') as f:
        json.dump(provenance, f, indent=2)
    print(f"  Provenance saved to: {manifest_path.resolve()}")

    # ── 4. Run planting recommender ──────────────────────────────────
    print("\n" + "-" * 65)
    print("  Step 2: Planting Site Recommendations")
    print("-" * 65)

    recommendations = recommend_planting_sites(
        blocks_df=merged,
        max_canopy_frac=0.15,
        max_imperv_frac=0.80,
        target_canopy_frac=0.30,
        top_n=10,
        output_path=str(RECOMMENDATIONS_CSV),
    )

    # ── 5. Summary ───────────────────────────────────────────────────
    print("\n" + "=" * 65)
    print("  SUMMARY")
    print("=" * 65)
    print(f"  Blocks with carbon data : {len(merged)}")
    print(f"  Carbon stock CO2e       : "
          f"{merged['carbon_stock_tonnes_co2e'].sum():.4f} tonnes")
    print(f"  Height data source      : "
          f"{merged['canopy_height_source'].iloc[0]}")
    print(f"  Carbon model source     : "
          f"{merged['carbon_model_source'].iloc[0]}")
    print(f"  Recommendations         : {len(recommendations)} blocks")
    if not recommendations.empty:
        print(f"  Additional stock potential: "
              f"{recommendations['additional_stock_co2e'].sum():.4f} tonnes")
    print(f"  NOTE: Carbon stock = standing biomass CO2e, not annual sequestration.")
    print(f"\n  Files written:")
    print(f"    {CARBON_OUTPUT_CSV.resolve()}")
    print(f"    {RECOMMENDATIONS_CSV.resolve()}")
    print("\nDone.")


if __name__ == "__main__":
    main()

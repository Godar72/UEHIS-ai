"""
Score Kothrud blocks using the UEHI scoring engine.

Pipeline
--------
1. Load merged GeoJSON (landcover + buildings + roads)
2. Tessellate the ROI into ~250m city blocks (grid cells)
3. Aggregate real & placeholder factor values per block
4. Compute entropy-based weights for the 7 base parameters
5. Apply canopy-temperature synergy (alpha=0.1)
6. Apply population impact multiplier (beta=0.3)
7. Score, classify risk, and save CSV

Placeholder factors are clearly logged.
"""

import sys, math
from pathlib import Path

import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from shapely.geometry import box

sys.path.insert(0, str(Path(__file__).resolve().parent))

from scoring.normalize import normalise_factor
from feature_engineering.unet import CLASS_NAMES

# ── Configuration ────────────────────────────────────────────────────────
MERGED_PATH   = Path("outputs/kothrud_merged.geojson")
COMPOSITE_TIF = Path("kothrud_pune_composite.tif")
SEG_TIF       = Path("outputs/kothrud_ndvi_segmentation.tif")
OUTPUT_CSV    = Path("outputs/kothrud_scores.csv")
OUTPUT_CSV_F  = Path("outputs/kothrud_scores_filtered.csv")

ALPHA = 0.1    # canopy-temperature synergy coefficient
BETA  = 0.3    # population impact multiplier coefficient
BLOCK_SIZE_M = 250  # approximate block dimension in metres

# ── Factor metadata ──────────────────────────────────────────────────────
FACTORS = {
    # name            direction    source
    "ndvi":                 ("positive", "REAL"),
    "tree_density":         ("positive", "REAL"),
    "biodiversity":         ("positive", "PLACEHOLDER"),
    "aqi":                  ("negative", "PLACEHOLDER"),
    "temperature":          ("negative", "PLACEHOLDER"),
    "impervious_surfaces":  ("negative", "REAL"),
    "water_availability":   ("positive", "PLACEHOLDER"),
    "population_exposure":  ("negative", "PLACEHOLDER"),
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


def entropy_weights(df, factor_cols):
    """
    Compute entropy-based weights from data variability.

    High-entropy (uniform) factors get lower weight;
    low-entropy (discriminating) factors get higher weight.
    """
    # Normalise each column to [0,1]
    normed = pd.DataFrame()
    for col in factor_cols:
        lo, hi = df[col].min(), df[col].max()
        if hi - lo > 0:
            normed[col] = (df[col] - lo) / (hi - lo)
        else:
            normed[col] = 0.0

    n = len(normed)
    if n <= 1:
        return {col: 1.0 / len(factor_cols) for col in factor_cols}

    # Proportions (add tiny epsilon to avoid log(0))
    eps = 1e-12
    p = normed.div(normed.sum(axis=0) + eps, axis=1) + eps

    # Shannon entropy for each factor
    k = 1.0 / math.log(n)  # normalisation constant
    entropy = {}
    for col in factor_cols:
        entropy[col] = -k * (p[col] * np.log(p[col])).sum()

    # Diversity = 1 - entropy  (higher diversity = more important)
    diversity = {col: max(1 - e, 0) for col, e in entropy.items()}
    total_d = sum(diversity.values()) or 1
    weights = {col: d / total_d for col, d in diversity.items()}

    return weights


# =====================================================================
# Main
# =====================================================================

def main():
    # ── 1. Load data ─────────────────────────────────────────────────────
    print("=" * 60)
    print("  UEHI Scoring Pipeline -- Kothrud, Pune")
    print("=" * 60)

    merged = gpd.read_file(str(MERGED_PATH))
    print(f"\n[Load] Merged GeoJSON: {len(merged)} features")
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

    block_records = []
    for _, block in grid.iterrows():
        block_geom = block.geometry
        bid = block.block_id

        # Clip landcover to block
        lc_in = lc[lc.intersects(block_geom)].copy()
        bldg_in = bldgs[bldgs.intersects(block_geom)]
        road_in = roads[roads.intersects(block_geom)]

        block_area = gpd.GeoSeries([block_geom], crs="EPSG:4326").to_crs(
            epsg=32643
        ).area.iloc[0]

        # ── REAL factors ─────────────────────────────────────────────────
        # 1. NDVI (mean from raster, sampled over block)
        # For simplicity, use the landcover NDVI stats from segmentation
        canopy_area = lc_in.loc[lc_in["class_id"] == 0, "area_m2"].sum()
        imperv_area = lc_in.loc[lc_in["class_id"] == 1, "area_m2"].sum()
        perv_area   = lc_in.loc[lc_in["class_id"] == 2, "area_m2"].sum()
        total_lc    = canopy_area + imperv_area + perv_area or 1

        # Canopy fraction as NDVI proxy (canopy ~0.5-0.8, imperv ~0.05, perv ~0.2)
        ndvi_est = (canopy_area * 0.55 + perv_area * 0.20 + imperv_area * 0.05) / total_lc

        # 2. Tree density (canopy fraction of total block area)
        tree_density = canopy_area / (block_area or 1)

        # 3. Impervious fraction (impervious lc + buildings + roads)
        bldg_area = 0
        if not bldg_in.empty:
            bldg_utm = bldg_in.to_crs(epsg=32643)
            bldg_area = bldg_utm.geometry.area.sum()

        road_area = 0
        if not road_in.empty:
            # Buffer roads by ~3m to get approximate area
            road_utm = road_in.to_crs(epsg=32643)
            road_area = road_utm.geometry.buffer(3).area.sum()

        imperv_total = imperv_area + bldg_area + road_area
        imperv_frac = min(imperv_total / (block_area or 1), 1.0)

        # ── PLACEHOLDER factors ──────────────────────────────────────────
        # Generate spatially-varying placeholders based on real data
        np.random.seed(hash(bid) % (2**31))

        # Biodiversity: correlate with canopy (more trees -> more biodiversity)
        biodiversity = 0.3 + 0.5 * tree_density + np.random.normal(0, 0.05)
        biodiversity = np.clip(biodiversity, 0, 1)

        # AQI: inversely correlate with greenness (50-200 range for Pune)
        aqi = 120 - 80 * tree_density + 40 * imperv_frac + np.random.normal(0, 10)
        aqi = np.clip(aqi, 30, 300)

        # Temperature (LST in C): correlate with impervious, anti-correlate with canopy
        temperature = 30 + 8 * imperv_frac - 5 * tree_density + np.random.normal(0, 1.5)
        temperature = np.clip(temperature, 25, 48)

        # Water availability: sparse in Kothrud (0-1 scale)
        water_avail = 0.1 + 0.2 * (1 - imperv_frac) + np.random.normal(0, 0.03)
        water_avail = np.clip(water_avail, 0, 1)

        # Population exposure (people/hectare): higher in dense built-up areas
        n_buildings = len(bldg_in)
        pop_density = 50 + 15 * n_buildings / max(block_area / 10000, 0.01)
        pop_density = np.clip(pop_density + np.random.normal(0, 20), 10, 800)

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
            # -- Factor columns --
            "ndvi": round(ndvi_est, 4),
            "tree_density": round(tree_density, 4),
            "biodiversity": round(biodiversity, 4),
            "aqi": round(aqi, 1),
            "temperature": round(temperature, 2),
            "impervious_surfaces": round(imperv_frac, 4),
            "water_availability": round(water_avail, 4),
            "population_exposure": round(pop_density, 1),
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

    # ── 4. Log real vs placeholder factors ───────────────────────────────
    print("\n[Factors] Data source per factor:")
    for name, (direction, source) in FACTORS.items():
        marker = "  [REAL]       " if source == "REAL" else "  [PLACEHOLDER]"
        print(f"{marker} {name:25s} ({direction})")

    # ── 5. Entropy-based weights ─────────────────────────────────────────
    factor_cols = list(FACTORS.keys())
    ew = entropy_weights(blocks, factor_cols)
    print("\n[Weights] Entropy-based weights (data-driven):")
    for col in factor_cols:
        source = FACTORS[col][1]
        print(f"  {col:25s}: {ew[col]:.4f}  ({source})")
    print(f"  {'SUM':25s}: {sum(ew.values()):.4f}")

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
    # High-population blocks get a penalty if score is low (amplifies urgency)
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
                    "impervious_surfaces", "temperature", "aqi",
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
        if count > 0:
            print(f"    {level:10s}: {count} blocks")

    # ── 12. Save CSV ─────────────────────────────────────────────────────
    OUTPUT_CSV.parent.mkdir(exist_ok=True)
    csv_cols = ["block_id", "block_row", "block_col", "block_area_m2",
                "n_buildings", "n_roads", "canopy_frac", "imperv_frac",
                "ndvi", "tree_density", "biodiversity", "aqi",
                "temperature", "impervious_surfaces", "water_availability",
                "population_exposure", "uehi_score", "risk_level"]
    blocks[csv_cols].to_csv(str(OUTPUT_CSV), index=False)
    print(f"\n[Output] Full scores saved to {OUTPUT_CSV.resolve()}")

    # Also save as the filtered CSV
    blocks[csv_cols].to_csv(str(OUTPUT_CSV_F), index=False)
    print(f"[Output] Filtered scores saved to {OUTPUT_CSV_F.resolve()}")
    print("Done.")


if __name__ == "__main__":
    main()

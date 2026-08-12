"""
Fetch OSM buildings + roads for Kothrud, Pune and merge with the
NDVI segmentation output into a single GeoDataFrame.

Output: outputs/kothrud_merged.geojson
"""

import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

sys.path.insert(0, str(Path(__file__).resolve().parent))

from data_ingestion.osm_features import fetch_building_footprints, fetch_road_network
from feature_engineering.overlay import vectorise_segmentation

# ── Configuration (same as ingestion step) ───────────────────────────────
LONGITUDE = 73.8077
LATITUDE  = 18.5074
BUFFER_M  = 2000  # 2 km

SEG_TIF = Path("outputs/kothrud_ndvi_segmentation.tif")
OUT_DIR = Path("outputs")
BUILDINGS_PATH = OUT_DIR / "kothrud_buildings.geojson"
ROADS_PATH     = OUT_DIR / "kothrud_roads.geojson"
MERGED_PATH    = OUT_DIR / "kothrud_merged.geojson"


def compute_bounds(lon: float, lat: float, buffer_m: float):
    """Approximate bounding box from a centre point + buffer in metres."""
    # ~111,320 m per degree latitude; longitude varies with cos(lat)
    import math
    lat_offset = buffer_m / 111_320
    lon_offset = buffer_m / (111_320 * math.cos(math.radians(lat)))
    west  = lon - lon_offset
    east  = lon + lon_offset
    south = lat - lat_offset
    north = lat + lat_offset
    return (west, south, east, north)


def main():
    bounds = compute_bounds(LONGITUDE, LATITUDE, BUFFER_M)
    print(f"[Config] Centre: {LATITUDE} N, {LONGITUDE} E")
    print(f"[Config] Buffer: {BUFFER_M / 1000:.0f} km")
    print(f"[Config] Bounds (W,S,E,N): {tuple(round(b, 6) for b in bounds)}")

    OUT_DIR.mkdir(exist_ok=True)

    # ── 1. Fetch OSM buildings ───────────────────────────────────────────
    print("\n--- Fetching building footprints ---")
    buildings = fetch_building_footprints(bounds, output_path=str(BUILDINGS_PATH))
    print(f"  Columns: {list(buildings.columns[:8])} ...")

    # ── 2. Fetch OSM roads ───────────────────────────────────────────────
    print("\n--- Fetching road network ---")
    roads = fetch_road_network(bounds, network_type="all", output_path=str(ROADS_PATH))
    print(f"  Columns: {list(roads.columns[:8])} ...")

    # ── 3. Vectorise segmentation ────────────────────────────────────────
    print("\n--- Vectorising segmentation ---")
    seg_gdf = vectorise_segmentation(SEG_TIF)

    # ── 4. Merge everything ──────────────────────────────────────────────
    print("\n--- Merging layers ---")

    # Tag each layer
    seg_gdf["feature_type"] = "landcover"
    seg_gdf["source"] = "ndvi_threshold"

    # Prepare buildings: keep a small set of useful columns + geometry
    bldg_cols = ["geometry"]
    for col in ["building", "name", "building:levels", "amenity", "height"]:
        if col in buildings.columns:
            bldg_cols.append(col)
    bldg_slim = buildings[bldg_cols].copy()
    bldg_slim["feature_type"] = "building"
    bldg_slim["source"] = "osm"

    # Spatial join: assign dominant land-cover class to each building
    if not seg_gdf.empty and not bldg_slim.empty:
        bldg_joined = gpd.sjoin(
            bldg_slim, seg_gdf[["geometry", "class_id", "class_name"]],
            how="left", predicate="intersects",
        )
        # If a building intersects multiple land-cover polygons, keep the
        # first match (largest overlap would require area calc; sjoin is
        # sufficient for this fallback workflow)
        bldg_joined = bldg_joined.drop_duplicates(subset="geometry", keep="first")
        bldg_joined.drop(columns=["index_right"], inplace=True, errors="ignore")
    else:
        bldg_joined = bldg_slim

    # Prepare roads: keep useful columns
    road_cols = ["geometry"]
    for col in ["highway", "name", "lanes", "maxspeed", "oneway", "surface"]:
        if col in roads.columns:
            road_cols.append(col)
    road_slim = roads[road_cols].copy()
    road_slim["feature_type"] = "road"
    road_slim["source"] = "osm"
    road_slim["class_id"] = 1        # roads are impervious
    road_slim["class_name"] = "impervious"

    # Concatenate all layers
    merged = gpd.GeoDataFrame(
        pd.concat([seg_gdf, bldg_joined, road_slim], ignore_index=True),
        crs=seg_gdf.crs,
    )

    # ── 5. Summary ───────────────────────────────────────────────────────
    print(f"\n{'='*55}")
    print(f"Merged GeoDataFrame: {len(merged)} features")
    print(f"  Landcover polygons : {len(seg_gdf):>6,}")
    print(f"  Building footprints: {len(bldg_joined):>6,}")
    print(f"  Road segments      : {len(road_slim):>6,}")
    print(f"{'='*55}")

    # Feature type breakdown
    print("\nFeature type counts:")
    for ft, count in merged["feature_type"].value_counts().items():
        print(f"  {ft:>12s}: {count:>6,}")

    # Land-cover class breakdown (across all features)
    print("\nLand-cover class distribution (all features with class_id):")
    classified = merged.dropna(subset=["class_id"])
    for cls_id in sorted(classified["class_id"].unique()):
        cls_name = classified.loc[classified["class_id"] == cls_id, "class_name"].iloc[0]
        count = int((classified["class_id"] == cls_id).sum())
        print(f"  {int(cls_id)} ({cls_name:>11s}): {count:>6,}")

    # ── 6. Save ──────────────────────────────────────────────────────────
    merged.to_file(str(MERGED_PATH), driver="GeoJSON")
    print(f"\n[Output] Saved to {MERGED_PATH.resolve()}")
    print("Done.")


if __name__ == "__main__":
    main()

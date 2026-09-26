"""
Fetch reproducible OSM water data for the Kothrud study area.

This script calls `fetch_water_bodies()` from `data_ingestion.osm_features`
to download water bodies and waterways from OpenStreetMap, clip them to the
Kothrud ROI, and save the result to `outputs/kothrud_water.geojson` with a
companion metadata JSON.

The existing water GeoJSON is backed up before replacement
(fetch → validate → replace pattern).

Usage
-----
    python run_data_fetch.py
"""

# Ensure UTF-8 output on Windows (OSM names may contain Devanagari/Marathi)
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")
import math
import json
import shutil
from pathlib import Path
from datetime import datetime, timezone

import geopandas as gpd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from data_ingestion.osm_features import fetch_water_bodies

# ── Configuration (same Kothrud ROI as run_osm_overlay.py) ────────────────
LONGITUDE = 73.8077
LATITUDE  = 18.5074
BUFFER_M  = 2000  # 2 km

ROI_NAME = "kothrud"
OUT_DIR  = Path("outputs")
WATER_PATH    = OUT_DIR / "kothrud_water.geojson"
METADATA_PATH = OUT_DIR / "kothrud_water_metadata.json"


def compute_bounds(lon: float, lat: float, buffer_m: float):
    """Approximate bounding box from a centre point + buffer in metres."""
    lat_offset = buffer_m / 111_320
    lon_offset = buffer_m / (111_320 * math.cos(math.radians(lat)))
    west  = lon - lon_offset
    east  = lon + lon_offset
    south = lat - lat_offset
    north = lat + lat_offset
    return (west, south, east, north)


def load_old_stats(path: Path) -> dict | None:
    """Load geometry statistics from the existing water GeoJSON (if any)."""
    if not path.exists():
        return None
    try:
        gdf = gpd.read_file(str(path))
        if gdf.empty:
            return {"total": 0, "polygon": 0, "linestring": 0,
                    "polygon_area_m2": 0.0, "line_length_m": 0.0}

        types = gdf.geometry.geom_type.value_counts().to_dict()

        # Area of polygons in EPSG:32643
        polys = gdf[gdf.geometry.geom_type.isin(["Polygon", "MultiPolygon"])]
        poly_area = 0.0
        if not polys.empty:
            poly_area = polys.to_crs(epsg=32643).geometry.area.sum()

        # Length of lines in EPSG:32643
        lines = gdf[gdf.geometry.geom_type.isin(["LineString", "MultiLineString"])]
        line_length = 0.0
        if not lines.empty:
            line_length = lines.to_crs(epsg=32643).geometry.length.sum()

        return {
            "total": len(gdf),
            "polygon": types.get("Polygon", 0),
            "multipolygon": types.get("MultiPolygon", 0),
            "linestring": types.get("LineString", 0),
            "multilinestring": types.get("MultiLineString", 0),
            "polygon_area_m2": poly_area,
            "line_length_m": line_length,
        }
    except Exception as exc:
        print(f"[Warning] Could not load old water file: {exc}")
        return None


def main():
    bounds = compute_bounds(LONGITUDE, LATITUDE, BUFFER_M)
    print("=" * 65)
    print("  OSM Water Data Ingestion — Kothrud, Pune")
    print("=" * 65)
    print(f"[Config] Centre  : {LATITUDE} N, {LONGITUDE} E")
    print(f"[Config] Buffer  : {BUFFER_M / 1000:.0f} km")
    print(f"[Config] Bounds  : (W={bounds[0]:.6f}, S={bounds[1]:.6f}, "
          f"E={bounds[2]:.6f}, N={bounds[3]:.6f})")
    print()

    OUT_DIR.mkdir(exist_ok=True)

    # ── 1. Capture old dataset stats ─────────────────────────────────────
    old_stats = load_old_stats(WATER_PATH)
    if old_stats:
        print("[Backup] Existing water file found — stats captured")
    else:
        print("[Backup] No existing water file found")

    # ── 2. Back up old file (if exists) ──────────────────────────────────
    backup_path = None
    if WATER_PATH.exists():
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = OUT_DIR / f"kothrud_water_backup_{ts}.geojson"
        shutil.copy2(str(WATER_PATH), str(backup_path))
        print(f"[Backup] Old file backed up to {backup_path}")

    # ── 3. Fetch new water data ──────────────────────────────────────────
    print("\n--- Fetching OSM water features ---\n")
    try:
        water_gdf = fetch_water_bodies(
            bounds,
            roi_name=ROI_NAME,
            output_path=str(WATER_PATH),
            metadata_path=str(METADATA_PATH),
        )
    except Exception as exc:
        print(f"\n[ERROR] Water ingestion failed: {exc}")
        if backup_path and backup_path.exists():
            # Restore the backup
            shutil.copy2(str(backup_path), str(WATER_PATH))
            print(f"[Recovery] Restored backup to {WATER_PATH}")
        sys.exit(1)

    # ── 4. Validation report ─────────────────────────────────────────────
    print("\n" + "=" * 65)
    print("  VALIDATION REPORT")
    print("=" * 65)

    geom_types = water_gdf.geometry.geom_type.value_counts().to_dict()
    polygon_count = geom_types.get("Polygon", 0)
    multipolygon_count = geom_types.get("MultiPolygon", 0)
    linestring_count = geom_types.get("LineString", 0)
    multilinestring_count = geom_types.get("MultiLineString", 0)

    print(f"\n  Total features       : {len(water_gdf)}")
    print(f"  Polygon              : {polygon_count}")
    print(f"  MultiPolygon         : {multipolygon_count}")
    print(f"  LineString           : {linestring_count}")
    print(f"  MultiLineString      : {multilinestring_count}")

    # Area & length in projected CRS
    polys = water_gdf[water_gdf.geometry.geom_type.isin(["Polygon", "MultiPolygon"])]
    lines = water_gdf[water_gdf.geometry.geom_type.isin(["LineString", "MultiLineString"])]

    poly_area_m2 = 0.0
    if not polys.empty:
        poly_area_m2 = polys.to_crs(epsg=32643).geometry.area.sum()
    print(f"\n  Total polygon area   : {poly_area_m2:,.2f} m²")
    print(f"                       : {poly_area_m2 / 1e6:,.6f} km²")

    line_length_m = 0.0
    if not lines.empty:
        line_length_m = lines.to_crs(epsg=32643).geometry.length.sum()
    print(f"  Total line length    : {line_length_m:,.2f} m")
    print(f"                       : {line_length_m / 1000:,.3f} km")

    # ROI coverage
    from shapely.geometry import box as shapely_box
    roi_polygon = shapely_box(*bounds)
    roi_area_m2 = gpd.GeoSeries([roi_polygon], crs="EPSG:4326").to_crs(
        epsg=32643
    ).area.iloc[0]
    coverage_pct = (poly_area_m2 / roi_area_m2 * 100) if roi_area_m2 > 0 else 0
    print(f"\n  ROI area             : {roi_area_m2:,.2f} m²")
    print(f"  Polygon ROI coverage : {coverage_pct:.4f}%")

    # Invalid / empty geometry check on the saved file
    n_invalid = (~water_gdf.geometry.is_valid).sum()
    n_empty = water_gdf.geometry.is_empty.sum()
    print(f"\n  Invalid geometries   : {n_invalid}")
    print(f"  Empty geometries     : {n_empty}")

    # Feature counts by OSM tag/category
    print("\n  Features by OSM category:")
    for tag_col in ["natural", "water", "waterway", "landuse"]:
        if tag_col in water_gdf.columns:
            vals = water_gdf[tag_col].dropna()
            if not vals.empty:
                for val, count in vals.value_counts().items():
                    print(f"    {tag_col}={val}: {count}")

    # Acquisition timestamp
    acq_time = "unknown"
    if METADATA_PATH.exists():
        with open(str(METADATA_PATH)) as f:
            meta = json.load(f)
            acq_time = meta.get("acquisition_timestamp_utc", "unknown")
    print(f"\n  Acquisition time     : {acq_time}")
    print(f"  Output file          : {WATER_PATH.resolve()}")
    print(f"  Metadata file        : {METADATA_PATH.resolve()}")

    # ── 5. Old vs New comparison ─────────────────────────────────────────
    print("\n" + "=" * 65)
    print("  OLD vs NEW DATASET COMPARISON")
    print("=" * 65)

    if old_stats:
        print(f"\n  OLD (previous kothrud_water.geojson):")
        print(f"    Total features     : {old_stats['total']}")
        print(f"    Polygon            : {old_stats.get('polygon', 0)}")
        print(f"    MultiPolygon       : {old_stats.get('multipolygon', 0)}")
        print(f"    LineString         : {old_stats.get('linestring', 0)}")
        print(f"    MultiLineString    : {old_stats.get('multilinestring', 0)}")
        print(f"    Polygon area       : {old_stats['polygon_area_m2']:,.2f} m²")
        print(f"    Line length        : {old_stats['line_length_m']:,.2f} m")

        print(f"\n  NEW (fetched from OSM):")
        print(f"    Total features     : {len(water_gdf)}")
        print(f"    Polygon            : {polygon_count}")
        print(f"    MultiPolygon       : {multipolygon_count}")
        print(f"    LineString         : {linestring_count}")
        print(f"    MultiLineString    : {multilinestring_count}")
        print(f"    Polygon area       : {poly_area_m2:,.2f} m²")
        print(f"    Line length        : {line_length_m:,.2f} m")

        # Deltas
        delta_features = len(water_gdf) - old_stats['total']
        delta_area = poly_area_m2 - old_stats['polygon_area_m2']
        delta_length = line_length_m - old_stats['line_length_m']
        print(f"\n  CHANGE:")
        print(f"    Features           : {delta_features:+d}")
        print(f"    Polygon area       : {delta_area:+,.2f} m²")
        print(f"    Line length        : {delta_length:+,.2f} m")
    else:
        print("\n  No previous dataset available for comparison.")
        print(f"\n  NEW (fetched from OSM):")
        print(f"    Total features     : {len(water_gdf)}")
        print(f"    Polygon            : {polygon_count}")
        print(f"    MultiPolygon       : {multipolygon_count}")
        print(f"    LineString         : {linestring_count}")
        print(f"    MultiLineString    : {multilinestring_count}")
        print(f"    Polygon area       : {poly_area_m2:,.2f} m²")
        print(f"    Line length        : {line_length_m:,.2f} m")

    # ── 6. Data completeness disclaimer ──────────────────────────────────
    print("\n" + "-" * 65)
    print("  IMPORTANT: OSM DATA COMPLETENESS DISCLAIMER")
    print("-" * 65)
    print("  The above counts reflect features MAPPED in OpenStreetMap.")
    print("  'Retrieved from OSM' ≠ 'all physical water present'.")
    print("  OSM completeness for water features in Kothrud/Pune cannot")
    print("  be assumed without independent ground-truth validation.")
    print("-" * 65)

    print("\nDone.")


if __name__ == "__main__":
    main()

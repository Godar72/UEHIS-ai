"""
data_ingestion/osm_features.py
──────────────────────────────
Uses OSMnx to download building footprints, road networks, and water
features for a given region and persist them as GeoJSON files.
"""

import os
import json
import math
from datetime import datetime, timezone

import geopandas as gpd
import osmnx as ox
import pandas as pd
from shapely.geometry import box, MultiPolygon, MultiLineString
from shapely.ops import unary_union
from shapely.validation import make_valid


class OSMDownloadError(Exception):
    """Raised when an OSMnx query returns no data or fails."""
    pass


# ---------------------------------------------------------------------------
# Building footprints
# ---------------------------------------------------------------------------

def fetch_building_footprints(
    bounds: tuple[float, float, float, float],
    output_path: str = "buildings.geojson",
) -> gpd.GeoDataFrame:
    """
    Download building footprints from OpenStreetMap for a bounding box.

    Parameters
    ----------
    bounds : tuple[float, float, float, float]
        ``(west, south, east, north)`` in WGS-84 degrees.
    output_path : str
        Destination GeoJSON file path.

    Returns
    -------
    geopandas.GeoDataFrame
        Building footprints with geometry and available OSM tags.

    Raises
    ------
    OSMDownloadError
        If no buildings are found in the specified region.
    """
    west, south, east, north = bounds
    polygon = box(west, south, east, north)

    try:
        buildings = ox.features_from_polygon(
            polygon,
            tags={"building": True},
        )
    except Exception as exc:
        raise OSMDownloadError(
            f"Failed to download building footprints: {exc}"
        ) from exc

    if buildings.empty:
        raise OSMDownloadError(
            f"No building footprints found within bounds {bounds}."
        )

    # Keep only polygon / multipolygon geometries (drop nodes)
    buildings = buildings[
        buildings.geometry.geom_type.isin(["Polygon", "MultiPolygon"])
    ].copy()

    if buildings.empty:
        raise OSMDownloadError(
            "Building data was returned but contained no polygon geometries."
        )

    # Ensure CRS is WGS-84
    if buildings.crs is None:
        buildings = buildings.set_crs(epsg=4326)

    # Persist to disk
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    buildings.to_file(output_path, driver="GeoJSON")
    print(
        f"[OSM] {len(buildings)} building footprints saved to "
        f"{os.path.abspath(output_path)}"
    )
    return buildings


# ---------------------------------------------------------------------------
# Road network
# ---------------------------------------------------------------------------

def fetch_road_network(
    bounds: tuple[float, float, float, float],
    network_type: str = "drive",
    output_path: str = "roads.geojson",
) -> gpd.GeoDataFrame:
    """
    Download the road network from OpenStreetMap for a bounding box.

    Parameters
    ----------
    bounds : tuple[float, float, float, float]
        ``(west, south, east, north)`` in WGS-84 degrees.
    network_type : str
        OSMnx network type — ``"drive"``, ``"walk"``, ``"bike"``, or ``"all"``
        (default ``"drive"``).
    output_path : str
        Destination GeoJSON file path for the edges (road segments).

    Returns
    -------
    geopandas.GeoDataFrame
        Road network edges with geometry and OSM attributes.

    Raises
    ------
    OSMDownloadError
        If no roads are found in the specified region.
    """
    west, south, east, north = bounds
    polygon = box(west, south, east, north)

    try:
        graph = ox.graph_from_polygon(
            polygon,
            network_type=network_type,
            simplify=True,
        )
    except Exception as exc:
        raise OSMDownloadError(
            f"Failed to download road network: {exc}"
        ) from exc

    # Convert graph edges to GeoDataFrame
    edges = ox.graph_to_gdfs(graph, nodes=False, edges=True)

    if edges.empty:
        raise OSMDownloadError(
            f"No road edges found within bounds {bounds} "
            f"for network type '{network_type}'."
        )

    # Persist to disk
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    edges.to_file(output_path, driver="GeoJSON")
    print(
        f"[OSM] {len(edges)} road segments ({network_type}) saved to "
        f"{os.path.abspath(output_path)}"
    )
    return edges


# ---------------------------------------------------------------------------
# Water bodies & waterways
# ---------------------------------------------------------------------------

# OSM tag groups for water feature retrieval
WATER_TAGS_POLYGON = {
    "natural": "water",
}
WATER_TAGS_LANDUSE = {
    "landuse": ["reservoir", "basin"],
}
WATER_TAGS_WATERWAY_POLYGON = {
    "waterway": "riverbank",          # legacy tag, still mapped in some areas
}
WATER_TAGS_WATERWAY_LINE = {
    "waterway": ["river", "stream", "canal", "drain", "ditch"],
}

# Provenance attributes to preserve from OSM (missing attrs become None)
_WATER_PROVENANCE_COLS = [
    "natural", "water", "waterway", "landuse", "name",
]


def _safe_get_col(gdf: gpd.GeoDataFrame, col: str) -> pd.Series:
    """Return a column from a GeoDataFrame, or None-filled Series if absent."""
    if col in gdf.columns:
        return gdf[col]
    return pd.Series([None] * len(gdf), index=gdf.index, name=col)


def _extract_element_info(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Extract osm_id and element_type from OSMnx multi-index.

    OSMnx returns features with a MultiIndex whose level names vary
    by version (e.g. ``('element_type', 'osmid')`` or ``('element', 'id')``).
    This helper flattens that into ``osm_id`` and ``element_type`` columns.
    """
    out = gdf.copy()
    if isinstance(out.index, pd.MultiIndex):
        out = out.reset_index()
        # Map known OSMnx index level names to our standard names
        rename_map = {}
        for col in out.columns:
            cl = col.lower()
            if cl in ("osmid", "id") and "osm_id" not in rename_map.values():
                rename_map[col] = "osm_id"
            elif cl in ("element_type", "element") and "element_type" not in rename_map.values():
                rename_map[col] = "element_type"
        if rename_map:
            out = out.rename(columns=rename_map)
    else:
        out = out.reset_index(drop=True)
    # Ensure columns exist even if not found in the index
    if "osm_id" not in out.columns:
        out["osm_id"] = None
    if "element_type" not in out.columns:
        out["element_type"] = None
    return out


def _query_osm_water(roi_polygon, tags: dict, label: str) -> gpd.GeoDataFrame:
    """
    Query OSMnx for features matching *tags* within *roi_polygon*.

    Returns an empty GeoDataFrame (with a geometry column) on failure
    so that callers can safely concatenate results.
    """
    try:
        gdf = ox.features_from_polygon(roi_polygon, tags=tags)
        print(f"  [OSM] {label}: {len(gdf)} raw features returned")
        return gdf
    except Exception as exc:
        print(f"  [OSM] {label}: query returned no data ({exc})")
        return gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")


def fetch_water_bodies(
    bounds: tuple[float, float, float, float],
    roi_name: str = "study_area",
    output_path: str = "water.geojson",
    metadata_path: str | None = None,
) -> gpd.GeoDataFrame:
    """
    Download water bodies and waterways from OpenStreetMap for a bounding box.

    Queries multiple OSM tag groups to retrieve:
      - Polygonal surface water (natural=water and subtypes)
      - Reservoir / basin landuse polygons
      - Legacy riverbank polygons
      - Linear waterways (river, stream, canal, drain, ditch)

    Geometry types are preserved: polygons stay as polygons, lines stay as
    lines.  No buffering of lines into polygons is performed.

    Parameters
    ----------
    bounds : tuple[float, float, float, float]
        ``(west, south, east, north)`` in WGS-84 degrees.
    roi_name : str
        Human-readable name for the ROI (used in logging & metadata).
    output_path : str
        Destination GeoJSON file path.
    metadata_path : str or None
        Path for the companion metadata JSON.  If ``None``, derived from
        *output_path* by appending ``_metadata.json``.

    Returns
    -------
    geopandas.GeoDataFrame
        Water features with geometry and provenance attributes.

    Raises
    ------
    OSMDownloadError
        If all queries fail or return zero valid features.
    """
    acquisition_time = datetime.now(timezone.utc)
    west, south, east, north = bounds
    roi_polygon = box(west, south, east, north)

    print(f"[Water] Fetching OSM water features for '{roi_name}'")
    print(f"[Water] Bounds (W,S,E,N): ({west:.6f}, {south:.6f}, "
          f"{east:.6f}, {north:.6f})")

    # ── 1. Query OSM for each tag group ──────────────────────────────────
    all_tags_queried = {}
    frames = []

    for tags, label in [
        (WATER_TAGS_POLYGON,          "natural=water"),
        (WATER_TAGS_LANDUSE,          "landuse=reservoir|basin"),
        (WATER_TAGS_WATERWAY_POLYGON, "waterway=riverbank"),
        (WATER_TAGS_WATERWAY_LINE,    "waterway=river|stream|canal|drain|ditch"),
    ]:
        gdf = _query_osm_water(roi_polygon, tags, label)
        all_tags_queried[label] = tags
        if not gdf.empty:
            frames.append(gdf)

    if not frames:
        raise OSMDownloadError(
            f"No water features found within bounds {bounds} "
            f"for ROI '{roi_name}'."
        )

    # ── 2. Combine & extract provenance ──────────────────────────────────
    combined = pd.concat(frames, ignore_index=False)
    combined = _extract_element_info(combined)

    # Keep only geometry + provenance columns
    keep_cols = ["geometry", "osm_id", "element_type"]
    for col in _WATER_PROVENANCE_COLS:
        keep_cols.append(col)

    out_cols = {}
    for col in keep_cols:
        if col == "geometry":
            continue
        out_cols[col] = _safe_get_col(combined, col)

    water = gpd.GeoDataFrame(out_cols, geometry=combined.geometry, crs=combined.crs)

    # Flatten list-valued cells (OSMnx sometimes returns lists for tags)
    for col in _WATER_PROVENANCE_COLS:
        if col in water.columns:
            water[col] = water[col].apply(
                lambda v: v[0] if isinstance(v, list) and len(v) > 0 else v
            )

    print(f"[Water] Combined: {len(water)} raw features before cleaning")

    # ── 3. Explode GeometryCollections ───────────────────────────────────
    exploded_rows = []
    for idx, row in water.iterrows():
        geom = row.geometry
        if geom is None or geom.is_empty:
            continue
        if geom.geom_type == "GeometryCollection":
            for part in geom.geoms:
                new_row = row.copy()
                new_row["geometry"] = part
                exploded_rows.append(new_row)
        else:
            exploded_rows.append(row)

    if exploded_rows:
        water = gpd.GeoDataFrame(exploded_rows, crs=water.crs)
    else:
        raise OSMDownloadError(
            f"All water features were empty GeometryCollections "
            f"for ROI '{roi_name}'."
        )

    # ── 4. Keep only relevant geometry types ─────────────────────────────
    valid_types = {"Polygon", "MultiPolygon", "LineString", "MultiLineString"}
    water = water[water.geometry.geom_type.isin(valid_types)].copy()

    if water.empty:
        raise OSMDownloadError(
            f"No Polygon or LineString water features found for "
            f"ROI '{roi_name}' after filtering geometry types."
        )

    # ── 5. Repair & validate geometries ──────────────────────────────────
    n_invalid_before = (~water.geometry.is_valid).sum()
    empty_before = water.geometry.is_empty.sum()

    # Attempt repair
    water["geometry"] = water.geometry.apply(
        lambda g: make_valid(g) if g is not None and not g.is_valid else g
    )

    # Drop still-invalid or empty geometries
    valid_mask = water.geometry.apply(
        lambda g: g is not None and not g.is_empty and g.is_valid
    )
    n_dropped_invalid = (~valid_mask).sum()
    water = water[valid_mask].copy()

    # After repair, some geometries may have changed type (e.g. Polygon → GeometryCollection)
    # Re-filter to valid types
    water = water[water.geometry.geom_type.isin(valid_types)].copy()

    print(f"[Water] Geometry cleaning: {n_invalid_before} invalid found, "
          f"{n_dropped_invalid} removed after repair attempt")

    # ── 6. Clip / intersect with ROI ─────────────────────────────────────
    clipped_geoms = []
    for geom in water.geometry:
        try:
            clipped = geom.intersection(roi_polygon)
            clipped_geoms.append(clipped)
        except Exception:
            clipped_geoms.append(geom)  # keep original if intersection fails

    water["geometry"] = clipped_geoms

    # Drop features that became empty after clipping
    water = water[~water.geometry.is_empty].copy()

    # Re-filter geometry types (intersection can produce GeometryCollections)
    final_rows = []
    for idx, row in water.iterrows():
        geom = row.geometry
        if geom.geom_type == "GeometryCollection":
            for part in geom.geoms:
                if part.geom_type in valid_types and not part.is_empty:
                    new_row = row.copy()
                    new_row["geometry"] = part
                    final_rows.append(new_row)
        elif geom.geom_type in valid_types:
            final_rows.append(row)

    if final_rows:
        water = gpd.GeoDataFrame(final_rows, crs=water.crs).reset_index(drop=True)
    else:
        raise OSMDownloadError(
            f"No water features remain after clipping to ROI '{roi_name}'."
        )

    # ── 7. Remove exact duplicate geometries ─────────────────────────────
    n_before_dedup = len(water)
    water["_wkt"] = water.geometry.apply(lambda g: g.wkt)
    water = water.drop_duplicates(subset="_wkt", keep="first").copy()
    water = water.drop(columns=["_wkt"])
    n_duplicates = n_before_dedup - len(water)
    print(f"[Water] Duplicates removed: {n_duplicates}")

    # ── 8. Ensure CRS is EPSG:4326 ──────────────────────────────────────
    if water.crs is None:
        water = water.set_crs(epsg=4326)
    elif water.crs.to_epsg() != 4326:
        water = water.to_crs(epsg=4326)

    water = water.reset_index(drop=True)

    # ── 9. Compute summary statistics ────────────────────────────────────
    geom_types = water.geometry.geom_type.value_counts().to_dict()
    polygon_count = geom_types.get("Polygon", 0)
    multipolygon_count = geom_types.get("MultiPolygon", 0)
    linestring_count = geom_types.get("LineString", 0)
    multilinestring_count = geom_types.get("MultiLineString", 0)
    total_features = len(water)

    print(f"\n[Water] ── Results for '{roi_name}' ──")
    print(f"  Total features     : {total_features}")
    print(f"  Polygon            : {polygon_count}")
    print(f"  MultiPolygon       : {multipolygon_count}")
    print(f"  LineString         : {linestring_count}")
    print(f"  MultiLineString    : {multilinestring_count}")

    # ── 10. Persist GeoJSON ──────────────────────────────────────────────
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    water.to_file(output_path, driver="GeoJSON", encoding="utf-8")
    print(f"\n[Water] GeoJSON saved to {os.path.abspath(output_path)}")

    # ── 11. Write companion metadata JSON ────────────────────────────────
    if metadata_path is None:
        base, _ = os.path.splitext(output_path)
        metadata_path = base + "_metadata.json"

    metadata = {
        "source": "OpenStreetMap",
        "acquisition_timestamp_utc": acquisition_time.isoformat(),
        "roi_name": roi_name,
        "roi_bounds_wgs84": {
            "west": west, "south": south, "east": east, "north": north,
        },
        "crs": "EPSG:4326",
        "osm_tags_queried": {k: str(v) for k, v in all_tags_queried.items()},
        "total_features": total_features,
        "polygon_count": polygon_count,
        "multipolygon_count": multipolygon_count,
        "linestring_count": linestring_count,
        "multilinestring_count": multilinestring_count,
        "invalid_geometries_removed": int(n_dropped_invalid),
        "empty_geometries_removed": int(empty_before),
        "duplicate_geometries_removed": int(n_duplicates),
        "notes": (
            "This dataset was retrieved from OpenStreetMap via OSMnx. "
            "OSM data completeness cannot be assumed — the features "
            "represent what was mapped in OSM at acquisition time, which "
            "may differ from actual physical water presence."
        ),
    }

    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    print(f"[Water] Metadata saved to {os.path.abspath(metadata_path)}")

    return water


# ---------------------------------------------------------------------------
# Convenience entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Quick smoke-test: small area in Bengaluru
    roi_bounds = (77.58, 12.95, 77.62, 12.99)

    print("— Fetching building footprints —")
    buildings_gdf = fetch_building_footprints(
        roi_bounds,
        output_path="output/buildings.geojson",
    )
    print(f"  Columns: {list(buildings_gdf.columns[:10])} ...")

    print("\n— Fetching road network —")
    roads_gdf = fetch_road_network(
        roi_bounds,
        network_type="drive",
        output_path="output/roads.geojson",
    )
    print(f"  Columns: {list(roads_gdf.columns[:10])} ...")

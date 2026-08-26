"""
feature_engineering/overlay.py
──────────────────────────────
Vectorises the U-Net segmentation raster and merges it with OSM building
footprints into a single GeoDataFrame for downstream UEHI scoring.
"""

from pathlib import Path

import numpy as np
import geopandas as gpd
import rasterio
from rasterio.features import shapes
from shapely.geometry import shape

from feature_engineering.unet import CLASS_NAMES


# ---------------------------------------------------------------------------
# Vectorise segmentation raster
# ---------------------------------------------------------------------------

def vectorise_segmentation(
    segmentation_path: str | Path,
) -> gpd.GeoDataFrame:
    """
    Convert a classified GeoTIFF (uint8 class IDs) into polygons.

    Parameters
    ----------
    segmentation_path : str | Path
        Path to the single-band segmentation GeoTIFF produced by
        :func:`predict.predict_composite`.

    Returns
    -------
    geopandas.GeoDataFrame
        Polygons with columns ``class_id`` (int) and ``class_name`` (str).
    """
    with rasterio.open(segmentation_path) as src:
        class_map = src.read(1)
        transform = src.transform
        crs = src.crs

    # Generate (geometry, class_id) pairs — skip nodata (255)
    mask = class_map != 255
    records = []
    for geom, value in shapes(class_map, mask=mask, transform=transform):
        class_id = int(value)
        records.append({
            "geometry": shape(geom),
            "class_id": class_id,
            "class_name": CLASS_NAMES.get(class_id, "unknown"),
        })

    if not records:
        print("[Overlay] Warning: segmentation raster produced no polygons.")
        return gpd.GeoDataFrame(
            columns=["geometry", "class_id", "class_name"],
            crs=crs,
        )

    gdf = gpd.GeoDataFrame(records, crs=crs)
    print(f"[Overlay] Vectorised {len(gdf)} polygons from segmentation raster.")
    return gdf


# ---------------------------------------------------------------------------
# Merge with OSM buildings
# ---------------------------------------------------------------------------

def merge_with_buildings(
    segmentation_path: str | Path,
    buildings_path: str | Path,
    output_path: str | None = None,
) -> gpd.GeoDataFrame:
    """
    Overlay the segmentation polygons with OSM building footprints.

    Each building polygon is enriched with the **dominant** land-cover class
    that intersects it (by area).  Non-building land-cover polygons are also
    retained so the full spatial extent is preserved.

    Parameters
    ----------
    segmentation_path : str | Path
        Path to the classified GeoTIFF.
    buildings_path : str | Path
        Path to the buildings GeoJSON produced by
        :func:`data_ingestion.osm_features.fetch_building_footprints`.
    output_path : str | None
        Optional path to save the merged GeoDataFrame as GeoJSON.

    Returns
    -------
    geopandas.GeoDataFrame
        Merged frame with columns:

        * ``class_id``, ``class_name`` — land-cover class
        * ``is_building`` — boolean flag
        * All original OSM building attributes (where applicable)
    """
    # Vectorise the segmentation raster
    seg_gdf = vectorise_segmentation(segmentation_path)

    # Load building footprints
    bldg_gdf = gpd.read_file(buildings_path)

    # Ensure matching CRS
    if bldg_gdf.crs != seg_gdf.crs:
        bldg_gdf = bldg_gdf.to_crs(seg_gdf.crs)

    # ── Spatial join: assign dominant class to each building ────────────
    if not bldg_gdf.empty and not seg_gdf.empty:
        # Intersection overlay — produces fragments where buildings
        # overlap different land-cover polygons
        overlay = gpd.overlay(bldg_gdf, seg_gdf, how="intersection")

        if not overlay.empty:
            # Compute area of each fragment
            overlay["_frag_area"] = overlay.geometry.area

            # Keep the fragment with the largest area per building
            # Use the building's original index as grouping key
            if "osmid" in overlay.columns:
                group_col = "osmid"
            else:
                # Fallback: use original building geometry WKT as key
                bldg_gdf = bldg_gdf.copy()
                bldg_gdf["_bldg_wkt"] = bldg_gdf.geometry.apply(lambda g: g.wkt)
                overlay["_bldg_wkt"] = overlay.geometry.apply(
                    lambda g: g.wkt  # approximate — fine for grouping
                )
                group_col = "_bldg_wkt"

            idx_max = overlay.groupby(group_col)["_frag_area"].idxmax()
            dominant = overlay.loc[idx_max].copy()
            dominant.drop(columns=["_frag_area"], inplace=True, errors="ignore")

            # Restore original building geometry (not the clipped fragment)
            if group_col == "osmid":
                dominant = dominant.set_index("osmid")
                dominant["geometry"] = bldg_gdf.set_index("osmid").loc[
                    dominant.index, "geometry"
                ]
                dominant = dominant.reset_index()

            dominant["is_building"] = True
        else:
            dominant = gpd.GeoDataFrame()
    else:
        dominant = gpd.GeoDataFrame()

    # ── Combine buildings + non-building land-cover ─────────────────────
    seg_gdf["is_building"] = False
    merged = gpd.GeoDataFrame(
        data=__import__("pandas").concat([dominant, seg_gdf], ignore_index=True),
        crs=seg_gdf.crs,
    )

    print(
        f"[Overlay] Merged GeoDataFrame: {len(merged)} features "
        f"({dominant.__len__() if not dominant.empty else 0} buildings, "
        f"{len(seg_gdf)} land-cover polygons)."
    )

    # Optionally save to disk
    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        merged.to_file(output_path, driver="GeoJSON")
        print(f"[Overlay] Saved to {Path(output_path).resolve()}")

    return merged

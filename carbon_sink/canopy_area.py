"""
Per-block canopy area (m²) from Landsat 8 segmentation landcover.

Canopy area for carbon stock is the sum of intersection areas:

    area(block ∩ canopy_polygon)   in EPSG:32643

for each landcover polygon with class_id == 0 (canopy).

Canopy polygons in the merged GeoJSON are non-overlapping within class 0,
so summing per-polygon intersections does not double-count canopy.

Fallback (scores CSV only): ``tree_density × block_area_m2`` reproduces the
UEHI scoring table encoding of canopy area. That scoring step uses the
full area of intersecting landcover polygons (not block-clipped area);
prefer merged GeoJSON + block geometries for carbon calculations.
"""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

CANOPY_CLASS_ID = 0
CANOPY_AREA_SOURCE_LANDCOVER = (
    "legacy_landsat_polygon_baseline"
)
CANOPY_AREA_SOURCE_RASTER = "unet_raster_production"
CANOPY_AREA_SOURCE_SCORES = "tree_density_x_block_area_m2"


def canopy_area_m2_from_score_columns(blocks_df: pd.DataFrame) -> np.ndarray:
    """
    Recover canopy area from UEHI block scores (``tree_density`` encoding).

    Requires ``tree_density`` and ``block_area_m2`` from the standard block schema.
    """
    missing = {"tree_density", "block_area_m2"} - set(blocks_df.columns)
    if missing:
        raise ValueError(
            f"Cannot derive canopy_area_m2 from scores: missing columns {sorted(missing)}"
        )
    return blocks_df["tree_density"].to_numpy(dtype=float) * blocks_df[
        "block_area_m2"
    ].to_numpy(dtype=float)


def _sum_block_canopy_intersection_area_m2(
    block_geom_utm,
    canopy_utm: gpd.GeoDataFrame,
) -> float:
    """Sum EPSG:32643 areas of block ∩ each canopy polygon."""
    candidates = canopy_utm[canopy_utm.intersects(block_geom_utm)]
    if candidates.empty:
        return 0.0
    return float(
        sum(
            block_geom_utm.intersection(geom).area
            for geom in candidates.geometry
        )
    )


def aggregate_canopy_area_m2_from_merged(
    blocks_gdf: gpd.GeoDataFrame,
    merged_geojson: str | Path,
) -> pd.DataFrame:
    """
    Sum block-clipped canopy area per spatial block (EPSG:32643).

    Geometry operation (per block, per canopy polygon)::

        intersection(block_geometry, canopy_polygon).area

    Parameters
    ----------
    blocks_gdf :
        GeoDataFrame with ``block_id`` and block polygon geometry (EPSG:4326).
    merged_geojson :
        Merged features GeoJSON with ``feature_type`` and ``class_id`` columns.
    """
    merged_path = Path(merged_geojson)
    if not merged_path.exists():
        raise FileNotFoundError(f"Merged GeoJSON not found: {merged_path.resolve()}")

    merged = gpd.read_file(str(merged_path))
    lc = merged[merged["feature_type"] == "landcover"].copy()
    if lc.empty:
        raise ValueError(f"No landcover features in {merged_path}")

    blocks = blocks_gdf[["block_id", "geometry"]].copy()
    if blocks.crs is None:
        blocks = blocks.set_crs("EPSG:4326")

    blocks_utm = blocks.to_crs(epsg=32643)
    lc_utm = lc.to_crs(epsg=32643)
    canopy_utm = lc_utm[lc_utm["class_id"] == CANOPY_CLASS_ID].copy()

    records = []
    for _, block in blocks_utm.iterrows():
        records.append(
            {
                "block_id": block.block_id,
                "canopy_area_m2": _sum_block_canopy_intersection_area_m2(
                    block.geometry,
                    canopy_utm,
                ),
            }
        )

    return pd.DataFrame(records)


def aggregate_canopy_area_m2_from_raster(
    blocks_gdf: gpd.GeoDataFrame,
    unet_tif: str | Path,
) -> pd.DataFrame:
    """
    Calculate canopy area exactly using block-local raster windows.
    For each block, reads the corresponding window from the raster,
    extracts exact class 0 polygon footprints, and computes the 
    intersection area in EPSG:32643.
    """
    unet_path = Path(unet_tif)
    if not unet_path.exists():
        raise FileNotFoundError(f"U-Net raster not found: {unet_path.resolve()}")

    import rasterio
    from rasterio.mask import mask
    from rasterio.features import shapes, geometry_mask
    import pyproj
    from shapely.ops import transform
    from shapely.geometry import shape

    if blocks_gdf.crs is None:
        blocks_gdf = blocks_gdf.set_crs("EPSG:32643")
    elif blocks_gdf.crs.to_string() != "EPSG:32643":
        blocks_gdf = blocks_gdf.to_crs("EPSG:32643")

    records = []
    with rasterio.open(unet_path) as src:
        nodata = src.nodata if src.nodata is not None else 255
        raster_crs = src.crs.to_string() if src.crs else "EPSG:4326"
        
        if raster_crs != "EPSG:32643":
            project_to_raster = pyproj.Transformer.from_crs("EPSG:32643", raster_crs, always_xy=True).transform
            project_to_32643 = pyproj.Transformer.from_crs(raster_crs, "EPSG:32643", always_xy=True).transform
        else:
            project_to_raster = None
            project_to_32643 = None
        
        for idx, row in blocks_gdf.iterrows():
            geom_32643 = row.geometry
            if project_to_raster:
                geom_raster = transform(project_to_raster, geom_32643)
            else:
                geom_raster = geom_32643
            
            try:
                # Use all_touched=True to ensure we capture any canopy pixel that slightly overlaps
                out_image, out_transform = mask(src, [geom_raster], crop=True, all_touched=True)
                
                # Generate a strict geometry mask to count exactly how many pixels touch the block
                inside_mask = geometry_mask([geom_raster], out_shape=out_image[0].shape, 
                                            transform=out_transform, all_touched=True, invert=True)
                
                valid_data_mask = (out_image[0] != nodata) & inside_mask
                canopy_mask = (out_image[0] == CANOPY_CLASS_ID) & inside_mask
                
                c_cnt = int(canopy_mask.sum())
                v_cnt = int(valid_data_mask.sum())
                t_cnt = int(inside_mask.sum())
                comp = v_cnt / t_cnt if t_cnt > 0 else 0.0
                
                clipped_area = 0.0
                if c_cnt > 0:
                    results = (
                        {"properties": {"val": v}, "geometry": s}
                        for i, (s, v) in enumerate(
                            shapes(out_image[0], mask=canopy_mask, transform=out_transform)
                        )
                    )
                    
                    for r in results:
                        poly_raster = shape(r["geometry"])
                        if project_to_32643:
                            poly_32643 = transform(project_to_32643, poly_raster)
                        else:
                            poly_32643 = poly_raster
                        inter = poly_32643.intersection(geom_32643)
                        clipped_area += inter.area

            except ValueError:
                c_cnt = 0
                v_cnt = 0
                comp = 0.0
                clipped_area = 0.0
                
            records.append({
                "block_id": row["block_id"],
                "block_area_m2": float(geom_32643.area),
                "canopy_pixel_count": c_cnt,
                "canopy_area_m2": float(clipped_area),
                "canopy_area_source": CANOPY_AREA_SOURCE_RASTER,
                "valid_pixel_count": v_cnt,
                "canopy_completeness": float(comp),
            })

    return pd.DataFrame(records)


def attach_canopy_area_m2(
    blocks_df: pd.DataFrame,
    *,
    unet_tif: str | Path | None = None,
    merged_geojson: str | Path | None = None,
    blocks_gdf: gpd.GeoDataFrame | None = None,
) -> tuple[pd.DataFrame, str]:
    """
    Add ``canopy_area_m2`` to a block table without modifying UEHI score columns.
    
    For Pune Production: U-Net Raster is the sole source.
    """
    result = blocks_df.copy()

    if "canopy_area_m2" in result.columns:
        return result, "input_canopy_area_m2"

    if unet_tif is not None and blocks_gdf is not None:
        canopy_df = aggregate_canopy_area_m2_from_raster(blocks_gdf, unet_tif)
        merge_cols = [c for c in canopy_df.columns if c not in result.columns or c == "block_id"]
        result = result.merge(canopy_df[merge_cols], on="block_id", how="left")
        result["canopy_area_m2"] = result["canopy_area_m2"].fillna(0.0)
        return result, CANOPY_AREA_SOURCE_RASTER

    if merged_geojson is not None and blocks_gdf is not None:
        # Retain for regression testing ONLY
        canopy_df = aggregate_canopy_area_m2_from_merged(blocks_gdf, merged_geojson)
        result = result.merge(canopy_df, on="block_id", how="left")
        result["canopy_area_m2"] = result["canopy_area_m2"].fillna(0.0)
        if result["canopy_area_m2"].isna().any():
            missing = result.loc[result["canopy_area_m2"].isna(), "block_id"].tolist()
            raise ValueError(f"Canopy area missing for blocks after landcover aggregate: {missing[:5]}")
        return result, CANOPY_AREA_SOURCE_LANDCOVER

    # For Pune production, we MUST fail if no raster was provided
    # Do not silently fall back to tree_density * block_area
    import os
    if os.environ.get("UEHIS_ALLOW_LEGACY_CANOPY_FALLBACK") == "1":
        result["canopy_area_m2"] = canopy_area_m2_from_score_columns(result)
        return result, CANOPY_AREA_SOURCE_SCORES
        
    raise RuntimeError("Pune production requires a valid unet_tif for canopy area. Legacy fallbacks are disabled.")

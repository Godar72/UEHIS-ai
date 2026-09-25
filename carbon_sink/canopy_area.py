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
    Calculate canopy area from U-Net raster segmentation (class_id == 0).
    Uses rasterize and bincount for vectorized O(N) aggregation.
    """
    unet_path = Path(unet_tif)
    if not unet_path.exists():
        raise FileNotFoundError(f"U-Net raster not found: {unet_path.resolve()}")

    import rasterio
    from rasterio.features import rasterize

    with rasterio.open(unet_path) as src:
        unet_data = src.read(1)
        prof = src.profile
        nodata = src.nodata if src.nodata is not None else 255
        pixel_area_m2 = prof['transform'][0] * abs(prof['transform'][4])
        if prof['crs'].is_geographic:
            import pyproj
            from shapely.geometry import box
            from shapely.ops import transform
            geom = box(
                prof['transform'][2], 
                prof['transform'][5] - abs(prof['transform'][4]),
                prof['transform'][2] + prof['transform'][0], 
                prof['transform'][5]
            )
            project = pyproj.Transformer.from_crs(prof['crs'], "EPSG:32643", always_xy=True).transform
            pixel_area_m2 = transform(project, geom).area

    if blocks_gdf.crs != prof['crs']:
        blocks_gdf = blocks_gdf.to_crs(prof['crs'])
        
    shapes_gen = ((geom, idx) for idx, geom in enumerate(blocks_gdf.geometry))
    try:
        block_idx_arr = rasterize(
            shapes_gen, 
            out_shape=(prof['height'], prof['width']), 
            transform=prof['transform'], 
            fill=-1, 
            dtype=np.int32, 
            all_touched=False
        )
    except ValueError:
        block_idx_arr = np.full((prof['height'], prof['width']), -1, dtype=np.int32)

    valid_mask = (block_idx_arr >= 0) & (unet_data != nodata)
    valid_bidx = block_idx_arr[valid_mask]
    valid_data = unet_data[valid_mask]
    
    num_blocks = len(blocks_gdf)
    c_cnt = np.bincount(valid_bidx[valid_data == CANOPY_CLASS_ID], minlength=num_blocks)
    v_cnt = np.bincount(valid_bidx, minlength=num_blocks)
    t_cnt = np.bincount(block_idx_arr[block_idx_arr >= 0], minlength=num_blocks)
    
    with np.errstate(divide='ignore', invalid='ignore'):
        comp = np.where(t_cnt > 0, v_cnt / t_cnt, 0.0)

    canopy_area_m2 = c_cnt * pixel_area_m2

    records = []
    for idx, row in blocks_gdf.iterrows():
        records.append({
            "block_id": row["block_id"],
            "block_area_m2": float(row.geometry.area),
            "canopy_pixel_count": int(c_cnt[idx]),
            "canopy_area_m2": float(canopy_area_m2[idx]),
            "canopy_area_source": CANOPY_AREA_SOURCE_RASTER,
            "valid_pixel_count": int(v_cnt[idx]),
            "canopy_completeness": float(comp[idx]),
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

    Priority:
    1. Existing ``canopy_area_m2`` column
    2. Raster aggregation from U-Net segmentation
    3. Block-clipped aggregate from merged landcover + block geometries
    4. ``tree_density × block_area_m2`` from the block scores schema

    Returns
    -------
    (dataframe, source_label)
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
        canopy_df = aggregate_canopy_area_m2_from_merged(blocks_gdf, merged_geojson)
        result = result.merge(canopy_df, on="block_id", how="left")
        result["canopy_area_m2"] = result["canopy_area_m2"].fillna(0.0)
        if result["canopy_area_m2"].isna().any():
            missing = result.loc[result["canopy_area_m2"].isna(), "block_id"].tolist()
            raise ValueError(
                f"Canopy area missing for blocks after landcover aggregate: {missing[:5]}"
            )
        return result, CANOPY_AREA_SOURCE_LANDCOVER

    result["canopy_area_m2"] = canopy_area_m2_from_score_columns(result)
    return result, CANOPY_AREA_SOURCE_SCORES

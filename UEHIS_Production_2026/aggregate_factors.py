import json
import hashlib
from datetime import datetime
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.features import rasterize, shapes
import shapely
from shapely.geometry import shape
from pathlib import Path
import warnings
import sys

# --- Geometry Hash ---
def canonical_geometry_hash(geom, crs):
    """
    Deterministically hash a geometry.
    - Reproject to EPSG:32643
    - Round coordinates to 3 decimal places
    - Serialize deterministically to WKT
    - Hash using SHA-256
    """
    if crs != "EPSG:32643":
        geom = gpd.GeoSeries([geom], crs=crs).to_crs("EPSG:32643").iloc[0]
    
    geom = shapely.set_precision(geom, 0.001)
    wkt_str = shapely.wkt.dumps(geom, rounding_precision=3)
    return hashlib.sha256(wkt_str.encode('utf-8')).hexdigest()

# --- Grid Validation ---
def validate_grid(raster_path, ref_profile):
    with rasterio.open(raster_path) as src:
        prof = src.profile
        if prof['crs'] != ref_profile['crs']:
            raise ValueError(f"CRS mismatch in {raster_path}: {prof['crs']} != {ref_profile['crs']}")
        if prof['width'] != ref_profile['width'] or prof['height'] != ref_profile['height']:
            raise ValueError(f"Dimensions mismatch in {raster_path}: {prof['width']}x{prof['height']} vs {ref_profile['width']}x{ref_profile['height']}")
        if prof['transform'] != ref_profile['transform']:
            raise ValueError(f"Transform mismatch in {raster_path}")
    return True

# --- OSM Rasterization ---
def rasterize_osm_to_grid(osm_gdf, target_raster_path, out_path, nodata=255):
    with rasterio.open(target_raster_path) as src:
        prof = src.profile.copy()
        
    if osm_gdf.empty:
        arr = np.full((prof['height'], prof['width']), 0, dtype=np.uint8) # 0 means pervious/non-built
    else:
        if osm_gdf.crs != prof['crs']:
            osm_gdf = osm_gdf.to_crs(prof['crs'])
        # all_touched=False assigns pixel if its center is within the polygon (50% threshold for squares).
        shapes_gen = ((geom, 1) for geom in osm_gdf.geometry if geom is not None and not geom.is_empty)
        try:
            arr = rasterize(shapes_gen, out_shape=(prof['height'], prof['width']), transform=prof['transform'], fill=0, dtype=np.uint8, all_touched=False)
        except ValueError:
            arr = np.full((prof['height'], prof['width']), 0, dtype=np.uint8)
            
    prof.update(dtype=rasterio.uint8, count=1, nodata=nodata, compress='lzw')
    with rasterio.open(out_path, 'w', **prof) as dst:
        dst.write(arr, 1)
    return Path(out_path)

# --- Impervious Union ---
def build_impervious_union(unet_tif, bldg_tif, road_tif, out_path):
    with rasterio.open(unet_tif) as src_u:
        unet = src_u.read(1)
        prof = src_u.profile.copy()
        nodata_u = src_u.nodata
    
    validate_grid(bldg_tif, prof)
    validate_grid(road_tif, prof)
    
    with rasterio.open(bldg_tif) as src_b, rasterio.open(road_tif) as src_r:
        bldg = src_b.read(1)
        road = src_r.read(1)
        nodata_b = src_b.nodata if src_b.nodata is not None else 255
        nodata_r = src_r.nodata if src_r.nodata is not None else 255
        
    u_valid = (unet != nodata_u) & (~np.isnan(unet) if unet.dtype.kind == 'f' else True)
    b_valid = (bldg != nodata_b)
    r_valid = (road != nodata_r)
    
    any_valid = u_valid | b_valid | r_valid
    union = np.full(unet.shape, 255, dtype=np.uint8)
    
    # Base fill for valid pixels is 0 (Pervious)
    union[any_valid] = 0
    
    # Impervious is any valid source being 1
    imp_mask = any_valid & (
        (u_valid & (unet == 1)) |
        (b_valid & (bldg == 1)) |
        (r_valid & (road == 1))
    )
    union[imp_mask] = 1
    
    prof.update(dtype=rasterio.uint8, count=1, nodata=255, compress='lzw')
    with rasterio.open(out_path, 'w', **prof) as dst:
        dst.write(union, 1)
    return Path(out_path)

# --- Zonal Core ---
def _rasterize_blocks(blocks_gdf, prof):
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
        block_idx_arr = np.full(
            (prof['height'], prof['width']),
            -1,
            dtype=np.int32
        )
    return block_idx_arr


def _build_boundary_aware_block_counts(
    block_idx_arr,
    boundary_mask,
    num_blocks
):
    """
    Calculate the number of authoritative Pune pixels belonging
    to each PN block.

    boundary_mask:
        1 = inside authoritative Pune boundary
        0 = outside Pune

    Only pixels satisfying both:
        block_idx_arr >= 0
        boundary_mask == 1

    are counted as valid Pune area.

    This is required because the authoritative 250 m PN grid
    contains partial boundary cells.
    """
    if boundary_mask.shape != block_idx_arr.shape:
        raise ValueError(
            "Boundary mask shape does not match block raster."
        )

    valid_boundary = (
        (block_idx_arr >= 0) &
        (boundary_mask == 1)
    )

    valid_block_idx = block_idx_arr[valid_boundary]

    boundary_pixel_count = np.bincount(
        valid_block_idx,
        minlength=num_blocks
    )

    return valid_boundary, boundary_pixel_count

def aggregate_segmentation_to_blocks(
    unet_data,
    unet_prof,
    block_idx_arr,
    boundary_mask,
    boundary_pixel_count,
    num_blocks
):
    nodata = unet_prof['nodata']

    valid_mask = (
        (block_idx_arr >= 0) &
        (boundary_mask == 1) &
        (unet_data != nodata)
    )

    valid_bidx = block_idx_arr[valid_mask]
    valid_data = unet_data[valid_mask]

    v_cnt = np.bincount(
        valid_bidx,
        minlength=num_blocks
    )

    c_cnt = np.bincount(
        valid_bidx[valid_data == 0],
        minlength=num_blocks
    )

    with np.errstate(divide='ignore', invalid='ignore'):
        td = np.where(
            v_cnt > 0,
            c_cnt / v_cnt,
            np.nan
        )

        comp = np.where(
            boundary_pixel_count > 0,
            v_cnt / boundary_pixel_count,
            0.0
        )

    return pd.DataFrame({
        "tree_density": td,
        "canopy_pixel_count": c_cnt,
        "segmentation_valid_pixel_count": v_cnt,
        "pune_boundary_pixel_count": boundary_pixel_count,
        "segmentation_completeness_fraction": comp
    })

def aggregate_impervious_to_blocks(
    unet_data,
    bldg_data,
    road_data,
    union_data,
    prof,
    block_idx_arr,
    boundary_mask,
    boundary_pixel_count,
    num_blocks
):
    valid_mask = (
        (block_idx_arr >= 0) &
        (boundary_mask == 1) &
        (union_data != 255)
    )

    bidx = block_idx_arr[valid_mask]
    u_valid = unet_data[valid_mask]
    b_valid = bldg_data[valid_mask]
    r_valid = road_data[valid_mask]
    union_valid = union_data[valid_mask]

    v_cnt = np.bincount(
        bidx,
        minlength=num_blocks
    )

    u_cnt = np.bincount(
        bidx[u_valid == 1],
        minlength=num_blocks
    )

    b_cnt = np.bincount(
        bidx[b_valid == 1],
        minlength=num_blocks
    )

    r_cnt = np.bincount(
        bidx[r_valid == 1],
        minlength=num_blocks
    )

    union_cnt = np.bincount(
        bidx[union_valid == 1],
        minlength=num_blocks
    )

    if not (
        np.all(union_cnt >= u_cnt) and
        np.all(union_cnt >= b_cnt) and
        np.all(union_cnt >= r_cnt)
    ):
        warnings.warn(
            "QA Failed: Union count is less than individual sources."
        )

    with np.errstate(divide='ignore', invalid='ignore'):
        imp = np.where(
            v_cnt > 0,
            union_cnt / v_cnt,
            np.nan
        )

        comp = np.where(
            boundary_pixel_count > 0,
            v_cnt / boundary_pixel_count,
            0.0
        )

    return pd.DataFrame({
        "impervious_surfaces": imp,
        "unet_impervious_pixel_count": u_cnt,
        "osm_building_pixel_count": b_cnt,
        "osm_road_pixel_count": r_cnt,
        "impervious_union_pixel_count": union_cnt,
        "impervious_valid_pixel_count": v_cnt,
        "pune_boundary_pixel_count": boundary_pixel_count,
        "impervious_completeness_fraction": comp
    })

def aggregate_ndvi_to_blocks(
    ndvi_tif,
    block_idx_arr,
    boundary_mask,
    boundary_pixel_count,
    num_blocks
):
    with rasterio.open(ndvi_tif) as src:
        data = src.read(1)
        nodata = src.nodata if src.nodata is not None else -9999

    valid_mask = (
        (block_idx_arr >= 0) &
        (boundary_mask == 1) &
        (data != nodata) &
        (~np.isnan(data))
    )

    bidx = block_idx_arr[valid_mask]
    valid_data = data[valid_mask]

    s_ndvi = np.bincount(
        bidx,
        weights=valid_data,
        minlength=num_blocks
    )

    c_ndvi = np.bincount(
        bidx,
        minlength=num_blocks
    )

    with np.errstate(divide='ignore', invalid='ignore'):
        ndvi_mean = np.where(
            c_ndvi > 0,
            s_ndvi / c_ndvi,
            np.nan
        )

        comp = np.where(
            boundary_pixel_count > 0,
            c_ndvi / boundary_pixel_count,
            0.0
        )

    return pd.DataFrame({
        "ndvi": ndvi_mean,
        "ndvi_valid_pixel_count": c_ndvi,
        "ndvi_completeness_fraction": comp
    })

def aggregate_temperature_to_blocks(
    temp_tif,
    block_idx_arr,
    boundary_mask,
    boundary_pixel_count,
    num_blocks
):
    with rasterio.open(temp_tif) as src:
        data = src.read(1)
        nodata = src.nodata

    valid_mask = (
        (block_idx_arr >= 0) &
        (boundary_mask == 1) &
        (~np.isnan(data))
    )

    if nodata is not None:
        valid_mask &= (data != nodata)

    bidx = block_idx_arr[valid_mask]
    valid_data = data[valid_mask]

    s_temp = np.bincount(
        bidx,
        weights=valid_data,
        minlength=num_blocks
    )

    c_temp = np.bincount(
        bidx,
        minlength=num_blocks
    )

    with np.errstate(divide='ignore', invalid='ignore'):
        t_mean = np.where(
            c_temp > 0,
            s_temp / c_temp,
            np.nan
        )

        comp = np.where(
            boundary_pixel_count > 0,
            c_temp / boundary_pixel_count,
            0.0
        )

    return pd.DataFrame({
        "temperature": t_mean,
        "temperature_valid_pixel_count": c_temp,
        "temperature_completeness_fraction": comp
    })

def aggregate_pm25_to_pn_blocks(pm25_tif, blocks_gdf):
    """
    Direct-index PM2.5 aggregator.

    Maps exactly one authoritative PN 250m cell to one PM2.5
    computational-grid cell.

    PM2.5 is an intensive atmospheric concentration, therefore
    boundary coverage is NOT used to dilute the value.

    The PM2.5 source is ACAG/WUSTL V6.GL.03 resampled to the
    UEHIS PN 250m computational grid.
    """

    with rasterio.open(pm25_tif) as src:
        prof = src.profile
        data = src.read(1)
        nodata = src.nodata

        # ----------------------------------------------------------
        # Strict PM2.5 grid validation
        # ----------------------------------------------------------

        crs_ok = (
            prof["crs"] is not None
            and str(prof["crs"]) == "EPSG:32643"
        )

        if not crs_ok:
            raise ValueError(
                f"CRS mismatch in PM2.5 raster: "
                f"expected EPSG:32643, got {prof['crs']}"
            )

        if not (
            np.isclose(src.res[0], 250.0)
            and np.isclose(src.res[1], 250.0)
        ):
            raise ValueError(
                "Resolution mismatch in PM2.5 raster: "
                f"expected 250m x 250m, got {src.res[0]} x {src.res[1]}"
            )

        if blocks_gdf.crs is None:
            raise ValueError(
                "PN blocks GeoDataFrame has no CRS."
            )

        if str(blocks_gdf.crs) != "EPSG:32643":
            raise ValueError(
                f"PN grid CRS mismatch: expected EPSG:32643, "
                f"got {blocks_gdf.crs}"
            )

        # The authoritative PN grid and PM2.5 raster occupy the
        # same fixed-origin 250m lattice extent.
        gdf_bounds = blocks_gdf.total_bounds

        bounds_ok = all([
            np.isclose(
                gdf_bounds[0],
                src.bounds.left,
                atol=1e-2
            ),
            np.isclose(
                gdf_bounds[1],
                src.bounds.bottom,
                atol=1e-2
            ),
            np.isclose(
                gdf_bounds[2],
                src.bounds.right,
                atol=1e-2
            ),
            np.isclose(
                gdf_bounds[3],
                src.bounds.top,
                atol=1e-2
            ),
        ])

        if not bounds_ok:
            raise ValueError(
                "PM2.5 raster bounds do not exactly match "
                "the authoritative PN grid bounds."
            )

        # ----------------------------------------------------------
        # Direct 1:1 PN-cell -> PM2.5-cell lookup
        # ----------------------------------------------------------

        pm25_vals = []
        counts = []
        comps = []

        centroids = blocks_gdf.geometry.centroid

        for pt in centroids:
            row, col = src.index(pt.x, pt.y)

            if 0 <= row < src.height and 0 <= col < src.width:
                val = data[row, col]

                if nodata is not None and np.isclose(
                    val,
                    nodata
                ):
                    val = np.nan

                if np.isfinite(val):
                    pm25_vals.append(float(val))
                    counts.append(1)
                    comps.append(1.0)
                else:
                    pm25_vals.append(np.nan)
                    counts.append(0)
                    comps.append(0.0)

            else:
                pm25_vals.append(np.nan)
                counts.append(0)
                comps.append(0.0)

    return pd.DataFrame(
        {
            "pm25": pm25_vals,
            "pm25_valid_pixel_count": counts,
            "pm25_completeness_fraction": comps,
        },
        index=blocks_gdf.index,
    )



def aggregate_population_to_blocks(pop_tif, blocks_gdf, boundary_gdf=None):
    """
    Aggregate WorldPop population to PN 250 m blocks using exact
    area-weighted extensive-variable allocation.

    Memory-safe implementation:
      - reads the source raster in windows
      - processes source cells in bounded chunks
      - never constructs the complete source-cell GeoDataFrame
      - never performs a full GeoPandas overlay between all
        WorldPop cells and all PN blocks

    Scientific method:
      population_allocated =
          source_population *
          intersection_area /
          original_source_cell_area

    Source-cell area is calculated BEFORE Pune-boundary clipping.
    Population is therefore not artificially inflated/normalized
    by the Pune boundary.

    Partial PN boundary cells are retained.
    Completeness is calculated against the actual Pune-covered
    area of each PN block.
    """
    import rasterio
    from rasterio.windows import Window
    from rasterio.transform import xy
    from shapely.geometry import box
    from shapely.ops import transform as shapely_transform
    from pyproj import Transformer

    TARGET_CRS = "EPSG:32643"
    CHUNK_SIZE = 1000

    # ------------------------------------------------------------
    # Validate input geometry
    # ------------------------------------------------------------
    if "block_id" not in blocks_gdf.columns:
        raise ValueError("blocks_gdf must contain 'block_id'.")

    if blocks_gdf.crs is None:
        raise ValueError("blocks_gdf must have a CRS.")

    # Work on a local copy so caller geometry is never mutated.
    blocks = blocks_gdf[["block_id", "geometry"]].copy()

    if str(blocks.crs) != TARGET_CRS:
        blocks = blocks.to_crs(TARGET_CRS)

    block_ids = blocks["block_id"].tolist()
    block_geoms = blocks.geometry.tolist()
    n_blocks = len(blocks)

    # ------------------------------------------------------------
    # Boundary union in metric CRS
    # ------------------------------------------------------------
    if boundary_gdf is not None:
        if boundary_gdf.crs is None:
            raise ValueError("boundary_gdf must have a CRS.")

        boundary = boundary_gdf.copy()

        if str(boundary.crs) != TARGET_CRS:
            boundary = boundary.to_crs(TARGET_CRS)

        boundary_geom = boundary.geometry.union_all()
    else:
        boundary_geom = None

    # ------------------------------------------------------------
    # Precompute exact Pune-covered area for each PN block.
    # This is also memory-safe: only 5,309 block geometries.
    # ------------------------------------------------------------
    boundary_area = np.zeros(n_blocks, dtype=np.float64)

    if boundary_geom is None:
        for i, geom in enumerate(block_geoms):
            boundary_area[i] = float(geom.area)
    else:
        for i, geom in enumerate(block_geoms):
            inter = geom.intersection(boundary_geom)
            if not inter.is_empty:
                boundary_area[i] = float(inter.area)

    # ------------------------------------------------------------
    # Spatial index for PN blocks
    # ------------------------------------------------------------
    block_sindex = blocks.sindex

    # ------------------------------------------------------------
    # Accumulators
    # ------------------------------------------------------------
    population_sum = np.zeros(n_blocks, dtype=np.float64)
    source_area_sum = np.zeros(n_blocks, dtype=np.float64)
    source_cell_sets = [set() for _ in range(n_blocks)]

    # ------------------------------------------------------------
    # Coordinate transformer
    # ------------------------------------------------------------
    with rasterio.open(pop_tif) as src:

        source_crs = src.crs

        if source_crs is None:
            raise ValueError("Population raster has no CRS.")

        transformer = Transformer.from_crs(
            source_crs,
            TARGET_CRS,
            always_xy=True
        )

        # --------------------------------------------------------
        # Determine raster window overlapping PN-grid bounds.
        # This avoids reading the entire India raster.
        # --------------------------------------------------------
        grid_bounds = blocks.total_bounds
        xmin, ymin, xmax, ymax = grid_bounds

        # Transform PN extent approximately into source CRS.
        # WorldPop source is EPSG:4326, but use the generic
        # inverse transformer for robustness.
        inverse_transformer = Transformer.from_crs(
            TARGET_CRS,
            source_crs,
            always_xy=True
        )

        sx1, sy1 = inverse_transformer.transform(xmin, ymin)
        sx2, sy2 = inverse_transformer.transform(xmax, ymax)

        src_xmin = min(sx1, sx2)
        src_xmax = max(sx1, sx2)
        src_ymin = min(sy1, sy2)
        src_ymax = max(sy1, sy2)

        row_min, col_min = src.index(src_xmin, src_ymax)
        row_max, col_max = src.index(src_xmax, src_ymin)

        row_min = max(0, min(src.height - 1, row_min))
        row_max = max(0, min(src.height - 1, row_max))
        col_min = max(0, min(src.width - 1, col_min))
        col_max = max(0, min(src.width - 1, col_max))

        if row_min > row_max:
            row_min, row_max = row_max, row_min

        if col_min > col_max:
            col_min, col_max = col_max, col_min

        total_valid_cells = 0
        processed_cells = 0

        # --------------------------------------------------------
        # Process raster in bounded windows.
        # --------------------------------------------------------
        for r0 in range(row_min, row_max + 1, CHUNK_SIZE):

            r1 = min(row_max + 1, r0 + CHUNK_SIZE)

            for c0 in range(col_min, col_max + 1, CHUNK_SIZE):

                c1 = min(col_max + 1, c0 + CHUNK_SIZE)

                window = Window(
                    c0,
                    r0,
                    c1 - c0,
                    r1 - r0
                )

                data = src.read(1, window=window)

                valid = np.isfinite(data)

                if src.nodata is not None:
                    valid &= data != src.nodata

                local_rows, local_cols = np.where(valid)

                if len(local_rows) == 0:
                    continue

                values = data[local_rows, local_cols].astype(
                    np.float64,
                    copy=False
                )

                total_valid_cells += len(values)

                # ------------------------------------------------
                # Process source cells in small bounded chunks.
                # ------------------------------------------------
                for start in range(0, len(values), CHUNK_SIZE):

                    end = min(start + CHUNK_SIZE, len(values))

                    rr = local_rows[start:end]
                    cc = local_cols[start:end]
                    vv = values[start:end]

                    global_rows = rr + r0
                    global_cols = cc + c0

                    # Build source polygons in source CRS.
                    src_polys = []

                    for gr, gc in zip(global_rows, global_cols):
                        x_ul, y_ul = xy(
                            src.transform,
                            int(gr),
                            int(gc),
                            offset="ul"
                        )
                        x_lr, y_lr = xy(
                            src.transform,
                            int(gr),
                            int(gc),
                            offset="lr"
                        )

                        src_polys.append(
                            box(
                                x_ul,
                                y_lr,
                                x_lr,
                                y_ul
                            )
                        )

                    # Transform polygons to metric CRS.
                    metric_polys = [
                        shapely_transform(
                            transformer.transform,
                            geom
                        )
                        for geom in src_polys
                    ]

                    for local_idx, (src_geom, pop_value) in enumerate(
                        zip(metric_polys, vv)
                    ):

                        source_cell_id = (
                            int(global_rows[local_idx]) * src.width
                            + int(global_cols[local_idx])
                        )

                        original_source_area = float(
                            src_geom.area
                        )

                        if original_source_area <= 0:
                            continue

                        # ----------------------------------------
                        # Clip source cell to authoritative boundary
                        # ----------------------------------------
                        if boundary_geom is not None:
                            clipped_source = src_geom.intersection(
                                boundary_geom
                            )

                            if clipped_source.is_empty:
                                continue
                        else:
                            clipped_source = src_geom

                        # ----------------------------------------
                        # Candidate PN blocks using spatial index
                        # ----------------------------------------
                        candidates = block_sindex.query(
                            clipped_source,
                            predicate="intersects"
                        )

                        for block_pos in candidates:

                            block_geom = block_geoms[int(block_pos)]

                            intersection = clipped_source.intersection(
                                block_geom
                            )

                            if intersection.is_empty:
                                continue

                            intersection_area = float(
                                intersection.area
                            )

                            if intersection_area <= 0:
                                continue

                            allocated_population = (
                                float(pop_value)
                                * intersection_area
                                / original_source_area
                            )

                            population_sum[int(block_pos)] += (
                                allocated_population
                            )

                            source_area_sum[int(block_pos)] += (
                                intersection_area
                            )

                            source_cell_sets[int(block_pos)].add(
                                source_cell_id
                            )

                    processed_cells += len(values[start:end])

        # --------------------------------------------------------
        # Build output
        # --------------------------------------------------------
        res_df = pd.DataFrame(index=blocks_gdf.index)

        res_df["population_exposure"] = population_sum
        res_df["population_source_cell_count"] = [
            len(s) for s in source_cell_sets
        ]
        res_df["population_source_valid_area_m2"] = (
            source_area_sum
        )

        res_df["population_completeness_fraction"] = np.where(
            boundary_area > 0,
            source_area_sum / boundary_area,
            0.0
        )

        # Numerical safety.
        res_df["population_exposure"] = (
            res_df["population_exposure"]
            .replace([np.inf, -np.inf], np.nan)
            .fillna(0.0)
        )

        res_df["population_source_cell_count"] = (
            res_df["population_source_cell_count"]
            .astype(int)
        )

        res_df["population_source_valid_area_m2"] = (
            res_df["population_source_valid_area_m2"]
            .replace([np.inf, -np.inf], np.nan)
            .fillna(0.0)
        )

        res_df["population_completeness_fraction"] = (
            res_df["population_completeness_fraction"]
            .replace([np.inf, -np.inf], np.nan)
            .fillna(0.0)
        )

        return res_df[
            [
                "population_exposure",
                "population_source_cell_count",
                "population_source_valid_area_m2",
                "population_completeness_fraction"
            ]
        ]


import uuid
import subprocess

def _hash_file(filepath):
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

def _get_git_commit():
    try:
        return subprocess.check_output(['git', 'rev-parse', 'HEAD'], stderr=subprocess.DEVNULL, text=True).strip()
    except Exception:
        return "unknown"

def _get_raster_provenance(filepath):
    path = str(filepath)
    try:
        content_hash = _hash_file(path)
        with rasterio.open(path) as src:
            tags = src.tags()
            res = src.res
            crs = src.crs.to_string() if src.crs else "unknown"
            
            acq_date = tags.get('TIFFTAG_DATETIME') or tags.get('acquisition_date') or "unknown"
            dataset = tags.get('TIFFTAG_IMAGEDESCRIPTION') or tags.get('dataset_identity') or "unknown"
            
            return {
                "path": path,
                "dataset_identity": dataset,
                "acquisition_date": acq_date,
                "spatial_resolution": {"x": res[0], "y": res[1]},
                "crs": crs,
                "content_sha256": content_hash
            }
    except Exception as e:
        return {
            "path": path,
            "dataset_identity": "unknown",
            "acquisition_date": "unknown",
            "spatial_resolution": "unknown",
            "crs": "unknown",
            "content_sha256": "unknown"
        }

def aggregate_all_factors(
    blocks_gdf,
    seg_tif,
    bldg_tif,
    road_tif,
    union_tif,
    ndvi_tif,
    temp_tif,
    pop_tif,
    pm25_tif,
    boundary_mask_tif,
    boundary_gdf=None,
    model_checksums="unknown"
):
    # Preload unet prof to validate all other factor grids on production path
    with rasterio.open(seg_tif) as su:
        unet_data = su.read(1)
        unet_prof = su.profile
        
    validate_grid(bldg_tif, unet_prof)
    validate_grid(road_tif, unet_prof)
    validate_grid(union_tif, unet_prof)
    validate_grid(ndvi_tif, unet_prof)
    validate_grid(boundary_mask_tif, unet_prof)
    validate_grid(temp_tif, unet_prof)
    with rasterio.open(bldg_tif) as sb, rasterio.open(road_tif) as sr, rasterio.open(union_tif) as sunion, rasterio.open(boundary_mask_tif) as sboundary:
        bldg_data = sb.read(1)
        road_data = sr.read(1)
        union_data = sunion.read(1)
        boundary_mask = sboundary.read(1)

    if not np.isin(boundary_mask, [0, 1]).all():
        raise ValueError(
            "Boundary mask must contain only 0/1 values."
        )
        
    # Create block raster once
    block_idx_arr = _rasterize_blocks(blocks_gdf, unet_prof)
    num_blocks = len(blocks_gdf)

    valid_boundary_mask, boundary_pixel_count = (
        _build_boundary_aware_block_counts(
            block_idx_arr,
            boundary_mask,
            num_blocks
        )
    )

    df_seg = aggregate_segmentation_to_blocks(
        unet_data,
        unet_prof,
        block_idx_arr,
        boundary_mask,
        boundary_pixel_count,
        num_blocks
    )
    df_seg.index = blocks_gdf.index
    
    df_imp = aggregate_impervious_to_blocks(
        unet_data,
        bldg_data,
        road_data,
        union_data,
        unet_prof,
        block_idx_arr,
        boundary_mask,
        boundary_pixel_count,
        num_blocks
    )
    df_imp.index = blocks_gdf.index
    
    df_ndvi = aggregate_ndvi_to_blocks(
        ndvi_tif,
        block_idx_arr,
        boundary_mask,
        boundary_pixel_count,
        num_blocks
    )
    df_ndvi.index = blocks_gdf.index
    
    df_temp = aggregate_temperature_to_blocks(
        temp_tif,
        block_idx_arr,
        boundary_mask,
        boundary_pixel_count,
        num_blocks
    )
    df_temp.index = blocks_gdf.index
    
    df_pop = aggregate_population_to_blocks(
        pop_tif,
        blocks_gdf,
        boundary_gdf
    )
    df_pop.index = blocks_gdf.index
    
    if pm25_tif:
        df_pm25 = aggregate_pm25_to_pn_blocks(
            pm25_tif,
            blocks_gdf
        )
    else:
        df_pm25 = pd.DataFrame({
            'pm25': np.nan,
            'pm25_valid_pixel_count': 0,
            'pm25_completeness_fraction': 0.0
        }, index=blocks_gdf.index)
    
    # Hash blocks for provenance
    final_df = blocks_gdf[['block_id']].copy()
    final_df['geometry_hash'] = blocks_gdf.geometry.apply(lambda g: canonical_geometry_hash(g, blocks_gdf.crs))
    
    final_df = pd.concat([final_df, df_seg, df_imp, df_ndvi, df_temp, df_pop, df_pm25], axis=1)
    
    manifest = {
        "run_id": str(uuid.uuid4()),
        "timestamp": datetime.now().isoformat(),
        "git_commit": _get_git_commit(),
        "aggregation_version": "1.1",
        "model_checksum": model_checksums,
        "python_version": sys.version.split()[0],
        "rasterio_version": rasterio.__version__,
        "geopandas_version": gpd.__version__,
        "numpy_version": np.__version__,
        "pandas_version": pd.__version__,
        "shapely_version": shapely.__version__,
        "geometry_specification": "EPSG:32643",
        "geometry_hash_specification": "SHA-256 of WKT rounded to 3 decimal places",
        "processing_configuration": {
            "osm_rasterization_threshold": "50_percent_center",
            "population_intersection": "exact_area_weighted",
            "impervious_nodata_policy": "unet_valid_or_osm_valid",
            "boundary_mask": "authoritative Pune boundary on exact U-Net grid",
            "boundary_rasterization": "all_touched=False",
            "block_completeness_denominator": "Pune-covered pixels per block"
        },
        "inputs": {
            "segmentation": _get_raster_provenance(seg_tif),
            "building": _get_raster_provenance(bldg_tif),
            "road": _get_raster_provenance(road_tif),
            "union": _get_raster_provenance(union_tif),
            "ndvi": _get_raster_provenance(ndvi_tif),
            "temperature": _get_raster_provenance(temp_tif),
            "population": _get_raster_provenance(pop_tif),
            "boundary_mask": _get_raster_provenance(boundary_mask_tif)
        }
    }
    if pm25_tif:
        manifest["inputs"]["pm25"] = _get_raster_provenance(pm25_tif)
        manifest["inputs"]["pm25"].update({
            "source": "ACAG/WUSTL V6.GL.03",
            "temporal_period": "Jan-Mar 2024",
            "source_resolution": "0.01 degree (~1.1 km)",
            "computational_grid": "UEHIS PN 250m",
            "resampling": "bilinear",
            "effective_information_resolution": "coarser than 250m",
            "boundary_mask": "NOT applied to PM2.5 raster",
            "aggregation": "direct 1:1 PN-cell lookup",
            "intensive_variable": True,
            "area_dilution": False
        })
    
    return final_df, manifest

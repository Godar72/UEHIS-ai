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
        block_idx_arr = rasterize(shapes_gen, out_shape=(prof['height'], prof['width']), transform=prof['transform'], fill=-1, dtype=np.int32, all_touched=False)
    except ValueError:
        block_idx_arr = np.full((prof['height'], prof['width']), -1, dtype=np.int32)
    return block_idx_arr

def aggregate_segmentation_to_blocks(unet_data, unet_prof, block_idx_arr, num_blocks):
    nodata = unet_prof['nodata']
    
    valid_mask = (block_idx_arr >= 0) & (unet_data != nodata)
    valid_bidx = block_idx_arr[valid_mask]
    valid_data = unet_data[valid_mask]
    
    v_cnt = np.bincount(valid_bidx, minlength=num_blocks)
    c_cnt = np.bincount(valid_bidx[valid_data == 0], minlength=num_blocks)
    t_cnt = np.bincount(block_idx_arr[block_idx_arr >= 0], minlength=num_blocks)
    
    with np.errstate(divide='ignore', invalid='ignore'):
        td = np.where(v_cnt > 0, c_cnt / v_cnt, np.nan)
        comp = np.where(t_cnt > 0, v_cnt / t_cnt, 0.0)
        
    return pd.DataFrame({
        "tree_density": td,
        "canopy_pixel_count": c_cnt,
        "segmentation_valid_pixel_count": v_cnt,
        "total_block_pixel_count": t_cnt,
        "segmentation_completeness_fraction": comp
    })

def aggregate_impervious_to_blocks(unet_data, bldg_data, road_data, union_data, prof, block_idx_arr, num_blocks):
    valid_mask = (block_idx_arr >= 0) & (union_data != 255)
    
    bidx = block_idx_arr[valid_mask]
    u_valid = unet_data[valid_mask]
    b_valid = bldg_data[valid_mask]
    r_valid = road_data[valid_mask]
    union_valid = union_data[valid_mask]
    
    v_cnt = np.bincount(bidx, minlength=num_blocks)
    u_cnt = np.bincount(bidx[u_valid == 1], minlength=num_blocks)
    b_cnt = np.bincount(bidx[b_valid == 1], minlength=num_blocks)
    r_cnt = np.bincount(bidx[r_valid == 1], minlength=num_blocks)
    union_cnt = np.bincount(bidx[union_valid == 1], minlength=num_blocks)
    
    if not (np.all(union_cnt >= u_cnt) and np.all(union_cnt >= b_cnt) and np.all(union_cnt >= r_cnt)):
        warnings.warn("QA Failed: Union count is less than individual sources.")
        
    t_cnt = np.bincount(block_idx_arr[block_idx_arr >= 0], minlength=num_blocks)
    
    with np.errstate(divide='ignore', invalid='ignore'):
        imp = np.where(v_cnt > 0, union_cnt / v_cnt, np.nan)
        comp = np.where(t_cnt > 0, v_cnt / t_cnt, 0.0)
        
    return pd.DataFrame({
        "impervious_surfaces": imp,
        "unet_impervious_pixel_count": u_cnt,
        "osm_building_pixel_count": b_cnt,
        "osm_road_pixel_count": r_cnt,
        "impervious_union_pixel_count": union_cnt,
        "impervious_valid_pixel_count": v_cnt,
        "impervious_completeness_fraction": comp
    })

def aggregate_ndvi_to_blocks(ndvi_tif, block_idx_arr, num_blocks):
    with rasterio.open(ndvi_tif) as src:
        data = src.read(1)
        nodata = src.nodata if src.nodata is not None else -9999
        
    valid_mask = (block_idx_arr >= 0) & (data != nodata) & (~np.isnan(data))
    bidx = block_idx_arr[valid_mask]
    valid_data = data[valid_mask]
    
    s_ndvi = np.bincount(bidx, weights=valid_data, minlength=num_blocks)
    c_ndvi = np.bincount(bidx, minlength=num_blocks)
    t_cnt = np.bincount(block_idx_arr[block_idx_arr >= 0], minlength=num_blocks)
    
    with np.errstate(divide='ignore', invalid='ignore'):
        ndvi_mean = np.where(c_ndvi > 0, s_ndvi / c_ndvi, np.nan)
        comp = np.where(t_cnt > 0, c_ndvi / t_cnt, 0.0)
        
    return pd.DataFrame({
        "ndvi": ndvi_mean,
        "ndvi_valid_pixel_count": c_ndvi,
        "ndvi_completeness_fraction": comp
    })

def aggregate_temperature_to_blocks(temp_tif, block_idx_arr, num_blocks):
    with rasterio.open(temp_tif) as src:
        data = src.read(1)
        nodata = src.nodata
        
    valid_mask = (block_idx_arr >= 0) & (~np.isnan(data))
    if nodata is not None:
        valid_mask &= (data != nodata)
        
    bidx = block_idx_arr[valid_mask]
    valid_data = data[valid_mask]
    
    s_temp = np.bincount(bidx, weights=valid_data, minlength=num_blocks)
    c_temp = np.bincount(bidx, minlength=num_blocks)
    t_cnt = np.bincount(block_idx_arr[block_idx_arr >= 0], minlength=num_blocks)
    
    with np.errstate(divide='ignore', invalid='ignore'):
        t_mean = np.where(c_temp > 0, s_temp / c_temp, np.nan)
        comp = np.where(t_cnt > 0, c_temp / t_cnt, 0.0)
        
    return pd.DataFrame({
        "temperature": t_mean,
        "temperature_valid_pixel_count": c_temp,
        "temperature_completeness_fraction": comp
    })

def aggregate_pm25_to_pn_blocks(pm25_tif, blocks_gdf):
    """
    Direct-index PM2.5 aggregator.
    Maps exactly 1 PN cell to 1 PM2.5 cell without area dilution or rasterization.
    """
    with rasterio.open(pm25_tif) as src:
        prof = src.profile
        data = src.read(1)
        nodata = src.nodata
        
        if prof['crs'] != "EPSG:32643" and prof['crs'] != blocks_gdf.crs:
            raise ValueError(f"CRS mismatch in PM2.5 raster: {prof['crs']} != EPSG:32643")
        
        if not (np.isclose(src.res[0], 250.0) and np.isclose(src.res[1], 250.0)):
            raise ValueError(f"Resolution mismatch in PM2.5 raster: Expected 250m, got {src.res[0]}x{src.res[1]}")
            
        gdf_bounds = blocks_gdf.total_bounds
        if not (np.isclose(gdf_bounds[0], src.bounds.left, atol=1e-2) and
                np.isclose(gdf_bounds[1], src.bounds.bottom, atol=1e-2) and
                np.isclose(gdf_bounds[2], src.bounds.right, atol=1e-2) and
                np.isclose(gdf_bounds[3], src.bounds.top, atol=1e-2)):
            raise ValueError("PM2.5 raster bounds do not exactly match PN grid bounds")
            
        pm25_vals = []
        counts = []
        comps = []
        
        # PN grid retains full cell geometries, so centroid maps perfectly to the cell center
        centroids = blocks_gdf.centroid
        
        for pt in centroids:
            row, col = src.index(pt.x, pt.y)
            if 0 <= row < src.height and 0 <= col < src.width:
                val = data[row, col]
                if nodata is not None and val == nodata:
                    val = np.nan
                if np.isnan(val):
                    pm25_vals.append(np.nan)
                    counts.append(0)
                    comps.append(0.0)
                else:
                    pm25_vals.append(float(val))
                    counts.append(1)
                    comps.append(1.0)
            else:
                pm25_vals.append(np.nan)
                counts.append(0)
                comps.append(0.0)
                
    return pd.DataFrame({
        "pm25": pm25_vals,
        "pm25_valid_pixel_count": counts,
        "pm25_completeness_fraction": comps
    }, index=blocks_gdf.index)


def aggregate_population_to_blocks(pop_tif, blocks_gdf, boundary_gdf=None):
    """
    Aggregate population to blocks using area-weighted extensive-variable allocation.
    
    For every valid WorldPop 100m source cell:
    1. Construct its actual source-cell polygon.
    2. Transform source geometry to EPSG:32643.
    3. Intersect it with the authoritative Pune boundary (if provided).
    4. Intersect the Pune-clipped source geometry with each PN 250m block.
    5. Apportion population according to geometric area fraction.
    """
    with rasterio.open(pop_tif) as src:
        data = src.read(1)
        nodata = src.nodata
        transform = src.transform
        crs = src.crs

    valid_mask = ~np.isnan(data)
    if nodata is not None:
        valid_mask &= (data != nodata)

    rows, cols = np.where(valid_mask)
    vals = data[valid_mask]
    
    if len(vals) == 0:
        res_df = pd.DataFrame(index=blocks_gdf.index)
        res_df["population_exposure"] = np.nan
        res_df["population_source_cell_count"] = 0
        res_df["population_source_valid_area_m2"] = 0.0
        res_df["population_completeness_fraction"] = 0.0
        return res_df

    # 1. Construct actual source-cell polygon
    from rasterio.transform import xy
    x_min, y_max = rasterio.transform.xy(transform, rows, cols, offset='ul')
    x_max, y_min = rasterio.transform.xy(transform, rows, cols, offset='lr')
    
    polygons = [shapely.geometry.box(xm, ym, xM, yM) for xm, ym, xM, yM in zip(x_min, y_min, x_max, y_max)]
    
    source_gdf = gpd.GeoDataFrame({
        'pop': vals,
        'cell_id': np.arange(len(vals))
    }, geometry=polygons, crs=crs)

    # 2. Transform source geometry to EPSG:32643
    if source_gdf.crs != "EPSG:32643":
        source_gdf = source_gdf.to_crs("EPSG:32643")
        
    source_gdf['source_area'] = source_gdf.geometry.area

    # 3. Intersect it with the authoritative boundary
    if boundary_gdf is not None:
        if boundary_gdf.crs != "EPSG:32643":
            boundary_gdf = boundary_gdf.to_crs("EPSG:32643")
        source_gdf = gpd.clip(source_gdf, boundary_gdf)
        source_gdf = source_gdf[source_gdf.geom_type.isin(['Polygon', 'MultiPolygon'])]
        
    # 4. Intersect the source geometry with each PN 250m block
    if blocks_gdf.crs != "EPSG:32643":
        blocks_gdf = blocks_gdf.to_crs("EPSG:32643")
        
    intersect_gdf = gpd.overlay(source_gdf, blocks_gdf[['block_id', 'geometry']], how='intersection')
    
    # 5. Apportion population
    intersect_gdf['intersect_area'] = intersect_gdf.geometry.area
    
    valid_intersect = intersect_gdf[intersect_gdf['source_area'] > 0].copy()
    valid_intersect['allocated_pop'] = valid_intersect['pop'] * (valid_intersect['intersect_area'] / valid_intersect['source_area'])
    
    # 6. Sum allocated population for every PN block
    grouped = valid_intersect.groupby('block_id').agg(
        population_exposure=('allocated_pop', 'sum'),
        population_source_cell_count=('cell_id', 'nunique'),
        population_source_valid_area_m2=('intersect_area', 'sum')
    )
    
    block_areas = blocks_gdf.set_index('block_id').geometry.area
    
    res_df = pd.DataFrame(index=blocks_gdf.index)
    res_df['block_id'] = blocks_gdf['block_id'].values
    res_df = res_df.join(grouped, on='block_id')
    
    res_df['population_exposure'] = res_df['population_exposure'].fillna(0.0)
    res_df['population_source_cell_count'] = res_df['population_source_cell_count'].fillna(0).astype(int)
    res_df['population_source_valid_area_m2'] = res_df['population_source_valid_area_m2'].fillna(0.0)
    
    # Calculate boundary intersection area for completeness
    if boundary_gdf is not None:
        grid_bound_intersect = gpd.overlay(blocks_gdf[['block_id', 'geometry']], boundary_gdf[['geometry']], how='intersection')
        grid_bound_intersect['boundary_intersection_area_m2'] = grid_bound_intersect.geometry.area
        bound_areas = grid_bound_intersect.groupby('block_id')['boundary_intersection_area_m2'].sum()
    else:
        bound_areas = blocks_gdf.set_index('block_id').geometry.area
        bound_areas.name = 'boundary_intersection_area_m2'
    
    res_df = res_df.join(bound_areas, on='block_id')
    res_df['boundary_intersection_area_m2'] = res_df['boundary_intersection_area_m2'].fillna(0.0)
    
    res_df['population_completeness_fraction'] = np.where(
        res_df['boundary_intersection_area_m2'] > 0,
        res_df['population_source_valid_area_m2'] / res_df['boundary_intersection_area_m2'],
        0.0
    )
    
    out_cols = [
        "population_exposure", 
        "population_source_cell_count", 
        "population_source_valid_area_m2", 
        "population_completeness_fraction"
    ]
    return res_df[out_cols]

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

def aggregate_all_factors(blocks_gdf, seg_tif, bldg_tif, road_tif, union_tif, ndvi_tif, temp_tif, pop_tif, pm25_tif, boundary_gdf=None, model_checksums="unknown"):
    # Preload unet prof to validate all other factor grids on production path
    with rasterio.open(seg_tif) as su:
        unet_data = su.read(1)
        unet_prof = su.profile
        
    validate_grid(bldg_tif, unet_prof)
    validate_grid(road_tif, unet_prof)
    validate_grid(union_tif, unet_prof)
    validate_grid(ndvi_tif, unet_prof)
    validate_grid(temp_tif, unet_prof)
    
    with rasterio.open(bldg_tif) as sb, rasterio.open(road_tif) as sr, rasterio.open(union_tif) as sunion:
        bldg_data = sb.read(1)
        road_data = sr.read(1)
        union_data = sunion.read(1)
        
    # Create block raster once
    block_idx_arr = _rasterize_blocks(blocks_gdf, unet_prof)
    num_blocks = len(blocks_gdf)
    
    df_seg = aggregate_segmentation_to_blocks(unet_data, unet_prof, block_idx_arr, num_blocks)
    df_seg.index = blocks_gdf.index
    
    df_imp = aggregate_impervious_to_blocks(unet_data, bldg_data, road_data, union_data, unet_prof, block_idx_arr, num_blocks)
    df_imp.index = blocks_gdf.index
    
    df_ndvi = aggregate_ndvi_to_blocks(ndvi_tif, block_idx_arr, num_blocks)
    df_ndvi.index = blocks_gdf.index
    
    df_temp = aggregate_temperature_to_blocks(temp_tif, block_idx_arr, num_blocks)
    df_temp.index = blocks_gdf.index
    
    df_pop = aggregate_population_to_blocks(pop_tif, blocks_gdf, boundary_gdf)
    df_pop.index = blocks_gdf.index
    
    if pm25_tif:
        df_pm25 = aggregate_pm25_to_pn_blocks(pm25_tif, blocks_gdf)
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
            "impervious_nodata_policy": "unet_valid_or_osm_valid"
        },
        "inputs": {
            "segmentation": _get_raster_provenance(seg_tif),
            "building": _get_raster_provenance(bldg_tif),
            "road": _get_raster_provenance(road_tif),
            "union": _get_raster_provenance(union_tif),
            "ndvi": _get_raster_provenance(ndvi_tif),
            "temperature": _get_raster_provenance(temp_tif),
            "population": _get_raster_provenance(pop_tif)
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

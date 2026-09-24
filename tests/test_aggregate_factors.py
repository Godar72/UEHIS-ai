import pytest
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
import hashlib
from shapely.geometry import box, Polygon, Point
from feature_engineering.aggregate_factors import (
    validate_grid,
    rasterize_osm_to_grid,
    build_impervious_union,
    aggregate_segmentation_to_blocks,
    aggregate_impervious_to_blocks,
    aggregate_ndvi_to_blocks,
    aggregate_temperature_to_blocks,
    aggregate_population_to_blocks,
    aggregate_all_factors,
    canonical_geometry_hash,
    _rasterize_blocks
)

@pytest.fixture
def dummy_grid_profile():
    return {
        'driver': 'GTiff',
        'dtype': 'uint8',
        'nodata': 255,
        'width': 10,
        'height': 10,
        'count': 1,
        'crs': 'EPSG:4326',
        'transform': rasterio.Affine(0.0001, 0.0, 73.0, 0.0, -0.0001, 18.0)
    }

@pytest.fixture
def tmp_rasters(tmp_path, dummy_grid_profile):
    seg_path = tmp_path / "seg.tif"
    ndvi_path = tmp_path / "ndvi.tif"
    temp_path = tmp_path / "temp.tif"
    bldg_path = tmp_path / "bldg.tif"
    road_path = tmp_path / "road.tif"
    pop_path = tmp_path / "pop.tif"
    union_path = tmp_path / "union.tif"
    
    seg_data = np.zeros((10, 10), dtype=np.uint8)
    seg_data[0:5, 0:5] = 0 # canopy
    seg_data[5:10, 5:10] = 1 # impervious
    seg_data[9, 9] = 255 # nodata
    
    ndvi_data = np.full((10, 10), 0.5, dtype=np.float32)
    ndvi_data[9, 9] = -9999 # nodata
    
    temp_data = np.full((10, 10), 30.0, dtype=np.float32)
    temp_data[9, 9] = np.nan # nodata
    
    bldg_data = np.full((10, 10), 0, dtype=np.uint8)
    bldg_data[0:2, 0:2] = 1
    
    road_data = np.full((10, 10), 0, dtype=np.uint8)
    road_data[0:1, 0:5] = 1
    
    with rasterio.open(seg_path, 'w', **dummy_grid_profile) as dst:
        dst.write(seg_data, 1)
        
    ndvi_prof = dummy_grid_profile.copy()
    ndvi_prof.update(dtype='float32', nodata=-9999)
    with rasterio.open(ndvi_path, 'w', **ndvi_prof) as dst:
        dst.write(ndvi_data, 1)
        
    temp_prof = dummy_grid_profile.copy()
    temp_prof.update(dtype='float32', nodata=np.nan)
    with rasterio.open(temp_path, 'w', **temp_prof) as dst:
        dst.write(temp_data, 1)
        
    with rasterio.open(bldg_path, 'w', **dummy_grid_profile) as dst:
        dst.write(bldg_data, 1)
        
    with rasterio.open(road_path, 'w', **dummy_grid_profile) as dst:
        dst.write(road_data, 1)
        
    build_impervious_union(seg_path, bldg_path, road_path, union_path)
        
    # Population raster
    pop_prof = dummy_grid_profile.copy()
    pop_prof.update(dtype='float32', nodata=-9999)
    pop_data = np.full((10, 10), 10.0, dtype=np.float32)
    with rasterio.open(pop_path, 'w', **pop_prof) as dst:
        dst.write(pop_data, 1)
        
    return {
        'seg': seg_path, 'ndvi': ndvi_path, 'temp': temp_path, 
        'bldg': bldg_path, 'road': road_path, 'pop': pop_path,
        'union': union_path,
        'profile': dummy_grid_profile
    }

@pytest.fixture
def blocks_gdf():
    b1 = box(73.0, 17.9995, 73.0005, 18.0)
    b2 = box(73.0005, 17.9985, 73.0015, 17.9995)
    return gpd.GeoDataFrame({'block_id': ['B1', 'B2']}, geometry=[b1, b2], crs="EPSG:4326")

# --- 1. Geometry Hash Tests ---
def test_geometry_hash():
    geom1 = Point(73.1234567, 18.1234567)
    geom2 = Point(73.123456701, 18.123456701) # Truly sub-millimeter diff in degrees (1e-9 deg ~ 0.1 mm)
    geom3 = Point(74.0, 19.0) # Material diff
    
    h1 = canonical_geometry_hash(geom1, "EPSG:4326")
    h2 = canonical_geometry_hash(geom2, "EPSG:4326")
    h3 = canonical_geometry_hash(geom3, "EPSG:4326")
    
    # 3-decimal precision ensures sub-millimeter differences hash the same
    # But wait, in UTM (32643), 0.001 meters is 1 millimeter. So we check if sub-mm differ.
    assert h1 == h2
    assert h1 != h3
    
    # SHA-256 length is 64 hex chars
    assert len(h1) == 64
    
    # Reprojection determinism
    geom1_utm = gpd.GeoSeries([geom1], crs="EPSG:4326").to_crs("EPSG:32643").iloc[0]
    h1_utm = canonical_geometry_hash(geom1_utm, "EPSG:32643")
    assert h1 == h1_utm

# --- 2. Grid Validation on Production Path ---
def test_grid_validation_shifted_raster(tmp_path, tmp_rasters, blocks_gdf):
    shifted_prof = tmp_rasters['profile'].copy()
    shifted_prof['transform'] = rasterio.Affine(0.0001, 0.0, 74.0, 0.0, -0.0001, 18.0)
    shifted_path = tmp_path / "shifted.tif"
    with rasterio.open(shifted_path, 'w', **shifted_prof) as dst:
        dst.write(np.zeros((10,10), dtype=np.uint8), 1)
        
    with pytest.raises(ValueError, match="Transform mismatch"):
        build_impervious_union(tmp_rasters['seg'], shifted_path, tmp_rasters['road'], tmp_path / "u.tif")
        
    with pytest.raises(ValueError, match="Transform mismatch"):
        aggregate_all_factors(blocks_gdf, tmp_rasters['seg'], tmp_rasters['bldg'], tmp_rasters['road'], tmp_rasters['union'], shifted_path, tmp_rasters['temp'], tmp_rasters['pop'], None)

# --- 3 & 7. Population Nodata & Conservation Tests ---
def test_population_conservation(tmp_path, tmp_rasters, dummy_grid_profile):
    pop_path = tmp_path / "test_pop.tif"
    pop_prof = dummy_grid_profile.copy()
    # 2x2 grid in UTM for precise area testing
    pop_prof.update(crs="EPSG:32643", width=2, height=2, transform=rasterio.Affine(100.0, 0.0, 300000.0, 0.0, -100.0, 2000000.0), dtype='float32', nodata=-9999)
    pop_data = np.array([[100.0, 200.0], [300.0, 400.0]], dtype=np.float32)
    with rasterio.open(pop_path, 'w', **pop_prof) as dst:
        dst.write(pop_data, 1)
        
    # A. All cells fully contained in one block
    b_all = box(300000.0, 1999800.0, 300200.0, 2000000.0)
    gdf_all = gpd.GeoDataFrame({'block_id': ['All']}, geometry=[b_all], crs="EPSG:32643")
    block_arr_all = _rasterize_blocks(gdf_all, pop_prof)
    res_all = aggregate_population_to_blocks(str(pop_path), block_arr_all, 1)
    assert np.isclose(res_all.loc[0, 'population_exposure'], 1000.0)
    
    # B. One cell split across two blocks (top-left cell: 100 pop)
    b_left = box(300000.0, 1999900.0, 300050.0, 2000000.0)
    b_right = box(300050.0, 1999900.0, 300100.0, 2000000.0)
    gdf_split = gpd.GeoDataFrame({'block_id': ['L', 'R']}, geometry=[b_left, b_right], crs="EPSG:32643")
    block_arr_split = _rasterize_blocks(gdf_split, pop_prof)
    res_split = aggregate_population_to_blocks(str(pop_path), block_arr_split, 2)
    
    # In raster-first zonal aggregation (center-based), the center (300050, 1999950)
    # belongs strictly to one block based on polygon overlap. 
    # For a 100x100 pixel, if center falls exactly on boundary, it goes to one. 
    # Total conserved is 100.
    total_split = res_split['population_exposure'].sum()
    assert np.isclose(total_split, 100.0)
    
    # E. No coverage -> NaN
    b_miss = box(400000.0, 1999800.0, 400200.0, 2000000.0)
    gdf_miss = gpd.GeoDataFrame({'block_id': ['Miss']}, geometry=[b_miss], crs="EPSG:32643")
    block_arr_miss = _rasterize_blocks(gdf_miss, pop_prof)
    res_miss = aggregate_population_to_blocks(str(pop_path), block_arr_miss, 1)
    assert np.isnan(res_miss.loc[0, 'population_exposure'])

# --- 5. Impervious Nodata Policy ---
def test_impervious_nodata_policy(tmp_path, dummy_grid_profile):
    unet_path = tmp_path / "u.tif"
    bldg_path = tmp_path / "b.tif"
    road_path = tmp_path / "r.tif"
    union_path = tmp_path / "union.tif"
    
    unet = np.full((10,10), 255, dtype=np.uint8)
    bldg = np.full((10,10), 255, dtype=np.uint8)
    road = np.full((10,10), 255, dtype=np.uint8)
    
    # F. All sources valid (pervious by default, imp if 1)
    unet[0,0], bldg[0,0], road[0,0] = 0, 0, 0 # Valid, pervious
    unet[0,1], bldg[0,1], road[0,1] = 1, 0, 0 # Valid, imp from unet
    
    # C/D. UNet nodata + OSM valid
    unet[1,0], bldg[1,0], road[1,0] = 255, 1, 255 # UNet nodata, bldg imp -> imp
    unet[1,1], bldg[1,1], road[1,1] = 255, 255, 1 # UNet nodata, road imp -> imp
    unet[1,2], bldg[1,2], road[1,2] = 255, 0, 0 # UNet nodata, OSM pervious -> pervious
    
    # E. All nodata
    # [2,2] left as 255 for all
    
    with rasterio.open(unet_path, 'w', **dummy_grid_profile) as dst: dst.write(unet, 1)
    with rasterio.open(bldg_path, 'w', **dummy_grid_profile) as dst: dst.write(bldg, 1)
    with rasterio.open(road_path, 'w', **dummy_grid_profile) as dst: dst.write(road, 1)
    
    build_impervious_union(unet_path, bldg_path, road_path, union_path)
    with rasterio.open(union_path) as src:
        union = src.read(1)
        
    assert union[0,0] == 0 # Pervious
    assert union[0,1] == 1 # Imp
    assert union[1,0] == 1 # Imp from bldg
    assert union[1,1] == 1 # Imp from road
    assert union[1,2] == 0 # Pervious from OSM
    assert union[2,2] == 255 # All nodata -> Nodata

# --- 8. CRS Mismatch Correctness Test ---
def test_crs_mismatch_correctness(tmp_rasters):
    b = box(73.0, 17.9995, 73.0005, 18.0)
    gdf_native = gpd.GeoDataFrame({'block_id': ['B1']}, geometry=[b], crs="EPSG:4326")
    gdf_proj = gdf_native.to_crs("EPSG:3857")
    
    with rasterio.open(tmp_rasters['seg']) as src:
        unet_data = src.read(1)
        prof = src.profile
    
    block_arr_native = _rasterize_blocks(gdf_native, prof)
    block_arr_proj = _rasterize_blocks(gdf_proj, prof)
    
    res_native = aggregate_segmentation_to_blocks(unet_data, prof, block_arr_native, 1)
    res_proj = aggregate_segmentation_to_blocks(unet_data, prof, block_arr_proj, 1)
    
    pd.testing.assert_frame_equal(res_native, res_proj)

# --- 12. Irregular OSM Rasterization ---
def test_osm_irregular_rasterization(tmp_path, dummy_grid_profile):
    target = tmp_path / "target.tif"
    with rasterio.open(target, 'w', **dummy_grid_profile) as dst:
        dst.write(np.zeros((10,10), dtype=np.uint8), 1)
        
    # Pixel (0,0) bounds: X(73.0, 73.0001), Y(17.9999, 18.0). Center is (73.00005, 17.99995)
    # Pixel (0,1) bounds: X(73.0001, 73.0002), Y(17.9999, 18.0). Center is (73.00015, 17.99995)
    
    # Polygon covers all of (0,0) and the left 20% of (0,1)
    # It strictly includes the center of (0,0) but strictly avoids the center of (0,1)
    poly = Polygon([(73.0, 18.0), (73.00012, 18.0), (73.00012, 17.9999), (73.0, 17.9999)])
    gdf = gpd.GeoDataFrame(geometry=[poly], crs="EPSG:4326")
    out = tmp_path / "osm.tif"
    
    rasterize_osm_to_grid(gdf, target, out)
    
    with rasterio.open(out) as src:
        arr = src.read(1)
        
    # Assert actual rasterization behavior
    assert arr[0, 0] == 1 # >50% covered (center inside)
    assert arr[0, 1] == 0 # <50% covered (center outside)

# --- 13. Provenance Manifest Tests ---
def test_provenance_manifest(tmp_rasters, blocks_gdf):
    df1, manifest1 = aggregate_all_factors(blocks_gdf, tmp_rasters['seg'], tmp_rasters['bldg'], tmp_rasters['road'], tmp_rasters['union'], tmp_rasters['ndvi'], tmp_rasters['temp'], tmp_rasters['pop'], None)
    df2, manifest2 = aggregate_all_factors(blocks_gdf, tmp_rasters['seg'], tmp_rasters['bldg'], tmp_rasters['road'], tmp_rasters['union'], tmp_rasters['ndvi'], tmp_rasters['temp'], tmp_rasters['pop'], None)
    
    # 1. Separate calls generate different run IDs
    assert manifest1['run_id'] != manifest2['run_id']
    
    # 4. Manifest contains required provenance fields
    assert "git_commit" in manifest1
    assert "aggregation_version" in manifest1
    assert "processing_configuration" in manifest1
    
    seg_prov = manifest1['inputs']['segmentation']
    assert "path" in seg_prov
    assert "dataset_identity" in seg_prov
    assert "acquisition_date" in seg_prov
    assert "spatial_resolution" in seg_prov
    assert "crs" in seg_prov
    assert "content_sha256" in seg_prov
    
    # 2. Content hash is a real SHA-256 hash (64 hex chars)
    h = seg_prov['content_sha256']
    assert len(h) == 64
    
    # 5. Unknown metadata represented explicitly
    assert seg_prov['acquisition_date'] == "unknown"
    assert seg_prov['dataset_identity'] == "unknown"
    
    # 3. Changing an input changes its content hash
    with open(tmp_rasters['seg'], 'ab') as f:
        f.write(b'\x00') # append a null byte to change hash
        
    _, manifest3 = aggregate_all_factors(blocks_gdf, tmp_rasters['seg'], tmp_rasters['bldg'], tmp_rasters['road'], tmp_rasters['union'], tmp_rasters['ndvi'], tmp_rasters['temp'], tmp_rasters['pop'], None)
    assert manifest3['inputs']['segmentation']['content_sha256'] != h

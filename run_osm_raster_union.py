"""
Phase 7: Impervious Surface rasterization and pixel-wise union.
"""
import sys
from pathlib import Path

import geopandas as gpd
import rasterio
from rasterio.features import rasterize
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from data_ingestion.osm_features import fetch_building_footprints, fetch_road_network

def compute_bounds(lon: float, lat: float, buffer_m: float):
    import math
    lat_offset = buffer_m / 111_320
    lon_offset = buffer_m / (111_320 * math.cos(math.radians(lat)))
    west  = lon - lon_offset
    east  = lon + lon_offset
    south = lat - lat_offset
    north = lat + lat_offset
    return (west, south, east, north)

def run_osm_raster_union():
    LONGITUDE = 73.8077
    LATITUDE  = 18.5074
    BUFFER_M  = 2000

    OUT_DIR = Path("outputs/unet_inference_v2")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    
    BUILDINGS_PATH = OUT_DIR / "kothrud_buildings.geojson"
    ROADS_PATH     = OUT_DIR / "kothrud_roads.geojson"
    
    SEG_TIF = OUT_DIR / "production_segmentation.tif"
    FINAL_IMPERVIOUS_TIF = OUT_DIR / "final_impervious_union.tif"
    
    bounds = compute_bounds(LONGITUDE, LATITUDE, BUFFER_M)
    
    print("\n--- Fetching OSM data ---")
    buildings = fetch_building_footprints(bounds, output_path=str(BUILDINGS_PATH))
    roads = fetch_road_network(bounds, network_type="all", output_path=str(ROADS_PATH))
    
    print(f"\n--- Reading U-Net segmentation from {SEG_TIF} ---")
    if not SEG_TIF.exists():
        print("ERROR: U-Net segmentation raster not found. Run inference first.")
        return
        
    with rasterio.open(SEG_TIF) as src:
        unet_map = src.read(1)
        transform = src.transform
        crs = src.crs
        out_shape = unet_map.shape
        profile = src.profile.copy()
        nodata = src.nodata if src.nodata is not None else 255
        
    unet_impervious = (unet_map == 1).astype(np.uint8)
    
    print("\n--- Rasterizing OSM features ---")
    if not buildings.empty and buildings.crs != crs:
        buildings = buildings.to_crs(crs)
    if not roads.empty and roads.crs != crs:
        roads = roads.to_crs(crs)
        
    if not buildings.empty:
        osm_buildings = rasterize(
            [(geom, 1) for geom in buildings.geometry],
            out_shape=out_shape,
            transform=transform,
            fill=0,
            dtype=np.uint8
        )
    else:
        osm_buildings = np.zeros(out_shape, dtype=np.uint8)
        
    if not roads.empty:
        if crs.is_projected:
            roads['geometry'] = roads.geometry.buffer(4.0)
        else:
            roads['geometry'] = roads.geometry.buffer(0.00004)
            
        osm_roads = rasterize(
            [(geom, 1) for geom in roads.geometry],
            out_shape=out_shape,
            transform=transform,
            fill=0,
            dtype=np.uint8
        )
    else:
        osm_roads = np.zeros(out_shape, dtype=np.uint8)
        
    osm_impervious = np.maximum(osm_buildings, osm_roads)
    final_impervious = np.maximum(unet_impervious, osm_impervious)
    final_impervious[unet_map == nodata] = nodata
    
    print("\n--- Summary ---")
    valid_mask = (unet_map != nodata)
    valid_pixels = int(valid_mask.sum())
    print(f"Total valid pixels: {valid_pixels:,}")
    print(f"U-Net Impervious pixels: {unet_impervious[valid_mask].sum():,}")
    print(f"OSM Buildings pixels: {osm_buildings[valid_mask].sum():,}")
    print(f"OSM Roads pixels: {osm_roads[valid_mask].sum():,}")
    print(f"OSM Impervious pixels: {osm_impervious[valid_mask].sum():,}")
    print(f"Final Impervious pixels: {(final_impervious == 1)[valid_mask].sum():,}")
    
    profile.update(
        dtype=rasterio.uint8,
        count=1,
        compress="lzw",
        nodata=nodata
    )
    
    with rasterio.open(FINAL_IMPERVIOUS_TIF, "w", **profile) as dst:
        dst.write(final_impervious, 1)
        
    print(f"\n[Output] Saved Final Impervious Raster to {FINAL_IMPERVIOUS_TIF.resolve()}")
    
if __name__ == "__main__":
    run_osm_raster_union()

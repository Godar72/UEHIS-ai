import os
import json
import numpy as np
import rasterio
from rasterio.warp import reproject, Resampling
from rasterio.transform import Affine
from rasterio.windows import Window
import requests
from pathlib import Path
import ee
from dotenv import load_dotenv
from datetime import datetime

# Authenticate EE
load_dotenv()
ee.Initialize(project=os.getenv('GEE_PROJECT_ID'))

OUT_DIR = Path("outputs/unet_validation")
OUT_DIR.mkdir(parents=True, exist_ok=True)
SLOPE_TIF = OUT_DIR / "srtm_slope_kothrud_10m.tif"
SLOPE_META = OUT_DIR / "srtm_slope_kothrud_10m.json"
FIVE_CHANNEL_TIF = OUT_DIR / "kothrud_5channel_input.tif"
COMPOSITE_TIF = Path("kothrud_pune_composite.tif")

def get_ee_download_url(image, bounds_dict, crs, transform_list, dimensions):
    """Get direct download URL for an EE image with exact grid specs."""
    try:
        url = image.getDownloadURL({
            'format': 'GEO_TIFF',
            'crs': crs,
            'crs_transform': transform_list,
            'dimensions': dimensions
        })
        return url
    except Exception as e:
        print(f"Error getting URL: {e}")
        raise

def fetch_and_save_slope():
    # 1. Read composite grid specs
    with rasterio.open(COMPOSITE_TIF) as src:
        prof = src.profile.copy()
        bounds = src.bounds
        width = src.width
        height = src.height
        crs_str = src.crs.to_string() # e.g. 'EPSG:4326' or 'EPSG:32643'
        transform = src.transform
        
    print(f"Composite CRS: {crs_str}")
    print(f"Composite Transform: {transform}")
    print(f"Composite Dimensions: {width}x{height}")
    
    # transform is (a, b, c, d, e, f) in affine
    transform_list = [transform.a, transform.b, transform.c, transform.d, transform.e, transform.f]
    dimensions = f"{width}x{height}"
    
    # 2. EE Slope Calculation
    # Compute slope first at native SRTM resolution
    dem = ee.Image("USGS/SRTMGL1_003")
    slope = ee.Terrain.slope(dem)
    # Apply bilinear resampling for when it is reprojected to the 10m export grid
    slope = slope.resample('bilinear')
    
    # 3. Export exactly on target grid
    # Get download URL
    print("Requesting download URL from EE...")
    url = get_ee_download_url(slope, None, crs_str, transform_list, dimensions)
    
    print("Downloading slope raster...")
    resp = requests.get(url)
    resp.raise_for_status()
    
    with open(SLOPE_TIF, 'wb') as f:
        f.write(resp.content)
        
    # 4. Validate slope
    print("Validating downloaded slope...")
    with rasterio.open(SLOPE_TIF) as src:
        slope_data = src.read(1)
        slope_prof = src.profile
        
    assert slope_prof['width'] == width, "Width mismatch"
    assert slope_prof['height'] == height, "Height mismatch"
    assert slope_prof['crs'].to_string() == crs_str, "CRS mismatch"
    assert slope_prof['transform'] == transform, "Transform mismatch"
    
    valid_mask = slope_data != src.nodata if src.nodata is not None else np.isfinite(slope_data)
    valid_slope = slope_data[valid_mask]
    
    min_s = float(valid_slope.min())
    max_s = float(valid_slope.max())
    mean_s = float(valid_slope.mean())
    median_s = float(np.median(valid_slope))
    nodata_count = int((~valid_mask).sum())
    total_pixels = slope_data.size
    
    assert min_s >= 0.0, f"Slope min {min_s} < 0"
    assert max_s <= 90.0, f"Slope max {max_s} > 90"
    
    meta = {
        "source_dataset": "USGS/SRTMGL1_003",
        "slope_method": "ee.Terrain.slope",
        "native_resolution": "approx 30m",
        "target_resolution": "10m",
        "resampling_method": "bilinear",
        "crs": crs_str,
        "transform": transform_list,
        "dimensions": [width, height],
        "bounds": [bounds.left, bounds.bottom, bounds.right, bounds.top],
        "min_slope": min_s,
        "max_slope": max_s,
        "mean_slope": mean_s,
        "median_slope": median_s,
        "nodata_count": nodata_count,
        "nodata_percentage": (nodata_count / total_pixels) * 100,
        "generation_timestamp": datetime.now().isoformat(),
        "validation": "PASSED"
    }
    
    with open(SLOPE_META, 'w') as f:
        json.dump(meta, f, indent=2)
        
    print(f"Slope validation PASSED. Min: {min_s:.2f}, Max: {max_s:.2f}, Mean: {mean_s:.2f}")
    
    # 5. Construct 5-channel input
    print("Constructing 5-channel input...")
    with rasterio.open(COMPOSITE_TIF) as src:
        comp_data = src.read()
        prof = src.profile.copy()
        
    prof.update(count=5)
    
    with rasterio.open(FIVE_CHANNEL_TIF, 'w', **prof) as dst:
        for i in range(4):
            dst.write(comp_data[i], i + 1)
        dst.write(slope_data, 5)
        
    print(f"5-channel input saved to {FIVE_CHANNEL_TIF}")
    
if __name__ == "__main__":
    fetch_and_save_slope()

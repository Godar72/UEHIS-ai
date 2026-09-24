"""
data_ingestion/acag_pm25.py
───────────────────────────
Fetches ACAG/WUSTL SatPM V6.GL.03 PM2.5 monthly estimates from Google Earth Engine,
computes a seasonal mean (Jan, Feb, Mar 2024), and aligns/resamples the raster
to match a given reference grid (UEHIS 250m block grid).

Provenance and ACAG metadata are handled strictly.
"""

import os
import json
import hashlib
import sys
import subprocess
from datetime import datetime
from pathlib import Path

import ee
import geemap
import numpy as np
import rasterio
from rasterio.warp import reproject, Resampling
from rasterio.transform import Affine

from data_ingestion.sentinel import authenticate_gee

# ---------------------------------------------------------------------------
# Configuration (ACAG PM2.5)
# ---------------------------------------------------------------------------
ACAG_GEE_COLLECTION = 'projects/gee-community-catalog/datasets/pm25_monthly'
PM25_YEAR = 2024
PM25_MONTHS = [1, 2, 3]  # Jan, Feb, Mar

class PM25FetchError(Exception):
    """Raised when PM2.5 fetch or validation fails."""
    pass

def _get_git_commit():
    try:
        return subprocess.check_output(['git', 'rev-parse', 'HEAD'], stderr=subprocess.DEVNULL, text=True).strip()
    except Exception:
        return "unknown"

def _hash_file(filepath):
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

def fetch_and_align_acag_pm25(
    roi_bounds: tuple[float, float, float, float],
    reference_tif_path: str,
    output_dir: str = "outputs/pm25"
) -> tuple[str, dict]:
    """
    Fetch ACAG PM2.5 from GEE for Jan-Mar 2024, compute mean, download native raster,
    and then strictly align (reproject + bilinear resample) to the reference_tif_path.
    
    Parameters
    ----------
    roi_bounds : tuple
        (west, south, east, north) in EPSG:4326.
    reference_tif_path : str
        Path to a reference GeoTIFF (e.g. unet segmentation) to align to exactly.
    output_dir : str
        Directory to save outputs.
        
    Returns
    -------
    tuple[str, dict]
        Path to the aligned seasonal PM2.5 GeoTIFF and its provenance manifest.
    """
    authenticate_gee()
    
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Temporal Validation
    start_date = f"{PM25_YEAR}-01-01"
    end_date = f"{PM25_YEAR}-04-01"
    
    col = ee.ImageCollection(ACAG_GEE_COLLECTION).filterDate(start_date, end_date)
    count = col.size().getInfo()
    
    if count != 3:
        raise PM25FetchError(
            f"Expected exactly 3 monthly images (Jan, Feb, Mar {PM25_YEAR}) but found {count}."
            " Cannot silently substitute missing data."
        )
        
    print(f"[PM2.5] Found {count} monthly grids for {PM25_YEAR}.")
    
    # Check that months are strictly 1, 2, 3
    img_list = col.toList(count)
    found_months = []
    for i in range(count):
        img = ee.Image(img_list.get(i))
        # The ACAG monthly images usually have system:time_start
        date = ee.Date(img.get('system:time_start')).getInfo()
        month = datetime.utcfromtimestamp(date['value']/1000.0).month
        found_months.append(month)
        
    if sorted(found_months) != sorted(PM25_MONTHS):
        raise PM25FetchError(
            f"Missing required months. Found: {found_months}, Expected: {PM25_MONTHS}"
        )
        
    print(f"[PM2.5] Verified months: {found_months}")
    
    # 2. Strict Band Validation
    first_img = ee.Image(img_list.get(0))
    band_names = first_img.bandNames().getInfo()
    if 'b1' not in band_names:
        raise PM25FetchError(f"Expected band 'b1' not found in collection. Available: {band_names}")
    
    col = col.select('b1')
    
    # 3. Compute Seasonal Mean with Strict 3-Month Validity
    # A pixel is only valid if it has valid data in all 3 months.
    valid_count = col.count()
    seasonal_mean = col.mean().updateMask(valid_count.eq(3))
    
    # 4. Export Native Raster (Buffered)
    west, south, east, north = roi_bounds
    # Buffer by ~0.05 deg (~5km) to ensure edge coverage during resampling
    buffer = 0.05
    export_roi = ee.Geometry.Rectangle([west - buffer, south - buffer, east + buffer, north + buffer])
    
    native_tif = os.path.join(output_dir, f"pm25_acag_v6gl03_{PM25_YEAR}_jan_mar_native.tif")
    
    print("[PM2.5] Downloading native PM2.5 raster from GEE...")
    geemap.ee_export_image(
        seasonal_mean,
        filename=native_tif,
        scale=1113.2, # ~0.01 deg
        region=export_roi,
        file_per_band=False,
    )
    
    if not os.path.exists(native_tif):
        raise PM25FetchError("Failed to download native raster from GEE.")
        
    # 4. Strict Alignment to Reference Grid
    aligned_tif = os.path.join(output_dir, f"pm25_acag_v6gl03_{PM25_YEAR}_jan_mar_seasonal_aligned.tif")
    
    with rasterio.open(reference_tif_path) as ref_src:
        ref_profile = ref_src.profile.copy()
        ref_crs = ref_src.crs
        ref_transform = ref_src.transform
        ref_width = ref_src.width
        ref_height = ref_src.height
        
    print(f"[PM2.5] Aligning to reference grid ({ref_width}x{ref_height}, {ref_crs})...")
    
    with rasterio.open(native_tif) as src:
        # We enforce Bilinear resampling for continuous PM2.5
        dst_array = np.empty((ref_height, ref_width), dtype=np.float32)
        
        reproject(
            source=rasterio.band(src, 1),
            destination=dst_array,
            src_transform=src.transform,
            src_crs=src.crs,
            dst_transform=ref_transform,
            dst_crs=ref_crs,
            resampling=Resampling.bilinear,
            src_nodata=src.nodata,
            dst_nodata=np.nan
        )
        
    # Removed value-based nodata masking (dst_array[dst_array <= 0] = np.nan)
    
    ref_profile.update(
        dtype=rasterio.float32,
        count=1,
        nodata=np.nan,
        compress='lzw'
    )
    
    with rasterio.open(aligned_tif, 'w', **ref_profile) as dst:
        dst.write(dst_array, 1)
        # Provenance tags
        dst.update_tags(
            dataset_identity="ACAG_V6GL03_SatPM25",
            temporal_window=f"{PM25_YEAR}-01 to {PM25_YEAR}-03",
            temporal_design="seasonal_mean_jan_feb_mar_strict",
            native_resolution="0.01 degrees",
            resampling_method="bilinear",
            processing_date=datetime.now().isoformat()
        )
        
    print(f"[PM2.5] Aligned raster saved to: {aligned_tif}")
    
    manifest = {
        "run_id": f"pm25_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{os.urandom(4).hex()}",
        "source_name": "ACAG/WUSTL SatPM",
        "product_version": "V6.GL.03",
        "source_url": "projects/gee-community-catalog/datasets/pm25_monthly",
        "download_date": datetime.now().isoformat(),
        "source_file_sha256": _hash_file(native_tif),
        "aligned_file_sha256": _hash_file(aligned_tif),
        "source_variable_name": "b1",
        "source_units": "ug/m3",
        "source_native_crs": str(src.crs),
        "source_native_spatial_resolution": "0.01 degrees",
        "requested_months": PM25_MONTHS,
        "selected_image_months": found_months,
        "seasonal_aggregation_rule": "Strict 3-month arithmetic mean (masked if any month missing)",
        "reprojection_crs": str(ref_crs),
        "target_uehis_grid_dimensions": f"{ref_width}x{ref_height}",
        "target_resolution": f"{ref_transform[0]}x{-ref_transform[4]} meters",
        "target_affine_transform": [ref_transform.a, ref_transform.b, ref_transform.c, ref_transform.d, ref_transform.e, ref_transform.f],
        "target_bounds": [ref_src.bounds.left, ref_src.bounds.bottom, ref_src.bounds.right, ref_src.bounds.top],
        "resampling_method": "bilinear",
        "nodata_handling": "Native nodata mapped to NaN; no value-based masking",
        "code_version": _get_git_commit(),
        "python_version": sys.version.split()[0]
    }
    
    manifest_path = os.path.join(output_dir, "pm25_provenance.json")
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)
        
    return aligned_tif, manifest

if __name__ == "__main__":
    # Test run
    # ROI: Pune bounds
    roi = (73.7498, 18.4295, 74.0202, 18.6209)
    # Require a reference TIF to exist. We can use outputs/kothrud_ndvi_segmentation.tif if it exists,
    # or just exit with a warning.
    ref_tif = Path("outputs/kothrud_ndvi_segmentation.tif")
    if ref_tif.exists():
        align, man = fetch_and_align_acag_pm25(roi, str(ref_tif))
        print("Success. Run ID:", man["run_id"])
    else:
        print(f"Test skipped: Reference TIF {ref_tif} not found.")

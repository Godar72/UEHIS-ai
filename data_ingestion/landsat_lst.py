"""
data_ingestion/landsat_lst.py
─────────────────────────────
Fetches Landsat 8 Collection 2 Level 2 surface temperature (ST_B10),
converts to Land Surface Temperature in Celsius, and provides helpers
to export a GeoTIFF and aggregate LST values to a block grid.

Conversion formula (USGS standard):
    LST_K  = DN × 0.00341802 + 149.0
    LST_C  = LST_K − 273.15
"""

import os
import math

import ee
import geemap
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.mask import mask as rasterio_mask
from shapely.geometry import mapping
from dotenv import load_dotenv

from data_ingestion.sentinel import (
    authenticate_gee,
    EmptyCollectionError,
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

load_dotenv()

# Landsat 8 ST_B10 scale factor & offset (Collection 2 Level 2)
_SCALE_FACTOR = 0.00341802
_OFFSET       = 149.0
_K_TO_C       = 273.15


# ---------------------------------------------------------------------------
# Cloud masking
# ---------------------------------------------------------------------------

def _mask_l8_clouds(image: ee.Image) -> ee.Image:
    """
    Apply QA_PIXEL bitmask cloud/shadow mask for Landsat 8 C2 L2.

    Bits used:
        bit 3 – cloud  (1 = cloud)
        bit 4 – cloud shadow  (1 = shadow)
    Pixels flagged as cloud or shadow are masked out.
    """
    qa = image.select("QA_PIXEL")
    cloud_bit = 1 << 3
    shadow_bit = 1 << 4
    mask = (
        qa.bitwiseAnd(cloud_bit).eq(0)
        .And(qa.bitwiseAnd(shadow_bit).eq(0))
    )
    return image.updateMask(mask)


# ---------------------------------------------------------------------------
# LST conversion
# ---------------------------------------------------------------------------

def _apply_lst_conversion(image: ee.Image) -> ee.Image:
    """
    Convert Landsat 8 C2 L2 ST_B10 digital numbers to LST in °C.

    Formula:  LST_C = DN × 0.00341802 + 149.0 − 273.15
    """
    lst_kelvin = (
        image.select("ST_B10")
        .multiply(_SCALE_FACTOR)
        .add(_OFFSET)
    )
    lst_celsius = lst_kelvin.subtract(_K_TO_C).rename("LST_C")
    return image.addBands(lst_celsius)


# ---------------------------------------------------------------------------
# Landsat 8 LST composite
# ---------------------------------------------------------------------------

def get_landsat8_lst(
    region: ee.Geometry,
    start_date: str,
    end_date: str,
    max_cloud_pct: float = 20,
) -> ee.Image:
    """
    Build a median Land Surface Temperature composite from Landsat 8 C2 L2.

    Parameters
    ----------
    region : ee.Geometry
        Area of interest.
    start_date, end_date : str
        ISO-format date range.
    max_cloud_pct : float
        Maximum scene-level cloud cover percentage (default 20 %).

    Returns
    -------
    ee.Image
        Single-band image (``LST_C``) in degrees Celsius, clipped to *region*.

    Raises
    ------
    EmptyCollectionError
        If no images remain after filtering.
    """
    collection = (
        ee.ImageCollection("LANDSAT/LC08/C02/T1_L2")
        .filterBounds(region)
        .filterDate(start_date, end_date)
        .filter(ee.Filter.lt("CLOUD_COVER", max_cloud_pct))
        .map(_mask_l8_clouds)
        .map(_apply_lst_conversion)
    )

    count = collection.size().getInfo()
    if count == 0:
        raise EmptyCollectionError(
            f"No Landsat 8 images found for the given region "
            f"between {start_date} and {end_date} with cloud cover < {max_cloud_pct}%."
        )

    print(f"[Landsat-8] {count} images matched -- computing median LST composite.")
    composite = collection.select("LST_C").median().clip(region)
    return composite


# ---------------------------------------------------------------------------
# GeoTIFF export
# ---------------------------------------------------------------------------

def export_lst_geotiff(
    lst_image: ee.Image,
    region: ee.Geometry,
    filename: str = "outputs/kothrud_lst.tif",
    scale: int = 30,
) -> str:
    """
    Download the LST composite as a GeoTIFF.

    Parameters
    ----------
    lst_image : ee.Image
        Single-band LST image (``LST_C``).
    region : ee.Geometry
        Bounding region for the export.
    filename : str
        Output file path.
    scale : int
        Spatial resolution in metres (default 30 m — Landsat native).

    Returns
    -------
    str
        Absolute path to the saved GeoTIFF.
    """
    geemap.ee_export_image(
        lst_image,
        filename=filename,
        scale=scale,
        region=region,
        file_per_band=False,
    )
    abs_path = os.path.abspath(filename)
    print(f"[Export] LST GeoTIFF saved to {abs_path}")
    return abs_path


# ---------------------------------------------------------------------------
# Aggregate LST to 250 m block grid
# ---------------------------------------------------------------------------

def aggregate_lst_to_blocks(
    lst_tif_path: str,
    block_grid: gpd.GeoDataFrame,
) -> pd.Series:
    """
    Compute the mean LST (°C) for each block in a grid from a raster.

    Parameters
    ----------
    lst_tif_path : str or Path
        Path to the LST GeoTIFF (single band, values in °C).
    block_grid : gpd.GeoDataFrame
        Grid of block polygons (must have a CRS set).

    Returns
    -------
    pd.Series
        Mean LST per block (index aligned with *block_grid*).
        Blocks with no valid pixels are ``NaN``.
    """
    lst_values = []

    with rasterio.open(str(lst_tif_path)) as src:
        raster_crs = src.crs
        # Reproject blocks to raster CRS if needed
        if block_grid.crs != raster_crs:
            grid_reprojected = block_grid.to_crs(raster_crs)
        else:
            grid_reprojected = block_grid

        nodata = src.nodata

        for idx in range(len(grid_reprojected)):
            geom = grid_reprojected.geometry.iloc[idx]
            try:
                out_image, _ = rasterio_mask(
                    src,
                    [mapping(geom)],
                    crop=True,
                    all_touched=True,
                )
                pixels = out_image[0]  # single band

                # Mask nodata and unreasonable values
                valid_mask = np.ones_like(pixels, dtype=bool)
                if nodata is not None:
                    valid_mask &= pixels != nodata
                # LST should be in a reasonable range (-40 to 70 °C)
                valid_mask &= (pixels > -40) & (pixels < 70)

                valid_pixels = pixels[valid_mask]
                if len(valid_pixels) > 0:
                    lst_values.append(round(float(np.mean(valid_pixels)), 2))
                else:
                    lst_values.append(np.nan)
            except Exception:
                # Block doesn't overlap raster at all
                lst_values.append(np.nan)

    return pd.Series(lst_values, index=block_grid.index, name="lst_celsius")


# ---------------------------------------------------------------------------
# Convenience entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # ── Region of Interest: Kothrud, Pune (same as sentinel.py) ──
    LONGITUDE = 73.8077
    LATITUDE  = 18.5074
    BUFFER_M  = 2000  # 2 kilometres

    # Date windows (same as Sentinel-2 module)
    START_DATE = "2024-01-01"
    END_DATE   = "2024-03-31"

    # Widened fallback window
    WIDE_START = "2023-01-01"
    WIDE_END   = "2024-12-31"

    OUTPUT_FILE = "outputs/kothrud_lst.tif"

    authenticate_gee()

    roi = ee.Geometry.Point([LONGITUDE, LATITUDE]).buffer(BUFFER_M)

    # ── Attempt 1: narrow date range ──
    try:
        print(f"\n[Run] Date range: {START_DATE} to {END_DATE}")
        lst_composite = get_landsat8_lst(roi, START_DATE, END_DATE)
        date_used = (START_DATE, END_DATE)
    except EmptyCollectionError:
        # ── Attempt 2: widened date range ──
        print(
            f"[Retry] No cloud-free Landsat images in {START_DATE}-{END_DATE}. "
            f"Widening to {WIDE_START}-{WIDE_END} and retrying..."
        )
        print(f"\n[Run] Date range: {WIDE_START} to {WIDE_END}")
        lst_composite = get_landsat8_lst(roi, WIDE_START, WIDE_END)
        date_used = (WIDE_START, WIDE_END)

    # ── Summary ──
    print(f"\n{'='*50}")
    print(f"Source        : Landsat 8 Collection 2 Level 2")
    print(f"Band          : ST_B10 -> LST (Celsius)")
    print(f"Region        : Kothrud, Pune")
    print(f"Centre        : {LATITUDE} N, {LONGITUDE} E")
    print(f"Buffer        : {BUFFER_M / 1000:.0f} km")
    print(f"Date range    : {date_used[0]} to {date_used[1]}")
    print("Cloud filter  : < 20%")
    print(f"{'='*50}")

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    export_lst_geotiff(lst_composite, region=roi, filename=OUTPUT_FILE)

"""
data_ingestion/worldpop.py
--------------------------
Downloads WorldPop gridded population data via Google Earth Engine,
clips to the Kothrud ROI, and aggregates population counts to a
250m block grid.

Uses the ``WorldPop/GP/100m/pop`` ImageCollection on GEE (100m
resolution, UN-adjusted population counts).
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

# WorldPop GEE dataset
_WORLDPOP_COLLECTION = "WorldPop/GP/100m/pop"
_COUNTRY = "IND"  # ISO3 for India
_YEAR = 2020      # most recent complete year


# ---------------------------------------------------------------------------
# WorldPop population raster
# ---------------------------------------------------------------------------

def get_worldpop_population(
    region: ee.Geometry,
    country: str = _COUNTRY,
    year: int = _YEAR,
) -> ee.Image:
    """
    Fetch the WorldPop 100m population grid for a region.

    Parameters
    ----------
    region : ee.Geometry
        Area of interest.
    country : str
        ISO3 country code (default ``"IND"``).
    year : int
        Year of the population estimate (default 2020).

    Returns
    -------
    ee.Image
        Single-band image (``population``) with people per 100m pixel,
        clipped to *region*.

    Raises
    ------
    EmptyCollectionError
        If no matching WorldPop image is found.
    """
    collection = (
        ee.ImageCollection(_WORLDPOP_COLLECTION)
        .filter(ee.Filter.eq("country", country))
        .filter(ee.Filter.eq("year", year))
        .select("population")
    )

    count = collection.size().getInfo()
    if count == 0:
        raise EmptyCollectionError(
            f"No WorldPop image found for country={country}, year={year}."
        )

    print(f"[WorldPop] {count} image(s) matched for {country} {year} "
          f"-- clipping to ROI.")
    image = collection.mosaic().clip(region)
    return image


# ---------------------------------------------------------------------------
# GeoTIFF export
# ---------------------------------------------------------------------------

def export_population_geotiff(
    pop_image: ee.Image,
    region: ee.Geometry,
    filename: str = "outputs/kothrud_population.tif",
    scale: int = 100,
) -> str:
    """
    Download the population raster as a GeoTIFF.

    Parameters
    ----------
    pop_image : ee.Image
        WorldPop population image.
    region : ee.Geometry
        Bounding region for the export.
    filename : str
        Output file path.
    scale : int
        Spatial resolution in metres (default 100m -- WorldPop native).

    Returns
    -------
    str
        Absolute path to the saved GeoTIFF.
    """
    geemap.ee_export_image(
        pop_image,
        filename=filename,
        scale=scale,
        region=region,
        file_per_band=False,
    )
    abs_path = os.path.abspath(filename)
    print(f"[Export] Population GeoTIFF saved to {abs_path}")
    return abs_path


# ---------------------------------------------------------------------------
# Aggregate population to 250m block grid
# ---------------------------------------------------------------------------

def aggregate_population_to_blocks(
    pop_tif_path: str,
    block_grid: gpd.GeoDataFrame,
) -> pd.Series:
    """
    Compute the total population for each block by summing 100m pixels.

    Parameters
    ----------
    pop_tif_path : str or Path
        Path to the WorldPop GeoTIFF (single band, people per pixel).
    block_grid : gpd.GeoDataFrame
        Grid of block polygons (must have a CRS set).

    Returns
    -------
    pd.Series
        Total population per block (index aligned with *block_grid*).
        Blocks with no valid pixels are ``NaN``.
    """
    pop_values = []

    with rasterio.open(str(pop_tif_path)) as src:
        raster_crs = src.crs
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

                # Mask nodata and negative values
                valid_mask = np.ones_like(pixels, dtype=bool)
                if nodata is not None:
                    valid_mask &= pixels != nodata
                valid_mask &= pixels >= 0

                valid_pixels = pixels[valid_mask]
                if len(valid_pixels) > 0:
                    # SUM for population (not mean)
                    pop_values.append(round(float(np.sum(valid_pixels)), 1))
                else:
                    pop_values.append(np.nan)
            except Exception:
                pop_values.append(np.nan)

    return pd.Series(pop_values, index=block_grid.index, name="population")


# ---------------------------------------------------------------------------
# Convenience entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Same Kothrud ROI as other modules
    LONGITUDE = 73.8077
    LATITUDE = 18.5074
    BUFFER_M = 2000

    OUTPUT_FILE = "outputs/kothrud_population.tif"

    authenticate_gee()

    roi = ee.Geometry.Point([LONGITUDE, LATITUDE]).buffer(BUFFER_M)

    print(f"\n[Run] Fetching WorldPop {_YEAR} population for Kothrud, Pune")
    pop_image = get_worldpop_population(roi)

    print(f"\n{'='*50}")
    print(f"Source        : WorldPop GP 100m")
    print(f"Country       : {_COUNTRY}")
    print(f"Year          : {_YEAR}")
    print(f"Region        : Kothrud, Pune")
    print(f"Centre        : {LATITUDE} N, {LONGITUDE} E")
    print(f"Buffer        : {BUFFER_M / 1000:.0f} km")
    print(f"Resolution    : 100m")
    print(f"{'='*50}")

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    export_population_geotiff(pop_image, region=roi, filename=OUTPUT_FILE)

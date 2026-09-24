"""
utils/raster.py
───────────────
Generic raster utility functions.
"""

from __future__ import annotations

from pathlib import Path
from typing import Union

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio.mask import mask as rasterio_mask
from shapely.geometry import mapping


def aggregate_raster_zonal_stats(
    raster_path: Union[str, Path],
    blocks_gdf: gpd.GeoDataFrame,
    band: int = 1,
    stat: str = "mean",
) -> pd.Series:
    """
    Aggregate continuous raster values within polygon geometries.

    Parameters
    ----------
    raster_path : str | Path
        Path to the raster file (e.g., GeoTIFF).
    blocks_gdf : gpd.GeoDataFrame
        Polygons over which to aggregate the raster values.
    band : int, optional
        Band index to read (1-indexed), by default 1.
    stat : str, optional
        Statistic to compute. Currently only 'mean' is supported.

    Returns
    -------
    pd.Series
        A pandas Series containing the aggregated value for each block,
        aligned with the index of `blocks_gdf`.
    """
    if stat != "mean":
        raise NotImplementedError(f"Statistic '{stat}' is not yet supported.")

    results = []

    with rasterio.open(raster_path) as src:
        # Ensure CRS match for the geometries
        if blocks_gdf.crs != src.crs:
            blocks_gdf_proj = blocks_gdf.to_crs(src.crs)
        else:
            blocks_gdf_proj = blocks_gdf

        nodata_val = src.nodatavals[band - 1]

        for _, row in blocks_gdf_proj.iterrows():
            geom = [mapping(row.geometry)]
            try:
                out_image, out_transform = rasterio_mask(
                    src, geom, crop=True, all_touched=True
                )
                
                band_data = out_image[band - 1]

                # Mask nodata
                if nodata_val is not None:
                    valid_pixels = band_data[band_data != nodata_val]
                else:
                    valid_pixels = band_data

                # Exclude nan
                valid_pixels = valid_pixels[~np.isnan(valid_pixels)]

                if valid_pixels.size > 0:
                    val = np.mean(valid_pixels)
                else:
                    val = np.nan
            except ValueError:
                # E.g. polygon does not overlap raster
                val = np.nan
            
            results.append(val)

    return pd.Series(results, index=blocks_gdf.index)

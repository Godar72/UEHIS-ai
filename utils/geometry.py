"""
Generic geometric intersection utilities.
"""

from __future__ import annotations
import geopandas as gpd

def sum_intersection_area_m2(
    block_geom_utm,
    features_utm: gpd.GeoDataFrame,
    buffer_m: float = 0.0,
) -> float:
    """
    Sum EPSG:32643 areas of block ∩ each feature polygon.
    
    Parameters
    ----------
    block_geom_utm :
        The block geometry in EPSG:32643.
    features_utm : gpd.GeoDataFrame
        The feature geometries in EPSG:32643.
    buffer_m : float, optional
        A buffer (in meters) to apply to each feature before clipping.
        Useful for approximating road areas from line geometries.
        
    Returns
    -------
    float
        The total area of the strictly clipped intersections.
    """
    if features_utm.empty:
        return 0.0

    candidates = features_utm[features_utm.intersects(block_geom_utm)]
    if candidates.empty:
        return 0.0

    total_area = 0.0
    for geom in candidates.geometry:
        if buffer_m > 0:
            geom = geom.buffer(buffer_m)
        clipped = block_geom_utm.intersection(geom)
        total_area += clipped.area
        
    return float(total_area)

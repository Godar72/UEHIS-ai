# UEHIS – Data Ingestion Module
# Handles satellite imagery retrieval from Google Earth Engine
# and urban feature extraction via OpenStreetMap.

from data_ingestion.sentinel import (
    authenticate_gee,
    get_sentinel2_composite,
    export_composite_geotiff,
    GEEAuthenticationError,
    EmptyCollectionError,
)
from data_ingestion.osm_features import (
    fetch_building_footprints,
    fetch_road_network,
    OSMDownloadError,
)

__all__ = [
    "authenticate_gee",
    "get_sentinel2_composite",
    "export_composite_geotiff",
    "GEEAuthenticationError",
    "EmptyCollectionError",
    "fetch_building_footprints",
    "fetch_road_network",
    "OSMDownloadError",
]

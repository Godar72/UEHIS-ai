import os
import json
import logging
import geopandas as gpd
from shapely.geometry import shape, Polygon, MultiPolygon
from shapely.errors import WKTReadingError
from fastapi import HTTPException
import pyproj
from shapely.ops import transform

from carbon_sink.canopy_area import aggregate_canopy_area_m2_from_raster
from carbon_sink.canopy_height import carbon_from_canopy_params
import ee

logger = logging.getLogger(__name__)

PUNE_BOUNDS = (73.7, 18.4, 74.0, 18.6)
MAX_AREA_M2 = 50_000_000 # 50 sq km

UNET_TIF = os.getenv("UEHIS_UNET_RASTER", "UEHIS_Production_2026/pune_unet_segmentation_FROZEN_2026.tif")
GEE_CANOPY_ASSET = "users/nlang/ETH_GlobalCanopyHeight_2020_10m_v1"
ALLOMETRIC_MODEL = "urban_generic"
METHODOLOGY_UUID = "v4.0.0-frozen-carbon"

def validate_and_transform_geometry(geom_wgs84: dict) -> gpd.GeoDataFrame:
    """
    Validates WGS84 geometry, checks bounds and size, 
    and returns a GeoDataFrame in EPSG:32643.
    """
    if not geom_wgs84 or 'type' not in geom_wgs84 or 'coordinates' not in geom_wgs84:
        raise HTTPException(status_code=400, detail="Malformed geometry")
        
    try:
        geom = shape(geom_wgs84)
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid geometry")
        
    if not isinstance(geom, (Polygon, MultiPolygon)):
        raise HTTPException(status_code=400, detail="Geometry must be a Polygon or MultiPolygon")
        
    if geom.is_empty:
        raise HTTPException(status_code=400, detail="Empty geometry")
        
    minx, miny, maxx, maxy = geom.bounds
    if minx < PUNE_BOUNDS[0] or maxx > PUNE_BOUNDS[2] or miny < PUNE_BOUNDS[1] or maxy > PUNE_BOUNDS[3]:
        raise HTTPException(status_code=400, detail="Geometry falls outside Pune production bounds")
        
    gdf_wgs84 = gpd.GeoDataFrame({'geometry': [geom]}, crs="EPSG:4326")
    gdf_32643 = gdf_wgs84.to_crs(epsg=32643)
    
    area_m2 = gdf_32643.geometry.area.iloc[0]
    if area_m2 > MAX_AREA_M2:
        raise HTTPException(status_code=400, detail=f"Study area exceeds maximum allowed size of {MAX_AREA_M2} m2")
        
    return gdf_32643

def fetch_canopy_height(geom_wgs84: dict) -> float:
    try:
        if not getattr(ee.data, '_credentials', None):
            ee.Initialize(project=os.getenv('GEE_PROJECT_ID'))
            
        fc = ee.FeatureCollection([ee.Feature(geom_wgs84)])
        canopy_img = ee.Image(GEE_CANOPY_ASSET)
        reduced = canopy_img.reduceRegions(
            collection=fc,
            reducer=ee.Reducer.mean(),
            scale=10,
            crs="EPSG:4326"
        )
        res = reduced.getInfo()
        if 'features' in res and len(res['features']) > 0:
            return res['features'][0]['properties'].get('mean', 0.0)
        return 0.0
    except ee.EEException as e:
        logger.error(f"GEE Service Unavailable")
        raise HTTPException(status_code=503, detail="Earth Engine service unavailable")
    except Exception as e:
        logger.error(f"GEE Fetch Error")
        raise HTTPException(status_code=503, detail="Earth Engine service unavailable")

def aggregate_study_area_carbon(geom_wgs84: dict) -> dict:
    # 1. Validation & Transformation
    gdf_32643 = validate_and_transform_geometry(geom_wgs84)
    gdf_32643['block_id'] = 'study_area'
    
    # 2. Extract Canopy Area (using UNET raster masking)
    area_df = aggregate_canopy_area_m2_from_raster(gdf_32643, UNET_TIF)
    canopy_area_m2 = area_df['canopy_area_m2'].iloc[0]
    
    # 3. Extract Canopy Height (GEE)
    # If canopy area is 0, we don't strictly need to call GEE because carbon will be 0.
    if canopy_area_m2 <= 0.0:
        height_m = 0.0
    else:
        height_m = fetch_canopy_height(geom_wgs84)
        
    # 4. Phase 4 Carbon Allometry
    n_trees, agb, co2 = carbon_from_canopy_params(
        [canopy_area_m2], 
        [height_m], 
        ALLOMETRIC_MODEL
    )
    
    co2_val = float(co2[0])
    
    # 5. Result and Provenance
    return {
        "carbon": {
            "aggregation_method": "spatial_recomputation_from_canopy_and_height",
            "standing_carbon_stock_tonnes_co2e": co2_val,
            "canopy_area_m2": canopy_area_m2,
            "canopy_height_m": height_m
        },
        "provenance": {
            "canopy_raster_source": "pune_unet_segmentation_FROZEN_2026",
            "canopy_height_source": GEE_CANOPY_ASSET,
            "allometric_model": ALLOMETRIC_MODEL,
            "methodology_version": METHODOLOGY_UUID,
            "computation_type": "spatial_recomputation"
        }
    }

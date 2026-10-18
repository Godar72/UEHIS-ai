import osmnx as ox
import pandas as pd
import geopandas as gpd
import numpy as np
import rasterio
from rasterio.mask import mask
import json
from datetime import datetime
import shapely
from shapely.geometry import Polygon, MultiPolygon
import hashlib
import warnings
import sys
import os

warnings.filterwarnings('ignore')

data_root = r"C:\Users\adity\Desktop\SL\UEHIS_Production_2026"
pn_grid_path = os.path.join(data_root, "pune_pn_grid_250m_2026.geojson")
scores_path = os.path.join(data_root, "pune_uehi_scores_phase3_production_2026.csv")
carbon_path = os.path.join(data_root, "pune_carbon_production_2026.csv")
unet_path = os.path.join(data_root, "pune_unet_segmentation_FROZEN_2026.tif")

out_candidates_path = os.path.join(data_root, "pune_planting_candidates.geojson")
out_manifest_path = os.path.join(data_root, "pune_planting_candidates_manifest.json")

def get_hash(filepath):
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

print("Loading data...")
pn_grid = gpd.read_file(pn_grid_path)
boundary = pn_grid.unary_union
boundary_gdf = gpd.GeoDataFrame(geometry=[boundary], crs=pn_grid.crs)
boundary_4326 = boundary_gdf.to_crs("EPSG:4326").geometry.iloc[0]

print("Fetching OSM data (Buildings)...")
try:
    bldgs = ox.features_from_polygon(boundary_4326, tags={"building": True})
except Exception as e:
    print("Warning: Failed to fetch buildings.", e)
    bldgs = gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")

print("Fetching OSM data (Water)...")
try:
    water = ox.features_from_polygon(boundary_4326, tags={"water": True, "waterway": True, "natural": ["water", "wetland"]})
except Exception as e:
    print("Warning: Failed to fetch water.", e)
    water = gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")

print("Fetching OSM data (Roads)...")
try:
    roads = ox.features_from_polygon(boundary_4326, tags={"highway": True})
except Exception as e:
    print("Warning: Failed to fetch roads.", e)
    roads = gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")

print("Fetching OSM data (Landuse)...")
try:
    lu = ox.features_from_polygon(boundary_4326, tags={"landuse": True, "leisure": True, "amenity": True})
except Exception as e:
    print("Warning: Failed to fetch landuse.", e)
    lu = gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")

print("Projecting...")
if not bldgs.empty: bldgs = bldgs.to_crs("EPSG:32643")
if not water.empty: water = water.to_crs("EPSG:32643")
if not roads.empty: roads = roads.to_crs("EPSG:32643")
if not lu.empty: lu = lu.to_crs("EPSG:32643")

if not roads.empty:
    # Approx 4 meters buffer for roads
    roads.geometry = roads.geometry.buffer(4.0)

exclude_geoms = []
if not bldgs.empty: exclude_geoms.extend(bldgs.geometry.tolist())
if not water.empty: exclude_geoms.extend(water.geometry.tolist())
if not roads.empty: exclude_geoms.extend(roads.geometry.tolist())

incompatible_lu = ["military", "railway", "quarry", "landfill"]
if not lu.empty:
    lu_excl = lu[lu.get("landuse", pd.Series(dtype=str)).isin(incompatible_lu)]
    lu_excl = lu_excl[lu_excl.geometry.type.isin(["Polygon", "MultiPolygon"])]
    exclude_geoms.extend(lu_excl.geometry.tolist())

print("Creating exclusion mask...")
exclusion_union = shapely.ops.unary_union(exclude_geoms)
open_space = boundary.difference(exclusion_union)

if open_space.is_empty:
    os_geoms = []
elif isinstance(open_space, Polygon):
    os_geoms = [open_space]
else:
    os_geoms = list(open_space.geoms)
    
os_gdf = gpd.GeoDataFrame(geometry=os_geoms, crs="EPSG:32643")

print("Classifying open space...")
if not lu.empty:
    lu_valid = lu[~lu.get("landuse", pd.Series(dtype=str)).isin(incompatible_lu)]
    cols = ["geometry"] + [c for c in ["landuse", "leisure", "amenity"] if c in lu_valid.columns]
    lu_valid = lu_valid[cols]
    
    # Filter to only Polygons and MultiPolygons
    lu_valid = lu_valid[lu_valid.geometry.type.isin(["Polygon", "MultiPolygon"])]
    
    # Overlay is safer if we reset index
    lu_valid = lu_valid.reset_index(drop=True)
    os_gdf = os_gdf.reset_index(drop=True)
    
    classified = gpd.overlay(os_gdf, lu_valid, how="intersection")
    unclassified = gpd.overlay(os_gdf, lu_valid, how="difference")
else:
    classified = gpd.GeoDataFrame(geometry=[], crs="EPSG:32643")
    unclassified = os_gdf

def assign_class(row):
    landuse = str(row.get("landuse", "")) if pd.notna(row.get("landuse")) else ""
    leisure = str(row.get("leisure", "")) if pd.notna(row.get("leisure")) else ""
    amenity = str(row.get("amenity", "")) if pd.notna(row.get("amenity")) else ""
    
    public_like = ["park", "garden", "recreation_ground", "pitch", "village_green"]
    if leisure in public_like or landuse in public_like:
        return "candidate_public_like_open_space"
    
    context = ["farmland", "cemetery", "school", "college", "university", "hospital", 
               "graveyard", "institutional", "education", "residential", "commercial", "industrial",
               "allotments", "retail"]
    if landuse in context or amenity in context:
        return "context_dependent"
        
    return "candidate_other_open_space"

if not classified.empty:
    classified["candidate_class"] = classified.apply(assign_class, axis=1)
    
    def make_source_lu(row):
        parts = []
        if pd.notna(row.get("landuse")) and row.get("landuse"): parts.append(f"landuse={row['landuse']}")
        if pd.notna(row.get("leisure")) and row.get("leisure"): parts.append(f"leisure={row['leisure']}")
        if pd.notna(row.get("amenity")) and row.get("amenity"): parts.append(f"amenity={row['amenity']}")
        return ", ".join(parts) if parts else "unknown"
        
    classified["source_land_use"] = classified.apply(make_source_lu, axis=1)
    
if not unclassified.empty:
    unclassified["candidate_class"] = "candidate_other_open_space"
    unclassified["source_land_use"] = "unknown"

all_cands = pd.concat([classified, unclassified], ignore_index=True)
all_cands = all_cands.explode(index_parts=False).reset_index(drop=True)
all_cands["candidate_area_m2"] = all_cands.geometry.area
all_cands = all_cands[all_cands["candidate_area_m2"] >= 50.0].reset_index(drop=True) # at least 50 sqm to reduce noise
all_cands["candidate_id"] = [f"CAND_{i}" for i in range(len(all_cands))]
all_cands["land_use_class"] = all_cands.get("source_land_use", "unknown")

print("Spatial join with PN Grid...")
pn_data = pn_grid[["block_id", "geometry"]].copy()
scores_df = pd.read_csv(scores_path)
carbon_df = pd.read_csv(carbon_path)
pn_data = pn_data.merge(scores_df, on="block_id", how="left")
pn_data = pn_data.merge(carbon_df[["block_id", "carbon_stock_tonnes_co2e"]], on="block_id", how="left")

all_cands["centroid"] = all_cands.geometry.centroid
all_cands_pt = all_cands.set_geometry("centroid")
joined = gpd.sjoin(all_cands_pt, pn_data, how="left", predicate="intersects")
# handle multiple joins by taking first
joined = joined[~joined.index.duplicated(keep='first')]

all_cands = all_cands.set_geometry("geometry")

for c in ["uehi_score", "risk_level", "temperature", "population_exposure", "carbon_stock_tonnes_co2e"]:
    all_cands[c] = joined[c].values

all_cands["carbon_stock_tonnes_co2e"] = all_cands["carbon_stock_tonnes_co2e"].fillna(0.0)

print("Calculating raster fractions...")
def calc_fractions(geom, src):
    try:
        out_image, _ = mask(src, [geom], crop=True)
        data = out_image[0]
        c = (data == 0).sum()
        i = (data == 1).sum()
        p = (data == 2).sum()
        tot = c + i + p
        if tot > 0:
            return float(c)/tot, float(i)/tot
        return 0.0, 0.0
    except ValueError:
        return 0.0, 0.0

with rasterio.open(unet_path) as src:
    fractions = [calc_fractions(g, src) for g in all_cands.geometry]
    
all_cands["existing_canopy_fraction"] = [f[0] for f in fractions]
all_cands["impervious_fraction"] = [f[1] for f in fractions]
all_cands["building_fraction"] = 0.0
all_cands["water_fraction"] = 0.0
all_cands["road_fraction"] = 0.0

print("Calculating distance to water...")
if not water.empty:
    water_union = shapely.ops.unary_union(water.geometry.tolist())
    all_cands["distance_to_water_m"] = all_cands.geometry.distance(water_union)
else:
    all_cands["distance_to_water_m"] = -1.0

all_cands["data_confidence"] = "high"
all_cands["ownership_status"] = "unknown"
all_cands["utility_status"] = "unknown"
all_cands["planting_permission_status"] = "unknown"

final_cols = [
    "candidate_id", "geometry", "source_land_use", "land_use_class", "candidate_class",
    "existing_canopy_fraction", "impervious_fraction", "building_fraction", "water_fraction",
    "road_fraction", "uehi_score", "risk_level", "temperature", "population_exposure",
    "carbon_stock_tonnes_co2e", "distance_to_water_m", "candidate_area_m2", "data_confidence",
    "ownership_status", "utility_status", "planting_permission_status"
]
for col in final_cols:
    if col not in all_cands.columns:
        all_cands[col] = "unknown"
all_cands = all_cands[final_cols]
all_cands.to_file(out_candidates_path, driver="GeoJSON")

manifest = {
    "source_dataset": "OpenStreetMap",
    "release_version": "Live Query",
    "download_method": "osmnx v2.1.1 Overpass API",
    "crs": "EPSG:32643",
    "license": "ODbL",
    "retrieval_timestamp": datetime.utcnow().isoformat(),
    "source_url": "https://overpass-api.de/api/interpreter",
    "candidate_count": len(all_cands),
    "file_hash": get_hash(out_candidates_path)
}
with open(out_manifest_path, "w") as f:
    json.dump(manifest, f, indent=2)

print(f"DONE. Generated {len(all_cands)} candidates.")

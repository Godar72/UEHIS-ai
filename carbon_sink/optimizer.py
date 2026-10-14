"""
carbon_sink/optimizer.py
────────────────────────
Optimization framework for candidate planting units based on Stage 2.2 candidates.

OBJECTIVE FUNCTION:
- UEHI score (0-100) is the STRICT primary environmental-priority variable.
- Water distance is a secondary contextual penalty (e.g., -10% priority if > 1000m) 
  and explicitly does NOT imply irrigation access or physical planting availability.
- No arbitrary sub-factor modifications (NDVI/Temp) are applied.
- Population exposure drives UEHI priority but is not interpreted as physical space.

All planting candidate units output from this module have:
- Unknown ownership, utility, and permission status.
- Distance to water provided ONLY as a contextual accessibility proxy.
- Scenario-based carbon estimates that represent an illustrative future potential, 
  NOT observed standing stock.
"""

import geopandas as gpd
import pandas as pd
import numpy as np
from shapely.geometry import Point
import logging
from scipy.spatial import cKDTree
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

def generate_planting_units(candidates_gdf: gpd.GeoDataFrame, spacing_m: float = 10.0) -> gpd.GeoDataFrame:
    """
    Generates explicit planting units (points) within candidate polygons.
    Guarantees Euclidean distance >= spacing_m between all points.
    
    Parameters
    ----------
    candidates_gdf : gpd.GeoDataFrame
        The Stage 2.2 candidate polygons.
    spacing_m : float
        Minimum tree spacing in meters. This is a configurable scenario assumption.
    """
    units = []
    
    # 1. Generate points per candidate
    for idx, row in candidates_gdf.iterrows():
        geom = row.geometry
        if geom.is_empty:
            continue
            
        minx, miny, maxx, maxy = geom.bounds
        x_coords = np.arange(minx + spacing_m/2, maxx, spacing_m)
        y_coords = np.arange(miny + spacing_m/2, maxy, spacing_m)
        
        if len(x_coords) == 0 or len(y_coords) == 0:
            if geom.area >= (spacing_m * spacing_m * 0.25):
                pt = geom.centroid
                if geom.contains(pt):
                    unit = row.to_dict()
                    unit['geometry'] = pt
                    unit['planting_area_m2'] = spacing_m * spacing_m
                    unit['parent_area_m2'] = geom.area
                    units.append(unit)
            continue
            
        xx, yy = np.meshgrid(x_coords, y_coords)
        pts = [Point(x, y) for x, y in zip(xx.flatten(), yy.flatten())]
        
        # Must be strictly inside the candidate geometry
        pts = [p for p in pts if geom.contains(p)]
        
        for p in pts:
            unit = row.to_dict()
            unit['geometry'] = p
            unit['planting_area_m2'] = spacing_m * spacing_m
            unit['parent_area_m2'] = geom.area
            units.append(unit)
            
    if not units:
        return gpd.GeoDataFrame(columns=list(candidates_gdf.columns) + ['planting_unit_id', 'planting_area_m2', 'parent_area_m2'], crs=candidates_gdf.crs)
        
    # 2. Enforce global minimum spacing across all candidates using spatial index (KDTree)
    coords = np.array([[u['geometry'].x, u['geometry'].y] for u in units])
    tree = cKDTree(coords)
    
    # Query pairs closer than spacing_m - epsilon
    epsilon = 1e-4
    pairs = tree.query_pairs(r=spacing_m - epsilon)
    
    to_remove = set()
    # Sort pairs to greedily remove the second point
    # A more optimal independent set could be found, but greedy is sufficient for spacing enforcement
    for i, j in sorted(list(pairs)):
        if i not in to_remove and j not in to_remove:
            to_remove.add(j)
            
    filtered_units = []
    unit_counter = 0
    for i, u in enumerate(units):
        if i not in to_remove:
            u['planting_unit_id'] = f"PU_{unit_counter}"
            filtered_units.append(u)
            unit_counter += 1
            
    return gpd.GeoDataFrame(filtered_units, crs=candidates_gdf.crs)


def score_planting_units(units_gdf: gpd.GeoDataFrame, 
                         scenario_carbon_per_tree_tonnes: float = 0.5,
                         spacing_m: float = 10.0,
                         scenario_name: str = "Standard 10m Illustrative Scenario") -> gpd.GeoDataFrame:
    """
    Scores planting units based on environmental priority and calculates scenario-based benefits.
    """
    if units_gdf.empty:
        return units_gdf
        
    scored = units_gdf.copy()
    
    # Priority explicitly driven by UEHI score
    scored['priority_score'] = scored['uehi_score'].fillna(0)
    
    dist = scored['distance_to_water_m'].replace(-1, 9999)
    dist_penalty = np.where(dist > 1000, 0.9, 1.0)
    scored['priority_score'] = scored['priority_score'] * dist_penalty
    
    scored['scenario_tree_count'] = 1
    # Rename to explicitly denote it is a scenario assumption, not observed carbon
    scored['scenario_potential_standing_carbon_tonnes_co2e'] = scenario_carbon_per_tree_tonnes
    
    scored['ownership_status'] = "unknown"
    scored['utility_status'] = "unknown"
    scored['planting_permission_status'] = "unknown"
    scored['optimization_status'] = "evaluated"
    
    # Provenance fields
    scored['scenario_carbon_per_mature_tree'] = scenario_carbon_per_tree_tonnes
    scored['spacing_m'] = spacing_m
    scored['scenario_name'] = scenario_name
    scored['carbon_assumption_type'] = "illustrative_scenario_assumption"
    scored['timestamp'] = datetime.now(timezone.utc).isoformat()
    
    # Ensure existing carbon stock is preserved but distinct
    if 'carbon_stock_tonnes_co2e' in scored.columns:
        scored = scored.rename(columns={'carbon_stock_tonnes_co2e': 'existing_carbon_stock_tonnes_co2e'})
        
    scored['provenance'] = "Phase 4 Stage 2.3 Optimization"
    
    return scored


def optimize_planting_budget(scored_units: gpd.GeoDataFrame, 
                             max_selected_units: int = None,
                             max_planting_area_m2: float = None,
                             max_budget: float = None) -> gpd.GeoDataFrame:
    """
    Selects the top priority planting units constrained by configurable deployment limits.
    
    Constraints supported:
    - max_selected_units: Maximum number of planting units.
    - max_planting_area_m2: Maximum cumulative planting area (m2).
    - max_budget: Hypothetical max budget.
    """
    if scored_units.empty:
        return scored_units
        
    # Sort strictly descending by priority score
    # Secondary sort by something stable (e.g., planting_unit_id) to ensure determinism
    if 'planting_unit_id' in scored_units.columns:
        sorted_units = scored_units.sort_values(by=['priority_score', 'planting_unit_id'], ascending=[False, True]).reset_index(drop=True)
    else:
        sorted_units = scored_units.sort_values(by='priority_score', ascending=False).reset_index(drop=True)
    
    # Evaluate constraints iteratively if area/budget exist, else simple head()
    if max_planting_area_m2 is None and max_budget is None:
        if max_selected_units is not None:
            selected = sorted_units.head(max_selected_units).copy()
        else:
            selected = sorted_units.copy()
    else:
        # We must iterate or use cumsum
        selected_mask = np.ones(len(sorted_units), dtype=bool)
        
        if max_selected_units is not None:
            selected_mask[max_selected_units:] = False
            
        if max_planting_area_m2 is not None:
            if 'planting_area_m2' in sorted_units.columns:
                cum_area = sorted_units['planting_area_m2'].cumsum()
                selected_mask = selected_mask & (cum_area <= max_planting_area_m2)
                
        if max_budget is not None:
            # Assuming a cost column exists if budget is constrained, else ignore or fail
            if 'cost' in sorted_units.columns:
                cum_cost = sorted_units['cost'].cumsum()
                selected_mask = selected_mask & (cum_cost <= max_budget)
                
        selected = sorted_units[selected_mask].copy()
        
    selected['optimization_status'] = "selected"
    
    return selected


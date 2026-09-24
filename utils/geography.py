"""
utils/geography.py
──────────────────
Core geographic foundation for the UEHIS Pune-wide expansion.

Handles source-agnostic ingestion of boundaries and wards,
metric grid generation with persistent geometry-derived IDs,
and maximum-area ward assignment. All operational geometry
must be transformed to EPSG:32643 (UTM Zone 43N).
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, List

import geopandas as gpd
import pandas as pd
from shapely.geometry import Polygon, MultiPolygon, box
import numpy as np

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

OPERATIONAL_CRS = "EPSG:32643"
FIXED_ORIGIN_E = 300000.0   # Fixed UTM Easting origin
FIXED_ORIGIN_N = 2000000.0  # Fixed UTM Northing origin
BLOCK_SIZE_M = 250.0        # Grid cell size in meters
AMBIGUITY_AREA_FRACTION = 0.01
SIGNIFICANT_DISCREPANCY_M2 = 100.0


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class ConfigurationError(Exception):
    pass

class ValidationError(Exception):
    pass


# ---------------------------------------------------------------------------
# Data Contracts & Provenance
# ---------------------------------------------------------------------------

def compute_geometry_hash(gdf: gpd.GeoDataFrame) -> str:
    """Generate a deterministic hash of all geometries in a GeoDataFrame."""
    if gdf.empty:
        return hashlib.sha256(b"empty").hexdigest()
    
    # 1. Transform to operational CRS
    if gdf.crs != OPERATIONAL_CRS:
        gdf = gdf.to_crs(OPERATIONAL_CRS)
        
    # 2. Normalize by rounding coordinates to 3 decimal places (1 mm)
    from shapely.ops import transform
    import shapely.wkt
    def round_coords(geom):
        if geom is None or geom.is_empty:
            return geom
        return transform(lambda x, y, z=None: (round(x, 3), round(y, 3)) if z is None else (round(x, 3), round(y, 3), round(z, 3)), geom)
        
    rounded_geoms = gdf.geometry.apply(round_coords)
    
    # 3. Serialize to WKT and hash
    wkt_strings = rounded_geoms.apply(lambda g: g.wkt if g else "")
    geom_bytes = "".join(wkt_strings).encode('utf-8')
    return hashlib.sha256(geom_bytes).hexdigest()


def append_provenance_metadata(
    gdf: gpd.GeoDataFrame,
    source_name: str,
    source_url: str,
    source_type: str,
    source_version: str,
    original_crs: str
) -> gpd.GeoDataFrame:
    """Attach required provenance metadata as column attributes to a GeoDataFrame."""
    gdf = gdf.copy()
    gdf["source_name"] = source_name
    gdf["source_url"] = source_url
    gdf["source_type"] = source_type
    gdf["source_version"] = source_version
    gdf["acquired_at"] = datetime.utcnow().isoformat()
    gdf["original_crs"] = original_crs
    gdf["operational_crs"] = OPERATIONAL_CRS
    gdf["geometry_hash"] = compute_geometry_hash(gdf)
    gdf["validation_status"] = "unvalidated"
    return gdf


# ---------------------------------------------------------------------------
# Ingestion
# ---------------------------------------------------------------------------

def load_pmc_boundary(
    path: str | Path | None = None,
    source_name: str = "unknown",
    source_url: str = "unknown",
    source_type: str = "unknown",
    source_version: str = "unknown",
) -> gpd.GeoDataFrame:
    """
    Load the authoritative PMC outer boundary.

    Raises ConfigurationError if not provided, explicitly enforcing
    that a valid source must be supplied.
    """
    if path is None or not Path(path).exists():
        raise ConfigurationError("Authoritative PMC boundary not configured.")

    gdf = gpd.read_file(path)
    
    if gdf.empty:
        raise ValidationError("Boundary dataset is empty.")
        
    if "source_type" in gdf.columns and gdf["source_type"].iloc[0] == "derived":
        raise ConfigurationError("Derived boundaries cannot be loaded as the authoritative PMC boundary.")
    
    original_crs = str(gdf.crs) if gdf.crs else "unknown"
    
    if not gdf.crs:
        raise ValidationError("Boundary dataset has no CRS defined.")

    # Project to Operational CRS
    gdf = gdf.to_crs(OPERATIONAL_CRS)

    return append_provenance_metadata(
        gdf, source_name, source_url, source_type, source_version, original_crs
    )


def load_ward_layer(
    path: str | Path | None = None,
    source_name: str = "unknown",
    source_url: str = "unknown",
    source_type: str = "unknown",
    source_version: str = "unknown",
) -> gpd.GeoDataFrame:
    """
    Load the authoritative administrative ward layer.

    Raises ConfigurationError if not provided, explicitly enforcing
    that a valid source must be supplied. Electoral datasets must not
    be substituted unless explicitly verified.
    """
    if path is None or not Path(path).exists():
        raise ConfigurationError("Authoritative PMC administrative ward layer not configured.")

    gdf = gpd.read_file(path)
    
    if gdf.empty:
        raise ValidationError("Ward dataset is empty.")
    
    original_crs = str(gdf.crs) if gdf.crs else "unknown"
    
    if not gdf.crs:
        raise ValidationError("Ward dataset has no CRS defined.")

    # Project to Operational CRS
    gdf = gdf.to_crs(OPERATIONAL_CRS)

    return append_provenance_metadata(
        gdf, source_name, source_url, source_type, source_version, original_crs
    )


def derive_pmc_boundary_from_wards(wards_gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Create a dissolved outer boundary from a valid ward layer.
    The original wards remain immutable; this returns a derived boundary.
    """
    if wards_gdf.crs != OPERATIONAL_CRS:
        wards_gdf = wards_gdf.to_crs(OPERATIONAL_CRS)
        
    dissolved_geom = wards_gdf.geometry.unary_union
    
    if dissolved_geom.geom_type == "Polygon":
        dissolved_geom = MultiPolygon([dissolved_geom])
        
    derived_gdf = gpd.GeoDataFrame(
        {"geometry": [dissolved_geom]}, 
        geometry="geometry", 
        crs=OPERATIONAL_CRS
    )
    
    # Grab source version from the first ward if it exists
    src_ver = wards_gdf["source_version"].iloc[0] if "source_version" in wards_gdf.columns else "unknown"
    src_name = wards_gdf["source_name"].iloc[0] if "source_name" in wards_gdf.columns else "unknown"
    
    derived_gdf = append_provenance_metadata(
        derived_gdf,
        source_name=f"Derived from {src_name}",
        source_url="internal",
        source_type="derived",
        source_version=src_ver,
        original_crs=OPERATIONAL_CRS
    )
    derived_gdf["validation_status"] = "validated"
    return derived_gdf


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_boundary(gdf: gpd.GeoDataFrame) -> Dict[str, Any]:
    """
    Validate the authoritative PMC boundary and report its metadata.
    """
    report = {
        "feature_count": len(gdf),
        "crs_transformable": gdf.crs == OPERATIONAL_CRS or bool(gdf.crs),
        "valid_geometries": int(gdf.geometry.is_valid.sum()),
        "empty_geometries": int(gdf.geometry.is_empty.sum()),
    }
    
    if gdf.crs != OPERATIONAL_CRS:
        test_gdf = gdf.to_crs(OPERATIONAL_CRS)
    else:
        test_gdf = gdf
        
    report["area_m2"] = float(test_gdf.geometry.area.sum())
    report["area_km2"] = report["area_m2"] / 1e6
    report["source_metadata"] = gdf.drop(columns="geometry").iloc[0].to_dict() if not gdf.empty else {}
    report["geometry_hash"] = compute_geometry_hash(test_gdf)
    
    return report


def validate_wards(wards_gdf: gpd.GeoDataFrame, pmc_boundary_gdf: gpd.GeoDataFrame, id_col: str, name_col: str) -> Dict[str, Any]:
    """
    Validate an administrative ward layer against the PMC boundary.
    """
    report = {
        "empty_geometries": int(wards_gdf.geometry.is_empty.sum()),
        "invalid_geometries": int((~wards_gdf.geometry.is_valid).sum()),
        "duplicate_ward_ids": int(wards_gdf.duplicated(subset=[id_col]).sum()) if id_col in wards_gdf.columns else len(wards_gdf),
        "missing_ward_ids": int(wards_gdf[id_col].isnull().sum()) if id_col in wards_gdf.columns else len(wards_gdf),
        "missing_ward_names": int(wards_gdf[name_col].isnull().sum()) if name_col in wards_gdf.columns else len(wards_gdf),
        "crs": str(wards_gdf.crs),
    }

    wards_proj = wards_gdf.to_crs(OPERATIONAL_CRS)
    pmc_proj = pmc_boundary_gdf.to_crs(OPERATIONAL_CRS)
    
    ward_union = wards_proj.geometry.unary_union
    pmc_union = pmc_proj.geometry.unary_union
    
    gap_geom = pmc_union.difference(ward_union)
    ext_geom = ward_union.difference(pmc_union)
    
    raw_gap_area = float(gap_geom.area) if gap_geom else 0.0
    raw_ext_area = float(ext_geom.area) if ext_geom else 0.0
    
    report["raw_gap_area_m2"] = raw_gap_area
    report["raw_extension_area_m2"] = raw_ext_area
    
    report["significant_gap_area_m2"] = raw_gap_area if raw_gap_area >= SIGNIFICANT_DISCREPANCY_M2 else 0.0
    report["significant_extension_area_m2"] = raw_ext_area if raw_ext_area >= SIGNIFICANT_DISCREPANCY_M2 else 0.0
    
    # Check internal overlaps
    overlap_area = 0.0
    affected_pairs = []
    
    n_wards = len(wards_proj)
    # Using spatial index for fast intersection
    sindex = wards_proj.sindex
    for i in range(n_wards):
        geom_i = wards_proj.geometry.iloc[i]
        id_i = wards_proj[id_col].iloc[i] if id_col in wards_proj.columns else i
        
        possible_matches_index = list(sindex.intersection(geom_i.bounds))
        for j in possible_matches_index:
            if i < j:
                geom_j = wards_proj.geometry.iloc[j]
                if geom_i.intersects(geom_j):
                    intersection = geom_i.intersection(geom_j)
                    # Ignore tiny slivers (e.g., < 1 m2) due to floating point precision
                    if intersection.area > 1.0:
                        overlap_area += float(intersection.area)
                        id_j = wards_proj[id_col].iloc[j] if id_col in wards_proj.columns else j
                        affected_pairs.append((id_i, id_j))
                        
    report["overlap_area_m2"] = overlap_area
    report["affected_ward_pairs"] = affected_pairs
    
    if pmc_union.area > 0:
        report["gap_percentage"] = (report["raw_gap_area_m2"] / pmc_union.area) * 100
        
    return report


# ---------------------------------------------------------------------------
# Grid Generation & Persistent IDs
# ---------------------------------------------------------------------------

def generate_block_grid(
    boundary_gdf: gpd.GeoDataFrame,
    cell_size: float = BLOCK_SIZE_M,
    origin_easting: float = FIXED_ORIGIN_E,
    origin_northing: float = FIXED_ORIGIN_N
) -> gpd.GeoDataFrame:
    """
    Construct a fixed-origin metric block grid covering the study area.
    
    1. Transforms boundary to EPSG:32643
    2. Determines grid-index range
    3. Constructs 250m x 250m cells
    4. Filters cells intersecting the boundary
    5. Retains FULL grid-cell geometry (no clipping of the block itself)
    """
    if boundary_gdf.crs != OPERATIONAL_CRS:
        boundary_gdf = boundary_gdf.to_crs(OPERATIONAL_CRS)
        
    boundary_union = boundary_gdf.geometry.unary_union
    minx, miny, maxx, maxy = boundary_union.bounds
    
    # Determine grid index bounds
    min_gx = math.floor((minx - origin_easting) / cell_size)
    max_gx = math.floor((maxx - origin_easting) / cell_size)
    min_gy = math.floor((miny - origin_northing) / cell_size)
    max_gy = math.floor((maxy - origin_northing) / cell_size)
    
    records = []
    
    for gx in range(min_gx, max_gx + 1):
        for gy in range(min_gy, max_gy + 1):
            x0 = origin_easting + (gx * cell_size)
            y0 = origin_northing + (gy * cell_size)
            x1 = x0 + cell_size
            y1 = y0 + cell_size
            
            cell_geom = box(x0, y0, x1, y1)
            
            # Keep full geometry, just filter by inclusion in boundary
            # Using intersects to include partial blocks at the edge
            if cell_geom.intersects(boundary_union):
                block_id = f"PN_{gx}_{gy}"
                records.append({
                    "block_id": block_id,
                    "geometry": cell_geom,
                    "area_m2": cell_geom.area
                })
                
    grid = gpd.GeoDataFrame(records, geometry="geometry", crs=OPERATIONAL_CRS)
    
    src_ver = boundary_gdf["source_version"].iloc[0] if "source_version" in boundary_gdf.columns else "unknown"
    grid["boundary_source_version"] = src_ver
    
    return grid


# ---------------------------------------------------------------------------
# Ward Assignment
# ---------------------------------------------------------------------------

def assign_blocks_to_wards(
    blocks_gdf: gpd.GeoDataFrame, 
    wards_gdf: gpd.GeoDataFrame,
    id_col: str,
    name_col: str
) -> gpd.GeoDataFrame:
    """
    Assign each block to a ward using MAXIMUM AREA OVERLAP.
    
    The block's geometry is NEVER clipped. This is metadata assignment only.
    Handles exact ambiguities and edge cases (outside boundary).
    """
    if wards_gdf.empty:
        raise ValueError("Cannot assign blocks: wards_gdf is empty.")
        
    if blocks_gdf.crs != OPERATIONAL_CRS:
        blocks_gdf = blocks_gdf.to_crs(OPERATIONAL_CRS)
    if wards_gdf.crs != OPERATIONAL_CRS:
        wards_gdf = wards_gdf.to_crs(OPERATIONAL_CRS)
        
    results = blocks_gdf.copy()
    
    ward_ids = []
    ward_names = []
    ward_overlap_areas = []
    ward_overlap_fractions = []
    ward_statuses = []
    
    sindex = wards_gdf.sindex
    
    for idx, block_row in blocks_gdf.iterrows():
        block_geom = block_row.geometry
        block_area = block_geom.area
        
        possible_matches_index = list(sindex.intersection(block_geom.bounds))
        possible_matches = wards_gdf.iloc[possible_matches_index]
        
        best_ward_id = None
        best_ward_name = None
        max_overlap = -1.0
        second_overlap = -1.0
        
        for _, ward_row in possible_matches.iterrows():
            ward_geom = ward_row.geometry
            if block_geom.intersects(ward_geom):
                intersection = block_geom.intersection(ward_geom)
                overlap_area = float(intersection.area)
                
                if overlap_area > max_overlap:
                    second_overlap = max_overlap
                    max_overlap = overlap_area
                    best_ward_id = ward_row[id_col] if id_col in ward_row else None
                    best_ward_name = ward_row[name_col] if name_col in ward_row else None
                elif overlap_area > second_overlap:
                    second_overlap = overlap_area
                    
        if max_overlap <= 1e-4:
            ward_ids.append(None)
            ward_names.append(None)
            ward_overlap_areas.append(0.0)
            ward_overlap_fractions.append(0.0)
            ward_statuses.append("no_overlap")
        else:
            ambiguity_fraction = (max_overlap - max(0.0, second_overlap)) / block_area
            if ambiguity_fraction <= AMBIGUITY_AREA_FRACTION:
                ward_ids.append(None)  # No distinct winner
                ward_names.append(None)
                ward_overlap_areas.append(max_overlap)
                ward_overlap_fractions.append(max_overlap / block_area)
                ward_statuses.append("ambiguous_overlap")
            else:
                ward_ids.append(best_ward_id)
                ward_names.append(best_ward_name)
                ward_overlap_areas.append(max_overlap)
                ward_overlap_fractions.append(max_overlap / block_area)
                ward_statuses.append("assigned")
            
    results["ward_id"] = ward_ids
    results["ward_name"] = ward_names
    results["ward_overlap_area_m2"] = ward_overlap_areas
    results["ward_overlap_fraction"] = ward_overlap_fractions
    results["ward_assignment_status"] = ward_statuses
    
    return results

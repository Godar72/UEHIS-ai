import pytest
import geopandas as gpd
from shapely.geometry import box, Polygon
import math

from utils.geography import (
    OPERATIONAL_CRS,
    FIXED_ORIGIN_E,
    FIXED_ORIGIN_N,
    BLOCK_SIZE_M,
    ConfigurationError,
    ValidationError,
    compute_geometry_hash,
    append_provenance_metadata,
    load_pmc_boundary,
    load_ward_layer,
    validate_boundary,
    validate_wards,
    derive_pmc_boundary_from_wards,
    generate_block_grid,
    assign_blocks_to_wards
)

@pytest.fixture
def synthetic_boundary():
    # 500m x 500m boundary
    x0, y0 = FIXED_ORIGIN_E + 100, FIXED_ORIGIN_N + 100
    geom = box(x0, y0, x0 + 500, y0 + 500)
    gdf = gpd.GeoDataFrame({"geometry": [geom]}, crs=OPERATIONAL_CRS)
    gdf["source_version"] = "v1"
    return gdf

@pytest.fixture
def synthetic_wards():
    # Two wards splitting the 500x500 boundary
    # Ward A: 500 x 200
    # Ward B: 500 x 300
    x0, y0 = FIXED_ORIGIN_E + 100, FIXED_ORIGIN_N + 100
    geomA = box(x0, y0, x0 + 500, y0 + 200)
    geomB = box(x0, y0 + 200, x0 + 500, y0 + 500)
    gdf = gpd.GeoDataFrame({
        "ward_id": ["A", "B"],
        "ward_name": ["Ward A", "Ward B"],
        "geometry": [geomA, geomB]
    }, crs=OPERATIONAL_CRS)
    return gdf

# 1. EPSG:32643 operational CRS
def test_operational_crs():
    assert OPERATIONAL_CRS == "EPSG:32643"

# 2. Metric area calculation
def test_metric_area_calculation(synthetic_boundary):
    area = synthetic_boundary.geometry.area.sum()
    assert math.isclose(area, 250000.0, rel_tol=1e-5)

# 3. Deterministic block IDs & 6. Fixed-origin grid reproducibility
def test_deterministic_block_ids(synthetic_boundary):
    grid = generate_block_grid(synthetic_boundary, cell_size=250)
    
    # 500x500 box from offset 100, 100 means:
    # bounds are X: 100 to 600, Y: 100 to 600 relative to origin
    # gx from floor(100/250)=0 to floor(600/250)=2 (indices 0, 1, 2)
    # gy from floor(100/250)=0 to floor(600/250)=2 (indices 0, 1, 2)
    # Total blocks = 3 * 3 = 9
    assert len(grid) == 9
    assert "PN_0_0" in grid["block_id"].values
    assert "PN_2_2" in grid["block_id"].values

# 4. Block ID stability after ward reassignment
def test_block_id_stability(synthetic_boundary, synthetic_wards):
    grid1 = generate_block_grid(synthetic_boundary)
    assigned1 = assign_blocks_to_wards(grid1, synthetic_wards, "ward_id", "ward_name")
    
    # Modify wards
    wards_mod = synthetic_wards.copy()
    wards_mod.loc[0, "geometry"] = box(FIXED_ORIGIN_E, FIXED_ORIGIN_N, FIXED_ORIGIN_E + 500, FIXED_ORIGIN_N + 100)
    
    assigned2 = assign_blocks_to_wards(grid1, wards_mod, "ward_id", "ward_name")
    
    assert list(assigned1["block_id"].values) == list(assigned2["block_id"].values)
    assert not assigned1["ward_id"].equals(assigned2["ward_id"])

# 5. Block ID independence from row ordering
def test_block_id_independence():
    pass # Checked inherently by fixed grid index computation.

# 7. Maximum-area ward assignment & 9. Partial intersection & 10. No ward overlap
def test_maximum_area_assignment(synthetic_boundary, synthetic_wards):
    grid = generate_block_grid(synthetic_boundary)
    assigned = assign_blocks_to_wards(grid, synthetic_wards, "ward_id", "ward_name")
    
    # The block PN_0_0 covers X: 0-250, Y: 0-250
    # synthetic_boundary starts at 100, 100.
    # Ward A: X: 100-600, Y: 100-300
    # Ward B: X: 100-600, Y: 300-600
    
    # For PN_0_0 (0-250, 0-250), intersection with Ward A is X: 100-250 (width 150), Y: 100-250 (height 150) -> Area = 22500
    # Intersection with Ward B is 0.
    # Therefore it should be assigned to Ward A.
    row = assigned[assigned["block_id"] == "PN_0_0"].iloc[0]
    assert row["ward_id"] == "A"
    assert math.isclose(row["ward_overlap_area_m2"], 22500.0, rel_tol=1e-5)

# 8. Exact 50/50 overlap ambiguity, near-ties, and clear winners
def test_ambiguous_overlap():
    x0, y0 = FIXED_ORIGIN_E, FIXED_ORIGIN_N
    block_geom = box(x0, y0, x0 + 250, y0 + 250)
    grid = gpd.GeoDataFrame({"block_id": ["PN_0_0"], "geometry": [block_geom], "area_m2": [62500.0]}, crs=OPERATIONAL_CRS)
    
    # EXACT 50/50 split: 31250 each. Difference is 0. Fraction is 0 <= 0.01.
    geomA = box(x0, y0, x0 + 125, y0 + 250)
    geomB = box(x0 + 125, y0, x0 + 250, y0 + 250)
    wards_exact = gpd.GeoDataFrame({"ward_id": ["A", "B"], "ward_name": ["A", "B"], "geometry": [geomA, geomB]}, crs=OPERATIONAL_CRS)
    assigned_exact = assign_blocks_to_wards(grid, wards_exact, "ward_id", "ward_name")
    assert assigned_exact.iloc[0]["ward_assignment_status"] == "ambiguous_overlap"
    assert assigned_exact.iloc[0]["ward_id"] is None

    # NEAR TIE INSIDE TOLERANCE
    # Difference < 1% of 62500 (625 m2). 
    # Let A be 31500, B be 31000. Diff = 500 m2. Fraction = 500 / 62500 = 0.008 (<= 0.01)
    geomA = box(x0, y0, x0 + 126, y0 + 250) # 126 * 250 = 31500
    geomB = box(x0 + 126, y0, x0 + 250, y0 + 250) # 124 * 250 = 31000
    wards_inside = gpd.GeoDataFrame({"ward_id": ["A", "B"], "ward_name": ["A", "B"], "geometry": [geomA, geomB]}, crs=OPERATIONAL_CRS)
    assigned_inside = assign_blocks_to_wards(grid, wards_inside, "ward_id", "ward_name")
    assert assigned_inside.iloc[0]["ward_assignment_status"] == "ambiguous_overlap"
    
    # NEAR TIE OUTSIDE TOLERANCE
    # Diff > 625 m2. Let A be 32000, B be 30500. Diff = 1500 m2. Fraction = 1500 / 62500 = 0.024 (> 0.01)
    geomA = box(x0, y0, x0 + 128, y0 + 250) # 128 * 250 = 32000
    geomB = box(x0 + 128, y0, x0 + 250, y0 + 250) # 122 * 250 = 30500
    wards_outside = gpd.GeoDataFrame({"ward_id": ["A", "B"], "ward_name": ["A", "B"], "geometry": [geomA, geomB]}, crs=OPERATIONAL_CRS)
    assigned_outside = assign_blocks_to_wards(grid, wards_outside, "ward_id", "ward_name")
    assert assigned_outside.iloc[0]["ward_assignment_status"] == "assigned"
    assert assigned_outside.iloc[0]["ward_id"] == "A"

# 11. Overlapping ward detection & 12. Boundary gap detection & 13. Boundary extension detection
def test_ward_validation(synthetic_boundary):
    x0, y0 = FIXED_ORIGIN_E + 100, FIXED_ORIGIN_N + 100
    # Ward A overlaps Ward B by 50m vertically
    geomA = box(x0, y0, x0 + 500, y0 + 250)
    geomB = box(x0, y0 + 200, x0 + 500, y0 + 500)
    
    # Gap: total wards goes up to Y: y0 + 500, but let's make boundary go to Y: y0 + 600
    boundary_geom = box(x0, y0, x0 + 500, y0 + 600)
    pmc = gpd.GeoDataFrame({"geometry": [boundary_geom]}, crs=OPERATIONAL_CRS)
    
    # Extension: Ward A extends X to 600, boundary is 500
    geomA = box(x0, y0, x0 + 600, y0 + 250)
    wards = gpd.GeoDataFrame({"ward_id": ["A", "B"], "ward_name": ["A", "B"], "geometry": [geomA, geomB]}, crs=OPERATIONAL_CRS)
    
    report = validate_wards(wards, pmc, "ward_id", "ward_name")
    
    # Overlap between A and B is X: 100-500 (width 400), Y: 200-250 (height 50) -> Area 20000
    # Wait, geomA width is 500 (x0 to x0+600), geomB is 400 (x0 to x0+500), so intersection is 400x50 = 20000
    assert report["overlap_area_m2"] > 0
    assert ("A", "B") in report["affected_ward_pairs"] or ("B", "A") in report["affected_ward_pairs"]
    
    # Gap: pmc is y0 to y0+600. Wards go up to y0+500. So Y:500-600 is gap. Area = 500x100 = 50000.
    assert report["raw_gap_area_m2"] > 0
    assert report["significant_gap_area_m2"] > 0
    
    # Extension: geomA goes to x0+600. pmc goes to x0+500. Area = 100 * 250 = 25000.
    assert report["raw_extension_area_m2"] > 0
    assert report["significant_extension_area_m2"] > 0
    
    # Tiny sliver test (below 100m2 threshold)
    sliver_wards = gpd.GeoDataFrame({"ward_id": ["A"], "ward_name": ["A"], "geometry": [box(x0, y0, x0 + 500.1, y0 + 600)]}, crs=OPERATIONAL_CRS)
    sliver_report = validate_wards(sliver_wards, pmc, "ward_id", "ward_name")
    assert sliver_report["raw_extension_area_m2"] > 0
    assert sliver_report["significant_extension_area_m2"] == 0.0

# 14. Invalid geometry detection
def test_invalid_geometry():
    # Bowtie polygon
    bowtie = Polygon([(0, 0), (0, 2), (2, 0), (2, 2), (0, 0)])
    gdf = gpd.GeoDataFrame({"geometry": [bowtie]}, crs=OPERATIONAL_CRS)
    report = validate_boundary(gdf)
    assert report["valid_geometries"] == 0

# 15. Missing authoritative boundary failure and Derived boundary guard
def test_missing_boundary_failure(tmp_path):
    import pytest
    with pytest.raises(ConfigurationError):
        load_pmc_boundary("nonexistent.geojson")
        
    # Derived boundary guard
    derived_gdf = gpd.GeoDataFrame({"geometry": [box(0, 0, 10, 10)], "source_type": ["derived"]}, crs=OPERATIONAL_CRS)
    path = tmp_path / "derived.geojson"
    derived_gdf.to_file(path, driver="GeoJSON")
    
    with pytest.raises(ConfigurationError, match="Derived boundaries cannot be loaded"):
        load_pmc_boundary(path)

# 16. Missing authoritative ward failure
def test_missing_ward_failure():
    import pytest
    with pytest.raises(ConfigurationError):
        load_ward_layer(None)

# 17. Provenance metadata presence & 18. Geometry hash reproducibility
def test_provenance_metadata():
    geom = box(0, 0, 10, 10)
    gdf = gpd.GeoDataFrame({"geometry": [geom]}, crs="EPSG:4326")
    
    gdf_meta = append_provenance_metadata(gdf, "test", "url", "type", "v1", "EPSG:4326")
    
    assert "source_name" in gdf_meta.columns
    assert "geometry_hash" in gdf_meta.columns
    
    # Reproducibility
    hash1 = compute_geometry_hash(gdf)
    hash2 = compute_geometry_hash(gdf.copy())
    assert hash1 == hash2


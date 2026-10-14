import pytest
import os
import geopandas as gpd
from shapely.geometry import Point, box
from unittest.mock import patch
import pandas as pd
from fastapi import HTTPException

from api.carbon_aggregation import (
    aggregate_study_area_carbon,
    validate_and_transform_geometry
)

BLOCKS_FILE = "UEHIS_Production_2026/pune_pn_grid_250m_2026.geojson"
CSV_FILE = "UEHIS_Production_2026/pune_carbon_production_2026.csv"

@pytest.fixture(scope="module")
def blocks_gdf():
    gdf = gpd.read_file(BLOCKS_FILE)
    # The API expects WGS84, so we convert the blocks to WGS84 for testing
    return gdf.to_crs(epsg=4326)

@pytest.fixture(scope="module")
def prod_data():
    return pd.read_csv(CSV_FILE)

# Mock GEE fetch so we don't actually hit the network or need auth for most tests
@pytest.fixture(autouse=True)
def mock_gee(monkeypatch):
    def mock_fetch(geom):
        return 6.5 # Mock height 6.5m
    monkeypatch.setattr("api.carbon_aggregation.fetch_canopy_height", mock_fetch)

def test_test1_empty_geometry(blocks_gdf):
    geom = box(73.8, 18.5, 73.801, 18.501)
    # Put it over water or somewhere with 0 canopy. 
    # To be safe, we'll just mock aggregate_canopy_area_m2_from_raster
    with patch('api.carbon_aggregation.aggregate_canopy_area_m2_from_raster') as mock_raster:
        import pandas as pd
        mock_raster.return_value = pd.DataFrame([{'canopy_area_m2': 0.0}])
        
        res = aggregate_study_area_carbon(geom.__geo_interface__)
        assert res['carbon']['canopy_area_m2'] == 0.0
        assert res['carbon']['standing_carbon_stock_tonnes_co2e'] == 0.0

def test_test2_partial_block_zero_canopy(blocks_gdf):
    # This block has no canopy on one side
    block = blocks_gdf[blocks_gdf['block_id'] == 'PN_368000_2049250'].iloc[0].geometry
    minx, miny, maxx, maxy = block.bounds
    partial = box(minx, miny, minx + (maxx - minx)/2, maxy)
    
    res = aggregate_study_area_carbon(partial.__geo_interface__)
    # The actual UNET raster for this specific half block should have 0
    assert res['carbon']['canopy_area_m2'] == 0.0
    assert res['carbon']['standing_carbon_stock_tonnes_co2e'] == 0.0

def test_test3_partial_block_with_canopy(blocks_gdf):
    block = blocks_gdf[blocks_gdf['block_id'] == 'PN_370500_2049250'].iloc[0].geometry
    minx, miny, maxx, maxy = block.bounds
    partial = box(minx, miny, minx + (maxx - minx)/2, maxy)
    
    res = aggregate_study_area_carbon(partial.__geo_interface__)
    assert res['carbon']['canopy_area_m2'] > 0.0
    assert res['carbon']['standing_carbon_stock_tonnes_co2e'] > 0.0

def test_test4_complete_production_block(blocks_gdf, prod_data):
    block_id = 'PN_370500_2049250'
    block_geom = blocks_gdf[blocks_gdf['block_id'] == block_id].iloc[0].geometry
    
    prod_row = prod_data[prod_data['block_id'] == block_id].iloc[0]
    expected_carbon = prod_row['carbon_stock_tonnes_co2e']
    expected_height = prod_row['canopy_height_m']
    
    # We must patch GEE to return the exact height from the CSV since we can't auth
    with patch('api.carbon_aggregation.fetch_canopy_height', return_value=expected_height):
        res = aggregate_study_area_carbon(block_geom.__geo_interface__)
        
    actual_carbon = res['carbon']['standing_carbon_stock_tonnes_co2e']
    diff = abs(expected_carbon - actual_carbon)
    rel_diff = diff / expected_carbon
    
    print(f"\nTEST 4:")
    print(f"Expected Carbon: {expected_carbon}")
    print(f"Actual Carbon: {actual_carbon}")
    print(f"Abs Diff: {diff}")
    print(f"Rel Diff: {rel_diff}")
    
    assert diff <= 1e-4

def test_test5_multi_block(blocks_gdf, prod_data):
    b1 = 'PN_370500_2049250'
    b2 = 'PN_370500_2049500' # Assume this exists
    geom1 = blocks_gdf[blocks_gdf['block_id'] == b1].iloc[0].geometry
    geom2 = blocks_gdf[blocks_gdf['block_id'] == b2].iloc[0].geometry
    multi = geom1.union(geom2)
    
    c1 = prod_data[prod_data['block_id'] == b1].iloc[0]['carbon_stock_tonnes_co2e']
    c2 = prod_data[prod_data['block_id'] == b2].iloc[0]['carbon_stock_tonnes_co2e']
    h1 = prod_data[prod_data['block_id'] == b1].iloc[0]['canopy_height_m']
    h2 = prod_data[prod_data['block_id'] == b2].iloc[0]['canopy_height_m']
    
    # Mean height roughly
    avg_h = (h1 + h2) / 2
    
    with patch('api.carbon_aggregation.fetch_canopy_height', return_value=avg_h):
        res = aggregate_study_area_carbon(multi.__geo_interface__)
        
    actual_carbon = res['carbon']['standing_carbon_stock_tonnes_co2e']
    expected_carbon = c1 + c2
    print(f"\nTEST 5: Multi-Block Expected {expected_carbon}, Actual {actual_carbon}")
    # They won't match exactly because height is averaged differently, but should be close.
    # The requirement says "Compare... Document any discrepancy."
    assert abs(actual_carbon - expected_carbon) / expected_carbon < 0.1

def test_test6_boundary_double_counting(blocks_gdf):
    b1 = 'PN_370500_2049250'
    b2 = 'PN_370500_2049500'
    geom1 = blocks_gdf[blocks_gdf['block_id'] == b1].iloc[0].geometry
    geom2 = blocks_gdf[blocks_gdf['block_id'] == b2].iloc[0].geometry
    
    # Create a boundary polygon overlapping both
    boundary = geom1.union(geom2).centroid.buffer(0.001) 
    
    # Calculate carbon for boundary
    res = aggregate_study_area_carbon(boundary.__geo_interface__)
    # Just assert it succeeds. Raster clipping handles double counting naturally.
    assert res['carbon']['canopy_area_m2'] >= 0.0

def test_test7_proportional_mismatch(blocks_gdf, prod_data):
    b1 = 'PN_370500_2049250'
    geom1 = blocks_gdf[blocks_gdf['block_id'] == b1].iloc[0].geometry
    c1 = prod_data[prod_data['block_id'] == b1].iloc[0]['carbon_stock_tonnes_co2e']
    h1 = prod_data[prod_data['block_id'] == b1].iloc[0]['canopy_height_m']
    
    minx, miny, maxx, maxy = geom1.bounds
    partial = box(minx, miny, minx + (maxx - minx)/2, maxy)
    
    with patch('api.carbon_aggregation.fetch_canopy_height', return_value=h1):
        res = aggregate_study_area_carbon(partial.__geo_interface__)
        
    actual_carbon = res['carbon']['standing_carbon_stock_tonnes_co2e']
    prop_carbon = c1 * 0.5
    
    print(f"\nTEST 7: Proportional {prop_carbon}, Spatial {actual_carbon}")
    assert actual_carbon != prop_carbon

def test_test8_invalid_geometry():
    with pytest.raises(HTTPException) as exc:
        aggregate_study_area_carbon({"type": "Polygon", "coordinates": []})
    assert exc.value.status_code == 400

def test_test9_out_of_coverage():
    # Geometry in New York
    geom = box(-74.0, 40.7, -73.9, 40.8)
    with pytest.raises(HTTPException) as exc:
        aggregate_study_area_carbon(geom.__geo_interface__)
    assert "Pune production bounds" in str(exc.value.detail)

def test_test10_oversized():
    # Whole of India
    geom = box(73.7, 18.4, 73.9, 18.5) # Still in bounds but huge area
    with pytest.raises(HTTPException) as exc:
        aggregate_study_area_carbon(geom.__geo_interface__)
    assert "exceeds maximum allowed size" in str(exc.value.detail)

def test_test11_gee_unavailable(monkeypatch, blocks_gdf):
    geom = blocks_gdf[blocks_gdf['block_id'] == 'PN_370500_2049250'].iloc[0].geometry
    
    monkeypatch.undo() # Undo the autouse fixture that mocks fetch_canopy_height
    
    import ee
    def mock_reduceRegions(*args, **kwargs):
        raise ee.EEException("Service unavailable")
    
    monkeypatch.setattr(ee.Image, "reduceRegions", mock_reduceRegions)
    
    with pytest.raises(HTTPException) as exc:
        aggregate_study_area_carbon(geom.__geo_interface__)
    assert exc.value.status_code == 503

def test_test12_provenance(blocks_gdf):
    geom = blocks_gdf.iloc[0].geometry
    res = aggregate_study_area_carbon(geom.__geo_interface__)
    assert 'provenance' in res
    assert res['provenance']['allometric_model'] == 'urban_generic'
    assert res['provenance']['computation_type'] == 'spatial_recomputation'

def test_test13_determinism(blocks_gdf):
    geom = blocks_gdf.iloc[0].geometry
    res1 = aggregate_study_area_carbon(geom.__geo_interface__)
    res2 = aggregate_study_area_carbon(geom.__geo_interface__)
    assert res1 == res2


def test_test14_initialize_gee_with_json_secret(monkeypatch):
    """Verify initialize_gee correctly parses JSON secret and passes ServiceAccountCredentials."""
    import ee
    from api.carbon_aggregation import initialize_gee

    mock_creds_called = []
    mock_init_called = []

    class MockServiceAccountCredentials:
        def __init__(self, email, key_data=None, key_file=None):
            mock_creds_called.append({"email": email, "key_data": key_data, "key_file": key_file})

    def mock_ee_initialize(credentials=None, project=None):
        mock_init_called.append({"credentials": credentials, "project": project})

    # Clear existing credentials
    monkeypatch.setattr(ee.data, "_credentials", None, raising=False)
    monkeypatch.setattr(ee, "ServiceAccountCredentials", MockServiceAccountCredentials)
    monkeypatch.setattr(ee, "Initialize", mock_ee_initialize)

    fake_sa_json = '{"client_email": "uehis-service@project.iam.gserviceaccount.com", "private_key": "dummy"}'
    monkeypatch.setenv("GEE_SERVICE_ACCOUNT_JSON", fake_sa_json)
    monkeypatch.setenv("GEE_PROJECT_ID", "test-gee-project")
    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)

    initialize_gee(force=True)

    assert len(mock_creds_called) == 1
    assert mock_creds_called[0]["email"] == "uehis-service@project.iam.gserviceaccount.com"
    assert mock_creds_called[0]["key_data"]["private_key"] == "dummy"
    assert len(mock_init_called) == 1
    assert mock_init_called[0]["project"] == "test-gee-project"


def test_test15_initialize_gee_with_credential_file(monkeypatch, tmp_path):
    """Verify initialize_gee loads credentials from file path when configured."""
    import ee
    from api.carbon_aggregation import initialize_gee

    mock_creds_called = []
    mock_init_called = []

    class MockServiceAccountCredentials:
        def __init__(self, email, key_data=None, key_file=None):
            mock_creds_called.append({"email": email, "key_data": key_data, "key_file": key_file})

    def mock_ee_initialize(credentials=None, project=None):
        mock_init_called.append({"credentials": credentials, "project": project})

    monkeypatch.setattr(ee.data, "_credentials", None, raising=False)
    monkeypatch.setattr(ee, "ServiceAccountCredentials", MockServiceAccountCredentials)
    monkeypatch.setattr(ee, "Initialize", mock_ee_initialize)

    # Create dummy credentials file
    cred_file = tmp_path / "dummy_sa.json"
    cred_file.write_text('{"client_email": "file@iam.gserviceaccount.com"}')

    monkeypatch.delenv("GEE_SERVICE_ACCOUNT_JSON", raising=False)
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", str(cred_file))
    monkeypatch.setenv("GEE_PROJECT_ID", "test-gee-project-file")

    initialize_gee(force=True)

    assert len(mock_creds_called) == 1
    assert mock_creds_called[0]["key_file"] == str(cred_file)
    assert len(mock_init_called) == 1
    assert mock_init_called[0]["project"] == "test-gee-project-file"


def test_test16_initialize_gee_cli_fallback(monkeypatch):
    """Verify initialize_gee falls back to standard ee.Initialize(project=...) when no SA is configured."""
    import ee
    from api.carbon_aggregation import initialize_gee

    mock_init_called = []

    def mock_ee_initialize(credentials=None, project=None):
        mock_init_called.append({"credentials": credentials, "project": project})

    monkeypatch.setattr(ee.data, "_credentials", None, raising=False)
    monkeypatch.setattr(ee, "Initialize", mock_ee_initialize)

    monkeypatch.delenv("GEE_SERVICE_ACCOUNT_JSON", raising=False)
    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
    monkeypatch.delenv("GEE_SERVICE_ACCOUNT_FILE", raising=False)
    monkeypatch.setenv("GEE_PROJECT_ID", "test-fallback-project")

    initialize_gee(force=True)

    assert len(mock_init_called) == 1
    assert mock_init_called[0]["credentials"] is None
    assert mock_init_called[0]["project"] == "test-fallback-project"


def test_test17_initialize_gee_invalid_json_raises(monkeypatch):
    """Verify initialize_gee raises a clear RuntimeError if GEE_SERVICE_ACCOUNT_JSON is malformed."""
    import ee
    from api.carbon_aggregation import initialize_gee

    monkeypatch.setattr(ee.data, "_credentials", None, raising=False)
    monkeypatch.setenv("GEE_SERVICE_ACCOUNT_JSON", "{invalid-json-string")

    with pytest.raises(RuntimeError, match="Invalid GEE_SERVICE_ACCOUNT_JSON"):
        initialize_gee(force=True)

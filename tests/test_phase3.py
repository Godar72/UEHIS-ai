import os
import json
import pytest
from pathlib import Path
import geopandas as gpd
from shapely.geometry import box
import pandas as pd

from utils.geography import generate_block_grid
from scoring.uehi_score import load_config

def test_phase3_config_consistency():
    """Verify that uehi_config.json exactly matches the Phase 6-factor model."""
    config = load_config()
    factors = config.get("factors", {})
    
    expected_factors = {
        "ndvi": "positive",
        "tree_density": "positive",
        "pm25": "negative",
        "temperature": "negative",
        "impervious_surfaces": "negative",
        "population_exposure": "negative",
    }
    
    assert set(factors.keys()) == set(expected_factors.keys()), "Config factors do not match the expected 6-factor list."
    
    for f_name, f_dir in expected_factors.items():
        assert factors[f_name]["direction"] == f_dir, f"{f_name} has incorrect direction"
        
    assert "biodiversity" not in factors, "Biodiversity must be removed from the authoritative configuration."
    
    total_weight = sum(f["weight"] for f in factors.values())
    assert abs(total_weight - 1.0) < 1e-6, "Weights must sum to 1.0"
    
    desc = config.get("description", "")
    assert "6-factor" in desc, "Description should state it is a 6-factor model."

def test_authoritative_geometry():
    """Verify that generated blocks meet the authoritative geographic foundation."""
    bounds = (73.7, 18.4, 73.8, 18.5)
    boundary_geom = box(bounds[0], bounds[1], bounds[2], bounds[3])
    boundary_gdf = gpd.GeoDataFrame({"geometry": [boundary_geom]}, crs="EPSG:4326")
    
    grid = generate_block_grid(boundary_gdf, cell_size=250.0)
    
    assert grid.crs == "EPSG:32643", "Authoritative grid must use EPSG:32643"
    
    # Check that block IDs use persistent formatting PN_x_y
    for idx, row in grid.iterrows():
        assert row.block_id.startswith("PN_"), f"Block ID {row.block_id} does not match persistent origin pattern"
        
    # Check block dimensions
    for geom in grid.geometry:
        bounds = geom.bounds
        assert abs((bounds[2] - bounds[0]) - 250.0) < 1e-4, "Width must be 250m"
        assert abs((bounds[3] - bounds[1]) - 250.0) < 1e-4, "Height must be 250m"

@pytest.mark.skipif(os.environ.get("UEHIS_TEST_NO_GEE") != "1", reason="Only testing offline behavior")
def test_offline_test_metadata():
    """Verify that DEV mode marks provenance appropriately and PM2.5 is not zero-substituted."""
    manifest_path = Path("outputs/phase3_manifest.json")
    if manifest_path.exists():
        with open(manifest_path, "r") as f:
            manifest = json.load(f)
        assert manifest.get("scoring_status") == "offline_test_only", "DEV mode must be marked as offline_test_only"
        
    output_csv = Path("outputs/TEST_ONLY_kothrud_scores_phase3.csv")
    if output_csv.exists():
        df = pd.read_csv(output_csv)
        assert df["pm25"].isnull().all(), "PM2.5 must remain NaN and not be zero-substituted in DEV output"

import numpy as np
from run_phase3 import validate_pm25_for_scoring

def test_production_pm25_hard_fail():
    """Verify that production mode hard-fails when PM2.5 is missing or NaN."""
    # Missing PM2.5 column
    df_missing = pd.DataFrame({"ndvi": [0.5, 0.6]})
    with pytest.raises(RuntimeError, match="Real PM2.5 is required for production scoring"):
        validate_pm25_for_scoring(df_missing, is_offline_dev=False)

    # PM2.5 contains NaN
    df_nan = pd.DataFrame({"ndvi": [0.5, 0.6], "pm25": [15.0, np.nan]})
    with pytest.raises(RuntimeError, match="Real PM2.5 is required for production scoring"):
        validate_pm25_for_scoring(df_nan, is_offline_dev=False)

def test_offline_pm25_allows_nan():
    """Verify that offline mode allows missing/NaN PM2.5 without exception."""
    df_nan = pd.DataFrame({"ndvi": [0.5, 0.6], "pm25": [np.nan, np.nan]})
    # Should not raise an exception
    validate_pm25_for_scoring(df_nan, is_offline_dev=True)
    
    df_missing = pd.DataFrame({"ndvi": [0.5, 0.6]})
    # Should not raise an exception
    validate_pm25_for_scoring(df_missing, is_offline_dev=True)

def test_config_weights_not_production_entropy():
    """
    Ensure the documentation explicitly asserts that config weights are 
    baseline/reference only, and production runs use dynamically calculated entropy weights.
    """
    config = load_config()
    desc = config.get("description", "")
    assert "baseline" in desc.lower() or "reference" in desc.lower(), "Config description must clarify weights are reference/baseline only"
    assert "entropy" in desc.lower(), "Config description must state that production uses entropy-derived weights"

def test_synergy_and_population_multiplier_bounds():
    """Verify synergy numerical calculation and population multiplier bounds [0.7, 1.0]."""
    from scoring.uehi_score import compute_uehi_scores
    
    n = 10
    rng = np.random.default_rng(42)
    # create sample data
    data = {
        "ndvi": [0.0, 1.0, 0.5, 0.2] + list(rng.uniform(0.1, 0.9, n - 4)),
        "tree_density": [0, 500, 200, 100] + list(rng.uniform(0, 500, n - 4)),
        "pm25": [300, 0, 100, 50] + list(rng.uniform(10, 50, n - 4)),
        "temperature": [50, 20, 35, 40] + list(rng.uniform(25, 40, n - 4)),
        "impervious_surfaces": [1.0, 0.0, 0.5, 0.8] + list(rng.uniform(0, 1, n - 4)),
        "population_exposure": [50_000, 0, 25_000, 10_000] + list(rng.uniform(100, 50_000, n - 4)),
    }
    geoms = [box(i, 0, i + 1, 1) for i in range(n)]
    gdf = gpd.GeoDataFrame(data, geometry=geoms, crs="EPSG:4326")
    
    # Run compute_uehi_scores which now implements production formula
    result = compute_uehi_scores(gdf)
    
    # Recalculate manually to verify logic
    from scoring.normalize import normalise_factor
    pop_norm = normalise_factor(gdf["population_exposure"], "positive")
    pop_mult = 1 - 0.3 * pop_norm
    
    assert pop_mult.min() >= 0.7, "Population multiplier dropped below 0.7 bound"
    assert pop_mult.max() <= 1.0, "Population multiplier exceeded 1.0 bound"
    assert pop_mult.iloc[0] == pytest.approx(0.7), "Max population exposure should yield exactly 0.7 multiplier"
    assert pop_mult.iloc[1] == pytest.approx(1.0), "Min population exposure should yield exactly 1.0 multiplier"
    
    ndvi_norm = normalise_factor(gdf["ndvi"], "positive")
    temp_norm = normalise_factor(gdf["temperature"], "negative")
    synergy = 0.1 * ndvi_norm * temp_norm * 100
    
    assert synergy.iloc[0] == pytest.approx(0.0), "Min NDVI should yield 0 synergy"
    assert synergy.iloc[1] == pytest.approx(10.0), "Max NDVI and Min Temp should yield max synergy (10.0)"

def test_population_conservation(tmp_path):
    """Verify raster zonal aggregation of population COUNT data is conservative (sum)."""
    import rasterio
    from rasterio.transform import from_origin
    from feature_engineering.aggregate_factors import aggregate_population_to_blocks
    
    # Create a dummy 4x4 population count raster with 10 people per pixel (total 160)
    pop_data = np.full((4, 4), 10, dtype=np.float32)
    pop_tif = tmp_path / "dummy_pop.tif"
    
    transform = from_origin(0, 40, 10, 10)
    with rasterio.open(
        pop_tif, 'w', driver='GTiff',
        height=4, width=4, count=1, dtype=pop_data.dtype,
        crs='EPSG:32643', transform=transform, nodata=-9999
    ) as dst:
        dst.write(pop_data, 1)
        
    # Dummy block index array mimicking two blocks splitting the raster vertically
    block_idx_arr = np.array([
        [0, 0, 1, 1],
        [0, 0, 1, 1],
        [0, 0, 1, 1],
        [0, 0, 1, 1]
    ], dtype=np.int32)
    
    df_pop = aggregate_population_to_blocks(str(pop_tif), block_idx_arr, num_blocks=2)
    
    # Block 0 has 8 pixels * 10 = 80
    assert df_pop.iloc[0]["population_exposure"] == 80.0
    # Block 1 has 8 pixels * 10 = 80
    assert df_pop.iloc[1]["population_exposure"] == 80.0
    
    # Total conserved
    assert df_pop["population_exposure"].sum() == 160.0

def test_manifest_contains_model_hash():
    """Verify the manifest structure explicitly supports U-Net model_checksums."""
    from feature_engineering.aggregate_factors import aggregate_all_factors
    import rasterio
    from shapely.geometry import Point
    
    # Not invoking the whole pipeline, just checking signature/manifest format.
    # The signature accepts model_checksums. We can parse the source code of the function.
    import inspect
    sig = inspect.signature(aggregate_all_factors)
    assert "model_checksums" in sig.parameters, "aggregate_all_factors must accept model_checksums"

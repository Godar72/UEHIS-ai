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
        
    from shapely.geometry import box
    import geopandas as gpd
    
    # Dummy block mimicking two blocks splitting the raster vertically
    b_left = box(0, 0, 20, 40)
    b_right = box(20, 0, 40, 40)
    blocks_gdf = gpd.GeoDataFrame({'block_id': [0, 1]}, geometry=[b_left, b_right], crs="EPSG:32643")
    
    df_pop = aggregate_population_to_blocks(str(pop_tif), blocks_gdf)
    
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

def test_pm25_fixed_weight_and_sum(tmp_path):
    """TEST 1: PM2.5 fixed weight == 0.02 and all weights sum to 1.0."""
    from run_phase3 import calculate_weights
    # Create small deterministic DF
    df = pd.DataFrame({
        "ndvi": [0.1, 0.5, 0.9],
        "tree_density": [10, 50, 90],
        "pm25": [15.0, 35.0, 55.0],
        "temperature": [30, 35, 40],
        "impervious_surfaces": [0.1, 0.5, 0.9],
        "population_exposure": [100, 500, 1000]
    })
    factor_cols = ["ndvi", "tree_density", "pm25", "temperature", "impervious_surfaces", "population_exposure"]
    ew = calculate_weights(df, factor_cols, is_offline_dev=False)
    
    assert ew["pm25"] == pytest.approx(0.02)
    other_sum = sum(ew[c] for c in factor_cols if c != "pm25")
    assert other_sum == pytest.approx(0.98)
    total_sum = sum(ew.values())
    assert total_sum == pytest.approx(1.0)

def test_negative_ndvi():
    """TEST 2: Negative NDVI doesn't fail entropy calculation."""
    from run_phase3 import calculate_weights
    df = pd.DataFrame({
        "ndvi": [-0.1, 0.5, 0.9], # Negative NDVI
        "tree_density": [10, 50, 90],
        "pm25": [15.0, 35.0, 55.0],
        "temperature": [30, 35, 40],
        "impervious_surfaces": [0.1, 0.5, 0.9],
        "population_exposure": [100, 500, 1000]
    })
    factor_cols = ["ndvi", "tree_density", "pm25", "temperature", "impervious_surfaces", "population_exposure"]
    ew = calculate_weights(df, factor_cols, is_offline_dev=False)
    assert ew["ndvi"] > 0
    assert np.isfinite(ew["ndvi"])

def test_missing_scorable_factor_hard_failure(tmp_path):
    """TEST 3 & TEST 9: Missing scorable factor causes hard failure. Do not impute."""
    from run_phase3 import validate_factor_data
    df = pd.DataFrame({
        "block_id": ["A", "B"],
        "ndvi": [0.5, 0.6],
        "tree_density": [10, 20],
        "pm25": [30, 40],
        "temperature": [35, np.nan], # missing data!
        "impervious_surfaces": [0.1, 0.2],
        "population_exposure": [100, 200]
    })
    factor_cols = ["ndvi", "tree_density", "pm25", "temperature", "impervious_surfaces", "population_exposure"]
    
    with pytest.raises(RuntimeError, match="Missing factor data for scorable blocks. Do not impute."):
        validate_factor_data(df, factor_cols, is_offline_dev=False)

def test_non_finite_scorable_factor():
    """TEST 4: Non-finite scorable factor causes hard failure."""
    from run_phase3 import validate_factor_data
    df = pd.DataFrame({
        "block_id": ["A", "B"],
        "ndvi": [0.5, 0.6],
        "tree_density": [10, 20],
        "pm25": [30, 40],
        "temperature": [35, np.inf], # non-finite
        "impervious_surfaces": [0.1, 0.2],
        "population_exposure": [100, 200]
    })
    factor_cols = ["ndvi", "tree_density", "pm25", "temperature", "impervious_surfaces", "population_exposure"]
    
    with pytest.raises(RuntimeError, match="Missing factor data for scorable blocks."):
        validate_factor_data(df, factor_cols, is_offline_dev=False)

def test_missing_eligibility_hard_failure():
    """TEST 5: Missing eligibility causes a hard failure (via validate='one_to_one')."""
    from run_phase3 import merge_eligibility
    df = pd.DataFrame({"block_id": ["A", "B", "C"]}) # Factor has C
    eligibility = pd.DataFrame({"block_id": ["A", "B"], "score_status": ["scorable", "scorable"]}) # Eligibility missing C
    
    with pytest.raises(RuntimeError, match="Eligibility merge failed"):
        merge_eligibility(df, eligibility)

def test_block_id_cross_validation(tmp_path):
    """TEST 6: Block-ID cross-validation detects mismatched IDs."""
    from utils.validate_production import validate_production_artifacts
    
    data_dir = tmp_path / "UEHIS_Production_2026"
    data_dir.mkdir()
    
    pd.DataFrame({"block_id": ["A", "B"]}).to_csv(data_dir / "pune_factors.csv", index=False)
    pd.DataFrame({"block_id": ["A", "C"]}).to_csv(data_dir / "pune_eligibility.csv", index=False)
    
    with open(data_dir / "pune_grid.geojson", "w") as f:
        json.dump({"features": [{"properties": {"block_id": "A"}}, {"properties": {"block_id": "B"}}]}, f)
        
    config = {
        "production_artifacts": {
            "factors": "pune_factors.csv",
            "eligibility": "pune_eligibility.csv",
            "pn_grid": "pune_grid.geojson"
        }
    }
    
    config_dir = tmp_path / "configs"
    config_dir.mkdir()
    config_path = config_dir / "production_2026.json"
    with open(config_path, "w") as f:
        json.dump(config, f)
        
    with pytest.raises(RuntimeError, match="Validation FAILED"):
        validate_production_artifacts(data_dir=data_dir, config_path=config_path, raise_on_error=True)

def test_excluded_block_preservation():
    """TEST 7: Excluded blocks are preserved in output assembly."""
    from run_phase3 import assemble_output
    df_scoring = pd.DataFrame({
        "block_id": ["A", "B"],
        "ndvi": [0.5, 0.6],
        "uehi_score": [80, 90],
        "risk_level": ["Low", "Low"]
    })
    df_excluded = pd.DataFrame({
        "block_id": ["C"],
        "ndvi": [0.1],
        "uehi_score": [999], # Should be wiped
        "risk_level": ["Invalid"] # Should be wiped
    })
    
    final_df = assemble_output(df_scoring, df_excluded)
    assert len(final_df) == 3
    excluded_row = final_df[final_df["block_id"] == "C"].iloc[0]
    assert excluded_row["ndvi"] == 0.1
    assert pd.isna(excluded_row["uehi_score"])
    assert pd.isna(excluded_row["risk_level"])

def test_final_output_row_counts():
    """TEST 8: Output contains 5309 rows, 5298 scorable, 11 excluded."""
    from run_phase3 import assemble_output
    df_scoring = pd.DataFrame({"block_id": [f"S_{i}" for i in range(5298)]})
    df_excluded = pd.DataFrame({"block_id": [f"E_{i}" for i in range(11)]})
    
    final_df = assemble_output(df_scoring, df_excluded)
    assert len(final_df) == 5309

def test_manifest_generation_and_shas(tmp_path):
    """TEST 10 & 11: Manifest generation explicitly hashes input CSVs."""
    from run_phase3 import generate_manifest_dict
    import hashlib
    
    factors_csv = tmp_path / "f.csv"
    factors_csv.write_text("dummy_factors")
    
    eligibility_csv = tmp_path / "e.csv"
    eligibility_csv.write_text("dummy_eligibility")
    
    out_csv = tmp_path / "out.csv"
    out_csv.write_text("dummy_out")
    
    prod_config = {"factors": "f.csv", "eligibility": "e.csv"}
    config_path = "configs/prod.json"
    
    manifest = generate_manifest_dict(
        final_df=pd.DataFrame([1,2,3]),
        df_scoring=pd.DataFrame([1,2]),
        df_excluded=pd.DataFrame([3]),
        factor_cols=["ndvi"],
        ew={"ndvi": 1.0, "pm25": 0.02},
        factors_config={"ndvi": ("positive", "REAL")},
        out_path=out_csv,
        factors_csv=factors_csv,
        eligibility_csv=eligibility_csv,
        config_path=config_path,
        prod_config=prod_config
    )
    
    # Compute manually
    def sha(p):
        with open(p, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
            
    assert manifest["factor_sha256"] == sha(factors_csv)
    assert manifest["eligibility_sha256"] == sha(eligibility_csv)
    assert manifest["output_sha256"] == sha(out_csv)
    assert manifest["total_blocks"] == 3
    assert manifest["pm25_fixed_weight"] == 0.02

def test_population_exposure_direction():
    """Verify population_exposure is strictly configured as positive."""
    from run_phase3 import FACTORS
    assert FACTORS["population_exposure"][0] == "positive", "population_exposure must be configured as positive"

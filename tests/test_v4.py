"""
tests/test_v4.py
────────────────
Unit tests for the V4 raw factor dataset generation.
"""

import pandas as pd
import numpy as np
import pytest
from pathlib import Path
import rasterio

V4_OUTPUT = Path("outputs/kothrud_factors_v4.csv")
COMPOSITE_TIF = Path("kothrud_pune_composite.tif")

@pytest.fixture
def v4_data():
    if not V4_OUTPUT.exists():
        pytest.skip(f"{V4_OUTPUT} not found. Run run_scoring.py first.")
    return pd.read_csv(V4_OUTPUT)

def test_v4_schema(v4_data):
    """Verify exactly 6 active factors + block_id exist."""
    expected_cols = {
        "block_id",
        "tree_density",
        "ndvi",
        "impervious_surfaces",
        "temperature",
        "population_exposure",
        "pm25"
    }
    assert set(v4_data.columns) == expected_cols
    assert "biodiversity" not in v4_data.columns

def test_v4_row_count(v4_data):
    """Verify exactly 256 blocks are preserved."""
    assert len(v4_data) == 256

import os

def test_v4_no_missing(v4_data):
    """Verify no missing data in the final matrix."""
    if os.environ.get("UEHIS_TEST_NO_GEE") == "1":
        # In DEV/test mode without GEE, pm25 is expected to be NaN
        check_cols = [c for c in v4_data.columns if c != "pm25"]
        assert not v4_data[check_cols].isnull().any().any()
    else:
        assert not v4_data.isnull().any().any()

def test_tree_density_bounds(v4_data):
    """Verify tree_density is strictly [0, 1]."""
    assert (v4_data["tree_density"] >= 0).all()
    assert (v4_data["tree_density"] <= 1).all()

def test_impervious_bounds(v4_data):
    """Verify impervious_surfaces is strictly [0, 1]."""
    assert (v4_data["impervious_surfaces"] >= 0).all()
    assert (v4_data["impervious_surfaces"] <= 1).all()

def test_ndvi_bounds(v4_data):
    """Verify NDVI is physically valid [-1, 1]."""
    assert (v4_data["ndvi"] >= -1).all()
    assert (v4_data["ndvi"] <= 1).all()

def test_temperature_valid(v4_data):
    """Verify temperature is somewhat reasonable for Pune (e.g., >0 C)."""
    assert (v4_data["temperature"] > 0).all()
    assert (v4_data["temperature"] < 60).all()

def test_population_valid(v4_data):
    """Verify population is >= 0."""
    assert (v4_data["population_exposure"] >= 0).all()

def test_pm25_valid(v4_data):
    """Verify PM2.5 is >= 0."""
    if os.environ.get("UEHIS_TEST_NO_GEE") == "1":
        # Missing data is allowed in dev mode
        valid_pm25 = v4_data["pm25"].dropna()
        assert (valid_pm25 >= 0).all()
    else:
        assert (v4_data["pm25"] >= 0).all()

def test_composite_ndvi_band():
    """Verify the 4th band of the composite raster is present."""
    if not COMPOSITE_TIF.exists():
        pytest.skip(f"{COMPOSITE_TIF} not found.")
    
    with rasterio.open(COMPOSITE_TIF) as src:
        assert src.count >= 4
        # Validate that we can read the 4th band
        band4 = src.read(4)
        assert band4 is not None

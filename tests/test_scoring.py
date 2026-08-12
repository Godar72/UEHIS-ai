"""
tests/test_scoring.py
─────────────────────
Unit tests for the UEHI scoring module.

Run with:  python -m pytest tests/test_scoring.py -v
"""

import json
import math
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
from shapely.geometry import box

from scoring.normalize import min_max_scale, inverted_min_max_scale, normalise_factor
from scoring.uehi_score import (
    compute_uehi_scores,
    classify_risk,
    load_config,
    ScoringConfigError,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def default_config():
    """Load the built-in default config."""
    return load_config()


@pytest.fixture
def sample_gdf():
    """
    Create a small GeoDataFrame with all 8 factor columns and varied values.
    """
    n = 20
    rng = np.random.default_rng(42)
    data = {
        "ndvi": rng.uniform(0.0, 0.8, n),
        "tree_density": rng.uniform(0, 500, n),
        "biodiversity": rng.uniform(0, 1, n),
        "aqi": rng.uniform(20, 300, n),
        "temperature": rng.uniform(25, 50, n),
        "impervious_surfaces": rng.uniform(0, 1, n),
        "water_availability": rng.uniform(0, 1, n),
        "population_exposure": rng.uniform(100, 50_000, n),
    }
    geoms = [box(i, 0, i + 1, 1) for i in range(n)]
    return gpd.GeoDataFrame(data, geometry=geoms, crs="EPSG:4326")


# ---------------------------------------------------------------------------
# Config tests
# ---------------------------------------------------------------------------

class TestConfig:
    def test_weights_sum_to_one(self, default_config):
        """Factor weights must sum to exactly 1.0."""
        factors = default_config["factors"]
        total = sum(f["weight"] for f in factors.values())
        assert math.isclose(total, 1.0, abs_tol=1e-9), (
            f"Weights sum to {total}, expected 1.0"
        )

    def test_all_factors_present(self, default_config):
        """Config must contain all 8 expected factors."""
        expected = {
            "ndvi", "tree_density", "biodiversity", "aqi",
            "temperature", "impervious_surfaces",
            "water_availability", "population_exposure",
        }
        assert set(default_config["factors"].keys()) == expected

    def test_valid_directions(self, default_config):
        """Each factor direction must be 'positive' or 'negative'."""
        for name, spec in default_config["factors"].items():
            assert spec["direction"] in ("positive", "negative"), (
                f"Factor '{name}' has invalid direction: {spec['direction']}"
            )

    def test_weights_in_range(self, default_config):
        """Each individual weight must be in [0, 1]."""
        for name, spec in default_config["factors"].items():
            assert 0.0 <= spec["weight"] <= 1.0, (
                f"Factor '{name}' weight {spec['weight']} out of range"
            )

    def test_invalid_config_bad_weights(self, tmp_path):
        """Config with weights not summing to 1 should raise."""
        bad_config = {
            "factors": {
                "ndvi": {"weight": 0.5, "direction": "positive"},
                "aqi": {"weight": 0.3, "direction": "negative"},
            }
        }
        path = tmp_path / "bad.json"
        path.write_text(json.dumps(bad_config))
        with pytest.raises(ScoringConfigError, match="sum to 1.0"):
            load_config(path)

    def test_missing_config_file(self):
        """Non-existent config path should raise."""
        with pytest.raises(ScoringConfigError, match="not found"):
            load_config("/nonexistent/path.json")


# ---------------------------------------------------------------------------
# Normalisation tests
# ---------------------------------------------------------------------------

class TestNormalize:
    def test_min_max_bounds(self):
        s = pd.Series([10, 20, 30, 40, 50])
        normed = min_max_scale(s)
        assert normed.min() == pytest.approx(0.0)
        assert normed.max() == pytest.approx(1.0)

    def test_inverted_min_max_bounds(self):
        s = pd.Series([10, 20, 30, 40, 50])
        normed = inverted_min_max_scale(s)
        assert normed.min() == pytest.approx(0.0)
        assert normed.max() == pytest.approx(1.0)
        # Highest raw value should map to lowest normalised
        assert normed.iloc[-1] == pytest.approx(0.0)
        assert normed.iloc[0] == pytest.approx(1.0)

    def test_constant_series_returns_zero(self):
        s = pd.Series([5.0, 5.0, 5.0])
        assert min_max_scale(s).sum() == 0.0
        assert inverted_min_max_scale(s).sum() == 0.0

    def test_dispatcher_positive(self):
        s = pd.Series([1, 2, 3])
        result = normalise_factor(s, "positive")
        assert result.iloc[-1] == pytest.approx(1.0)

    def test_dispatcher_negative(self):
        s = pd.Series([1, 2, 3])
        result = normalise_factor(s, "negative")
        assert result.iloc[0] == pytest.approx(1.0)

    def test_dispatcher_invalid_raises(self):
        with pytest.raises(ValueError, match="Unknown direction"):
            normalise_factor(pd.Series([1, 2]), "sideways")


# ---------------------------------------------------------------------------
# Scoring tests
# ---------------------------------------------------------------------------

class TestUEHIScoring:
    def test_score_column_exists(self, sample_gdf):
        result = compute_uehi_scores(sample_gdf)
        assert "uehi_score" in result.columns

    def test_score_never_exceeds_100(self, sample_gdf):
        result = compute_uehi_scores(sample_gdf)
        assert result["uehi_score"].max() <= 100.0, (
            f"Max score {result['uehi_score'].max()} exceeds 100"
        )

    def test_score_never_below_zero(self, sample_gdf):
        result = compute_uehi_scores(sample_gdf)
        assert result["uehi_score"].min() >= 0.0, (
            f"Min score {result['uehi_score'].min()} is below 0"
        )

    def test_score_range_with_extreme_values(self):
        """Even with extreme inputs, score must stay in [0, 100]."""
        n = 100
        rng = np.random.default_rng(99)
        data = {
            "ndvi": rng.uniform(-1, 1, n),
            "tree_density": rng.uniform(0, 10_000, n),
            "biodiversity": rng.uniform(0, 10, n),
            "aqi": rng.uniform(0, 999, n),
            "temperature": rng.uniform(-40, 60, n),
            "impervious_surfaces": rng.uniform(0, 1, n),
            "water_availability": rng.uniform(0, 1, n),
            "population_exposure": rng.uniform(0, 1_000_000, n),
        }
        geoms = [box(i, 0, i + 1, 1) for i in range(n)]
        gdf = gpd.GeoDataFrame(data, geometry=geoms, crs="EPSG:4326")

        result = compute_uehi_scores(gdf)
        assert result["uehi_score"].min() >= 0.0
        assert result["uehi_score"].max() <= 100.0

    def test_perfect_positive_scores_100(self):
        """All-best indicators should yield score = 100."""
        # When all rows have identical values, normalisation gives 0,
        # so we need at least 2 rows with a "best" and "worst" row.
        data = {
            "ndvi": [1.0, 0.0],            # positive: higher is better
            "tree_density": [500, 0],       # positive
            "biodiversity": [1.0, 0.0],     # positive
            "aqi": [0, 300],                # negative: lower is better
            "temperature": [20, 50],        # negative
            "impervious_surfaces": [0, 1],  # negative
            "water_availability": [1, 0],   # positive
            "population_exposure": [0, 50000],  # negative
        }
        geoms = [box(0, 0, 1, 1), box(1, 0, 2, 1)]
        gdf = gpd.GeoDataFrame(data, geometry=geoms, crs="EPSG:4326")

        result = compute_uehi_scores(gdf)
        # First row should score 100 (all positive maxed, all negative minimised)
        assert result["uehi_score"].iloc[0] == pytest.approx(100.0)
        # Second row should score 0
        assert result["uehi_score"].iloc[1] == pytest.approx(0.0)

    def test_missing_column_raises(self, sample_gdf):
        gdf = sample_gdf.drop(columns=["ndvi"])
        with pytest.raises(KeyError, match="ndvi"):
            compute_uehi_scores(gdf)

    def test_custom_score_column_name(self, sample_gdf):
        result = compute_uehi_scores(sample_gdf, score_column="eco_index")
        assert "eco_index" in result.columns
        assert "uehi_score" not in result.columns

    def test_original_gdf_unmodified(self, sample_gdf):
        """Scoring must not mutate the input GeoDataFrame."""
        cols_before = list(sample_gdf.columns)
        _ = compute_uehi_scores(sample_gdf)
        assert list(sample_gdf.columns) == cols_before


# ---------------------------------------------------------------------------
# Risk classification tests
# ---------------------------------------------------------------------------

class TestRiskClassification:
    def test_risk_levels(self):
        data = {
            "uehi_score": [10, 30, 60, 90],
            "geometry": [box(i, 0, i + 1, 1) for i in range(4)],
        }
        gdf = gpd.GeoDataFrame(data, crs="EPSG:4326")
        result = classify_risk(gdf)
        assert list(result["risk_level"]) == [
            "Critical", "High", "Moderate", "Low"
        ]

    def test_boundary_values(self):
        data = {
            "uehi_score": [0, 25, 50, 75, 100],
            "geometry": [box(i, 0, i + 1, 1) for i in range(5)],
        }
        gdf = gpd.GeoDataFrame(data, crs="EPSG:4326")
        result = classify_risk(gdf)
        assert list(result["risk_level"]) == [
            "Critical", "High", "Moderate", "Low", "Low"
        ]

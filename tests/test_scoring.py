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
from scoring.entropy import (
    entropy_weights,
    compute_factor_diagnostics,
    EntropyWeightError,
    MODAL_SHARE_THRESHOLD,
    DEGENERATE_WEIGHT_CAP,
    WEIGHT_SUM_TOLERANCE,
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
    Create a small GeoDataFrame with all 7 factor columns and varied values.
    """
    n = 20
    rng = np.random.default_rng(42)
    data = {
        "ndvi": rng.uniform(0.0, 0.8, n),
        "tree_density": rng.uniform(0, 500, n),
        "pm25": rng.uniform(1, 50, n),
        "temperature": rng.uniform(25, 50, n),
        "impervious_surfaces": rng.uniform(0, 1, n),
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
        """Config must contain all 6 expected factors."""
        expected = {
            "ndvi", "tree_density", "pm25",
            "temperature", "impervious_surfaces",
            "population_exposure",
        }
        assert set(default_config["factors"].keys()) == expected

    def test_water_excluded(self, default_config):
        """water_availability must NOT be in the active factors."""
        assert "water_availability" not in default_config["factors"]
        # But should be documented in excluded_factors
        assert "water_availability" in default_config.get("excluded_factors", {})

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

    def test_pm25_provenance(self, default_config):
        """PM2.5 factor must have ACAG/WUSTL source metadata."""
        pm25_spec = default_config["factors"]["pm25"]
        assert pm25_spec["direction"] == "negative"
        assert pm25_spec.get("source") == "ACAG_V6GL03_SatPM25"

    def test_invalid_config_bad_weights(self, tmp_path):
        """Config with weights not summing to 1 should raise."""
        bad_config = {
            "factors": {
                "ndvi": {"weight": 0.5, "direction": "positive"},
                "pm25": {"weight": 0.3, "direction": "negative"},
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
            "pm25": rng.uniform(0, 500, n),
            "temperature": rng.uniform(-40, 60, n),
            "impervious_surfaces": rng.uniform(0, 1, n),
            "population_exposure": rng.uniform(0, 1_000_000, n),
        }
        geoms = [box(i, 0, i + 1, 1) for i in range(n)]
        gdf = gpd.GeoDataFrame(data, geometry=geoms, crs="EPSG:4326")

        result = compute_uehi_scores(gdf)
        assert result["uehi_score"].min() >= 0.0
        assert result["uehi_score"].max() <= 100.0

    def test_perfect_positive_scores_100(self):
        """All-best indicators should yield score = 100."""
        data = {
            "ndvi": [1.0, 0.0],            # positive: higher is better
            "tree_density": [500, 0],       # positive
            "pm25": [0, 300],               # negative: lower is better
            "temperature": [20, 50],        # negative
            "impervious_surfaces": [0, 1],  # negative
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


# ---------------------------------------------------------------------------
# Entropy weight tests — Safeguard A, B, and diagnostics
# ---------------------------------------------------------------------------

class TestEntropyWeightsConstantFactor:
    """TEST 1 — Fully constant factor.

    A factor with all identical values [1,1,1,1,1] should receive
    weight = 0, be excluded from entropy, remaining weights must
    renormalize, and total must = 1.
    """

    def test_constant_factor_gets_zero_weight(self):
        df = pd.DataFrame({
            "const": [1, 1, 1, 1, 1],
            "vary_a": [1, 2, 3, 4, 5],
            "vary_b": [5, 4, 3, 2, 1],
        })
        weights = entropy_weights(df, ["const", "vary_a", "vary_b"])

        # Constant factor must have zero weight
        assert weights["const"] == 0.0, (
            f"Constant factor should have weight 0, got {weights['const']}"
        )
        # Variable factors must have positive weight
        assert weights["vary_a"] > 0.0
        assert weights["vary_b"] > 0.0
        # Total = 1
        assert abs(sum(weights.values()) - 1.0) <= WEIGHT_SUM_TOLERANCE

    def test_all_constant_factors_equal_fallback(self):
        """If every factor is constant, use equal weights and don't crash."""
        df = pd.DataFrame({
            "A": [1, 1, 1, 1],
            "B": [2, 2, 2, 2],
            "C": [3, 3, 3, 3],
        })
        weights = entropy_weights(df, ["A", "B", "C"])

        for col, w in weights.items():
            assert not math.isnan(w), f"Weight for {col} is NaN"
            assert not math.isinf(w), f"Weight for {col} is Inf"
            assert w >= 0.0

        assert abs(sum(weights.values()) - 1.0) <= WEIGHT_SUM_TOLERANCE

    def test_constant_excluded_from_entropy_calc(self):
        """Remaining non-constant weights should renormalize fully."""
        df = pd.DataFrame({
            "const": [7, 7, 7, 7, 7, 7, 7, 7, 7, 7],
            "vary": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        })
        weights = entropy_weights(df, ["const", "vary"])

        assert weights["const"] == 0.0
        # The only variable factor must get all the weight
        assert abs(weights["vary"] - 1.0) <= WEIGHT_SUM_TOLERANCE


class TestEntropyWeightsDegenerateDistribution:
    """TEST 2 — Sparse degenerate factor.

    A factor like [0,0,0,0,100] has non-zero variance but >95%
    modal share. Its raw entropy weight should be calculated,
    then capped at 0.03, with freed weight redistributed.
    """

    def test_sparse_degenerate_capped(self):
        n = 100
        # Factor A: 96 zeros + 4 nonzero → 96% modal share → degenerate
        A = [0.0] * 96 + [10.0, 20.0, 30.0, 40.0]
        # Factor B: uniform variation → healthy
        B = list(range(1, n + 1))
        # Factor C: uniform variation → healthy
        C = list(range(n, 0, -1))

        df = pd.DataFrame({"A": A, "B": B, "C": C})
        weights = entropy_weights(df, ["A", "B", "C"])

        # A has non-zero variance
        assert pd.Series(A).std() > 0

        # A has >95% modal share
        from collections import Counter
        modal_share = Counter(A).most_common(1)[0][1] / n
        assert modal_share > MODAL_SHARE_THRESHOLD

        # A's weight should be capped at 0.03
        assert weights["A"] <= DEGENERATE_WEIGHT_CAP + 1e-12

        # B and C should have positive weights
        assert weights["B"] > 0.0
        assert weights["C"] > 0.0

        # Total = 1
        assert abs(sum(weights.values()) - 1.0) <= WEIGHT_SUM_TOLERANCE

    def test_raw_weight_calculated_before_cap(self):
        """The raw entropy weight should be non-zero before capping."""
        n = 100
        A = [0.0] * 96 + [100.0] * 4
        B = list(range(n))

        df = pd.DataFrame({"A": A, "B": B})
        diagnostics = compute_factor_diagnostics(df, ["A", "B"])

        diag_a = [d for d in diagnostics if d["name"] == "A"][0]
        # Raw weight should be positive (factor has SOME variation)
        assert diag_a["raw_entropy_weight"] > 0.0
        # Final weight should be capped
        assert diag_a["final_weight"] <= DEGENERATE_WEIGHT_CAP + 1e-12
        # Degenerate flag should be set
        assert diag_a["degenerate"] is True


class TestEntropyWeightsMultipleDegenerate:
    """TEST 3 — Multiple degenerate factors.

    When two or more factors each have >95% modal share, both must
    be detected, both capped at 0.03, total freed weight pooled
    and redistributed correctly, and total = 1.
    """

    def test_two_degenerate_factors(self):
        n = 100
        # D1: 97 zeros + 3 nonzero → 97% modal share
        D1 = [0.0] * 97 + [1.0, 2.0, 3.0]
        # D2: 96 fives + 4 nonzero → 96% modal share
        D2 = [5.0] * 96 + [10.0, 20.0, 30.0, 40.0]
        # Healthy: full variation
        H1 = list(range(1, n + 1))
        H2 = list(range(n, 0, -1))

        df = pd.DataFrame({"D1": D1, "D2": D2, "H1": H1, "H2": H2})
        weights = entropy_weights(df, ["D1", "D2", "H1", "H2"])

        # Both degenerate factors should be capped
        assert weights["D1"] <= DEGENERATE_WEIGHT_CAP + 1e-12
        assert weights["D2"] <= DEGENERATE_WEIGHT_CAP + 1e-12

        # Healthy factors should receive the freed weight
        assert weights["H1"] > 0.0
        assert weights["H2"] > 0.0

        # The healthy factors should together hold most of the weight
        healthy_total = weights["H1"] + weights["H2"]
        assert healthy_total > 0.9  # close to 1.0 minus the two caps

        # Total = 1
        assert abs(sum(weights.values()) - 1.0) <= WEIGHT_SUM_TOLERANCE

    def test_diagnostics_detect_both(self):
        n = 100
        D1 = [0.0] * 97 + [1.0, 2.0, 3.0]
        D2 = [5.0] * 96 + [10.0, 20.0, 30.0, 40.0]
        H = list(range(1, n + 1))

        df = pd.DataFrame({"D1": D1, "D2": D2, "H": H})
        diagnostics = compute_factor_diagnostics(df, ["D1", "D2", "H"])

        diag_map = {d["name"]: d for d in diagnostics}
        assert diag_map["D1"]["degenerate"] is True
        assert diag_map["D2"]["degenerate"] is True
        assert diag_map["H"]["degenerate"] is False


class TestEntropyWeightsLowVariation:
    """TEST 4 — Low-variation continuous factor.

    A synthetic continuous factor with small variation but most values
    NOT exactly identical should:
    - NOT be classified as constant
    - NOT be classified as >95%-modal degenerate
    - Have a valid raw entropy weight
    - Be flagged with low_spatial_variation separately
    """

    def test_low_variation_not_misclassified(self):
        n = 100
        rng = np.random.default_rng(42)
        # Small continuous variation around 50, CV ≈ 2%
        low_var = 50 + rng.normal(0, 1, n)
        # Normal variation factor
        normal_var = rng.uniform(0, 100, n)

        df = pd.DataFrame({"low": low_var, "normal": normal_var})
        diagnostics = compute_factor_diagnostics(df, ["low", "normal"])

        diag_low = [d for d in diagnostics if d["name"] == "low"][0]

        # NOT constant (values are NOT all identical)
        assert diag_low["constant"] is False

        # NOT degenerate (most values are unique, modal share << 95%)
        assert diag_low["degenerate"] is False

        # Raw entropy weight is valid (positive)
        assert diag_low["raw_entropy_weight"] > 0.0

        # Low spatial variation IS flagged
        assert diag_low["low_spatial_variation"] is True

        # The weight was NOT automatically capped
        assert diag_low["final_weight"] == pytest.approx(
            diag_low["raw_entropy_weight"], abs=1e-9
        )

    def test_low_cv_not_treated_as_degenerate(self):
        """PM2.5-like factor: 2 unique values, 56% modal share, CV ~ 2.7%."""
        n = 256
        # Simulate PM2.5 distribution: 144 at 3.6, 112 at 3.8
        pm25_like = [3.6] * 144 + [3.8] * 112
        normal = list(range(n))

        df = pd.DataFrame({"pm25": pm25_like, "other": normal})
        diagnostics = compute_factor_diagnostics(df, ["pm25", "other"])

        diag_pm25 = [d for d in diagnostics if d["name"] == "pm25"][0]

        # Not constant
        assert diag_pm25["constant"] is False
        # Modal share is 144/256 = 56.25%, NOT > 95%
        assert diag_pm25["modal_share_pct"] < 95.0
        # Therefore NOT degenerate
        assert diag_pm25["degenerate"] is False
        # Low spatial variation IS flagged (CV < 5%)
        assert diag_pm25["low_spatial_variation"] is True
        # Weight is NOT capped at 0.03
        assert diag_pm25["final_weight"] == pytest.approx(
            diag_pm25["raw_entropy_weight"], abs=1e-9
        )


class TestEntropyWeightsWeightSum:
    """TEST 5 — Weight sum.

    For every conceivable scenario, abs(sum(weights) - 1.0) <= 1e-9.
    """

    def test_sum_all_varied(self):
        rng = np.random.default_rng(123)
        df = pd.DataFrame({
            "X": rng.uniform(0, 10, 50),
            "Y": rng.uniform(0, 100, 50),
            "Z": rng.uniform(0, 1, 50),
        })
        weights = entropy_weights(df, ["X", "Y", "Z"])
        assert abs(sum(weights.values()) - 1.0) <= WEIGHT_SUM_TOLERANCE

    def test_sum_with_constant(self):
        df = pd.DataFrame({
            "A": [1, 1, 1, 1],
            "B": [1, 2, 3, 4],
            "C": [4, 3, 2, 1],
        })
        weights = entropy_weights(df, ["A", "B", "C"])
        assert abs(sum(weights.values()) - 1.0) <= WEIGHT_SUM_TOLERANCE

    def test_sum_all_constant(self):
        df = pd.DataFrame({
            "A": [1, 1, 1, 1],
            "B": [2, 2, 2, 2],
        })
        weights = entropy_weights(df, ["A", "B"])
        assert abs(sum(weights.values()) - 1.0) <= WEIGHT_SUM_TOLERANCE

    def test_sum_with_degenerate(self):
        n = 100
        df = pd.DataFrame({
            "D": [0.0] * 96 + [100.0] * 4,
            "H": list(range(n)),
        })
        weights = entropy_weights(df, ["D", "H"])
        assert abs(sum(weights.values()) - 1.0) <= WEIGHT_SUM_TOLERANCE

    def test_sum_mixed_scenario(self):
        """Mix of constant, degenerate, low-var, and healthy factors."""
        n = 200
        rng = np.random.default_rng(77)
        df = pd.DataFrame({
            "const": [5.0] * n,
            "degen": [0.0] * 195 + [10.0] * 5,
            "lowvar": 100 + rng.normal(0, 0.5, n),
            "healthy": rng.uniform(0, 100, n),
        })
        weights = entropy_weights(df, ["const", "degen", "lowvar", "healthy"])
        assert abs(sum(weights.values()) - 1.0) <= WEIGHT_SUM_TOLERANCE
        # Constant factor must be 0
        assert weights["const"] == 0.0
        # Degenerate must be capped
        assert weights["degen"] <= DEGENERATE_WEIGHT_CAP + 1e-12

    def test_determinism(self):
        """Same data → same weights, always."""
        rng = np.random.default_rng(42)
        df = pd.DataFrame({
            "X": rng.uniform(0, 10, 50),
            "Y": rng.uniform(0, 100, 50),
            "Z": rng.uniform(0, 1, 50),
        })
        w1 = entropy_weights(df, ["X", "Y", "Z"])
        w2 = entropy_weights(df, ["X", "Y", "Z"])
        for col in ["X", "Y", "Z"]:
            assert math.isclose(w1[col], w2[col], abs_tol=1e-12)

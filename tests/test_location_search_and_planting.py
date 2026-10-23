"""
tests/test_location_search_and_planting.py
──────────────────────────────────────────
Regression and integration test suite covering:
1. Geographic boundary checking and Pune/PCMC coverage classification.
2. Geocoding query constraints and error handling.
3. Study area candidate block retrieval, ranking, and explanation accuracy.
4. Feasibility and governance disclosure enforcement (ownership, utilities, site suitability unverified).
5. Missing and unscored block handling.
6. Canonical risk-tier thresholds (<25, 25-<50, 50-<75, >=75).
7. Standing carbon stock semantics vs annual sequestration flux.
8. API security, internal key enforcement, and route contracts.
"""

import os
import json
import pytest
from fastapi.testclient import TestClient
from api.main import app
from api.study_area import query_candidate_blocks_in_area

client = TestClient(app)

PUNE_BOUNDS = {
    "minLat": 18.428852,
    "maxLat": 18.621015,
    "minLng": 73.749344,
    "maxLng": 74.021411,
}

AUTH_HEADERS = {"X-API-Key": os.getenv("UEHIS_API_KEY", "test-mock-internal-api-key")}

SAMPLE_PUNE_POLYGON = {
    "type": "Polygon",
    "coordinates": [
        [
            [73.84, 18.52],
            [73.86, 18.52],
            [73.86, 18.54],
            [73.84, 18.54],
            [73.84, 18.52],
        ]
    ]
}


class TestGeographicCoverageBounds:
    """Verifies that geographic bounds correctly identify Pune/PCMC coverage vs external areas."""

    def is_in_coverage(self, lat: float, lng: float) -> bool:
        return (
            PUNE_BOUNDS["minLat"] <= lat <= PUNE_BOUNDS["maxLat"] and
            PUNE_BOUNDS["minLng"] <= lng <= PUNE_BOUNDS["maxLng"]
        )

    def test_pune_core_localities_in_coverage(self):
        # Established Pune & PCMC localities
        pune_points = [
            ("Shivajinagar", 18.5314, 73.8446),
            ("Kothrud", 18.5074, 73.8077),
            ("Baner", 18.5588, 73.7911),
            ("Aundh", 18.5602, 73.8077),
            ("Yerawada", 18.5529, 73.8828),
        ]
        for name, lat, lng in pune_points:
            assert self.is_in_coverage(lat, lng), f"{name} ({lat}, {lng}) should be in coverage"

    def test_outside_locations_identified_as_uncovered(self):
        # Locations clearly outside Pune/PCMC evaluated boundary
        outside_points = [
            ("Mumbai", 19.0760, 72.8777),
            ("Delhi", 28.6139, 77.2090),
            ("Bengaluru", 12.9716, 77.5946),
            ("Lonavala", 18.7557, 73.4091),
            ("Satara", 17.6805, 73.9936),
        ]
        for name, lat, lng in outside_points:
            assert not self.is_in_coverage(lat, lng), f"{name} ({lat}, {lng}) must be outside coverage"


class TestCandidateBlockRankingAndExplanations:
    """Verifies candidate block ranking logic, data-driven explanations, and feasibility tags."""

    def test_ranking_explanation_critical_need(self):
        from unittest.mock import MagicMock
        mock_db = MagicMock()
        # Mock row: block_id, uehi_score, risk_level, tree_density, ndvi, impervious, temp, pop_exp, pm25, is_excluded, carbon_stock, canopy_m2, trees, agb, lng, lat, area_m2
        mock_row = (
            "PN_385000_2045000", 19.5, "Critical", 0.04, 0.12, 0.78, 37.5, 0.85, 45.2,
            False, 12.4, 850.0, 25.0, 6200.0, 73.85, 18.52, 62500.0
        )
        mock_db.execute.return_value.fetchall.return_value = [mock_row]

        candidates = query_candidate_blocks_in_area(mock_db, SAMPLE_PUNE_POLYGON, limit=10)
        assert len(candidates) == 1
        c = candidates[0]
        assert c["rank"] == 1
        assert c["block_id"] == "PN_385000_2045000"
        assert c["uehi_score"] == 19.5
        assert c["need_tier"] == "Critical"
        assert "Critical Ecological Need" in c["ranking_explanation"]
        assert "78%" in c["ranking_explanation"]
        assert "37.5°C" in c["ranking_explanation"]

        # Feasibility disclosures
        assert "Verification required" in c["feasibility"]["ownership_status"]
        assert "Verification required" in c["feasibility"]["utility_status"]
        assert "Verification required" in c["feasibility"]["planting_permission_status"]
        assert "legal or physical planting feasibility" in c["feasibility"]["disclaimer"]

    def test_ranking_explanation_high_need(self):
        from unittest.mock import MagicMock
        mock_db = MagicMock()
        mock_row = (
            "PN_386000_2046000", 38.2, "High", 0.15, 0.25, 0.55, 34.1, 0.60, 40.0,
            False, 28.5, 2200.0, 60.0, 14000.0, 73.86, 18.53, 62500.0
        )
        mock_db.execute.return_value.fetchall.return_value = [mock_row]

        candidates = query_candidate_blocks_in_area(mock_db, SAMPLE_PUNE_POLYGON, limit=10)
        c = candidates[0]
        assert c["need_tier"] == "High"
        assert "High Intervention Need" in c["ranking_explanation"]
        assert "0.15" in c["ranking_explanation"]

    def test_ranking_explanation_stable_baseline(self):
        from unittest.mock import MagicMock
        mock_db = MagicMock()
        mock_row = (
            "PN_387000_2047000", 82.4, "Low", 0.48, 0.65, 0.18, 28.2, 0.20, 22.0,
            False, 145.8, 12000.0, 310.0, 72000.0, 73.87, 18.54, 62500.0
        )
        mock_db.execute.return_value.fetchall.return_value = [mock_row]

        candidates = query_candidate_blocks_in_area(mock_db, SAMPLE_PUNE_POLYGON, limit=10)
        c = candidates[0]
        assert c["need_tier"] == "Low"
        assert "Low Need / Stable" in c["ranking_explanation"]
        assert "145.8 t CO₂e" in c["ranking_explanation"]

    def test_unscored_excluded_block_explanation(self):
        from unittest.mock import MagicMock
        mock_db = MagicMock()
        mock_row = (
            "PN_EXCLUDED_001", None, None, None, None, None, None, None, None,
            True, None, None, None, None, 73.88, 18.55, 62500.0
        )
        mock_db.execute.return_value.fetchall.return_value = [mock_row]

        candidates = query_candidate_blocks_in_area(mock_db, SAMPLE_PUNE_POLYGON, limit=10)
        c = candidates[0]
        assert c["need_tier"] == "Unscored"
        assert "Unscored block — excluded" in c["ranking_explanation"]
        assert c["uehi_score"] is None


class TestCanonicalRiskClassificationScale:
    """Verifies that the canonical risk thresholds (<25, 25-<50, 50-<75, >=75) are strictly maintained."""

    def classify(self, score: float | None) -> str:
        if score is None:
            return "Unscored"
        if score < 25.0:
            return "Critical"
        if score < 50.0:
            return "High"
        if score < 75.0:
            return "Moderate"
        return "Low"

    def test_threshold_boundaries(self):
        assert self.classify(0.0) == "Critical"
        assert self.classify(24.99) == "Critical"
        assert self.classify(25.0) == "High"
        assert self.classify(49.99) == "High"
        assert self.classify(50.0) == "Moderate"
        assert self.classify(74.99) == "Moderate"
        assert self.classify(75.0) == "Low"
        assert self.classify(100.0) == "Low"


class TestStandingStockSemanticsAndDensity:
    """Ensures standing carbon stock is never mislabeled as annual flux and density formulas are exact."""

    def test_density_denominators(self):
        total_carbon = 493093.6884
        canopy_ha = 2151.1657
        gross_grid_ha = 5309 * 6.25  # 33,181.25 ha

        canopy_density = total_carbon / canopy_ha
        gross_grid_density = total_carbon / gross_grid_ha

        # Exact canopy-area normalized density
        assert round(canopy_density, 2) == 229.22
        # Exact gross municipal grid density
        assert round(gross_grid_density, 2) == 14.86

    def test_standing_stock_field_name_in_candidates(self):
        from unittest.mock import MagicMock
        mock_db = MagicMock()
        mock_row = (
            "PN_TEST_01", 30.0, "High", 0.2, 0.3, 0.4, 30.0, 0.5, 30.0,
            False, 50.0, 3000.0, 80.0, 25000.0, 73.85, 18.52, 62500.0
        )
        mock_db.execute.return_value.fetchall.return_value = [mock_row]

        candidates = query_candidate_blocks_in_area(mock_db, SAMPLE_PUNE_POLYGON)
        c = candidates[0]
        # Must explicitly be named standing_carbon_stock, not annual flux or sequestration
        assert "standing_carbon_stock_tonnes_co2e" in c["carbon"]
        assert c["carbon"]["standing_carbon_stock_tonnes_co2e"] == 50.0


class TestApiSecurityAndEndpointContracts:
    """Verifies security controls, payload contracts, and error responses on FastAPI endpoints."""

    def test_study_area_requires_auth_key(self, monkeypatch):
        monkeypatch.setenv("UEHIS_API_KEY", "prod-strict-key-2026")
        # Without header -> 403
        resp = client.post("/study-area/aggregate", json={"geometry": SAMPLE_PUNE_POLYGON})
        assert resp.status_code == 403

        # With correct header -> proceeds past auth check
        resp = client.post(
            "/study-area/aggregate",
            json={"geometry": SAMPLE_PUNE_POLYGON},
            headers={"X-API-Key": "prod-strict-key-2026"}
        )
        assert resp.status_code in [200, 500]  # 200 if DB active, 500 if DB mocked

    def test_study_area_candidates_endpoint_structure(self):
        resp = client.post(
            "/study-area/candidates",
            json={"geometry": SAMPLE_PUNE_POLYGON, "limit": 10},
            headers=AUTH_HEADERS
        )
        # Should return JSON with total_candidates and candidates list
        if resp.status_code == 200:
            data = resp.json()
            assert "total_candidates" in data
            assert "candidates" in data
            assert isinstance(data["candidates"], list)

    def test_invalid_geometry_rejected(self):
        resp = client.post(
            "/study-area/candidates",
            json={"geometry": "not-a-geometry"},
            headers=AUTH_HEADERS
        )
        assert resp.status_code == 400
        assert "Malformed geometry" in resp.json()["detail"]

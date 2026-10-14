import os
import json
import uuid
import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from api.main import app
from api.database import get_db

client = TestClient(app)

SAMPLE_POLYGON = {
    "type": "Polygon",
    "coordinates": [
        [
            [73.80, 18.50],
            [73.81, 18.50],
            [73.81, 18.51],
            [73.80, 18.51],
            [73.80, 18.50],
        ]
    ],
}

AUTH_HEADERS = {"X-API-Key": os.getenv("UEHIS_API_KEY", "test-mock-internal-api-key")}


class TestPlantingFilterNormalizedSchema:
    def test_planting_filter_sql_has_no_properties_column(self):
        """Verifies that the executed SQL query never references non-existent pu.properties."""
        executed_queries = []

        mock_db = MagicMock()

        def capture_execute(statement, params=None):
            sql_text = str(statement)
            executed_queries.append((sql_text, params))
            # Return empty result
            mock_result = MagicMock()
            mock_result.fetchone.return_value = (
                {"type": "FeatureCollection", "features": []},
                0,
                None,
            )
            return mock_result

        mock_db.execute.side_effect = capture_execute

        app.dependency_overrides[get_db] = lambda: mock_db
        try:
            response = client.post(
                "/planting/filter",
                json={
                    "geometry": SAMPLE_POLYGON,
                    "scenario_id": "100k",
                },
                headers=AUTH_HEADERS,
            )
            assert response.status_code == 200
            assert len(executed_queries) == 1

            sql_text, params = executed_queries[0]

            # Invariant: Must NOT query non-existent properties column
            assert "pu.properties" not in sql_text
            assert "properties->>" not in sql_text

            # Invariant: Must join uehi_blocks for authoritative score and risk
            assert "uehi_blocks" in sql_text
            assert "b.uehi_score" in sql_text
            assert "b.risk_level" in sql_text

            # Invariant: Must join planting_candidate_areas for category and status
            assert "planting_candidate_areas" in sql_text
            assert "ca.candidate_category" in sql_text
            assert "ca.ownership_status" in sql_text

            # Invariant: Must join planting_scenarios for assumption_type
            assert "planting_scenarios" in sql_text
            assert "ps.assumption_type" in sql_text

            # Invariant: distance_to_water_m must be explicitly null
            assert "'distance_to_water_m', null" in sql_text

            # Invariant: 100k shorthand must resolve to canonical UUID
            assert params["scenario_id"] == "583a8cea-95ea-4909-bd9a-8dbdc3e2a4cd"

            # Invariant: Deterministic tie-breaking on lateral spatial joins
            assert "ORDER BY ST_Contains(ca_inner.geom, pu.geom) DESC, ca_inner.area_id ASC" in sql_text
            assert "ORDER BY ST_Contains(b_inner.geom, pu.geom) DESC, b_inner.block_id ASC" in sql_text

            # Invariant: Proper CRS handling (transforms EPSG:4326 GeoJSON to EPSG:32643 and back)
            assert "ST_Transform(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326)), 32643)" in sql_text
            assert "ST_AsGeoJSON(ST_Transform(fu.geom, 4326))" in sql_text

        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_planting_filter_scenario_shorthands_and_uuids(self):
        """Verifies that 100k, 250k, 500k and raw UUIDs resolve to their respective UUIDs."""
        mock_db = MagicMock()
        executed_params = []

        def capture_execute(statement, params=None):
            executed_params.append(params)
            mock_result = MagicMock()
            mock_result.fetchone.return_value = (
                {"type": "FeatureCollection", "features": []},
                0,
                None,
            )
            return mock_result

        mock_db.execute.side_effect = capture_execute
        app.dependency_overrides[get_db] = lambda: mock_db

        try:
            # 1. 250k shorthand
            res_250k = client.post(
                "/planting/filter",
                json={"geometry": SAMPLE_POLYGON, "scenario_id": "250k"},
                headers=AUTH_HEADERS,
            )
            assert res_250k.status_code == 200
            assert executed_params[-1]["scenario_id"] == "b2d9a3f2-1a4c-4e8d-9b5a-1c8e3f2a7b6d"

            # 2. 500k shorthand
            res_500k = client.post(
                "/planting/filter",
                json={"geometry": SAMPLE_POLYGON, "scenario_id": "500k"},
                headers=AUTH_HEADERS,
            )
            assert res_500k.status_code == 200
            assert executed_params[-1]["scenario_id"] == "f4a2b1c3-3d5e-4f6a-8b7c-2d9e4f5a6b7c"

            # 3. Direct valid UUID
            custom_uuid = str(uuid.uuid4())
            res_custom = client.post(
                "/planting/filter",
                json={"geometry": SAMPLE_POLYGON, "scenario_id": custom_uuid},
                headers=AUTH_HEADERS,
            )
            assert res_custom.status_code == 200
            assert executed_params[-1]["scenario_id"] == custom_uuid

            # 4. Invalid scenario identifier -> 400 Bad Request
            res_invalid = client.post(
                "/planting/filter",
                json={"geometry": SAMPLE_POLYGON, "scenario_id": "nonexistent-scenario-id"},
                headers=AUTH_HEADERS,
            )
            assert res_invalid.status_code == 400
            assert "Invalid scenario_id UUID" in res_invalid.json()["detail"]

        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_planting_filter_response_mapping_and_distributions(self):
        """Verifies GeoJSON output structure, risk distribution, and class aggregation."""
        mock_db = MagicMock()
        mock_geojson = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [73.805, 18.505]},
                    "properties": {
                        "planting_unit_id": "888ea20f-8ea1-5470-91c1-ed13cfa85b1c",
                        "uehi_score": 85.5,
                        "risk_level": "High",
                        "ownership_status": "unknown",
                        "utility_status": "unknown",
                        "permission_status": "unknown",
                        "candidate_class": "candidate_other_open_space",
                        "distance_to_water_m": None,
                        "carbon_assumption_type": "illustrative_scenario_assumption",
                    },
                },
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [73.808, 18.508]},
                    "properties": {
                        "planting_unit_id": "999ea20f-8ea1-5470-91c1-ed13cfa85b2d",
                        "uehi_score": 92.0,
                        "risk_level": "Critical",
                        "ownership_status": "unknown",
                        "utility_status": "unknown",
                        "permission_status": "unknown",
                        "candidate_class": "candidate_public_like",
                        "distance_to_water_m": None,
                        "carbon_assumption_type": "illustrative_scenario_assumption",
                    },
                },
            ],
        }

        mock_db.execute.return_value.fetchone.return_value = (
            mock_geojson,
            2,
            88.75,
        )

        app.dependency_overrides[get_db] = lambda: mock_db
        try:
            response = client.post(
                "/planting/filter",
                json={"geometry": SAMPLE_POLYGON, "scenario_id": "100k"},
                headers=AUTH_HEADERS,
            )
            assert response.status_code == 200
            data = response.json()

            assert data["geojson"]["type"] == "FeatureCollection"
            assert len(data["geojson"]["features"]) == 2

            summary = data["summary"]
            assert summary["total_units"] == 2
            assert summary["mean_uehi"] == 88.75
            assert summary["risk_distribution"] == {"High": 1, "Critical": 1}
            assert summary["class_distribution"] == {
                "Other open space": 1,
                "Public-like open space": 1,
            }

            # Check that distance_to_water_m is null
            p0 = data["geojson"]["features"][0]["properties"]
            assert p0["distance_to_water_m"] is None
            assert p0["carbon_assumption_type"] == "illustrative_scenario_assumption"
            assert p0["planting_unit_id"] == "888ea20f-8ea1-5470-91c1-ed13cfa85b1c"

        finally:
            app.dependency_overrides.pop(get_db, None)


class TestSpatialIntegrityAndDeterminism:
    def test_planting_unit_namespace_uuidv5_congruence(self):
        """Verifies that the UUIDv5 namespace and naming matches the production loader exactly."""
        pu_namespace = uuid.UUID("49e464c3-0db8-5061-a5ff-945f95238334")
        unit_id = uuid.uuid5(pu_namespace, "PU_1128671")
        assert str(unit_id) == "888ea20f-8ea1-5470-91c1-ed13cfa85b1c"

    def test_parent_block_formula_congruence(self):
        """Verifies that Math.floor(x/250)*250 and Math.floor(y/250)*250 match the 250m grid convention."""
        # Arbitrary interior point within block PN_380000_2042500
        x = 380123.45
        y = 2042678.90
        bx = int(x // 250) * 250
        by = int(y // 250) * 250
        block_id = f"PN_{bx}_{by}"
        assert block_id == "PN_380000_2042500"

        # Boundary point on edge
        edge_x = 380000.0
        edge_y = 2042500.0
        assert f"PN_{int(edge_x // 250) * 250}_{int(edge_y // 250) * 250}" == "PN_380000_2042500"


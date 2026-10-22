import os
import pytest
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

SAMPLE_POLYGON = {
    "type": "Polygon",
    "coordinates": [
        [
            [73.80, 18.50],
            [73.81, 18.50],
            [73.81, 18.51],
            [73.80, 18.51],
            [73.80, 18.50]
        ]
    ]
}

def test_health_check_endpoint():
    """Verify system health endpoint returns 200 OK and service metadata."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "uehis-api"

AUTH_HEADERS = {"X-API-Key": os.getenv("UEHIS_API_KEY", "test-mock-internal-api-key")}

def test_study_area_malformed_payload():
    """Verify 400 Bad Request on malformed geometry when authenticated."""
    response = client.post("/study-area/aggregate", json={"invalid": "payload"}, headers=AUTH_HEADERS)
    assert response.status_code == 400
    assert "Malformed geometry" in response.json()["detail"]

def test_planting_filter_missing_arguments():
    """Verify 400 Bad Request on missing geometry or scenario_id when authenticated."""
    # Missing scenario_id
    response = client.post("/planting/filter", json={"geometry": SAMPLE_POLYGON}, headers=AUTH_HEADERS)
    assert response.status_code == 400
    assert "Missing geometry or scenario_id" in response.json()["detail"]

    # Missing geometry
    response = client.post("/planting/filter", json={"scenario_id": "test-scenario"}, headers=AUTH_HEADERS)
    assert response.status_code == 400
    assert "Missing geometry or scenario_id" in response.json()["detail"]

def test_internal_api_key_security(monkeypatch):
    """Verify that when UEHIS_API_KEY is configured, unauthenticated requests are rejected with 403."""
    monkeypatch.setenv("UEHIS_API_KEY", "secure_secret_token_2026")

    # Request without API key header -> 403
    response = client.post("/study-area/aggregate", json={"geometry": SAMPLE_POLYGON})
    assert response.status_code == 403
    assert "Could not validate API key" in response.json()["detail"]

    # Request with invalid API key header -> 403
    response = client.post(
        "/study-area/aggregate",
        json={"geometry": SAMPLE_POLYGON},
        headers={"X-API-Key": "wrong_key"}
    )
    assert response.status_code == 403

    # Request without key on /planting/filter -> 403
    response = client.post("/planting/filter", json={"geometry": SAMPLE_POLYGON, "scenario_id": "any"})
    assert response.status_code == 403

    # Request without key on /summary -> 403
    response = client.get("/summary")
    assert response.status_code == 403

def test_production_api_key_fail_closed_missing_or_empty(monkeypatch):
    """Verify that in production mode, missing or empty UEHIS_API_KEY fails closed with 500."""
    monkeypatch.setenv("ENVIRONMENT", "production")

    # When UEHIS_API_KEY is unset
    monkeypatch.delenv("UEHIS_API_KEY", raising=False)
    response = client.get("/summary")
    assert response.status_code == 500
    assert "Server configuration error" in response.json()["detail"]

    # When UEHIS_API_KEY is empty string
    monkeypatch.setenv("UEHIS_API_KEY", "")
    response = client.post("/study-area/aggregate", json={"geometry": SAMPLE_POLYGON})
    assert response.status_code == 500
    assert "Server configuration error" in response.json()["detail"]

    # When UEHIS_API_KEY is whitespace
    monkeypatch.setenv("UEHIS_API_KEY", "   ")
    response = client.post("/planting/filter", json={"geometry": SAMPLE_POLYGON, "scenario_id": "test"})
    assert response.status_code == 500
    assert "Server configuration error" in response.json()["detail"]

def test_production_api_key_valid_and_invalid(monkeypatch):
    """Verify that in production mode, requests with invalid key get 403 and valid key can proceed."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("UEHIS_API_KEY", "prod-super-secret-key-2026")

    # Missing header -> 403
    response = client.get("/summary")
    assert response.status_code == 403
    assert "Could not validate API key" in response.json()["detail"]

    # Wrong key -> 403
    response = client.get("/summary", headers={"X-API-Key": "incorrect-key"})
    assert response.status_code == 403

    # Empty key header -> 403
    response = client.get("/summary", headers={"X-API-Key": ""})
    assert response.status_code == 403

    # Correct key -> Passes auth check (proceeds to business logic)
    response = client.post(
        "/study-area/aggregate",
        json={"invalid": "payload"},
        headers={"X-API-Key": "prod-super-secret-key-2026"}
    )
    # Auth succeeded, rejected by payload validation (400)
    assert response.status_code == 400
    assert "Malformed geometry" in response.json()["detail"]

def test_startup_validation_in_production(monkeypatch):
    """Verify validate_startup_security enforces API key, remote DB, and TLS in production."""
    from api.security import validate_startup_security
    import pytest

    monkeypatch.setenv("ENVIRONMENT", "production")

    # 1. Missing UEHIS_API_KEY -> raises
    monkeypatch.delenv("UEHIS_API_KEY", raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@db.example.co:5432/postgres?sslmode=require")
    with pytest.raises(RuntimeError, match="CRITICAL SECURITY CONFIGURATION ERROR"):
        validate_startup_security()

    # 2. Configured key, but missing DATABASE_URL -> raises
    monkeypatch.setenv("UEHIS_API_KEY", "valid_key")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("DOCKER_DATABASE_URL", raising=False)
    with pytest.raises(RuntimeError, match="CRITICAL DATABASE CONFIGURATION ERROR"):
        validate_startup_security()

    # 3. Localhost in DATABASE_URL in production -> raises
    monkeypatch.setenv("DATABASE_URL", "postgresql://uehis:pass@localhost:5432/uehis?sslmode=require")
    with pytest.raises(RuntimeError, match="CRITICAL DATABASE SECURITY ERROR.*local host"):
        validate_startup_security()

    monkeypatch.setenv("DATABASE_URL", "postgresql://uehis:pass@127.0.0.1:5432/uehis?sslmode=require")
    with pytest.raises(RuntimeError, match="CRITICAL DATABASE SECURITY ERROR.*local host"):
        validate_startup_security()

    # 4. Remote host without sslmode=require in production -> raises
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@aws-0-ap-south-1.pooler.supabase.com:6543/postgres")
    with pytest.raises(RuntimeError, match="CRITICAL DATABASE SECURITY ERROR.*sslmode=require"):
        validate_startup_security()

    # 5. Remote host with sslmode=prefer in production -> raises
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@db.project.supabase.co:5432/postgres?sslmode=prefer")
    with pytest.raises(RuntimeError, match="CRITICAL DATABASE SECURITY ERROR.*sslmode=require"):
        validate_startup_security()

    # 6. Valid remote host with sslmode=require -> passes cleanly
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg2://user:pass@db.project.supabase.co:5432/postgres?sslmode=require")
    validate_startup_security()

    # 7. Valid remote host with DOCKER_DATABASE_URL override -> passes cleanly
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("DOCKER_DATABASE_URL", "postgresql://user:pass@db.project.supabase.co:5432/postgres?sslmode=verify-full")
    validate_startup_security()


def test_startup_validation_in_development(monkeypatch):
    """Verify validate_startup_security allows local development without remote DB or TLS."""
    from api.security import validate_startup_security

    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.delenv("UEHIS_API_KEY", raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql://uehis:uehis@localhost:5432/uehis")

    # Should not raise in development
    validate_startup_security()


def test_block_detail_endpoint_not_found(monkeypatch):
    """Verify 404 Not Found for non-existent block IDs."""
    from unittest.mock import MagicMock
    from api.main import get_db

    # Override get_db to return an empty query result
    mock_db = MagicMock()
    mock_db.execute.return_value.mappings.return_value.first.return_value = None
    mock_db.execute.return_value.scalar_one_or_none.return_value = None
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        response = client.get("/blocks/PN_000000_0000000")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_block_detail_endpoint_success_schema(monkeypatch):
    """Verify GET /blocks/{block_id} returns compliant BlockResponse attributes."""
    from unittest.mock import MagicMock
    from api.main import get_db

    mock_row = {
        "block_id": "PN_379500_2050750",
        "uehi_score": 58.42,
        "risk_level": "Moderate",
        "ndvi": 0.284,
        "tree_density": 0.142,
        "impervious_surfaces": 0.45,
        "temperature": 34.2,
        "population_exposure": 12.4,
        "pm25": 48.6,
        "standing_carbon_stock": 142.5,
        "canopy_area_m2": 8900.0,
        "estimated_tree_count": 180.0,
        "above_ground_biomass_kg": 285000.0,
        "geojson": '{"type": "Polygon", "coordinates": [[[73.85, 18.52], [73.86, 18.52], [73.86, 18.53], [73.85, 18.53], [73.85, 18.52]]]}',
    }

    mock_db = MagicMock()
    mock_db.execute.return_value.mappings.return_value.first.return_value = mock_row
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        response = client.get("/blocks/PN_379500_2050750")
        assert response.status_code == 200
        data = response.json()
        assert data["block_id"] == "PN_379500_2050750"
        assert data["uehi_score"] == 58.42
        assert data["risk_level"] == "Moderate"
        assert data["factors"]["ndvi"] == 0.284
        assert data["factors"]["tree_density"] == 0.142
        assert data["factors"]["impervious_surfaces"] == 0.45
        assert data["factors"]["temperature"] == 34.2
        assert data["factors"]["population_exposure"] == 12.4
        assert data["factors"]["aqi"] == 48.6
        assert data["co2_tonnes"] == 142.5
        assert data["carbon_details"]["canopy_area_m2"] == 8900.0
        assert data["carbon_details"]["estimated_tree_count"] == 180.0
        assert data["carbon_details"]["above_ground_biomass_kg"] == 285000.0
    finally:
        app.dependency_overrides.pop(get_db, None)


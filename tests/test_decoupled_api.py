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
    """Verify validate_startup_security raises RuntimeError if UEHIS_API_KEY is missing in production."""
    from api.security import validate_startup_security
    import pytest

    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("UEHIS_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="CRITICAL SECURITY CONFIGURATION ERROR"):
        validate_startup_security()

    monkeypatch.setenv("UEHIS_API_KEY", "valid_key")
    # Should not raise
    validate_startup_security()


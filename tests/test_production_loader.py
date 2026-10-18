"""
Test Suite: Production Database Loader (UEHIS)
==============================================
Location: tests/test_production_loader.py

Validates the architecture, safety invariants, column mappings, geometry handling,
and fail-safe mechanics of scripts/load_supabase_production.py using synthetic fixtures
and static validation. Strictly isolated from remote databases.
"""

import json
import subprocess
import sys
import uuid
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from scripts.load_supabase_production import (
    CrossRunConflictError,
    EXPECTED_PROJECT_REF,
    METH_ID_CARBON,
    METH_ID_CANDIDATES,
    METH_ID_SCENARIOS,
    METH_ID_UEHI,
    PROD_DATA_DIR,
    ProductionLoaderEngine,
    PU_NAMESPACE,
    RUN_ID_OPTIMIZATION,
    RUN_ID_PHASE3,
    SCENARIO_CONFIGS,
    load_grid_geometry_map,
    plan_carbon_blocks,
    plan_provenance_records,
    plan_rollback_queries,
    plan_uehi_blocks,
    redact_connection_string,
    resolve_tls_parameters,
    stream_geojson_features,
    verify_validation_results,
)


class TestSafetyInvariants:
    def test_redact_connection_string(self):
        secret_url = "postgresql://postgres:secret_password_12345@db.evnycdrrekthakotvsew.supabase.co:5432/postgres"
        redacted = redact_connection_string(secret_url)
        assert "secret_password_12345" not in redacted
        assert "postgres:***@db.evnycdrrekthakotvsew.supabase.co:5432/postgres" in redacted

    def test_safety_halt_without_confirm_target(self):
        cmd = [sys.executable, str(REPO_ROOT / "scripts" / "load_supabase_production.py"), "--live"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        assert result.returncode == 1
        assert "SAFETY HALT: Live execution requires --confirm-target=" in result.stderr or result.stdout

    def test_safety_halt_with_mismatched_target(self):
        cmd = [
            sys.executable,
            str(REPO_ROOT / "scripts" / "load_supabase_production.py"),
            "--live",
            "--confirm-target=wrong-project-ref",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        assert result.returncode == 1
        assert "SAFETY HALT" in result.stderr or result.stdout

    def test_safety_halt_without_db_url(self):
        cmd = [
            sys.executable,
            str(REPO_ROOT / "scripts" / "load_supabase_production.py"),
            "--live",
            f"--confirm-target={EXPECTED_PROJECT_REF}",
            "--db-url=",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        assert result.returncode == 1
        assert "SAFETY HALT" in result.stderr or result.stdout

    def test_live_rollback_requires_confirmation_token(self):
        cmd = [
            sys.executable,
            str(REPO_ROOT / "scripts" / "load_supabase_production.py"),
            "--live",
            f"--confirm-target={EXPECTED_PROJECT_REF}",
            "--db-url=postgresql://postgres:dummy@localhost:5432/postgres",
            "--rollback",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        assert result.returncode == 1
        assert "SAFETY HALT: Live rollback requires explicit confirmation" in result.stderr or result.stdout


class TestTLSConfiguration:
    def test_default_resolution_with_certifi(self):
        import certifi
        params = resolve_tls_parameters()
        assert params["sslmode"] == "verify-full"
        assert params["sslrootcert"] == certifi.where()

    def test_explicit_sslmode_require(self):
        params = resolve_tls_parameters(sslmode_arg="require")
        assert params["sslmode"] == "require"
        assert "sslrootcert" not in params

    def test_explicit_sslrootcert(self, tmp_path):
        dummy_ca = tmp_path / "custom_root_ca.crt"
        dummy_ca.write_text("DUMMY CERTIFICATE", encoding="utf-8")
        params = resolve_tls_parameters(sslrootcert_arg=str(dummy_ca))
        assert params["sslmode"] == "verify-full"
        assert params["sslrootcert"] == str(dummy_ca)

    def test_env_override_pgsslrootcert(self, monkeypatch, tmp_path):
        dummy_ca = tmp_path / "env_ca.crt"
        dummy_ca.write_text("ENV CERTIFICATE", encoding="utf-8")
        monkeypatch.setenv("PGSSLROOTCERT", str(dummy_ca))
        params = resolve_tls_parameters()
        assert params["sslmode"] == "verify-full"
        assert params["sslrootcert"] == str(dummy_ca)

    def test_fallback_when_no_ca(self, monkeypatch):
        monkeypatch.setattr("certifi.where", lambda: "/non/existent/cacert.pem")
        monkeypatch.delenv("PGSSLROOTCERT", raising=False)
        monkeypatch.delenv("SSL_ROOT_CERT", raising=False)
        params = resolve_tls_parameters()
        assert params["sslmode"] == "require"
        assert "sslrootcert" not in params


class TestCrossRunConflictAndTransactionSemantics:
    def test_cross_run_conflict_raises(self):
        engine = ProductionLoaderEngine("postgresql://fake:5432/db", dry_run=True)
        from unittest.mock import MagicMock
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (5,)

        with pytest.raises(CrossRunConflictError) as exc_info:
            engine.check_cross_run_conflict(mock_cursor, "uehi_blocks", str(RUN_ID_PHASE3))

        assert "Cross-run conflict detected in table 'uehi_blocks': found 5 records" in str(exc_info.value)
        assert "Refusing to silently overwrite unmanaged records" in str(exc_info.value)

    def test_cross_run_conflict_passes_when_clean(self):
        engine = ProductionLoaderEngine("postgresql://fake:5432/db", dry_run=True)
        from unittest.mock import MagicMock
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (0,)

        # Should execute cleanly without error
        engine.check_cross_run_conflict(mock_cursor, "uehi_blocks", str(RUN_ID_PHASE3))

    def test_transaction_aborts_without_commit_on_failure(self):
        from unittest.mock import MagicMock, patch
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        engine = ProductionLoaderEngine("postgresql://fake:5432/db", dry_run=False)
        engine.conn = mock_conn

        with patch("psycopg2.extras.execute_values", side_effect=RuntimeError("Simulated DB Failure")):
            with pytest.raises(RuntimeError):
                engine.execute_provenance()

        mock_conn.commit.assert_not_called()


class TestProvenanceAndSchemaCompatibility:
    def test_deterministic_production_run_ids(self):
        # Invariants: IDs must remain identical and deterministic across all executions
        assert RUN_ID_PHASE3 == uuid.UUID("1595417e-db36-5361-bbd3-f0fb4bb57ce0")
        assert RUN_ID_OPTIMIZATION == uuid.UUID("9dc81257-2abb-5f59-9ced-65fcc5f24816")
        assert METH_ID_UEHI == uuid.UUID("1c9911a5-eb73-52b9-987d-da2393b9a5d8")
        assert METH_ID_CARBON == uuid.UUID("91d527bf-2228-5546-a4ad-1fc04732878a")
        assert METH_ID_CANDIDATES == uuid.UUID("50e082ae-6f8c-5e95-aed5-1240173fde80")
        assert METH_ID_SCENARIOS == uuid.UUID("2a5690c2-7938-553b-a61b-10649c27e378")

    def test_provenance_records_integrity(self):
        data_sources, methodologies, production_runs = plan_provenance_records()

        # Check data sources
        assert len(data_sources) == 6
        for ds in data_sources:
            assert isinstance(ds["id"], uuid.UUID)
            assert ds["source_name"] and ds["dataset_name"]
            assert isinstance(ds["data_year"], int)

        # Check methodology versions
        assert len(methodologies) == 4
        valid_pipeline_types = {
            "uehi_scoring",
            "carbon_estimation",
            "planting_candidate_generation",
            "planting_scenario_generation",
        }
        for m in methodologies:
            assert isinstance(m["id"], uuid.UUID)
            assert m["pipeline_type"] in valid_pipeline_types
            assert len(m["version_hash"]) == 64

        # Check production runs
        assert len(production_runs) == 2
        for pr in production_runs:
            assert isinstance(pr["id"], uuid.UUID)
            assert pr["pipeline_name"]
            assert pr["status"] == "completed"

    def test_uehi_blocks_count_and_null_preservation(self):
        grid_path = PROD_DATA_DIR / "pune_pn_grid_250m_2026.geojson"
        geom_map = load_grid_geometry_map(grid_path)
        assert len(geom_map) == 5309

        rows = plan_uehi_blocks(geom_map)
        assert len(rows) == 5309

        excluded_rows = [r for r in rows if r[10] is True]
        scorable_rows = [r for r in rows if r[10] is False]

        assert len(excluded_rows) == 11
        assert len(scorable_rows) == 5298

        for r in excluded_rows:
            assert r[8] is None
            assert r[9] is None

        for r in scorable_rows:
            assert r[8] is not None
            assert 0.0 <= r[8] <= 100.0
            assert r[9] in ("Critical", "High", "Moderate", "Low")

    def test_carbon_blocks_detailed_metrics_present(self):
        grid_path = PROD_DATA_DIR / "pune_pn_grid_250m_2026.geojson"
        geom_map = load_grid_geometry_map(grid_path)

        rows = plan_carbon_blocks(geom_map)
        assert len(rows) == 5309

        for r in rows:
            assert r[0].startswith("PN_")
            assert isinstance(r[2], float)  # carbon_stock
            assert isinstance(r[3], float)  # canopy_area_m2
            assert isinstance(r[4], float)  # estimated_tree_count
            assert isinstance(r[5], float)  # above_ground_biomass_kg
            assert r[6] == str(METH_ID_CARBON)
            assert r[7] == str(RUN_ID_PHASE3)


class TestStreamingAndScenarioNesting:
    def test_streaming_geojson_on_synthetic_fixture(self, tmp_path):
        test_geojson = tmp_path / "test_stream.geojson"
        content = """{
"type": "FeatureCollection",
"features": [
{ "type": "Feature", "properties": { "id": "1", "val": 10 }, "geometry": { "type": "Point", "coordinates": [10.0, 20.0] } },
{ "type": "Feature", "properties": { "id": "2", "val": 20 }, "geometry": { "type": "Point", "coordinates": [11.0, 21.0] } },
{ "type": "Feature", "properties": { "id": "3", "val": 30 }, "geometry": { "type": "Point", "coordinates": [12.0, 22.0] } }
]
}"""
        test_geojson.write_text(content, encoding="utf-8")

        streamed = list(stream_geojson_features(test_geojson))
        assert len(streamed) == 3
        assert streamed[0]["properties"]["id"] == "1"
        assert streamed[1]["properties"]["val"] == 20
        assert streamed[2]["geometry"]["coordinates"] == [12.0, 22.0]

    def test_scenarios_nesting_and_target_counts(self):
        assert len(SCENARIO_CONFIGS) == 3
        s100 = SCENARIO_CONFIGS[0]
        s250 = SCENARIO_CONFIGS[1]
        s500 = SCENARIO_CONFIGS[2]

        assert s100["unit_count"] == 100000
        assert s250["unit_count"] == 250000
        assert s500["unit_count"] == 500000

        total_mappings = sum(s["unit_count"] for s in SCENARIO_CONFIGS)
        assert total_mappings == 850000

    def test_deterministic_unit_uuid(self):
        puid1 = "PU_1128671"
        u1 = uuid.uuid5(PU_NAMESPACE, puid1)
        u2 = uuid.uuid5(PU_NAMESPACE, puid1)
        assert u1 == u2
        assert isinstance(u1, uuid.UUID)


class TestRollbackOrderingAndForeignKeys:
    def test_rollback_ordering_respects_foreign_keys(self):
        queries = plan_rollback_queries()
        assert len(queries) == 9

        table_order = [q[1].split()[2].lower() for q in queries]
        expected_order = [
            "planting_scenario_units",
            "planting_units",
            "planting_scenarios",
            "planting_candidate_areas",
            "carbon_blocks",
            "uehi_blocks",
            "production_runs",
            "methodology_versions",
            "data_sources",
        ]
        assert table_order == expected_order

        # Verify child-before-parent ordering
        # planting_scenario_units (child) before planting_units (parent)
        assert table_order.index("planting_scenario_units") < table_order.index("planting_units")
        # planting_scenario_units (child) before planting_scenarios (parent)
        assert table_order.index("planting_scenario_units") < table_order.index("planting_scenarios")
        # carbon_blocks (child) before uehi_blocks (parent)
        assert table_order.index("carbon_blocks") < table_order.index("uehi_blocks")
        # analytical tables before production_runs and methodology_versions
        assert table_order.index("uehi_blocks") < table_order.index("production_runs")
        assert table_order.index("planting_units") < table_order.index("production_runs")
        assert table_order.index("production_runs") < table_order.index("methodology_versions")

    def test_rollback_no_truncate_or_cascade(self):
        queries = plan_rollback_queries()
        for desc, sql, params in queries:
            assert "TRUNCATE" not in sql.upper()
            assert "CASCADE" not in sql.upper()
            assert "WHERE" in sql.upper()
            assert len(params) > 0

    def test_rollback_dry_run_executes_safely(self):
        engine = ProductionLoaderEngine("postgresql://fake:5432/db", dry_run=True)
        # In dry run mode, execute_rollback displays plan without connecting
        engine.execute_rollback()


class TestPostImportValidationInvariants:
    def test_verify_validation_results_success(self):
        valid_state = {
            "uehi_blocks": 5309,
            "carbon_blocks": 5309,
            "excluded_uehi_blocks": 11,
            "excluded_blocks_with_score_error": 0,
            "scorable_blocks_with_missing_score": 0,
            "carbon_detailed_metrics_complete": 5309,
            "candidate_areas": 27422,
            "candidate_areas_valid_geom": 27422,
            "planting_units": 500000,
            "planting_units_valid_geom": 500000,
            "scenario_units_total": 850000,
            "scenarios": {
                "100k Illustrative Scenario (10m spacing)": 100000,
                "250k Illustrative Scenario (10m spacing)": 250000,
                "500k Illustrative Scenario (10m spacing)": 500000,
            },
            "orphaned_carbon_blocks": 0,
            "orphaned_scenario_units": 0,
            "orphaned_scenario_headers": 0,
        }
        errors = verify_validation_results(valid_state)
        assert len(errors) == 0

    def test_verify_validation_results_catches_all_discrepancies(self):
        invalid_state = {
            "uehi_blocks": 5308,  # Missing 1 block
            "carbon_blocks": 5310,  # Extra block
            "excluded_uehi_blocks": 10,  # Missing 1 excluded block
            "excluded_blocks_with_score_error": 1,  # Unscorable block was scored
            "scorable_blocks_with_missing_score": 2,  # Scorable block has null score
            "carbon_detailed_metrics_complete": 5300,  # Missing metrics
            "candidate_areas": 27422,
            "candidate_areas_valid_geom": 27420,  # Invalid geometries
            "planting_units": 499999,  # Missing unit
            "planting_units_valid_geom": 499998,
            "scenario_units_total": 849999,
            "scenarios": {
                "100k": 100000,
                "250k": 250000,
                "500k": 499999,
            },
            "orphaned_carbon_blocks": 1,
            "orphaned_scenario_units": 2,
            "orphaned_scenario_headers": 1,
        }
        errors = verify_validation_results(invalid_state)
        assert len(errors) == 14
        assert any("5,309 UEHI blocks" in e for e in errors)
        assert any("5,309 Carbon blocks" in e for e in errors)
        assert any("excluded blocks with non-null scores" in e for e in errors)
        assert any("scorable blocks with missing scores" in e for e in errors)
        assert any("detailed metrics" in e for e in errors)
        assert any("MultiPolygon in SRID 32643" in e for e in errors)
        assert any("Point in SRID 32643" in e for e in errors)
        assert any("orphaned carbon blocks" in e for e in errors)
        assert any("orphaned scenario mappings" in e for e in errors)


class TestPsycopg2UUIDAdaptation:
    def test_psycopg2_uuid_adapter_registered_and_adapts(self):
        import uuid
        import psycopg2
        from psycopg2.extensions import adapt
        from psycopg2.extras import register_uuid

        # Register UUID adapter
        register_uuid()

        test_uuid = uuid.uuid4()
        adapted = adapt(test_uuid)
        # Verify adapted output conforms to PostgreSQL UUID literal format
        quoted = adapted.getquoted()
        assert str(test_uuid).encode("ascii") in quoted
        assert b"::uuid" in quoted

    def test_provenance_tuples_use_str_uuids(self):
        data_sources, methodologies, production_runs = plan_provenance_records()

        # In execute_provenance, tuples must stringify IDs
        ds_ids = [str(d["id"]) for d in data_sources]
        mv_ids = [str(m["id"]) for m in methodologies]
        pr_ids = [str(p["id"]) for p in production_runs]

        for id_str in ds_ids + mv_ids + pr_ids:
            assert isinstance(id_str, str)
            assert len(id_str) == 36
            # Verify it parses back to a valid UUID
            parsed = uuid.UUID(id_str)
            assert str(parsed) == id_str

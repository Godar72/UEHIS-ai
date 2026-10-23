"""
tests/test_carbon_density_regression.py
──────────────────────────────────────
Regression and mathematical tests for carbon density calculations and standing stock semantics.
Specifically catches the historical factor-of-ten decimal error (22.92 vs 229.22 t CO2e/ha canopy)
and validates denominator labeling consistency across spatial extents.
"""

import math
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from carbon_sink.canopy_height import compute_block_co2


class TestCarbonDensityMathematics:
    """Validate mathematical precision, denominator definitions, and 10x regression."""

    TOTAL_CARBON_STOCK_TONNES = 493093.6884
    CANOPY_AREA_HA = 2151.165725  # 21,511,657.25 m² / 10,000
    CANOPY_AREA_KM2 = 21.51165725
    GROSS_GRID_BLOCKS = 5309
    BLOCK_AREA_M2 = 62500.0
    GROSS_GRID_HA = 5309 * (62500.0 / 10000.0)  # 33,181.25 ha

    def test_canopy_area_normalized_density(self):
        """Canopy-normalized density must be ~229.22 t CO2e/ha."""
        density = self.TOTAL_CARBON_STOCK_TONNES / self.CANOPY_AREA_HA
        assert math.isclose(density, 229.222, rel_tol=1e-3)
        assert round(density, 2) == 229.22

    def test_gross_grid_normalized_density(self):
        """Gross-grid-normalized density across 5,309 blocks must be ~14.86 t CO2e/ha."""
        density = self.TOTAL_CARBON_STOCK_TONNES / self.GROSS_GRID_HA
        assert math.isclose(density, 14.8606, rel_tol=1e-3)
        assert round(density, 2) == 14.86

    def test_factor_of_ten_regression(self):
        """
        Regression test: Assert that the canopy-normalized carbon density
        is NOT the legacy erroneous factor-of-ten value (22.92 ± 0.5).
        Legacy defect arose from confusing 1 km² = 100 ha with 1000 ha.
        """
        density = self.TOTAL_CARBON_STOCK_TONNES / self.CANOPY_AREA_HA
        # The legacy erroneous value was 22.92
        assert abs(density - 22.92) > 150.0, (
            f"Regression detected: density {density} is close to legacy erroneous value 22.92!"
        )
        # Factor between true density and legacy value must be approx 10
        ratio = density / 22.92
        assert math.isclose(ratio, 10.0, rel_tol=0.01)

    def test_km2_to_ha_conversion(self):
        """Verify 1 km² = 100 ha, preventing the division-by-1000 bug."""
        canopy_ha_from_km2 = self.CANOPY_AREA_KM2 * 100.0
        assert math.isclose(canopy_ha_from_km2, self.CANOPY_AREA_HA, rel_tol=1e-6)
        # Density derived from km² must match density derived from ha
        density_via_km2 = self.TOTAL_CARBON_STOCK_TONNES / (self.CANOPY_AREA_KM2 * 100.0)
        assert round(density_via_km2, 2) == 229.22


class TestProductionDatasetDensityIntegrity:
    """Verify density calculations directly against the production CSV dataset."""

    CSV_PATH = Path("UEHIS_Production_2026/pune_carbon_production_2026.csv")

    @pytest.mark.skipif(not Path("UEHIS_Production_2026/pune_carbon_production_2026.csv").exists(),
                        reason="Production CSV not present")
    def test_production_csv_totals_and_density(self):
        df = pd.read_csv(self.CSV_PATH)
        assert len(df) == 5309

        total_stock = df["carbon_stock_tonnes_co2e"].sum()
        total_canopy_m2 = df["canopy_area_m2"].sum()
        canopy_ha = total_canopy_m2 / 10000.0

        assert math.isclose(total_stock, 493093.69, abs_tol=0.05)
        assert math.isclose(canopy_ha, 2151.17, abs_tol=0.05)

        canopy_density = total_stock / canopy_ha
        assert round(canopy_density, 2) == 229.22

        grid_ha = len(df) * 6.25  # 5,309 × 6.25 = 33,181.25 ha
        grid_density = total_stock / grid_ha
        assert round(grid_density, 2) == 14.86

        # Check backward compatibility: carbon_tons_sequestered must equal carbon_stock_tonnes_co2e
        diff = (df["carbon_stock_tonnes_co2e"] - df["carbon_tons_sequestered"]).abs().max()
        assert diff == 0.0, "carbon_tons_sequestered differs from carbon_stock_tonnes_co2e"


class TestStandingStockSemanticsCompatibility:
    """Verify that compute_block_co2 returns both canonical and backward-compatible fields."""

    def test_standing_stock_column_names(self, monkeypatch):
        monkeypatch.setenv("ALLOW_UNCALIBRATED_HEIGHT_FALLBACK", "true")
        monkeypatch.setenv("UEHIS_ALLOW_LEGACY_CANOPY_FALLBACK", "1")
        monkeypatch.setenv("UEHIS_TEST_NO_GEE", "1")

        blocks_df = pd.DataFrame({
            "block_id": ["TEST_B1", "TEST_B2"],
            "block_area_m2": [62500.0, 62500.0],
            "canopy_area_m2": [10000.0, 5000.0],
            "tree_density": [0.16, 0.08],
        })

        result = compute_block_co2(blocks_df, allometric_model="urban_generic")

        # Canonical standing stock column
        assert "standing_carbon_stock_tonnes_co2e" in result.columns
        assert "carbon_stock_tonnes_co2e" in result.columns

        # Backward-compatible deprecated alias
        assert "carbon_tons_sequestered" in result.columns

        # Verify values are identical
        np.testing.assert_allclose(
            result["standing_carbon_stock_tonnes_co2e"].values,
            result["carbon_stock_tonnes_co2e"].values,
        )
        np.testing.assert_allclose(
            result["carbon_tons_sequestered"].values,
            result["carbon_stock_tonnes_co2e"].values,
        )


class TestApiSummaryCarbonDensity:
    """Verify that the FastAPI summary endpoint calculates and returns unambiguous densities."""

    def test_api_summary_density_calculation(self, monkeypatch):
        from unittest.mock import MagicMock
        from fastapi.testclient import TestClient
        from api.main import app
        from api.database import get_db

        monkeypatch.setenv("UEHIS_API_KEY", "test-key")

        mock_db = MagicMock()

        def mock_execute(statement, *args, **kwargs):
            query = str(statement)
            res = MagicMock()
            if "FROM uehi_blocks" in query:
                res.fetchone.return_value = (5309, 5298, 46.85)
            elif "FROM carbon_blocks" in query:
                res.fetchone.return_value = (
                    493093.6884,  # standing_carbon_stock
                    21511657.25,  # canopy_area_m2
                    4600003.20,   # estimated_tree_count
                    286127865.13, # above_ground_biomass_kg
                    1261          # nonzero_blocks
                )
            return res

        mock_db.execute.side_effect = mock_execute

        def override_get_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_get_db

        try:
            client = TestClient(app)
            response = client.get("/summary", headers={"X-API-Key": "test-key"})
            assert response.status_code == 200
            data = response.json()

            carbon = data["carbon"]
            assert carbon["total_carbon"] == pytest.approx(493093.6884, rel=1e-4)
            assert carbon["canopy_area_km2"] == pytest.approx(21.511657, rel=1e-4)
            assert carbon["canopy_area_ha"] == pytest.approx(2151.1657, rel=1e-4)

            # Canopy-normalized density must be 229.22 t CO2e/ha
            assert carbon["canopy_density_t_co2e_per_ha"] == 229.22

            # Gross-grid-normalized density must be 14.86 t CO2e/ha
            assert carbon["gross_grid_density_t_co2e_per_ha"] == 14.86
        finally:
            app.dependency_overrides.pop(get_db, None)


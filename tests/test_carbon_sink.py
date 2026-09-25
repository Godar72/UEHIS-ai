import math
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import box, Polygon
import pytest

from carbon_sink.canopy_height import (
    fallback_height_from_frac,
    carbon_from_canopy_params,
    compute_block_co2,
)
from carbon_sink.biomass import (
    estimate_dbh_from_crown,
    compute_agb,
    agb_to_co2_tonnes,
)
from carbon_sink.canopy_area import (
    _sum_block_canopy_intersection_area_m2,
    CANOPY_AREA_SOURCE_RASTER,
)

class TestFallbackHeight:
    def test_zero_canopy(self):
        """Zero or near-zero canopy fraction should yield 0 height."""
        assert fallback_height_from_frac(0.0) == 0.0
        assert fallback_height_from_frac(0.00005) == 0.0

    def test_normal_canopy(self):
        """Normal canopy fraction: 3.0 + 12.0 * frac"""
        assert math.isclose(fallback_height_from_frac(0.5), 9.0)
        assert math.isclose(fallback_height_from_frac(0.1), 4.2)

    def test_max_clamped(self):
        """Canopy fraction at or above 1.0 should clamp to 15.0"""
        assert math.isclose(fallback_height_from_frac(1.0), 15.0)
        assert math.isclose(fallback_height_from_frac(1.5), 15.0)

class TestHeightProductionSafety:
    def test_gee_failure_hard_failure_default(self, monkeypatch):
        """If GEE fails and fallback is not explicitly enabled, it should hard fail."""
        # Monkeypatch fetch_canopy_height_ee to simulate failure (return None)
        import carbon_sink.canopy_height
        monkeypatch.setattr(carbon_sink.canopy_height, "fetch_canopy_height_ee", lambda df, geo: None)
        
        # Ensure env var is not set
        monkeypatch.delenv("ALLOW_UNCALIBRATED_HEIGHT_FALLBACK", raising=False)
        
        blocks_df = pd.DataFrame({"block_id": ["B1"], "canopy_area_m2": [1000], "block_area_m2": [10000]})
        
        with pytest.raises(RuntimeError, match="scientifically uncalibrated fallback cannot be silently substituted"):
            carbon_sink.canopy_height.get_canopy_height(blocks_df)

    def test_gee_failure_explicit_fallback_enabled(self, monkeypatch):
        """If GEE fails but fallback is explicitly enabled, it should succeed and label as UNCALIBRATED_FALLBACK."""
        import carbon_sink.canopy_height
        monkeypatch.setattr(carbon_sink.canopy_height, "fetch_canopy_height_ee", lambda df, geo: None)
        
        # Enable fallback
        monkeypatch.setenv("ALLOW_UNCALIBRATED_HEIGHT_FALLBACK", "true")
        
        blocks_df = pd.DataFrame({"block_id": ["B1"], "canopy_area_m2": [1000], "block_area_m2": [10000]})
        
        result_df, source = carbon_sink.canopy_height.get_canopy_height(blocks_df)
        assert source == "UNCALIBRATED_FALLBACK(canopy_area/block_area)"
        assert "canopy_height_m" in result_df.columns
        assert len(result_df) == 1


class TestDBHCalculation:
    def test_dbh_conversion(self):
        """DBH (cm) = crown_diameter (m) * 100 / ratio"""
        # With default ratio 20
        assert math.isclose(estimate_dbh_from_crown(10.0), 50.0)
        assert math.isclose(estimate_dbh_from_crown(5.0), 25.0)


class TestAGBCalculation:
    def test_urban_generic_agb(self):
        """AGB = a * DBH^b for urban generic (McPherson 2016)
        a=0.1066, b=2.4572"""
        dbh = 50.0
        expected = 0.1066 * (dbh ** 2.4572)
        assert math.isclose(compute_agb(dbh, "urban_generic"), expected)


class TestCO2Conversion:
    def test_agb_to_co2(self):
        """CO2 tonnes = AGB(kg) * 0.47 * (44/12) / 1000"""
        agb = 1000.0
        expected = agb * 0.47 * (44.0 / 12.0) / 1000.0
        assert math.isclose(agb_to_co2_tonnes(agb), expected)


class TestCarbonChain:
    def test_zero_canopy(self):
        """Zero canopy area should yield zero trees, zero AGB, zero CO2"""
        n_trees, agb, co2 = carbon_from_canopy_params(0.0, 10.0)
        assert n_trees == 0.0
        assert agb == 0.0
        assert co2 == 0.0

    def test_valid_area(self):
        """Valid area and height should produce positive carbon stock"""
        n_trees, agb, co2 = carbon_from_canopy_params(100.0, 10.0)
        assert n_trees > 0
        assert agb > 0
        assert co2 > 0


class TestCanopyAreaIntegrity:
    def test_intersection_area(self):
        """Test that canopy area is physical intersection area, bounded by block area"""
        block_geom = box(0, 0, 10, 10)  # Area = 100
        # Canopy completely covering block, but is much larger
        canopy_geom1 = box(-10, -10, 20, 20)
        # Canopy partially covering
        canopy_geom2 = box(5, 0, 15, 10) # Overlap area = 50
        
        canopy_gdf = gpd.GeoDataFrame(geometry=[canopy_geom1])
        area1 = _sum_block_canopy_intersection_area_m2(block_geom, canopy_gdf)
        # Bounded by block area
        assert math.isclose(area1, 100.0)

        canopy_gdf = gpd.GeoDataFrame(geometry=[canopy_geom2])
        area2 = _sum_block_canopy_intersection_area_m2(block_geom, canopy_gdf)
        assert math.isclose(area2, 50.0)

    def test_no_intersection(self):
        block_geom = box(0, 0, 10, 10)
        canopy_geom = box(20, 20, 30, 30)
        canopy_gdf = gpd.GeoDataFrame(geometry=[canopy_geom])
        area = _sum_block_canopy_intersection_area_m2(block_geom, canopy_gdf)
        assert area == 0.0


class TestWaterIndependence:
    def test_no_water_required(self, monkeypatch):
        """Compute block CO2 without water columns"""
        monkeypatch.setenv("ALLOW_UNCALIBRATED_HEIGHT_FALLBACK", "true")
        blocks_df = pd.DataFrame({
            "block_id": ["B1"],
            "block_area_m2": [10000.0],
            "tree_density": [1.0], # Needed for fallback area
            "canopy_frac": [0.5]
        })
        
        result = compute_block_co2(blocks_df, allometric_model="urban_generic")
        
        assert "carbon_stock_tonnes_co2e" in result.columns
        assert not result["carbon_stock_tonnes_co2e"].isna().all()
        # Verify no water columns were magically added
        assert "water_availability" not in result.columns

class TestOutputIntegrity:
    def test_no_mutation(self, monkeypatch):
        """Input dataframe should not be mutated in place"""
        monkeypatch.setenv("ALLOW_UNCALIBRATED_HEIGHT_FALLBACK", "true")
        blocks_df = pd.DataFrame({
            "block_id": ["B1"],
            "block_area_m2": [10000.0],
            "tree_density": [1.0],
            "canopy_frac": [0.5]
        })
        original_cols = list(blocks_df.columns)
        
        result = compute_block_co2(blocks_df, allometric_model="urban_generic")
        
        # Original shouldn't have new columns
        assert list(blocks_df.columns) == original_cols
        # Result should have new columns
        assert "carbon_stock_tonnes_co2e" in result.columns

class TestLegacyBaseline:
    def test_legacy_landsat_polygon_baseline(self):
        """Regression guard for the legacy Landsat pipeline.
        Ensures the original Kothrud baseline remains unmodified."""
        from pathlib import Path
        import pandas as pd
        import pytest
        import math
        from carbon_sink.canopy_height import fallback_height_from_frac, carbon_from_canopy_params
        
        # Paths to historical baseline artifacts
        scores_path = Path("outputs/kothrud_scores.csv")
        cs_path = Path("outputs/kothrud_carbon_stock.csv")
        
        if not cs_path.exists() or not scores_path.exists():
            pytest.skip("Historical Kothrud artifacts not found for legacy regression test.")
            
        # 1. Load scores and historical carbon stock
        scores = pd.read_csv(scores_path)
        cs = pd.read_csv(cs_path)
        
        # Merge them to use the preserved canopy_area_m2 and canopy_frac together
        merged = scores[["block_id", "canopy_frac"]].merge(cs[["block_id", "canopy_area_m2"]], on="block_id")
        
        # 2. Run historical fallback logic directly
        height_m = fallback_height_from_frac(merged["canopy_frac"])
        
        # 3. Run allometric chain
        _, _, co2_tonnes = carbon_from_canopy_params(
            canopy_area_m2=merged["canopy_area_m2"],
            height_m=height_m,
            allometric_model="urban_generic"
        )
        
        total_canopy_area = merged["canopy_area_m2"].sum()
        total_carbon_stock = co2_tonnes.sum()
        
        # Using the exact figures specified in the audit findings
        expected_canopy_area = 3799138.57
        expected_carbon_stock = 75980.06
        
        # Check numerical values
        print(f"Computed total_canopy_area: {total_canopy_area}")
        print(f"Computed total_carbon_stock: {total_carbon_stock}")
        
        assert math.isclose(total_canopy_area, expected_canopy_area, rel_tol=0.05), \
            f"Canopy area changed! Expected ~{expected_canopy_area}, got {total_canopy_area}"
            
        assert math.isclose(total_carbon_stock, expected_carbon_stock, rel_tol=0.001), \
            f"Carbon stock changed! Expected ~{expected_carbon_stock}, got {total_carbon_stock}"

class TestRasterFirstCanopy:
    def test_unet_raster_production(self, tmp_path):
        """Test raster-first canopy calculation characteristics:
        - nodata handling
        - partial block
        - 100% canopy block
        - zero-canopy block
        - CRS/grid alignment"""
        import rasterio
        from rasterio.transform import Affine
        from carbon_sink.canopy_area import aggregate_canopy_area_m2_from_raster, CANOPY_CLASS_ID
        
        tif_path = tmp_path / "synthetic_unet.tif"
        
        data = np.full((10, 10), 255, dtype=np.uint8)
        data[0:5, 0:5] = CANOPY_CLASS_ID
        data[0:5, 5:10] = 1
        
        transform = Affine.translation(300000.0, 2000000.0) * Affine.scale(10.0, -10.0)
        
        with rasterio.open(
            tif_path, 'w',
            driver='GTiff',
            height=data.shape[0],
            width=data.shape[1],
            count=1,
            dtype=data.dtype,
            crs='EPSG:32643',
            transform=transform,
            nodata=255
        ) as dst:
            dst.write(data, 1)
            
        geom1 = box(300000.0, 1999950.0, 300050.0, 2000000.0)
        geom2 = box(300050.0, 1999950.0, 300100.0, 2000000.0)
        geom3 = box(300000.0, 1999900.0, 300100.0, 1999950.0)
        
        blocks_gdf = gpd.GeoDataFrame({
            "block_id": ["B1", "B2", "B3"],
            "geometry": [geom1, geom2, geom3]
        }, crs='EPSG:32643')
        
        result = aggregate_canopy_area_m2_from_raster(blocks_gdf, tif_path)
        
        assert len(result) == 3
        
        b1_res = result[result["block_id"] == "B1"].iloc[0]
        assert b1_res["canopy_pixel_count"] == 25
        assert math.isclose(b1_res["canopy_area_m2"], 2500.0)
        assert math.isclose(b1_res["block_area_m2"], 2500.0)
        assert b1_res["canopy_area_source"] == CANOPY_AREA_SOURCE_RASTER
        assert b1_res["valid_pixel_count"] == 25
        assert b1_res["canopy_completeness"] == 1.0
        
        b2_res = result[result["block_id"] == "B2"].iloc[0]
        assert b2_res["canopy_pixel_count"] == 0
        assert b2_res["valid_pixel_count"] == 25
        assert math.isclose(b2_res["canopy_area_m2"], 0.0)
        assert b2_res["canopy_completeness"] == 1.0
        
        b3_res = result[result["block_id"] == "B3"].iloc[0]
        assert b3_res["canopy_pixel_count"] == 0
        assert b3_res["valid_pixel_count"] == 0
        assert math.isclose(b3_res["canopy_area_m2"], 0.0)
        assert b3_res["canopy_completeness"] == 0.0

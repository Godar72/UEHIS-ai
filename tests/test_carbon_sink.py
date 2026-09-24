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
from carbon_sink.canopy_area import _sum_block_canopy_intersection_area_m2

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
    def test_no_water_required(self):
        """Compute block CO2 without water columns"""
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
    def test_no_mutation(self):
        """Input dataframe should not be mutated in place"""
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

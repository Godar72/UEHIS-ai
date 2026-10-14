import math
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import box, Polygon
import pytest
import os

os.environ["UEHIS_TEST_NO_GEE"] = "1"

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
        monkeypatch.setenv("UEHIS_ALLOW_LEGACY_CANOPY_FALLBACK", "1")
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
        monkeypatch.setenv("UEHIS_ALLOW_LEGACY_CANOPY_FALLBACK", "1")
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
    def test_legacy_landsat_polygon_baseline(self, monkeypatch):
        """Regression guard for the legacy Landsat pipeline.
        Ensures the original Kothrud baseline remains unmodified."""
        monkeypatch.setenv("UEHIS_ALLOW_LEGACY_CANOPY_FALLBACK", "1")
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


class TestQAIntegrity:
    def test_duplicate_block_id(self, monkeypatch):
        monkeypatch.setenv("ALLOW_UNCALIBRATED_HEIGHT_FALLBACK", "true")
        monkeypatch.setenv("UEHIS_ALLOW_LEGACY_CANOPY_FALLBACK", "1")
        blocks_df = pd.DataFrame({"block_id": ["B1", "B1"], "block_area_m2": [10000, 10000], "canopy_area_m2": [1000, 1000], "tree_density": [1.0, 1.0]})
        with pytest.raises(ValueError, match="QA FAILED: Duplicate block IDs found"):
            compute_block_co2(blocks_df, allometric_model="urban_generic")
            
    def test_negative_canopy_area(self, monkeypatch):
        monkeypatch.setenv("ALLOW_UNCALIBRATED_HEIGHT_FALLBACK", "true")
        monkeypatch.setenv("UEHIS_ALLOW_LEGACY_CANOPY_FALLBACK", "1")
        blocks_df = pd.DataFrame({"block_id": ["B1"], "block_area_m2": [10000], "canopy_area_m2": [-10], "tree_density": [1.0]})
        with pytest.raises(ValueError, match="QA FAILED: Negative canopy_area_m2 found."):
            compute_block_co2(blocks_df, allometric_model="urban_generic")
            
    def test_canopy_area_exceeds_block(self, monkeypatch):
        monkeypatch.setenv("ALLOW_UNCALIBRATED_HEIGHT_FALLBACK", "true")
        monkeypatch.setenv("UEHIS_ALLOW_LEGACY_CANOPY_FALLBACK", "1")
        blocks_df = pd.DataFrame({"block_id": ["B1"], "block_area_m2": [10000], "canopy_area_m2": [15000], "tree_density": [1.0]})
        with pytest.raises(ValueError, match="QA FAILED: canopy_area_m2 exceeds block_area_m2."):
            compute_block_co2(blocks_df, allometric_model="urban_generic")
            
    def test_negative_height(self, monkeypatch):
        monkeypatch.setenv("ALLOW_UNCALIBRATED_HEIGHT_FALLBACK", "true")
        monkeypatch.setenv("UEHIS_ALLOW_LEGACY_CANOPY_FALLBACK", "1")
        blocks_df = pd.DataFrame({"block_id": ["B1"], "block_area_m2": [10000], "canopy_area_m2": [1000], "canopy_frac": [0.5], "tree_density": [1.0]})
        import carbon_sink.canopy_height
        monkeypatch.setattr(carbon_sink.canopy_height, "get_canopy_height", lambda df, geo: (pd.DataFrame({"block_id": ["B1"], "canopy_height_m": [-1.0]}), "mocked"))
        
        with pytest.raises(ValueError, match="QA FAILED: Negative canopy height found."):
            compute_block_co2(blocks_df, allometric_model="urban_generic")

    def test_canopy_fraction_bounds(self, monkeypatch):
        monkeypatch.setenv("ALLOW_UNCALIBRATED_HEIGHT_FALLBACK", "true")
        monkeypatch.setenv("UEHIS_ALLOW_LEGACY_CANOPY_FALLBACK", "1")
        blocks_df = pd.DataFrame({"block_id": ["B1"], "block_area_m2": [10000], "canopy_area_m2": [1000], "canopy_fraction": [1.5], "tree_density": [1.0]})
        with pytest.raises(ValueError, match="QA FAILED: canopy_fraction outside"):
            compute_block_co2(blocks_df, allometric_model="urban_generic")


class TestModernCarbonValidation:
    def test_modern_carbon_result_matches_independently(self):
        """Verify the Kothrud modern production output against independent calc."""
        import os
        import pandas as pd
        from carbon_sink.canopy_height import carbon_from_canopy_params
        csv_path = 'outputs/unet_raster_production.csv'
        if not os.path.exists(csv_path):
            return
        df = pd.read_csv(csv_path)
        if 'ETH_GlobalCanopyHeight_2020' not in df['canopy_height_source'].iloc[0]:
            return
        n_trees, total_agb_kg, co2_tonnes = carbon_from_canopy_params(
            df['canopy_area_m2'].values,
            df['canopy_height_m'].values,
            'urban_generic'
        )
        assert abs(n_trees.sum() - 181032) < 2
        assert abs(total_agb_kg.sum() - 5145785) < 2
        assert abs(co2_tonnes.sum() - 8867.9) < 0.1


class TestPuneProductionArchitecture:
    def test_rejection_of_legacy_canopy_fallback(self):
        """Ensure Pune production strictly fails if raster is missing and fallback is not explicitly allowed."""
        from carbon_sink.canopy_area import attach_canopy_area_m2
        import pandas as pd
        import pytest
        import os
        
        blocks_df = pd.DataFrame({"block_id": ["A"], "tree_density": [1.0], "block_area_m2": [100.0]})
        
        # Make sure fallback env is NOT set
        if "UEHIS_ALLOW_LEGACY_CANOPY_FALLBACK" in os.environ:
            del os.environ["UEHIS_ALLOW_LEGACY_CANOPY_FALLBACK"]
            
        with pytest.raises(RuntimeError, match="Pune production requires a valid unet_tif"):
            attach_canopy_area_m2(blocks_df)
            
    def test_gee_chunking_logic(self, monkeypatch):
        """Ensure chunk size defaults to 500 and chunks correctly."""
        import carbon_sink.canopy_height
        import ee
        
        features_sent = []
        
        class MockFeatureCollection:
            def __init__(self, f):
                self.f = f
                
        class MockFCResult:
            def getInfo(self):
                return {"features": []}
                
        class MockImage:
            def reduceRegions(self, collection, reducer, scale, tileScale):
                features_sent.append(len(collection.f))
                return MockFCResult()
                
        monkeypatch.setenv("UEHIS_TEST_NO_GEE", "0")
        
        import sys
        mock_ee = type("MockEE", (), {
            "Image": lambda x: MockImage(),
            "FeatureCollection": MockFeatureCollection,
            "Feature": lambda g, p: p,
            "Geometry": type("MockGeometry", (), {"Polygon": lambda *a, **k: None}),
            "Reducer": type("MockReducer", (), {"mean": lambda: None})
        })
        sys.modules['ee'] = mock_ee
        
        import carbon_sink.canopy_height
        
        # also mock authenticate_gee
        monkeypatch.setattr(carbon_sink.canopy_height, "authenticate_gee", lambda: None, raising=False)
        # Because authenticate_gee is in data_ingestion.sentinel
        import sys
        sys.modules['data_ingestion.sentinel'] = type("MockDI", (), {"authenticate_gee": lambda: None})
        
        from shapely.geometry import box
        import pandas as pd
        
        # 5309 blocks
        blocks_df = pd.DataFrame({"block_id": [f"B_{i}" for i in range(5309)]})
        blocks_df["geometry"] = [box(0,0,1,1) for _ in range(5309)]
        
        carbon_sink.canopy_height.fetch_canopy_height_ee(blocks_df)
        
        assert len(features_sent) == 11
        assert sum(features_sent) == 5309
        assert features_sent[0] == 500
        assert features_sent[-1] == 309

    def test_authoritative_pn_grid_loading(self, tmp_path):
        """Verify authoritative grid requirements: 5309 blocks, unique IDs, EPSG:32643."""
        from run_carbon_sequestration import load_and_validate_pn_grid
        import geopandas as gpd
        from shapely.geometry import box
        import pytest
        
        # Create a mock valid GeoJSON
        valid_gdf = gpd.GeoDataFrame({
            "block_id": [f"B_{i}" for i in range(5309)],
            "block_area_m2": [62500.0] * 5309,
            "boundary_intersection_area_m2": [62500.0] * 5309,
            "boundary_coverage_fraction": [1.0] * 5309,
            "geometry": [box(0, 0, 250, 250)] * 5309
        }, crs="EPSG:32643")
        
        valid_path = tmp_path / "valid.geojson"
        valid_gdf.to_file(valid_path, driver="GeoJSON")
        
        # 1. Should load successfully
        loaded = load_and_validate_pn_grid(valid_path)
        assert len(loaded) == 5309
        
        # 2. Wrong row count fails
        invalid_gdf = valid_gdf.iloc[:5308]
        invalid_path = tmp_path / "invalid_rows.geojson"
        invalid_gdf.to_file(invalid_path, driver="GeoJSON")
        with pytest.raises(RuntimeError, match="exactly 5,309 blocks"):
            load_and_validate_pn_grid(invalid_path)
            
        # 3. Duplicate block IDs fail
        dup_gdf = valid_gdf.copy()
        dup_gdf.loc[0, "block_id"] = "B_1"
        dup_path = tmp_path / "dup.geojson"
        dup_gdf.to_file(dup_path, driver="GeoJSON")
        with pytest.raises(RuntimeError, match="unique block IDs"):
            load_and_validate_pn_grid(dup_path)
            
        # 4. Wrong CRS fails
        crs_gdf = valid_gdf.copy().to_crs("EPSG:4326")
        crs_path = tmp_path / "crs.geojson"
        crs_gdf.to_file(crs_path, driver="GeoJSON")
        with pytest.raises(RuntimeError, match="EPSG:32643"):
            load_and_validate_pn_grid(crs_path)
            
        # 5. Missing required boundary columns fails
        missing_col_gdf = valid_gdf.copy().drop(columns=["boundary_intersection_area_m2"])
        missing_path = tmp_path / "missing.geojson"
        missing_col_gdf.to_file(missing_path, driver="GeoJSON")
        with pytest.raises(RuntimeError, match="missing required column"):
            load_and_validate_pn_grid(missing_path)

        # 6. Wrong area fails
        area_gdf = valid_gdf.copy()
        area_gdf.loc[0, "block_area_m2"] = 1000.0
        area_path = tmp_path / "area.geojson"
        area_gdf.to_file(area_path, driver="GeoJSON")
        with pytest.raises(RuntimeError, match="exactly 62500"):
            load_and_validate_pn_grid(area_path)
            
        # 7. Real production grid test (if available)
        import os
        from pathlib import Path
        data_root = os.environ.get("UEHIS_DATA_ROOT")
        if data_root:
            prod_grid_path = Path(data_root) / "pune_pn_grid_250m_2026.geojson"
            if prod_grid_path.exists():
                prod_gdf = load_and_validate_pn_grid(prod_grid_path)
                assert len(prod_gdf) == 5309
                assert prod_gdf.crs.to_string() == "EPSG:32643"

    def test_canopy_pixel_count_propagation(self):
        """Verify canopy_pixel_count is retained from raster through to enriched output."""
        import pandas as pd
        import geopandas as gpd
        from shapely.geometry import box
        from carbon_sink.canopy_area import attach_canopy_area_m2
        import rasterio
        from rasterio.transform import Affine
        import numpy as np
        import tempfile
        
        with tempfile.NamedTemporaryFile(suffix=".tif", delete=False) as tmp:
            tif_path = tmp.name
            
        try:
            data = np.full((10, 10), 0, dtype=np.uint8) # Class 0 = canopy
            transform = Affine.translation(0, 10) * Affine.scale(1, -1)
            with rasterio.open(tif_path, 'w', driver='GTiff', height=10, width=10, count=1, dtype=data.dtype, crs='EPSG:32643', transform=transform, nodata=255) as dst:
                dst.write(data, 1)
                
            blocks_gdf = gpd.GeoDataFrame({
                "block_id": ["B1"],
                "geometry": [box(0, 0, 10, 10)]
            }, crs='EPSG:32643')
            
            blocks_df = pd.DataFrame({"block_id": ["B1"]})
            
            result, source = attach_canopy_area_m2(blocks_df, unet_tif=tif_path, blocks_gdf=blocks_gdf)
            
            assert "canopy_pixel_count" in result.columns
            assert result["canopy_pixel_count"].iloc[0] == 100
        finally:
            import os
            os.remove(tif_path)
            
    def test_required_carbon_output_fields(self):
        """Verify the required output fields are specified in new_cols."""
        import ast
        with open("run_carbon_sequestration.py", "r") as f:
            content = f.read()
            
        assert '"canopy_pixel_count"' in content
        assert '"canopy_area_m2"' in content
        assert '"canopy_height_m"' in content
        assert '"carbon_stock_tonnes_co2e"' in content
        assert '"agb_kg"' in content
        assert '"n_trees_est"' in content
        assert '"allometric_model"' in content

    def test_canopy_area_invariant_and_regression(self):
        """Test physical bound invariant and specific 13-block regression."""
        import os
        from pathlib import Path
        import pandas as pd
        import geopandas as gpd
        import pytest
        from carbon_sink.canopy_area import attach_canopy_area_m2
        
        data_root = os.environ.get("UEHIS_DATA_ROOT")
        if not data_root:
            pytest.skip("UEHIS_DATA_ROOT not set, skipping production regression test.")
            
        data_root = Path(data_root)
        pn_grid = data_root / "pune_pn_grid_250m_2026.geojson"
        unet_tif = data_root / "pune_unet_segmentation_FROZEN_2026.tif"
        scores = data_root / "pune_uehi_scores_phase3_production_2026.csv"
        
        if not pn_grid.exists() or not unet_tif.exists() or not scores.exists():
            pytest.skip("Production artifacts missing.")
            
        gdf = gpd.read_file(pn_grid)
        gdf["block_area_m2"] = gdf.geometry.area
        df = pd.read_csv(scores)
        
        violating_ids = [
            "PN_371500_2049250", "PN_371500_2049500", "PN_371750_2049250",
            "PN_372000_2049000", "PN_372000_2049250", "PN_372250_2048000",
            "PN_372750_2047750", "PN_375250_2048750", "PN_379000_2052250",
            "PN_379500_2050500", "PN_379500_2052000", "PN_379750_2052250",
            "PN_381750_2052500"
        ]
        
        subset_gdf = gdf[gdf["block_id"].isin(violating_ids)].copy()
        subset_df = df[df["block_id"].isin(violating_ids)].copy()
        
        res, _ = attach_canopy_area_m2(subset_df, unet_tif=unet_tif, blocks_gdf=subset_gdf)
        
        res = res.merge(subset_gdf[["block_id", "boundary_intersection_area_m2"]], on="block_id")
        
        for _, row in res.iterrows():
            area = row["canopy_area_m2"]
            block_area = row["block_area_m2"]
            intersect = row["boundary_intersection_area_m2"]
            
            # Invariant: <= boundary_intersection_area_m2 + epsilon
            assert area <= intersect + 1e-6, f"Canopy {area} exceeds intersection {intersect} for {row['block_id']}"
            
            # Invariant: <= block_area_m2
            assert area <= block_area + 1e-6, f"Canopy {area} exceeds block {block_area} for {row['block_id']}"
            
            # Fraction <= 1
            frac = area / max(block_area, 1.0)
            assert frac <= 1.0 + 1e-6, f"Canopy fraction {frac} > 1.0 for {row['block_id']}"

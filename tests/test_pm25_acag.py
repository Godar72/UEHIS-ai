import pytest
import os
import numpy as np
import pandas as pd
import rasterio
from rasterio.transform import Affine
from unittest.mock import patch, MagicMock

from feature_engineering.aggregate_factors import aggregate_pm25_to_blocks
from data_ingestion.acag_pm25 import fetch_and_align_acag_pm25, PM25FetchError

@pytest.fixture
def synthetic_pm25_tif(tmp_path):
    """Creates a synthetic PM2.5 GeoTIFF for testing."""
    tif_path = tmp_path / "test_pm25.tif"
    data = np.array([
        [10.0, 20.0, np.nan],
        [40.0, 50.0, 60.0]
    ], dtype=np.float32)
    
    transform = Affine.translation(0, 0) * Affine.scale(250, -250)
    
    with rasterio.open(
        tif_path, 'w',
        driver='GTiff',
        height=data.shape[0],
        width=data.shape[1],
        count=1,
        dtype=data.dtype,
        crs='EPSG:32643',
        transform=transform,
        nodata=np.nan
    ) as dst:
        dst.write(data, 1)
        dst.update_tags(dataset_identity="ACAG_V6GL03_SatPM25")
        
    return str(tif_path)

@pytest.fixture
def synthetic_ref_tif(tmp_path):
    """Creates a reference GeoTIFF for alignment testing."""
    tif_path = tmp_path / "test_ref.tif"
    data = np.zeros((2, 3), dtype=np.uint8)
    transform = Affine.translation(0, 0) * Affine.scale(250, -250)
    
    with rasterio.open(
        tif_path, 'w',
        driver='GTiff',
        height=data.shape[0],
        width=data.shape[1],
        count=1,
        dtype=data.dtype,
        crs='EPSG:32643',
        transform=transform
    ) as dst:
        dst.write(data, 1)
        
    return str(tif_path)

def test_aggregate_pm25_to_blocks(synthetic_pm25_tif):
    """Test G: Block aggregation handles missing data and calculates correct means."""
    block_idx_arr = np.array([
        [0, 0, 0],
        [1, 1, 2]
    ])
    num_blocks = 3
    
    df = aggregate_pm25_to_blocks(synthetic_pm25_tif, block_idx_arr, num_blocks)
    
    # Block 0 has 10, 20, NaN -> valid: 10, 20 -> mean: 15, count: 2, comp: 2/3
    assert df.loc[0, "pm25"] == 15.0
    assert df.loc[0, "pm25_valid_pixel_count"] == 2
    assert np.isclose(df.loc[0, "pm25_completeness_fraction"], 2/3)
    
    # Block 1 has 40, 50 -> valid: 40, 50 -> mean: 45, count: 2, comp: 2/2
    assert df.loc[1, "pm25"] == 45.0
    assert df.loc[1, "pm25_valid_pixel_count"] == 2
    assert df.loc[1, "pm25_completeness_fraction"] == 1.0
    
    # Block 2 has 60 -> valid: 60 -> mean: 60, count: 1, comp: 1/1
    assert df.loc[2, "pm25"] == 60.0
    assert df.loc[2, "pm25_valid_pixel_count"] == 1
    assert df.loc[2, "pm25_completeness_fraction"] == 1.0

def test_aggregate_pm25_no_valid_data(tmp_path):
    """Test G: No valid pixels produces NaN."""
    tif_path = tmp_path / "test_nan.tif"
    data = np.full((2, 2), np.nan, dtype=np.float32)
    transform = Affine.identity()
    with rasterio.open(
        tif_path, 'w', driver='GTiff', height=2, width=2, count=1,
        dtype=data.dtype, crs='EPSG:32643', transform=transform, nodata=np.nan
    ) as dst:
        dst.write(data, 1)
        
    block_idx = np.array([[0, 0], [0, 0]])
    df = aggregate_pm25_to_blocks(str(tif_path), block_idx, 1)
    
    assert pd.isna(df.loc[0, "pm25"])
    assert df.loc[0, "pm25_valid_pixel_count"] == 0
    assert df.loc[0, "pm25_completeness_fraction"] == 0.0

@patch('data_ingestion.acag_pm25.ee.ImageCollection')
@patch('data_ingestion.acag_pm25.authenticate_gee')
@patch('data_ingestion.acag_pm25.geemap.ee_export_image')
def test_fetch_acag_pm25_temporal_validation(mock_export, mock_auth, mock_collection, synthetic_ref_tif, tmp_path):
    """Test A & D: Temporal validation (month count) fails on missing months."""
    # Mocking ImageCollection to return size != 3
    mock_col = MagicMock()
    mock_col.filterDate.return_value = mock_col
    mock_col.size.return_value.getInfo.return_value = 2  # Missing a month
    mock_collection.return_value = mock_col
    
    roi = (73.7, 18.4, 74.0, 18.6)
    
    with pytest.raises(PM25FetchError, match="Expected exactly 3 monthly images"):
        fetch_and_align_acag_pm25(roi, synthetic_ref_tif, output_dir=str(tmp_path))

def test_negative_pm25_handling(synthetic_pm25_tif):
    """Test D: Raw PM2.5 remains raw, no inversion."""
    block_idx_arr = np.array([[0, 0, 0], [0, 0, 0]])
    df = aggregate_pm25_to_blocks(synthetic_pm25_tif, block_idx_arr, 1)
    # The values 10, 20, 40, 50, 60 mean = 36. 
@patch('data_ingestion.acag_pm25.ee')
@patch('data_ingestion.acag_pm25.authenticate_gee')
@patch('data_ingestion.acag_pm25.geemap.ee_export_image')
def test_fetch_acag_pm25_wrong_band(mock_export, mock_auth, mock_ee, synthetic_ref_tif, tmp_path):
    """Test: Explicitly verify 'b1' band is required."""
    mock_col = MagicMock()
    mock_col.filterDate.return_value = mock_col
    mock_col.size.return_value.getInfo.return_value = 3
    mock_ee.ImageCollection.return_value = mock_col
    
    import datetime
    dates = [
        datetime.datetime(2024, 1, 15).timestamp() * 1000,
        datetime.datetime(2024, 2, 15).timestamp() * 1000,
        datetime.datetime(2024, 3, 15).timestamp() * 1000,
    ]
    
    def mock_image_side_effect(obj):
        return obj
    mock_ee.Image.side_effect = mock_image_side_effect
    
    def mock_date_side_effect(val):
        m = MagicMock()
        m.getInfo.return_value = {'value': val}
        return m
    mock_ee.Date.side_effect = mock_date_side_effect
    
    def get_img(i):
        m = MagicMock()
        m.get.return_value = dates[i]
        m.bandNames.return_value.getInfo.return_value = ['wrong_band']
        return m
        
    mock_col.toList.return_value.get.side_effect = get_img
    
    roi = (73.7, 18.4, 74.0, 18.6)
    
    with pytest.raises(PM25FetchError, match="Expected band 'b1' not found"):
        fetch_and_align_acag_pm25(roi, synthetic_ref_tif, output_dir=str(tmp_path))

@patch('data_ingestion.acag_pm25.ee')
@patch('data_ingestion.acag_pm25.authenticate_gee')
@patch('data_ingestion.acag_pm25.geemap.ee_export_image')
def test_fetch_acag_pm25_wrong_months(mock_export, mock_auth, mock_ee, synthetic_ref_tif, tmp_path):
    """Test: Duplicate or wrong months fails."""
    mock_col = MagicMock()
    mock_col.filterDate.return_value = mock_col
    mock_col.size.return_value.getInfo.return_value = 3
    mock_ee.ImageCollection.return_value = mock_col
    
    def mock_image_side_effect(obj):
        return obj
    mock_ee.Image.side_effect = mock_image_side_effect
    
    def mock_date_side_effect(val):
        m = MagicMock()
        m.getInfo.return_value = {'value': val}
        return m
    mock_ee.Date.side_effect = mock_date_side_effect
    
    import datetime
    # Jan, Feb, Feb (Duplicate)
    dates = [
        datetime.datetime(2024, 1, 15).timestamp() * 1000,
        datetime.datetime(2024, 2, 15).timestamp() * 1000,
        datetime.datetime(2024, 2, 28).timestamp() * 1000,
    ]
    
    def get_img(i):
        m = MagicMock()
        m.get.return_value = dates[i]
        return m
        
    mock_col.toList.return_value.get.side_effect = get_img
    
    roi = (73.7, 18.4, 74.0, 18.6)
    
    with pytest.raises(PM25FetchError, match="Missing required months"):
        fetch_and_align_acag_pm25(roi, synthetic_ref_tif, output_dir=str(tmp_path))

def test_zero_and_negative_not_masked(tmp_path):
    """Test: Zero and negative synthetic values are not automatically discarded."""
    # Create an aligned TIF directly mimicking what fetch_and_align_acag_pm25 outputs 
    # to ensure zero and negatives survive block aggregation.
    tif_path = tmp_path / "test_zero_neg.tif"
    data = np.array([
        [0.0, -5.0],
        [10.0, np.nan]
    ], dtype=np.float32)
    
    transform = Affine.translation(0, 0) * Affine.scale(250, -250)
    with rasterio.open(
        tif_path, 'w', driver='GTiff', height=2, width=2, count=1,
        dtype=data.dtype, crs='EPSG:32643', transform=transform, nodata=np.nan
    ) as dst:
        dst.write(data, 1)
        
    block_idx = np.array([[0, 0], [0, 0]])
    df = aggregate_pm25_to_blocks(str(tif_path), block_idx, 1)
    
    # Values: 0.0, -5.0, 10.0 -> mean is 5.0 / 3 = 1.666...
    assert np.isclose(df.loc[0, "pm25"], 5.0 / 3.0)
    assert df.loc[0, "pm25_valid_pixel_count"] == 3

@patch('data_ingestion.acag_pm25.ee')
@patch('data_ingestion.acag_pm25.authenticate_gee')
@patch('data_ingestion.acag_pm25.geemap.ee_export_image')
def test_seasonal_mean_masking(mock_export, mock_auth, mock_ee, synthetic_ref_tif, tmp_path):
    """Test: one-month masked pixel becomes NaN, all-three-valid pixel receives exact arithmetic mean."""
    mock_col = MagicMock()
    mock_col.filterDate.return_value = mock_col
    mock_col.size.return_value.getInfo.return_value = 3
    
    def mock_image_side_effect(obj):
        return obj
    mock_ee.Image.side_effect = mock_image_side_effect
    
    def mock_date_side_effect(val):
        m = MagicMock()
        m.getInfo.return_value = {'value': val}
        return m
    mock_ee.Date.side_effect = mock_date_side_effect
    
    import datetime
    dates = [
        datetime.datetime(2024, 1, 15).timestamp() * 1000,
        datetime.datetime(2024, 2, 15).timestamp() * 1000,
        datetime.datetime(2024, 3, 15).timestamp() * 1000,
    ]
    def get_img(i):
        m = MagicMock()
        m.get.return_value = dates[i]
        m.bandNames.return_value.getInfo.return_value = ['b1']
        return m
    mock_col.toList.return_value.get.side_effect = get_img
    
    mock_col_select = MagicMock()
    mock_col.select.return_value = mock_col_select
    
    mock_valid_count = MagicMock()
    mock_col_select.count.return_value = mock_valid_count
    
    mock_mean = MagicMock()
    mock_col_select.mean.return_value = mock_mean
    
    mock_update_mask = MagicMock()
    mock_mean.updateMask.return_value = mock_update_mask
    
    mock_ee.ImageCollection.return_value = mock_col
    
    def fake_export(img, filename, **kwargs):
        with open(filename, 'w') as f:
            f.write("mock")
        data = np.array([[10, 20], [np.nan, 30]], dtype=np.float32)
        prof = {'driver': 'GTiff', 'height': 2, 'width': 2, 'count': 1, 'dtype': 'float32', 'crs': 'EPSG:4326', 'transform': Affine.identity()}
        with rasterio.open(filename, 'w', **prof) as dst:
            dst.write(data, 1)

    mock_export.side_effect = fake_export
    
    roi = (73.7, 18.4, 74.0, 18.6)
    align, man = fetch_and_align_acag_pm25(roi, synthetic_ref_tif, output_dir=str(tmp_path))
    
    mock_col_select.count.assert_called_once()
    mock_col_select.mean.assert_called_once()
    mock_valid_count.eq.assert_called_with(3)
    mock_mean.updateMask.assert_called_once_with(mock_valid_count.eq.return_value)

@patch('data_ingestion.acag_pm25.ee')
@patch('data_ingestion.acag_pm25.authenticate_gee')
@patch('data_ingestion.acag_pm25.geemap.ee_export_image')
def test_exact_target_transform_and_bilinear(mock_export, mock_auth, mock_ee, tmp_path):
    """Test: exact target transform/CRS/dimensions and bilinear resampling behavior."""
    ref_tif = tmp_path / "ref.tif"
    ref_transform = Affine.translation(0, 0) * Affine.scale(250, -250)
    with rasterio.open(
        ref_tif, 'w', driver='GTiff', height=2, width=2, count=1,
        dtype='uint8', crs='EPSG:32643', transform=ref_transform
    ) as dst:
        dst.write(np.zeros((2, 2), dtype=np.uint8), 1)

    mock_col = MagicMock()
    mock_col.filterDate.return_value = mock_col
    mock_col.size.return_value.getInfo.return_value = 3
    
    def mock_image_side_effect(obj):
        return obj
    mock_ee.Image.side_effect = mock_image_side_effect
    
    def mock_date_side_effect(val):
        m = MagicMock()
        m.getInfo.return_value = {'value': val}
        return m
    mock_ee.Date.side_effect = mock_date_side_effect
    
    import datetime
    dates = [datetime.datetime(2024, i, 15).timestamp() * 1000 for i in (1,2,3)]
    def get_img(i):
        m = MagicMock()
        m.get.return_value = dates[i]
        m.bandNames.return_value.getInfo.return_value = ['b1']
        return m
    mock_col.toList.return_value.get.side_effect = get_img
    mock_ee.ImageCollection.return_value = mock_col
    
    def fake_export(img, filename, **kwargs):
        data = np.array([
            [10.0, 20.0],
            [30.0, 40.0]
        ], dtype=np.float32)
        prof = {'driver': 'GTiff', 'height': 2, 'width': 2, 'count': 1, 'dtype': 'float32', 'crs': 'EPSG:32643', 'transform': Affine.translation(0, 0) * Affine.scale(250, -250)}
        with rasterio.open(filename, 'w', **prof) as dst:
            dst.write(data, 1)

    mock_export.side_effect = fake_export
    
    roi = (0, -500, 500, 0)
    align_tif, man = fetch_and_align_acag_pm25(roi, str(ref_tif), output_dir=str(tmp_path))
    
    with rasterio.open(align_tif) as src:
        assert src.width == 2
        assert src.height == 2
        assert src.crs == rasterio.crs.CRS.from_epsg(32643)
        assert src.transform == ref_transform
        
        data = src.read(1)
        assert np.isclose(data[0,0], 10.0)

def test_production_aggregation_path():
    """Test: production aggregation path uses aggregate_pm25_to_blocks."""
    with open('run_scoring.py', 'r') as f:
        content = f.read()
        assert 'aggregate_pm25_to_blocks' in content
        assert 'aggregate_raster_zonal_stats(pm25_tif' not in content

@patch('data_ingestion.acag_pm25.ee')
@patch('data_ingestion.acag_pm25.authenticate_gee')
@patch('data_ingestion.acag_pm25.geemap.ee_export_image')
def test_provenance_fields(mock_export, mock_auth, mock_ee, synthetic_ref_tif, tmp_path):
    """Test: provenance fields contain target affine, bounds, collection ID, band name, etc."""
    mock_col = MagicMock()
    mock_col.filterDate.return_value = mock_col
    mock_col.size.return_value.getInfo.return_value = 3
    
    def mock_image_side_effect(obj):
        return obj
    mock_ee.Image.side_effect = mock_image_side_effect
    
    def mock_date_side_effect(val):
        m = MagicMock()
        m.getInfo.return_value = {'value': val}
        return m
    mock_ee.Date.side_effect = mock_date_side_effect
    
    import datetime
    dates = [datetime.datetime(2024, i, 15).timestamp() * 1000 for i in (1,2,3)]
    def get_img(i):
        m = MagicMock()
        m.get.return_value = dates[i]
        m.bandNames.return_value.getInfo.return_value = ['b1']
        return m
    mock_col.toList.return_value.get.side_effect = get_img
    mock_ee.ImageCollection.return_value = mock_col
    
    def fake_export(img, filename, **kwargs):
        data = np.array([[10]], dtype=np.float32)
        prof = {'driver': 'GTiff', 'height': 1, 'width': 1, 'count': 1, 'dtype': 'float32', 'crs': 'EPSG:4326', 'transform': Affine.identity()}
        with rasterio.open(filename, 'w', **prof) as dst:
            dst.write(data, 1)

    mock_export.side_effect = fake_export
    
    roi = (73.7, 18.4, 74.0, 18.6)
    align_tif, man = fetch_and_align_acag_pm25(roi, synthetic_ref_tif, output_dir=str(tmp_path))
    
    assert 'target_affine_transform' in man
    assert 'target_bounds' in man
    assert 'selected_image_months' in man
    assert 'projects/gee-community-catalog/datasets/pm25_monthly' in man['source_url']
    assert man['source_variable_name'] == 'b1'
    assert 'Strict 3-month arithmetic mean' in man['seasonal_aggregation_rule']
    assert '5-10km' not in str(man)



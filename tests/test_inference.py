import numpy as np
import pytest
import torch

from feature_engineering.predict import _normalise_tile

def test_preprocessing():
    # Create synthetic tile with 5 bands: B, G, R, NDVI, Slope
    tile = np.zeros((5, 10, 10), dtype=np.float32)
    # Band 0: min 100, max 300
    tile[0, ...] = np.linspace(100, 300, 100).reshape(10, 10)
    # NDVI: -1 to 1
    tile[3, ...] = np.linspace(-1.0, 1.0, 100).reshape(10, 10)
    # Slope: 0 to 90
    tile[4, ...] = np.linspace(0.0, 90.0, 100).reshape(10, 10)
    
    norm = _normalise_tile(tile)
    
    # Check band 0 is min-max [0, 1]
    assert np.isclose(norm[0].min(), 0.0)
    assert np.isclose(norm[0].max(), 1.0)
    
    # Check NDVI is (val + 1) / 2
    assert np.isclose(norm[3].min(), 0.0)
    assert np.isclose(norm[3].max(), 1.0)
    assert np.isclose(norm[3, 5, 0], (tile[3, 5, 0] + 1) / 2)
    
    # Check Slope is val / 90
    assert np.isclose(norm[4].min(), 0.0)
    assert np.isclose(norm[4].max(), 1.0)
    assert np.isclose(norm[4, 5, 0], tile[4, 5, 0] / 90.0)

def apply_tta(x, idx):
    # x is (C, H, W)
    if idx == 0: return x
    if idx == 1: return np.flip(x, axis=2) # hflip
    if idx == 2: return np.flip(x, axis=1) # vflip
    if idx == 3: return np.rot90(x, k=1, axes=(1, 2))
    if idx == 4: return np.rot90(x, k=2, axes=(1, 2))
    if idx == 5: return np.rot90(x, k=3, axes=(1, 2))
    if idx == 6: return np.rot90(np.flip(x, axis=2), k=1, axes=(1, 2))
    if idx == 7: return np.rot90(np.flip(x, axis=1), k=1, axes=(1, 2))

def inverse_tta(x, idx):
    # x is (C, H, W)
    if idx == 0: return x
    if idx == 1: return np.flip(x, axis=2) # hflip
    if idx == 2: return np.flip(x, axis=1) # vflip
    if idx == 3: return np.rot90(x, k=-1, axes=(1, 2))
    if idx == 4: return np.rot90(x, k=-2, axes=(1, 2))
    if idx == 5: return np.rot90(x, k=-3, axes=(1, 2))
    if idx == 6: return np.flip(np.rot90(x, k=-1, axes=(1, 2)), axis=2)
    if idx == 7: return np.flip(np.rot90(x, k=-1, axes=(1, 2)), axis=1)

def test_tta():
    # Test that inverse_tta(apply_tta(x)) == x
    np.random.seed(42)
    x = np.random.rand(4, 256, 256).astype(np.float32)
    for i in range(8):
        y = apply_tta(x, i)
        z = inverse_tta(y, i)
        assert np.allclose(x, z), f"Failed TTA {i}"

def test_probability_averaging():
    # 3 models, 8 TTA = 24 maps
    probs = np.random.rand(3, 8, 4, 10, 10).astype(np.float32)
    # average 8 TTA views per model -> average 3 models -> argmax
    avg_tta = probs.mean(axis=1) # (3, 4, 10, 10)
    avg_model = avg_tta.mean(axis=0) # (4, 10, 10)
    argmaxed = avg_model.argmax(axis=0) # (10, 10)
    assert argmaxed.shape == (10, 10)

def test_nodata_tracking():
    # Invalid pixels must not contribute to probability averaging
    # Create mask of 1s (valid) and 0s (invalid)
    valid_mask = np.ones((10, 10), dtype=np.float32)
    valid_mask[0:2, 0:2] = 0 # top left 2x2 is invalid
    
    # 3 models outputting some probability
    prob1 = np.ones((4, 10, 10)) * 0.1
    prob1[0, :, :] = 0.7 # class 0 dominant
    
    # If a pixel is invalid, it should not be counted.
    # Accumulate
    acc_prob = prob1 * valid_mask
    acc_weight = valid_mask.copy()
    
    # Normalize
    acc_weight[acc_weight == 0] = 1 # avoid div by zero
    final_prob = acc_prob / acc_weight
    
    assert final_prob.shape == (4, 10, 10)
    # Invalid pixels might still have 0 probability in the end, which is fine.
    # We will just map them to 255 at argmax time.
    final_class = final_prob.argmax(axis=0)
    final_class[valid_mask == 0] = 255
    assert final_class[0, 0] == 255
    assert final_class[5, 5] == 0

def test_random_fallback_disabled():
    import sys
    from pathlib import Path
    
    # temporarily rename one of the weights to trigger FileNotFoundError
    weight_file = Path("unet_weights_slope_run1.pth")
    if weight_file.exists():
        temp_name = Path("unet_weights_slope_run1.pth.bak")
        weight_file.rename(temp_name)
        
    try:
        from run_inference import run_production_inference
        with pytest.raises(FileNotFoundError, match="Trained weights not found"):
            run_production_inference()
    finally:
        if 'temp_name' in locals() and temp_name.exists():
            temp_name.rename(weight_file)

import time
import psutil
import torch
import numpy as np
import rasterio
from pathlib import Path
import sys

from feature_engineering.unet import UNet, NUM_CLASSES
from run_inference import _normalise_tile, apply_tta, inverse_tta

DEVICE = "cpu"
IN_CHANNELS = 5
PATCH_SIZE = 256

def measure_time(name, func, *args, **kwargs):
    start = time.perf_counter()
    result = func(*args, **kwargs)
    end = time.perf_counter()
    return result, end - start

def load_tile(path):
    with rasterio.open(path) as src:
        image = src.read().astype(np.float32)
    # Just take top-left 256x256
    tile = image[:, :PATCH_SIZE, :PATCH_SIZE]
    if tile.shape[1] < PATCH_SIZE or tile.shape[2] < PATCH_SIZE:
        tile = np.pad(tile, ((0,0), (0, PATCH_SIZE - tile.shape[1]), (0, PATCH_SIZE - tile.shape[2])), mode='reflect')
    return tile

def benchmark_single_tile():
    print("--- 1-TILE BENCHMARK ---")
    tile, t_read = measure_time("read_raster", load_tile, "outputs/unet_validation/kothrud_5channel_input.tif")
    print(f"Read raster: {t_read:.3f} s")
    
    tile_norm, t_norm = measure_time("normalize", _normalise_tile, tile)
    print(f"Normalize: {t_norm:.3f} s")
    
    def make_batch():
        ttas = [apply_tta(tile_norm, i) for i in range(8)]
        return torch.from_numpy(np.stack(ttas)).to(DEVICE)
        
    tensor_8, t_tta = measure_time("tta_batch", make_batch)
    print(f"TTA batching: {t_tta:.3f} s  Shape: {tensor_8.shape}")
    
    models = []
    for i in range(1, 4):
        m_path = f"unet_weights_slope_run{i}.pth"
        model = UNet(in_channels=IN_CHANNELS, num_classes=NUM_CLASSES)
        model.load_state_dict(torch.load(m_path, map_location=DEVICE))
        model.eval()
        models.append(model)
    print("Models loaded.")
    
    for idx, model in enumerate(models):
        print(f"\nEvaluating Model {idx+1}")
        
        # We can test sequential inference
        def run_forward():
            probs_list = []
            with torch.no_grad():
                for i in range(8):
                    # extract shape (1, 5, 256, 256)
                    single_t = tensor_8[i:i+1]
                    logits = model(single_t)
                    probs_list.append(torch.softmax(logits, dim=1).cpu().numpy()[0])
            return probs_list
            
        probs_8, t_fwd = measure_time("forward", run_forward)
        print(f"  Forward pass: {t_fwd:.3f} s")
        
        def run_inverse():
            for i in range(8):
                inverse_tta(probs_8[i], i)
                
        _, t_inv = measure_time("inverse_tta", run_inverse)
        print(f"  Inverse TTA: {t_inv:.3f} s")
        
        mem = psutil.Process().memory_info().rss / (1024 * 1024)
        print(f"  Memory: {mem:.1f} MB")
        
if __name__ == "__main__":
    benchmark_single_tile()

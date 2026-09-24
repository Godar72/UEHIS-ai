import sys
import json
import hashlib
from pathlib import Path
from datetime import datetime

import numpy as np
import rasterio
import torch
from matplotlib.colors import ListedColormap
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))
from feature_engineering.unet import UNet, NUM_CLASSES, CLASS_NAMES
from feature_engineering.predict import _normalise_tile

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

PATCH_SIZE = 256
STRIDE = 128
MARGIN = 96
IN_CHANNELS = 5

def apply_tta(x: np.ndarray, idx: int) -> np.ndarray:
    if idx == 0: return x
    if idx == 1: return np.flip(x, axis=2)
    if idx == 2: return np.flip(x, axis=1)
    if idx == 3: return np.rot90(x, k=1, axes=(1, 2))
    if idx == 4: return np.rot90(x, k=2, axes=(1, 2))
    if idx == 5: return np.rot90(x, k=3, axes=(1, 2))
    if idx == 6: return np.rot90(np.flip(x, axis=2), k=1, axes=(1, 2))
    if idx == 7: return np.rot90(np.flip(x, axis=1), k=1, axes=(1, 2))
    return x

def inverse_tta(x: np.ndarray, idx: int) -> np.ndarray:
    if idx == 0: return x
    if idx == 1: return np.flip(x, axis=2)
    if idx == 2: return np.flip(x, axis=1)
    if idx == 3: return np.rot90(x, k=-1, axes=(1, 2))
    if idx == 4: return np.rot90(x, k=-2, axes=(1, 2))
    if idx == 5: return np.rot90(x, k=-3, axes=(1, 2))
    if idx == 6: return np.flip(np.rot90(x, k=-1, axes=(1, 2)), axis=2)
    if idx == 7: return np.flip(np.rot90(x, k=-1, axes=(1, 2)), axis=1)
    return x

def file_hash(path: Path) -> str:
    if not path.exists(): return "file_not_found"
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

import argparse

def run_production_inference(input_path="kothrud_pune_composite.tif", out_dir="outputs/unet_inference_v2"):
    OUT_DIR = Path(out_dir)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    
    COMPOSITE = Path(input_path)
    SEG_TIF = OUT_DIR / "production_segmentation.tif"
    MANIFEST = OUT_DIR / "inference_manifest.json"
    
    models_paths = [
        Path("unet_weights_slope_run1.pth"),
        Path("unet_weights_slope_run2.pth"),
        Path("unet_weights_slope_run3.pth"),
    ]
    
    manifest = {
        "timestamp": datetime.utcnow().isoformat(),
        "source_raster_path": str(COMPOSITE),
        "source_raster_hash": file_hash(COMPOSITE),
        "model_paths": [str(p) for p in models_paths],
        "model_hashes": [file_hash(p) for p in models_paths],
        "model_architecture_identifier": "UNet",
        "preprocessing_configuration": "Fixed range for NDVI and Slope, per-tile min-max for others",
        "input_channel_order": "B, G, R, NDVI, Slope" if IN_CHANNELS==5 else "B, G, R, NDVI",
        "tile_size": PATCH_SIZE,
        "stride": STRIDE,
        "receptive_field_margin": MARGIN,
        "tta_transformations": 8,
        "ensemble_count": 3,
        "class_mapping": CLASS_NAMES,
        "nodata_value": 255,
        "python_version": sys.version
    }
    
    print(f"\n[Input] {COMPOSITE}")
    with rasterio.open(COMPOSITE) as src:
        profile = src.profile.copy()
        manifest["crs"] = str(src.crs)
        manifest["resolution"] = src.res
        image = src.read().astype(np.float32)
        nodata_val = src.nodata
        if nodata_val is not None:
            nodata_mask = (image[0] == nodata_val)
        else:
            nodata_mask = (image[0] == 0)
            
    if image.shape[0] == 4 and IN_CHANNELS == 5:
        print("[Warning] Input raster has 4 bands. Stacking a dummy 0-slope band to match 5-channel weights.")
        slope_band = np.zeros((1, image.shape[1], image.shape[2]), dtype=np.float32)
        image = np.concatenate([image, slope_band], axis=0)
        
    _, full_h, full_w = image.shape
    print(f"  Size: {full_w}x{full_h}, Bands: {image.shape[0]}")
    
    pad_h = int(np.ceil(max(0, full_h + 2*MARGIN - PATCH_SIZE) / STRIDE) * STRIDE) + PATCH_SIZE
    pad_w = int(np.ceil(max(0, full_w + 2*MARGIN - PATCH_SIZE) / STRIDE) * STRIDE) + PATCH_SIZE
    
    pad_y_after = max(0, pad_h - full_h - MARGIN)
    pad_x_after = max(0, pad_w - full_w - MARGIN)
    
    image_padded = np.pad(image, ((0, 0), (MARGIN, pad_y_after), (MARGIN, pad_x_after)), mode='reflect')
    nodata_mask_padded = np.pad(nodata_mask, ((MARGIN, pad_y_after), (MARGIN, pad_x_after)), mode='constant', constant_values=True)
    
    vote_sum = np.zeros((NUM_CLASSES, full_h, full_w), dtype=np.float64)
    vote_cnt = np.zeros((full_h, full_w), dtype=np.float64)
    
    # Weight window
    window_1d = np.bartlett(PATCH_SIZE)
    window_2d = np.outer(window_1d, window_1d)
    
    models = []
    for model_idx, model_path in enumerate(models_paths):
        print(f"\n[Model {model_idx+1}/3] Loading {model_path}")
        model = UNet(in_channels=IN_CHANNELS, num_classes=NUM_CLASSES).to(DEVICE)
        
        if not model_path.exists():
            raise FileNotFoundError(f"Trained weights not found: {model_path}")
            
        if model_path.stat().st_size < 1000:
            raise ValueError(f"File {model_path} appears to be a Git LFS pointer. Scientific validation requires actual weights.")
            
        try:
            model.load_state_dict(torch.load(model_path, map_location=DEVICE))
            print(f"  Loaded actual weights.")
        except Exception as e:
            raise RuntimeError(f"Failed to load real trained weights from {model_path}: {e}")
            
        model.eval()
        models.append(model)
        
    tiles_coords = []
    for y0 in range(0, pad_h - PATCH_SIZE + 1, STRIDE):
        for x0 in range(0, pad_w - PATCH_SIZE + 1, STRIDE):
            tiles_coords.append((y0, x0))
            
    total_tiles = len(tiles_coords)
    
    ckpt_sum_path = OUT_DIR / "ckpt_vote_sum.npy"
    ckpt_cnt_path = OUT_DIR / "ckpt_vote_cnt.npy"
    ckpt_meta_path = OUT_DIR / "ckpt_meta.json"
    
    completed_tiles = []
    if ckpt_sum_path.exists() and ckpt_cnt_path.exists() and ckpt_meta_path.exists():
        print("[Checkpoint] Found existing checkpoints. Resuming...")
        vote_sum = np.load(ckpt_sum_path)
        vote_cnt = np.load(ckpt_cnt_path)
        with open(ckpt_meta_path, 'r') as f:
            completed_tiles = json.load(f)
            
    import os
    for tile_idx, (y0, x0) in enumerate(tiles_coords):
        if [y0, x0] in completed_tiles:
            # print(f"Skipping tile {tile_idx+1}/{total_tiles} (already completed in checkpoint)")
            continue
            
        print(f"Tile {tile_idx+1}/{total_tiles}")
        
        tile = image_padded[:, y0:y0+PATCH_SIZE, x0:x0+PATCH_SIZE]
        valid_mask = ~nodata_mask_padded[y0:y0+PATCH_SIZE, x0:x0+PATCH_SIZE]
        tile_norm = _normalise_tile(tile)
        
        # Batch 8 TTAs together for efficiency
        tile_ttas = [apply_tta(tile_norm, i) for i in range(8)]
        tensor_8 = torch.from_numpy(np.stack(tile_ttas)).to(DEVICE)
        
        orig_y0, orig_x0 = y0 - MARGIN, x0 - MARGIN
        orig_y1, orig_x1 = orig_y0 + PATCH_SIZE, orig_x0 + PATCH_SIZE
        out_y0, out_y1 = max(0, orig_y0), min(full_h, orig_y1)
        out_x0, out_x1 = max(0, orig_x0), min(full_w, orig_x1)
        
        tile_y0, tile_y1 = out_y0 - orig_y0, out_y0 - orig_y0 + (out_y1 - out_y0)
        tile_x0, tile_x1 = out_x0 - orig_x0, out_x0 - orig_x0 + (out_x1 - out_x0)
        
        if out_y1 <= out_y0 or out_x1 <= out_x0:
            completed_tiles.append([y0, x0])
            continue
            
        valid_region = valid_mask[tile_y0:tile_y1, tile_x0:tile_x1]
        weight_region = window_2d[tile_y0:tile_y1, tile_x0:tile_x1] * valid_region
        
        for model_idx, model in enumerate(models):
            print(f"  Model {model_idx+1}/{len(models)}")
            with torch.inference_mode():
                logits = model(tensor_8)
                probs_8 = torch.softmax(logits, dim=1).cpu().numpy()
                
            for tta_idx in range(8):
                print(f"    TTA {tta_idx+1}/8")
                probs = inverse_tta(probs_8[tta_idx], tta_idx)
                probs_region = probs[:, tile_y0:tile_y1, tile_x0:tile_x1] * weight_region
                
                vote_sum[:, out_y0:out_y1, out_x0:out_x1] += probs_region
                vote_cnt[out_y0:out_y1, out_x0:out_x1] += weight_region
                
        completed_tiles.append([y0, x0])
        
        # Atomic saves
        sum_tmp = ckpt_sum_path.with_suffix('.tmp.npy')
        cnt_tmp = ckpt_cnt_path.with_suffix('.tmp.npy')
        meta_tmp = ckpt_meta_path.with_suffix('.tmp.json')
        
        np.save(sum_tmp, vote_sum)
        np.save(cnt_tmp, vote_cnt)
        with open(meta_tmp, 'w') as f:
            json.dump(completed_tiles, f)
            
        os.replace(sum_tmp, ckpt_sum_path)
        os.replace(cnt_tmp, ckpt_cnt_path)
        os.replace(meta_tmp, ckpt_meta_path)

    print("\n[Inference] Processed all models and TTAs")

    vote_cnt_safe = vote_cnt.copy()
    vote_cnt_safe[vote_cnt_safe == 0] = 1
    avg_probs = vote_sum / vote_cnt_safe[np.newaxis, :, :]
    class_map = avg_probs.argmax(axis=0).astype(np.uint8)
    
    invalid_final = (vote_cnt == 0)
    class_map[invalid_final] = 255
    
    valid_pixel_count = int((~invalid_final).sum())
    total_pixels = class_map.size
    data_completeness_fraction = valid_pixel_count / total_pixels
    
    manifest["valid_pixel_count"] = valid_pixel_count
    manifest["data_completeness_fraction"] = float(data_completeness_fraction)

    print("\n[Result] Class distribution (valid pixels):")
    for cls_id, cls_name in CLASS_NAMES.items():
        count = int((class_map == cls_id).sum())
        pct = 100.0 * count / max(1, valid_pixel_count)
        print(f"  {cls_id} ({cls_name:>11s}): {count:>8,} px  ({pct:5.1f}%)")

    out_profile = profile.copy()
    out_profile.update(
        dtype=rasterio.uint8,
        count=1,
        compress="lzw",
        nodata=255,
    )

    with rasterio.open(SEG_TIF, "w", **out_profile) as dst:
        dst.write(class_map, 1)
        dst.write_colormap(1, {
            0: (34, 139, 34, 255),
            1: (128, 128, 128, 255),
            2: (210, 180, 140, 255),
            255: (0, 0, 0, 0),
        })

    print(f"\n[Output] Classified GeoTIFF: {SEG_TIF.resolve()}")
    
    with open(MANIFEST, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"[Output] Manifest: {MANIFEST.resolve()}")
    
    print("\nDone.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run U-Net Production Inference")
    parser.add_argument("--input", type=str, default="kothrud_pune_composite.tif", help="Path to input composite")
    parser.add_argument("--out_dir", type=str, default="outputs/unet_inference_v2", help="Output directory")
    args = parser.parse_args()
    
    run_production_inference(input_path=args.input, out_dir=args.out_dir)

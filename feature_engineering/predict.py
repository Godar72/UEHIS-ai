"""
feature_engineering/predict.py
──────────────────────────────
Runs sliding-window inference on a full Sentinel-2 composite GeoTIFF
using a trained U-Net and writes the classified output as a GeoTIFF.
"""

import argparse
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_bounds
import torch

from feature_engineering.unet import UNet, NUM_CLASSES, CLASS_NAMES


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalise_tile(tile: np.ndarray) -> np.ndarray:
    """Per-band min-max normalisation to [0, 1] for raw bands, fixed range for NDVI/slope."""
    out = tile.copy().astype(np.float32)
    
    NDVI_BAND_INDEX = 3
    SLOPE_BAND_INDEX = 4
    SLOPE_MAX_DEGREES = 90.0
    
    for b in range(out.shape[0]):
        if b == NDVI_BAND_INDEX:
            out[b] = np.clip((out[b] + 1.0) / 2.0, 0.0, 1.0)
        elif b == SLOPE_BAND_INDEX:
            out[b] = np.clip(out[b] / SLOPE_MAX_DEGREES, 0.0, 1.0)
        else:
            bmin, bmax = out[b].min(), out[b].max()
            if bmax - bmin > 0:
                out[b] = (out[b] - bmin) / (bmax - bmin)
                
    return out


def _pad_to(array: np.ndarray, h: int, w: int) -> np.ndarray:
    """Zero-pad a (C, H', W') array to (C, h, w)."""
    _, h0, w0 = array.shape
    padded = np.zeros((array.shape[0], h, w), dtype=array.dtype)
    padded[:, :h0, :w0] = array
    return padded


# ---------------------------------------------------------------------------
# Inference
# ---------------------------------------------------------------------------

def predict_composite(
    composite_path: str | Path,
    weights_path: str | Path,
    output_path: str = "segmentation.tif",
    patch_size: int = 256,
    stride: int = 256,
    in_channels: int = 4,
    band_indices: list[int] | None = None,
    device: str | None = None,
) -> str:
    """
    Run U-Net inference on a full GeoTIFF composite with a sliding window.

    Parameters
    ----------
    composite_path : str | Path
        Path to the multi-band Sentinel-2 composite GeoTIFF.
    weights_path : str | Path
        Path to the saved U-Net weight file (``.pth``).
    output_path : str
        Destination path for the classified GeoTIFF (uint8, single-band).
    patch_size : int
        Tile dimension for inference (must match training patch size).
    stride : int
        Step size between tiles.  Use ``stride < patch_size`` for overlap
        (predictions are averaged in overlapping regions).
    in_channels : int
        Number of input bands the model expects.
    band_indices : list[int] | None
        1-based rasterio band indices to read.  ``None`` reads the first
        *in_channels* bands.
    device : str | None
        ``"cuda"``, ``"cpu"``, or ``None`` for auto-detect.

    Returns
    -------
    str
        Absolute path to the output classified GeoTIFF.
    """
    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"

    # ── Load model ──────────────────────────────────────────────────────
    model = UNet(in_channels=in_channels, num_classes=NUM_CLASSES).to(device)
    model.load_state_dict(torch.load(weights_path, map_location=device))
    model.eval()
    print(f"[Predict] Model loaded from {weights_path} (device={device})")

    # ── Read composite ──────────────────────────────────────────────────
    with rasterio.open(composite_path) as src:
        profile = src.profile.copy()
        transform = src.transform
        crs = src.crs

        if band_indices is None:
            band_indices = list(range(1, in_channels + 1))
        image = src.read(band_indices).astype(np.float32)  # (C, H, W)

    _, full_h, full_w = image.shape
    print(f"[Predict] Composite size: {full_w}×{full_h}, bands: {band_indices}")

    # Accumulator for soft votes (class probabilities)
    vote_sum = np.zeros((NUM_CLASSES, full_h, full_w), dtype=np.float64)
    vote_cnt = np.zeros((full_h, full_w), dtype=np.float64)

    # ── Sliding window ──────────────────────────────────────────────────
    with torch.no_grad():
        for y0 in range(0, full_h, stride):
            for x0 in range(0, full_w, stride):
                y1 = min(y0 + patch_size, full_h)
                x1 = min(x0 + patch_size, full_w)

                tile = image[:, y0:y1, x0:x1]
                tile = _normalise_tile(tile)

                # Pad if tile is smaller than patch_size
                th, tw = tile.shape[1], tile.shape[2]
                if th < patch_size or tw < patch_size:
                    tile = _pad_to(tile, patch_size, patch_size)

                tensor = torch.from_numpy(tile).unsqueeze(0).to(device)
                logits = model(tensor)  # (1, C, ps, ps)
                probs = torch.softmax(logits, dim=1).cpu().numpy()[0]

                # Crop back to actual tile size and accumulate
                probs = probs[:, :th, :tw]
                vote_sum[:, y0:y1, x0:x1] += probs
                vote_cnt[y0:y1, x0:x1] += 1.0

    # Argmax over averaged probabilities
    vote_cnt[vote_cnt == 0] = 1  # avoid divide-by-zero
    avg_probs = vote_sum / vote_cnt[np.newaxis, :, :]
    class_map = avg_probs.argmax(axis=0).astype(np.uint8)

    # ── Write output GeoTIFF ────────────────────────────────────────────
    out_profile = profile.copy()
    out_profile.update(
        dtype=rasterio.uint8,
        count=1,
        compress="lzw",
        nodata=255,
    )

    with rasterio.open(output_path, "w", **out_profile) as dst:
        dst.write(class_map, 1)
        # Attach class colour map for easy visualisation
        dst.write_colormap(1, {
            0: (34, 139, 34, 255),    # canopy    → forest green
            1: (128, 128, 128, 255),  # impervious → grey
            2: (210, 180, 140, 255),  # pervious  → tan
            255: (0, 0, 0, 0),        # nodata    → transparent
        })

    abs_path = str(Path(output_path).resolve())
    print(f"[Predict] Classification saved to {abs_path}")
    print(f"[Predict] Classes: {CLASS_NAMES}")
    return abs_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run U-Net segmentation on a composite")
    parser.add_argument("composite", help="Path to the input GeoTIFF composite")
    parser.add_argument("weights", help="Path to trained .pth weights")
    parser.add_argument("--output", default="segmentation.tif")
    parser.add_argument("--patch-size", type=int, default=256)
    parser.add_argument("--stride", type=int, default=256)
    parser.add_argument("--in-channels", type=int, default=4)
    parser.add_argument("--device", default=None)
    args = parser.parse_args()

    predict_composite(
        composite_path=args.composite,
        weights_path=args.weights,
        output_path=args.output,
        patch_size=args.patch_size,
        stride=args.stride,
        in_channels=args.in_channels,
        device=args.device,
    )

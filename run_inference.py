"""
Run U-Net inference on the Kothrud composite with randomly-initialised
weights (no pretrained checkpoint available yet).

Outputs
-------
- outputs/kothrud_segmentation.tif  -- single-band uint8 class map
- outputs/kothrud_segmentation.png  -- side-by-side RGB + classification
"""

import sys
from pathlib import Path

import numpy as np
import rasterio
import torch
import matplotlib
matplotlib.use("Agg")  # headless backend
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch

# ── project imports ──────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parent))
from feature_engineering.unet import UNet, NUM_CLASSES, CLASS_NAMES
from feature_engineering.predict import _normalise_tile, _pad_to

# ── paths ────────────────────────────────────────────────────────────────
COMPOSITE = Path("kothrud_pune_composite.tif")
OUT_DIR   = Path("outputs")
SEG_TIF   = OUT_DIR / "kothrud_segmentation.tif"
SEG_PNG   = OUT_DIR / "kothrud_segmentation.png"

PATCH_SIZE = 256
STRIDE     = 256
IN_CHANNELS = 4
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# ── colour scheme ────────────────────────────────────────────────────────
CLASS_COLOURS = {
    0: (34, 139, 34),      # canopy      -> forest green
    1: (128, 128, 128),    # impervious  -> grey
    2: (210, 180, 140),    # pervious    -> tan
}


def run_inference():
    """Run sliding-window U-Net inference (random weights)."""

    # ── 1. Initialise model (random weights) ─────────────────────────────
    model = UNet(in_channels=IN_CHANNELS, num_classes=NUM_CLASSES).to(DEVICE)
    model.eval()
    total_params = sum(p.numel() for p in model.parameters())
    print(f"[Model] UNet initialised with random weights ({total_params:,} params, device={DEVICE})")
    print(f"[Model] Input channels: {IN_CHANNELS}, Output classes: {NUM_CLASSES}")
    print(f"[Model] Classes: {CLASS_NAMES}")

    # ── 2. Read composite ────────────────────────────────────────────────
    with rasterio.open(COMPOSITE) as src:
        profile = src.profile.copy()
        image = src.read().astype(np.float32)  # (C, H, W)
        crs = src.crs
        transform = src.transform

    _, full_h, full_w = image.shape
    print(f"\n[Input] {COMPOSITE} : {image.shape[0]} bands, {full_w}x{full_h} px")
    for b in range(image.shape[0]):
        print(f"  Band {b+1}: min={image[b].min():.2f}, max={image[b].max():.2f}")

    # ── 3. Sliding-window inference ──────────────────────────────────────
    vote_sum = np.zeros((NUM_CLASSES, full_h, full_w), dtype=np.float64)
    vote_cnt = np.zeros((full_h, full_w), dtype=np.float64)

    n_patches = 0
    with torch.no_grad():
        for y0 in range(0, full_h, STRIDE):
            for x0 in range(0, full_w, STRIDE):
                y1 = min(y0 + PATCH_SIZE, full_h)
                x1 = min(x0 + PATCH_SIZE, full_w)

                tile = image[:, y0:y1, x0:x1]
                tile = _normalise_tile(tile)

                th, tw = tile.shape[1], tile.shape[2]
                if th < PATCH_SIZE or tw < PATCH_SIZE:
                    tile = _pad_to(tile, PATCH_SIZE, PATCH_SIZE)

                tensor = torch.from_numpy(tile).unsqueeze(0).to(DEVICE)
                logits = model(tensor)
                probs = torch.softmax(logits, dim=1).cpu().numpy()[0]

                probs = probs[:, :th, :tw]
                vote_sum[:, y0:y1, x0:x1] += probs
                vote_cnt[y0:y1, x0:x1] += 1.0
                n_patches += 1

    print(f"\n[Inference] Processed {n_patches} patches ({PATCH_SIZE}x{PATCH_SIZE}, stride={STRIDE})")

    # Argmax
    vote_cnt[vote_cnt == 0] = 1
    avg_probs = vote_sum / vote_cnt[np.newaxis, :, :]
    class_map = avg_probs.argmax(axis=0).astype(np.uint8)

    # Class distribution
    print("\n[Result] Class distribution:")
    for cls_id, cls_name in CLASS_NAMES.items():
        count = int((class_map == cls_id).sum())
        pct = 100.0 * count / class_map.size
        print(f"  {cls_id} ({cls_name:>11s}): {count:>8,} px  ({pct:5.1f}%)")

    # ── 4. Save classified GeoTIFF ───────────────────────────────────────
    out_profile = profile.copy()
    out_profile.update(
        dtype=rasterio.uint8,
        count=1,
        compress="lzw",
        nodata=255,
    )

    OUT_DIR.mkdir(exist_ok=True)
    with rasterio.open(SEG_TIF, "w", **out_profile) as dst:
        dst.write(class_map, 1)
        dst.write_colormap(1, {
            0: (34, 139, 34, 255),
            1: (128, 128, 128, 255),
            2: (210, 180, 140, 255),
            255: (0, 0, 0, 0),
        })

    print(f"\n[Output] Classified GeoTIFF: {SEG_TIF.resolve()}")

    # ── 5. Save PNG visualisation ────────────────────────────────────────
    # Build RGB from bands 1-3 (B4=Red, B3=Green, B2=Blue)
    rgb = np.stack([image[0], image[1], image[2]], axis=-1)  # (H, W, 3)
    # Clip and normalise to 0-1 for display (typical S2 SR range ~0-3000)
    rgb = np.clip(rgb / 3000.0, 0, 1)

    # Build coloured class map
    colour_map = np.zeros((full_h, full_w, 3), dtype=np.float32)
    for cls_id, colour in CLASS_COLOURS.items():
        mask = class_map == cls_id
        colour_map[mask] = [c / 255.0 for c in colour]

    fig, axes = plt.subplots(1, 2, figsize=(16, 8), dpi=120)

    axes[0].imshow(rgb)
    axes[0].set_title("Sentinel-2 RGB (Kothrud, Pune)", fontsize=13)
    axes[0].axis("off")

    axes[1].imshow(colour_map)
    axes[1].set_title("U-Net Classification (random weights)", fontsize=13)
    axes[1].axis("off")

    # Legend
    legend_patches = [
        Patch(facecolor=[c / 255 for c in CLASS_COLOURS[k]], label=f"{k}: {v}")
        for k, v in CLASS_NAMES.items()
    ]
    axes[1].legend(handles=legend_patches, loc="lower right", fontsize=10,
                   framealpha=0.8, edgecolor="gray")

    plt.suptitle("Kothrud, Pune -- Land Cover Segmentation", fontsize=15, y=0.98)
    plt.tight_layout()
    plt.savefig(SEG_PNG, bbox_inches="tight", pad_inches=0.1)
    plt.close()

    print(f"[Output] Visualisation PNG: {SEG_PNG.resolve()}")
    print("\nDone.")


if __name__ == "__main__":
    run_inference()

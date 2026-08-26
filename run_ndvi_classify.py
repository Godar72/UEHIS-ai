"""
Run the NDVI threshold classifier on the Kothrud composite and
produce a classified GeoTIFF + side-by-side PNG visualisation.
"""

import sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from feature_engineering.ndvi_classifier import classify_ndvi, CLASS_COLOURS
from feature_engineering.unet import CLASS_NAMES

# ── paths ────────────────────────────────────────────────────────────────
COMPOSITE = Path("kothrud_pune_composite.tif")
OUT_DIR   = Path("outputs")
SEG_TIF   = OUT_DIR / "kothrud_ndvi_segmentation.tif"
SEG_PNG   = OUT_DIR / "kothrud_ndvi_segmentation.png"


def main():
    # ── 1. Run classifier ────────────────────────────────────────────────
    class_map, all_bands, stats = classify_ndvi(
        composite_path=COMPOSITE,
        output_path=SEG_TIF,
    )

    full_h, full_w = class_map.shape

    # ── 2. Build RGB from bands 1-3 (B4=Red, B3=Green, B2=Blue) ─────────
    rgb = np.stack([all_bands[0], all_bands[1], all_bands[2]], axis=-1)
    rgb = np.clip(rgb / 3000.0, 0, 1)

    # ── 3. Build NDVI false-colour ───────────────────────────────────────
    ndvi = all_bands[3]  # band 4 = NDVI

    # ── 4. Build coloured class map ──────────────────────────────────────
    colour_map = np.zeros((full_h, full_w, 3), dtype=np.float32)
    for cls_id, colour in CLASS_COLOURS.items():
        mask = class_map == cls_id
        colour_map[mask] = [c / 255.0 for c in colour]

    # ── 5. Create 3-panel visualisation ──────────────────────────────────
    fig, axes = plt.subplots(1, 3, figsize=(22, 8), dpi=120)

    # Panel 1: RGB
    axes[0].imshow(rgb)
    axes[0].set_title("Sentinel-2 RGB", fontsize=13)
    axes[0].axis("off")

    # Panel 2: NDVI heatmap
    im = axes[1].imshow(ndvi, cmap="RdYlGn", vmin=-0.1, vmax=0.8)
    axes[1].set_title("NDVI", fontsize=13)
    axes[1].axis("off")
    cbar = plt.colorbar(im, ax=axes[1], fraction=0.046, pad=0.04)
    cbar.set_label("NDVI value", fontsize=10)
    # Draw threshold lines on the colorbar
    cbar.ax.axhline(y=0.35, color="green", linewidth=1.5, linestyle="--")
    cbar.ax.axhline(y=0.10, color="red", linewidth=1.5, linestyle="--")

    # Panel 3: Classification
    axes[2].imshow(colour_map)
    axes[2].set_title("NDVI Threshold Classification", fontsize=13)
    axes[2].axis("off")

    legend_patches = [
        Patch(facecolor=[c / 255 for c in CLASS_COLOURS[k]],
              edgecolor="black", linewidth=0.5,
              label=f"{k}: {v} ({stats[v]['pct']:.1f}%)")
        for k, v in CLASS_NAMES.items()
    ]
    axes[2].legend(handles=legend_patches, loc="lower right", fontsize=10,
                   framealpha=0.9, edgecolor="gray")

    plt.suptitle("Kothrud, Pune -- NDVI Threshold Land Cover Classification",
                 fontsize=15, y=0.98)
    plt.tight_layout()
    plt.savefig(SEG_PNG, bbox_inches="tight", pad_inches=0.1)
    plt.close()

    print(f"[Output] Visualisation PNG: {SEG_PNG.resolve()}")
    print("\nDone.")


if __name__ == "__main__":
    main()

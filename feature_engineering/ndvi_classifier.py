"""
feature_engineering/ndvi_classifier.py
──────────────────────────────────────
Fallback land-cover classifier using simple NDVI thresholds.
Used when no trained U-Net checkpoint is available.

Classes
-------
0 = canopy          (NDVI >= 0.35)
1 = impervious      (NDVI <  0.10)
2 = pervious        (0.10 <= NDVI < 0.35)
"""

from pathlib import Path

import numpy as np
import rasterio

from feature_engineering.unet import CLASS_NAMES, NUM_CLASSES


# ---------------------------------------------------------------------------
# Default thresholds
# ---------------------------------------------------------------------------

NDVI_CANOPY_MIN = 0.35      # NDVI >= this  -> canopy
NDVI_IMPERVIOUS_MAX = 0.10  # NDVI <  this  -> impervious
                            # everything else -> pervious

# Colour scheme (matches predict.py)
CLASS_COLOURS = {
    0: (34, 139, 34),      # canopy      -> forest green
    1: (128, 128, 128),    # impervious  -> grey
    2: (210, 180, 140),    # pervious    -> tan
}


# ---------------------------------------------------------------------------
# Classifier
# ---------------------------------------------------------------------------

def classify_ndvi(
    composite_path: str | Path,
    output_path: str | Path = "ndvi_segmentation.tif",
    ndvi_band: int = 4,
    canopy_min: float = NDVI_CANOPY_MIN,
    impervious_max: float = NDVI_IMPERVIOUS_MAX,
) -> tuple[np.ndarray, dict]:
    """
    Classify a Sentinel-2 composite using NDVI thresholds.

    Parameters
    ----------
    composite_path : str | Path
        Path to the multi-band GeoTIFF (must include an NDVI band).
    output_path : str | Path
        Destination for the classified GeoTIFF (uint8, single-band).
    ndvi_band : int
        1-based band index for the NDVI channel (default 4).
    canopy_min : float
        NDVI >= this value is classified as canopy.
    impervious_max : float
        NDVI < this value is classified as impervious.

    Returns
    -------
    class_map : np.ndarray
        (H, W) uint8 array of class labels.
    stats : dict
        Per-class pixel counts and percentages.
    """
    composite_path = Path(composite_path)
    output_path = Path(output_path)

    # ── Read NDVI band ───────────────────────────────────────────────────
    with rasterio.open(composite_path) as src:
        profile = src.profile.copy()
        ndvi = src.read(ndvi_band).astype(np.float32)  # (H, W)
        all_bands = src.read().astype(np.float32)       # (C, H, W)

    h, w = ndvi.shape
    print(f"[NDVI Classifier] Input: {composite_path.name} ({w}x{h})")
    print(f"[NDVI Classifier] NDVI band {ndvi_band}: "
          f"min={ndvi.min():.4f}, max={ndvi.max():.4f}, mean={ndvi.mean():.4f}")
    print(f"[NDVI Classifier] Thresholds: canopy >= {canopy_min}, "
          f"impervious < {impervious_max}")

    # ── Apply thresholds ─────────────────────────────────────────────────
    class_map = np.full((h, w), 2, dtype=np.uint8)  # default = pervious
    class_map[ndvi >= canopy_min] = 0                # canopy
    class_map[ndvi < impervious_max] = 1             # impervious

    # ── Stats ────────────────────────────────────────────────────────────
    total = class_map.size
    stats = {}
    print("\n[NDVI Classifier] Class distribution:")
    for cls_id, cls_name in CLASS_NAMES.items():
        count = int((class_map == cls_id).sum())
        pct = 100.0 * count / total
        stats[cls_name] = {"count": count, "pct": pct}
        print(f"  {cls_id} ({cls_name:>11s}): {count:>8,} px  ({pct:5.1f}%)")

    # ── Write classified GeoTIFF ─────────────────────────────────────────
    out_profile = profile.copy()
    out_profile.update(
        dtype=rasterio.uint8,
        count=1,
        compress="lzw",
        nodata=255,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(output_path, "w", **out_profile) as dst:
        dst.write(class_map, 1)
        dst.write_colormap(1, {
            0: (34, 139, 34, 255),     # canopy
            1: (128, 128, 128, 255),   # impervious
            2: (210, 180, 140, 255),   # pervious
            255: (0, 0, 0, 0),         # nodata
        })

    print(f"\n[Output] Classified GeoTIFF: {output_path.resolve()}")
    return class_map, all_bands, stats

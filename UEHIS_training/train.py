"""
feature_engineering/train.py
────────────────────────────
Training script for the U-Net segmentation model.

Expected data layout
--------------------
Instead of a single directory that gets randomly split, this script now
expects three SEPARATE directories, each already geographically split
(see data_ingestion/spatial_split.py) so that train/val/test patches
never overlap or sit adjacent to one another:

<train_dir>/
├── images/          # multi-band GeoTIFF patches  (e.g. 256×256, 4 bands)
│   ├── patch_1280_256.tif
│   └── ...
└── masks/           # single-band uint8 GeoTIFFs
    ├── patch_1280_256.tif  # raw class IDs: 0=nodata, 1=canopy, 2=impervious, 3=pervious, 4=water
    └── ...

<val_dir>/   (same images/ + masks/ layout)
<test_dir>/  (same images/ + masks/ layout)

Image and mask filenames must match within each directory.

Note: raw mask values (0-4) are remapped internally to contiguous
0-indexed classes (canopy=0, impervious=1, pervious=2, water=3), with
nodata (raw 0) mapped to ignore_index=255 so it's excluded from loss
and accuracy calculations entirely.
"""

import os
import argparse
from pathlib import Path

import numpy as np
import rasterio
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader

from feature_engineering.unet import UNet, NUM_CLASSES


# ---------------------------------------------------------------------------
# Label remapping
# ---------------------------------------------------------------------------

# Raw label values in the exported GeoTIFFs -> contiguous training classes.
# Raw 0 (nodata) is mapped to IGNORE_INDEX so it never contributes to loss
# or accuracy — it is not a real land-cover class.
IGNORE_INDEX = 255
RAW_TO_TRAIN = {0: IGNORE_INDEX, 1: 0, 2: 1, 3: 2, 4: 3}

# Patches manually, visually confirmed (via RGB + NDVI + satellite
# cross-check) to have large urban blocks mislabeled as canopy — likely
# from the Dynamic World auto-labeling source struggling with urban tree
# cover. Unlike an automatic NDVI-threshold rule (tried and reverted — it
# also stripped out valid, low-NDVI hillside canopy), this list only
# excludes patches a human actually looked at and confirmed are wrong,
# so it can't accidentally remove genuinely hard-but-real examples.
EXCLUDED_PATCHES = {
    "patch_1152_1472.tif",
    "patch_1024_1472.tif",
    "patch_896_1408.tif",
}


def remap_mask(mask: np.ndarray) -> np.ndarray:
    """Remap raw exported label values to contiguous training class IDs."""
    remapped = np.full_like(mask, IGNORE_INDEX)
    for raw_val, train_val in RAW_TO_TRAIN.items():
        remapped[mask == raw_val] = train_val
    return remapped


# ---------------------------------------------------------------------------
# Dataset
# ---------------------------------------------------------------------------

class PatchDataset(Dataset):
    """
    Loads paired image/mask GeoTIFF patches from disk.

    Parameters
    ----------
    images_dir : str | Path
        Directory of multi-band GeoTIFF image patches.
    masks_dir : str | Path
        Directory of single-band uint8 mask patches (raw class IDs).
    """

    def __init__(
        self,
        images_dir: str | Path,
        masks_dir: str | Path,
        augment: bool = False,
        clean_labels: bool = False,
        canopy_ndvi_floor: float = 0.30,
        slope_dir: str | Path | None = None,
    ):
        self.images_dir = Path(images_dir)
        self.masks_dir = Path(masks_dir)
        # slope_dir: optional directory of single-band slope GeoTIFFs, one
        # per patch filename, matching images_dir exactly in bounds/shape
        # (see data_ingestion — generated from SRTM elevation via Earth
        # Engine). When given, slope is stacked as a 5th input band,
        # giving the model terrain information NDVI alone cannot provide
        # — useful for telling apart tree cover and bare/scrub ground that
        # sit differently on a hillside despite similar NDVI.
        self.slope_dir = Path(slope_dir) if slope_dir is not None else None
        # augment=True randomly flips/rotates each patch (image+mask together,
        # so they stay aligned) every time it's loaded. This is only meant
        # for the training set — it artificially increases variety seen by
        # the model, which helps a lot when train data is limited (a few
        # hundred patches), and reduces overfitting. Never set this True
        # for val/test — those must stay exactly as-is for honest metrics.
        self.augment = augment
        # clean_labels=True catches likely-WRONG canopy labels: pixels the
        # mask calls canopy, but whose actual NDVI value is too low to be
        # real dense vegetation (found via manual spot-checking — several
        # patches had large urban blocks mislabeled as canopy, likely from
        # the Dynamic World auto-labeling source). Those specific pixels
        # are excluded from the loss (treated like nodata) rather than
        # trusted, since forcing the model to match a wrong label just
        # teaches it the wrong thing. canopy_ndvi_floor=0.30 is below the
        # dataset's measured canopy mean (~0.475) but above pervious's
        # mean (~0.214), so it only strips out clear mismatches, not
        # genuinely ambiguous hillside cases sitting in between.
        self.clean_labels = clean_labels
        self.canopy_ndvi_floor = canopy_ndvi_floor

        self.filenames = sorted([
            f.name for f in self.images_dir.glob("*.tif")
            if (self.masks_dir / f.name).exists()
            and f.name not in EXCLUDED_PATCHES
        ])
        if not self.filenames:
            raise FileNotFoundError(
                f"No matching image/mask pairs found in "
                f"{self.images_dir} and {self.masks_dir}."
            )

    def __len__(self) -> int:
        return len(self.filenames)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, torch.Tensor]:
        name = self.filenames[idx]

        # Read image — shape (bands, H, W), float32
        with rasterio.open(self.images_dir / name) as src:
            image = src.read().astype(np.float32)
        # Clean any NaN/Inf pixels (from areas outside the clipped
        # Pune boundary that fall inside the rectangular exported .tif)
        image = np.nan_to_num(image, nan=0.0, posinf=0.0, neginf=0.0)

        if self.slope_dir is not None:
            # Stack slope as a 5th band. Its file has the exact same
            # bounds/shape as the image patch (verified at generation
            # time), so it lines up pixel-for-pixel with no extra work.
            with rasterio.open(self.slope_dir / name) as src:
                slope = src.read(1).astype(np.float32)
            slope = np.nan_to_num(slope, nan=0.0, posinf=0.0, neginf=0.0)
            image = np.concatenate([image, slope[np.newaxis, :, :]], axis=0)

        # Read mask — shape (H, W), raw class IDs (0-4)
        with rasterio.open(self.masks_dir / name) as src:
            mask = src.read(1).astype(np.int64)

        # Remap raw values (0=nodata,1=canopy,2=impervious,3=pervious,4=water)
        # to contiguous training classes (canopy=0,impervious=1,pervious=2,
        # water=3), with nodata sent to IGNORE_INDEX.
        mask = remap_mask(mask)

        if self.clean_labels:
            # Catch likely-mislabeled canopy pixels: label says canopy, but
            # the actual (raw, un-normalized) NDVI value is too low to be
            # real dense vegetation. These get excluded from the loss
            # entirely (same treatment as nodata) rather than trusted.
            raw_ndvi = image[3]  # NDVI band, still in its original -1..1 scale here
            labeled_canopy = mask == 0  # canopy = training class 0
            likely_mislabeled = labeled_canopy & (raw_ndvi < self.canopy_ndvi_floor)
            mask[likely_mislabeled] = IGNORE_INDEX

        # Simple normalisation: per-band min-max to [0, 1]
        # NOTE: band 4 (index 3) is NDVI, band 5 (index 4, if present) is
        # slope. Both have a fixed, meaningful real-world scale, so both
        # are normalized using their fixed theoretical range rather than
        # each patch's own min/max — the same reasoning as NDVI: a per-
        # patch rescale would make the same real slope value (e.g. 15
        # degrees) map to different numbers in different patches,
        # destroying the signal.
        NDVI_BAND_INDEX = 3
        SLOPE_BAND_INDEX = 4
        SLOPE_MAX_DEGREES = 90.0
        for b in range(image.shape[0]):
            band = image[b]
            if b == NDVI_BAND_INDEX:
                # Fixed range normalisation: -1..1 -> 0..1
                image[b] = np.clip((band + 1.0) / 2.0, 0.0, 1.0)
            elif b == SLOPE_BAND_INDEX:
                # Fixed range normalisation: 0..90 degrees -> 0..1
                image[b] = np.clip(band / SLOPE_MAX_DEGREES, 0.0, 1.0)
            else:
                bmin, bmax = band.min(), band.max()
                if bmax - bmin > 0:
                    image[b] = (band - bmin) / (bmax - bmin)

        if self.augment:
            # Randomly apply a horizontal flip, a vertical flip, and a
            # 90-degree rotation (each independently, 50/50 chance), always
            # applying the SAME transform to image and mask together so
            # they stay pixel-aligned. This is a cheap way to multiply the
            # effective variety of a small training set.
            if np.random.rand() < 0.5:
                image = np.flip(image, axis=2).copy()  # horizontal flip (W axis)
                mask = np.flip(mask, axis=1).copy()
            if np.random.rand() < 0.5:
                image = np.flip(image, axis=1).copy()  # vertical flip (H axis)
                mask = np.flip(mask, axis=0).copy()
            if np.random.rand() < 0.5:
                k = np.random.choice([1, 2, 3])  # rotate 90/180/270 degrees
                image = np.rot90(image, k=k, axes=(1, 2)).copy()
                mask = np.rot90(mask, k=k, axes=(0, 1)).copy()

            # Brightness/contrast jitter — RGB bands (0-2) ONLY. NDVI (band
            # 3) is deliberately left untouched: it has a fixed physical
            # meaning (real vegetation signal), so jittering it would
            # corrupt real information rather than add useful variety.
            # This teaches the model to be robust to real-world lighting/
            # atmospheric variation across different satellite captures.
            if np.random.rand() < 0.5:
                brightness = np.random.uniform(0.85, 1.15)
                image[:3] = np.clip(image[:3] * brightness, 0.0, 1.0)
            if np.random.rand() < 0.5:
                contrast = np.random.uniform(0.85, 1.15)
                mean = image[:3].mean(axis=(1, 2), keepdims=True)
                image[:3] = np.clip((image[:3] - mean) * contrast + mean, 0.0, 1.0)

        return torch.from_numpy(image), torch.from_numpy(mask)


# ---------------------------------------------------------------------------
# Class weights (computed from actual pixel counts across the dataset)
# ---------------------------------------------------------------------------

def compute_class_weights(class_pixel_counts: dict[int, int], device: str) -> torch.Tensor:
    """
    Square-root inverse-frequency class weights, ordered by training class
    index (0=canopy, 1=impervious, 2=pervious, 3=water).

    Plain inverse frequency (total / (n_classes * count)) can produce very
    extreme weights for rare classes (e.g. water, which is a small fraction
    of total pixels) — this pushes the loss to favor guessing that class
    aggressively, which can destabilise training and cause the model to
    over-predict it everywhere (high recall, poor precision). Taking the
    square root keeps rare classes up-weighted, but far less extremely,
    which tends to train more stably.

    Parameters
    ----------
    class_pixel_counts : dict[int, int]
        Mapping of training class index -> total pixel count across the dataset.
    device : str
        Device to place the resulting tensor on.
    """
    counts = torch.tensor(
        [class_pixel_counts[i] for i in range(len(class_pixel_counts))],
        dtype=torch.float32,
    )
    raw_weights = counts.sum() / (len(counts) * counts)
    weights = torch.sqrt(raw_weights)
    return weights.to(device)


# ---------------------------------------------------------------------------
# Training loop
# ---------------------------------------------------------------------------

def train_model(
    train_dir: str | Path,
    val_dir: str | Path,
    test_dir: str | Path,
    output_path: str = "unet_weights.pth",
    in_channels: int = 4,
    use_slope: bool = False,
    epochs: int = 50,
    batch_size: int = 8,
    lr: float = 1e-3,
    weight_decay: float = 1e-4,
    early_stopping_patience: int = 20,
    min_epochs: int = 20,
    device: str | None = None,
) -> None:
    """
    Train the U-Net on labeled patches and save the best weights.

    Parameters
    ----------
    train_dir : str | Path
        Directory containing ``images/`` and ``masks/`` subdirectories for
        the training split (geographically separated — see
        data_ingestion/spatial_split.py).
    val_dir : str | Path
        Directory containing ``images/`` and ``masks/`` subdirectories for
        the validation split.
    test_dir : str | Path
        Directory containing ``images/`` and ``masks/`` subdirectories for
        the held-out test split. Not used during training — this script
        just reports its size so you know it's wired up correctly. Run a
        separate evaluation pass on it after training is finished.
    output_path : str
        Path to save the best model weights.
    in_channels : int
        Number of input bands in the image patches.
    epochs : int
        Total training epochs.
    batch_size : int
        Mini-batch size.
    lr : float
        Learning rate for Adam optimiser.
    weight_decay : float
        L2 regularisation strength for the Adam optimiser. Small values
        (1e-4 to 1e-5) discourage the model from fitting training noise,
        which helps when the training set is small.
    early_stopping_patience : int
        Number of consecutive epochs allowed with no val_loss improvement
        before training stops automatically. Prevents wasting time/compute
        training past the point where the model stops generalising better.
    min_epochs : int
        Early stopping cannot trigger before this many epochs have run,
        regardless of patience. Protects against stopping on an early,
        possibly-lucky checkpoint before the model has had a fair chance
        to stabilise (especially relevant with heavily weighted rare
        classes, which can cause noisy early-epoch behaviour).
    device : str | None
        ``"cuda"``, ``"cpu"``, or ``None`` for auto-detect.
    """
    train_dir = Path(train_dir)
    val_dir = Path(val_dir)
    test_dir = Path(test_dir)

    if use_slope and in_channels == 4:
        # Auto-bump to 5 channels so the model architecture matches the
        # actual stacked input — avoids a silent shape mismatch if the
        # caller forgets to update in_channels when turning slope on.
        in_channels = 5
    print(f"[Train] use_slope={use_slope}, in_channels={in_channels}")

    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[Train] Device: {device}")

    # ── Data ────────────────────────────────────────────────────────────
    # Each split lives in its own directory, already geographically
    # separated (with buffer gaps) so there is zero spatial overlap
    # between train, val, and test patches. See data_ingestion/spatial_split.py.
    # augment=True only for train — val/test must reflect real, unmodified
    # data so metrics stay honest and comparable across runs.
    # clean_labels=False: TRIED and REVERTED. A simple NDVI-threshold rule
    # (flag canopy-labeled pixels with NDVI < 0.30 as mislabeled) was tested
    # and made canopy performance significantly WORSE (IoU dropped from
    # ~59% to ~40%). Reason: canopy's real NDVI naturally ranges down to
    # ~0.27 at its 10th percentile, so the threshold stripped out a lot of
    # genuinely valid, low-NDVI, harder canopy examples (e.g. sparse
    # hillside canopy) along with the intended urban mislabels — teaching
    # the model an artificially narrow definition of canopy. A single NDVI
    # cutoff can't separate "mislabeled" from "genuinely sparse but real"
    # — that would need per-patch manual review, not a threshold rule.
    # use_slope=True stacks a 5th input band (terrain slope, degrees,
    # from SRTM elevation data) alongside the existing 4 bands. Requires
    # a slope/ subfolder inside each of train_dir/val_dir/test_dir,
    # matching images/ in filenames and exact geographic bounds (see
    # data_ingestion — generated once via Earth Engine, not regenerated
    # per training run).
    slope_kwargs = {"slope_dir": train_dir / "slope"} if use_slope else {}
    train_ds = PatchDataset(train_dir / "images", train_dir / "masks", augment=True, clean_labels=False, **slope_kwargs)
    slope_kwargs = {"slope_dir": val_dir / "slope"} if use_slope else {}
    val_ds = PatchDataset(val_dir / "images", val_dir / "masks", augment=False, clean_labels=False, **slope_kwargs)
    slope_kwargs = {"slope_dir": test_dir / "slope"} if use_slope else {}
    test_ds = PatchDataset(test_dir / "images", test_dir / "masks", augment=False, clean_labels=False, **slope_kwargs)

    n_train, n_val, n_test = len(train_ds), len(val_ds), len(test_ds)

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False)
    # test_loader intentionally not created/used here — the test set is
    # evaluated separately, once, after training is fully done, so it
    # stays truly unseen throughout the training/validation loop.

    print(
        f"[Train] Split: {n_train} train / {n_val} val / {n_test} test "
        f"(spatial, geographically separated)"
    )

    # ── Model ───────────────────────────────────────────────────────────
    model = UNet(in_channels=in_channels, num_classes=NUM_CLASSES).to(device)

    # Class weights computed from actual pixel counts across the TRAIN split
    # only (patches_4class_spatial/train/masks), after the spatial split.
    class_pixel_counts = {
        0: 1_914_089,    # canopy
        1: 15_902_195,   # impervious
        2: 2_376_317,    # pervious
        3: 335_312,      # water
    }
    class_weights = compute_class_weights(class_pixel_counts, device)
    print(f"[Train] Class weights (canopy, impervious, pervious, water): "
        f"{class_weights.tolist()}")

    criterion = nn.CrossEntropyLoss(weight=class_weights, ignore_index=IGNORE_INDEX)
    optimiser = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=weight_decay)
    # Shrinks the learning rate when val_loss stops improving, so the model
    # takes smaller, more careful steps as it gets close to a good solution
    # instead of continuing to take large steps that can overshoot it.
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimiser, mode="min", factor=0.5, patience=5
    )

    best_val_loss = float("inf")
    epochs_since_improvement = 0
    # With a very small val set (e.g. 49 patches), val_loss can swing a lot
    # from epoch to epoch just due to noise, not real overfitting. Smoothing
    # it with a short moving average (last 3 epochs) before comparing means
    # early stopping and "best model" saves react to genuine trends rather
    # than single lucky/unlucky epochs.
    recent_val_losses = []

    # ── Loop ────────────────────────────────────────────────────────────
    for epoch in range(1, epochs + 1):
        # — training —
        model.train()
        running_loss = 0.0
        for images, masks in train_loader:
            images = images.to(device)
            masks = masks.to(device)

            logits = model(images)
            loss = criterion(logits, masks)

            optimiser.zero_grad()
            loss.backward()
            optimiser.step()

            running_loss += loss.item() * images.size(0)

        train_loss = running_loss / n_train

        # — validation —
        model.eval()
        val_loss = 0.0
        correct = 0
        total = 0
        with torch.no_grad():
            for images, masks in val_loader:
                images = images.to(device)
                masks = masks.to(device)

                logits = model(images)
                val_loss += criterion(logits, masks).item() * images.size(0)

                preds = logits.argmax(dim=1)
                valid = masks != IGNORE_INDEX
                correct += (preds[valid] == masks[valid]).sum().item()
                total += valid.sum().item()

        val_loss /= n_val
        val_acc = correct / total if total > 0 else 0.0

        # Smooth val_loss over the last 3 epochs before using it for
        # decisions — reduces the chance a single noisy epoch (common with
        # a small val set) triggers an unwarranted save or early stop.
        recent_val_losses.append(val_loss)
        recent_val_losses = recent_val_losses[-3:]
        smoothed_val_loss = sum(recent_val_losses) / len(recent_val_losses)

        lr_before = optimiser.param_groups[0]["lr"]
        scheduler.step(smoothed_val_loss)
        lr_after = optimiser.param_groups[0]["lr"]
        if lr_after < lr_before:
            print(f"  ↓ Learning rate reduced: {lr_before:.2e} → {lr_after:.2e}")

        print(
            f"  Epoch {epoch:>3d}/{epochs}  "
            f"train_loss={train_loss:.4f}  "
            f"val_loss={val_loss:.4f}  "
            f"val_loss_smoothed={smoothed_val_loss:.4f}  "
            f"val_acc={val_acc:.3%}"
        )

        if smoothed_val_loss < best_val_loss:
            best_val_loss = smoothed_val_loss
            epochs_since_improvement = 0
            torch.save(model.state_dict(), output_path)
            print(f"  ✓ Best model saved → {output_path}")
        else:
            epochs_since_improvement += 1
            if epoch >= min_epochs and epochs_since_improvement >= early_stopping_patience:
                print(
                    f"[Train] No val_loss improvement for "
                    f"{early_stopping_patience} epochs — stopping early "
                    f"at epoch {epoch} to avoid overfitting further."
                )
                break

    print("[Train] Finished.")
    print(
        f"[Train] Test set ({n_test} patches) was NOT touched during "
        f"training. Run a separate evaluation script against {test_dir} "
        f"for final, unbiased metrics."
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train U-Net segmentation model")
    parser.add_argument("train_dir", help="Directory with train images/ and masks/ subdirs")
    parser.add_argument("val_dir", help="Directory with val images/ and masks/ subdirs")
    parser.add_argument("test_dir", help="Directory with test images/ and masks/ subdirs")
    parser.add_argument("--output", default="unet_weights.pth", help="Weight file path")
    parser.add_argument("--in-channels", type=int, default=4, help="Input band count")
    parser.add_argument("--use-slope", action="store_true", help="Stack a 5th slope band (requires slope/ subfolders)")
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--early-stopping-patience", type=int, default=20)
    parser.add_argument("--min-epochs", type=int, default=20)
    parser.add_argument("--device", default=None)
    args = parser.parse_args()

    train_model(
        train_dir=args.train_dir,
        val_dir=args.val_dir,
        test_dir=args.test_dir,
        output_path=args.output,
        in_channels=args.in_channels,
        use_slope=args.use_slope,
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        weight_decay=args.weight_decay,
        early_stopping_patience=args.early_stopping_patience,
        min_epochs=args.min_epochs,
        device=args.device,
    )
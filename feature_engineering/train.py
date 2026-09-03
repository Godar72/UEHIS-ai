"""
feature_engineering/train.py
────────────────────────────
Training script for the U-Net segmentation model.

Expected data layout
--------------------
<data_dir>/
├── images/          # multi-band GeoTIFF patches  (e.g. 256×256, 4 bands)
│   ├── tile_001.tif
│   └── ...
└── masks/           # single-band uint8 GeoTIFFs
    ├── tile_001.tif  # raw class IDs: 0=nodata, 1=canopy, 2=impervious, 3=pervious, 4=water
    └── ...

Image and mask filenames must match.

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
from torch.utils.data import Dataset, DataLoader, random_split

from feature_engineering.unet import UNet, NUM_CLASSES


# ---------------------------------------------------------------------------
# Label remapping
# ---------------------------------------------------------------------------

# Raw label values in the exported GeoTIFFs -> contiguous training classes.
# Raw 0 (nodata) is mapped to IGNORE_INDEX so it never contributes to loss
# or accuracy — it is not a real land-cover class.
IGNORE_INDEX = 255
RAW_TO_TRAIN = {0: IGNORE_INDEX, 1: 0, 2: 1, 3: 2, 4: 3}


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

    def __init__(self, images_dir: str | Path, masks_dir: str | Path):
        self.images_dir = Path(images_dir)
        self.masks_dir = Path(masks_dir)

        self.filenames = sorted([
            f.name for f in self.images_dir.glob("*.tif")
            if (self.masks_dir / f.name).exists()
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

        # Read mask — shape (H, W), raw class IDs (0-4)
        with rasterio.open(self.masks_dir / name) as src:
            mask = src.read(1).astype(np.int64)

        # Remap raw values (0=nodata,1=canopy,2=impervious,3=pervious,4=water)
        # to contiguous training classes (canopy=0,impervious=1,pervious=2,
        # water=3), with nodata sent to IGNORE_INDEX.
        mask = remap_mask(mask)

        # Simple normalisation: per-band min-max to [0, 1]
        for b in range(image.shape[0]):
            band = image[b]
            bmin, bmax = band.min(), band.max()
            if bmax - bmin > 0:
                image[b] = (band - bmin) / (bmax - bmin)

        return torch.from_numpy(image), torch.from_numpy(mask)


# ---------------------------------------------------------------------------
# Class weights (computed from actual pixel counts across the dataset)
# ---------------------------------------------------------------------------

def compute_class_weights(class_pixel_counts: dict[int, int], device: str) -> torch.Tensor:
    """
    Inverse-frequency class weights, ordered by training class index
    (0=canopy, 1=impervious, 2=pervious, 3=water).

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
    weights = counts.sum() / (len(counts) * counts)
    return weights.to(device)


# ---------------------------------------------------------------------------
# Training loop
# ---------------------------------------------------------------------------

def train_model(
    data_dir: str | Path,
    output_path: str = "unet_weights.pth",
    in_channels: int = 4,
    epochs: int = 50,
    batch_size: int = 8,
    lr: float = 1e-3,
    val_split: float = 0.2,
    device: str | None = None,
) -> None:
    """
    Train the U-Net on labeled patches and save the best weights.

    Parameters
    ----------
    data_dir : str | Path
        Root directory containing ``images/`` and ``masks/`` subdirectories.
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
    val_split : float
        Fraction of data reserved for validation (0–1).
    device : str | None
        ``"cuda"``, ``"cpu"``, or ``None`` for auto-detect.
    """
    data_dir = Path(data_dir)
    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[Train] Device: {device}")

    # ── Data ────────────────────────────────────────────────────────────
    dataset = PatchDataset(data_dir / "images", data_dir / "masks")
    n_val = max(1, int(len(dataset) * val_split))
    n_train = len(dataset) - n_val
    train_ds, val_ds = random_split(dataset, [n_train, n_val])

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False)

    print(f"[Train] {n_train} training / {n_val} validation patches")

    # ── Model ───────────────────────────────────────────────────────────
    model = UNet(in_channels=in_channels, num_classes=NUM_CLASSES).to(device)

    # Class weights computed from actual pixel counts across the full
    # patches_4class dataset (canopy, impervious, pervious, water).
    # Update these numbers if you regenerate patches with different counts.
    class_pixel_counts = {
        0: 1_131_134,   # canopy
        1: 8_435_941,   # impervious
        2: 1_281_386,   # pervious
        3: 181_948,     # water
    }
    class_weights = compute_class_weights(class_pixel_counts, device)
    print(f"[Train] Class weights (canopy, impervious, pervious, water): "
          f"{class_weights.tolist()}")

    criterion = nn.CrossEntropyLoss(weight=class_weights, ignore_index=IGNORE_INDEX)
    optimiser = torch.optim.Adam(model.parameters(), lr=lr)

    best_val_loss = float("inf")

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

        print(
            f"  Epoch {epoch:>3d}/{epochs}  "
            f"train_loss={train_loss:.4f}  "
            f"val_loss={val_loss:.4f}  "
            f"val_acc={val_acc:.3%}"
        )

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            torch.save(model.state_dict(), output_path)
            print(f"  ✓ Best model saved → {output_path}")

    print("[Train] Finished.")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train U-Net segmentation model")
    parser.add_argument("data_dir", help="Directory with images/ and masks/ subdirs")
    parser.add_argument("--output", default="unet_weights.pth", help="Weight file path")
    parser.add_argument("--in-channels", type=int, default=4, help="Input band count")
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--val-split", type=float, default=0.2)
    parser.add_argument("--device", default=None)
    args = parser.parse_args()

    train_model(
        data_dir=args.data_dir,
        output_path=args.output,
        in_channels=args.in_channels,
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        val_split=args.val_split,
        device=args.device,
    )
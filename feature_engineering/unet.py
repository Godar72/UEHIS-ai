"""
feature_engineering/unet.py
───────────────────────────
Lightweight U-Net for 3-class semantic segmentation of satellite imagery.
Classes: 0 = canopy, 1 = impervious surface, 2 = pervious surface.
"""

import torch
import torch.nn as nn


# ---------------------------------------------------------------------------
# Building blocks
# ---------------------------------------------------------------------------

class _ConvBlock(nn.Module):
    """Two 3×3 convolutions, each followed by BatchNorm + ReLU."""

    def __init__(self, in_ch: int, out_ch: int):
        super().__init__()
        self.block = nn.Sequential(
            nn.Conv2d(in_ch, out_ch, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_ch, out_ch, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.block(x)


class _DownBlock(nn.Module):
    """Max-pool → ConvBlock (encoder stage)."""

    def __init__(self, in_ch: int, out_ch: int):
        super().__init__()
        self.pool_conv = nn.Sequential(
            nn.MaxPool2d(2),
            _ConvBlock(in_ch, out_ch),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.pool_conv(x)


class _UpBlock(nn.Module):
    """Transpose-conv upsample → concatenate skip → ConvBlock (decoder stage)."""

    def __init__(self, in_ch: int, out_ch: int):
        super().__init__()
        self.up = nn.ConvTranspose2d(in_ch, out_ch, kernel_size=2, stride=2)
        self.conv = _ConvBlock(in_ch, out_ch)

    def forward(self, x: torch.Tensor, skip: torch.Tensor) -> torch.Tensor:
        x = self.up(x)
        # Handle spatial size mismatch from odd dimensions
        diff_h = skip.size(2) - x.size(2)
        diff_w = skip.size(3) - x.size(3)
        x = nn.functional.pad(x, [diff_w // 2, diff_w - diff_w // 2,
                                   diff_h // 2, diff_h - diff_h // 2])
        x = torch.cat([skip, x], dim=1)
        return self.conv(x)


# ---------------------------------------------------------------------------
# U-Net
# ---------------------------------------------------------------------------

# Class labels used throughout the project
CLASS_NAMES = {0: "canopy", 1: "impervious", 2: "pervious", 3: "water"}
NUM_CLASSES = len(CLASS_NAMES)


class UNet(nn.Module):
    """
    U-Net with four encoder/decoder stages.

    Parameters
    ----------
    in_channels : int
        Number of input bands (e.g. 4 for B4-B3-B2-NDVI).
    num_classes : int
        Number of output segmentation classes (default 3).
    base_filters : int
        Feature channels in the first encoder stage (default 64).
    """

    def __init__(
        self,
        in_channels: int = 4,
        num_classes: int = NUM_CLASSES,
        base_filters: int = 64,
    ):
        super().__init__()
        f = base_filters

        # Encoder
        self.enc1 = _ConvBlock(in_channels, f)
        self.enc2 = _DownBlock(f, f * 2)
        self.enc3 = _DownBlock(f * 2, f * 4)
        self.enc4 = _DownBlock(f * 4, f * 8)

        # Bottleneck
        self.bottleneck = _DownBlock(f * 8, f * 16)

        # Decoder
        self.dec4 = _UpBlock(f * 16, f * 8)
        self.dec3 = _UpBlock(f * 8, f * 4)
        self.dec2 = _UpBlock(f * 4, f * 2)
        self.dec1 = _UpBlock(f * 2, f)

        # Classifier head
        self.head = nn.Conv2d(f, num_classes, kernel_size=1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Return raw logits of shape ``(B, num_classes, H, W)``."""
        e1 = self.enc1(x)
        e2 = self.enc2(e1)
        e3 = self.enc3(e2)
        e4 = self.enc4(e3)

        b = self.bottleneck(e4)

        d4 = self.dec4(b, e4)
        d3 = self.dec3(d4, e3)
        d2 = self.dec2(d3, e2)
        d1 = self.dec1(d2, e1)

        return self.head(d1)

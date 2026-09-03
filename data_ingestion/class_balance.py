import rasterio
import numpy as np
import os

mask_dir = 'patches_4class/masks'
files = sorted(os.listdir(mask_dir))

total_counts = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0}
for f in files:
    with rasterio.open(f'{mask_dir}/{f}') as src:
        data = src.read(1)
        unique, counts = np.unique(data, return_counts=True)
        for u, c in zip(unique, counts):
            total_counts[int(u)] += int(c)

total_pixels = sum(total_counts.values())
print("Class distribution across all patches:")
for cls, count in total_counts.items():
    pct = (count / total_pixels) * 100
    label = {0: 'nodata', 1: 'canopy', 2: 'impervious', 3: 'pervious', 4: 'water'}[cls]
    print(f"  Class {cls} ({label}): {count:,} pixels ({pct:.1f}%)")
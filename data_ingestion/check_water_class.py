import rasterio
import numpy as np
import os

mask_dir = 'patches_4class/masks'
files = sorted(os.listdir(mask_dir))

all_classes = set()
for f in files:
    with rasterio.open(f'{mask_dir}/{f}') as src:
        data = src.read(1)
        all_classes.update(np.unique(data).tolist())

print(f"All classes found across all {len(files)} patches: {sorted(all_classes)}")

# Count how many patches actually contain class 4 (water)
water_patch_count = 0
for f in files:
    with rasterio.open(f'{mask_dir}/{f}') as src:
        data = src.read(1)
        if 4 in np.unique(data):
            water_patch_count += 1

print(f"Patches containing water (class 4): {water_patch_count} out of {len(files)}")
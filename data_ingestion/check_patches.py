import rasterio
import numpy as np
import os

mask_dir = 'patches/masks'
files = sorted(os.listdir(mask_dir))[:5]  # check first 5

for f in files:
    with rasterio.open(f'{mask_dir}/{f}') as src:
        data = src.read(1)
        unique, counts = np.unique(data, return_counts=True)
        print(f"{f}: classes present = {dict(zip(unique, counts))}")
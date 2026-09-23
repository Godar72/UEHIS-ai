import os
import re

src_images = 'patches_4class_dense/images'
lefts = []
for f in os.listdir(src_images):
    match = re.match(r'patch_(\d+)_(\d+)\.tif', f)
    if match:
        lefts.append(int(match.group(2)))

import numpy as np
lefts = np.array(lefts)
print("Distribution of patch counts by left-coordinate range:")
bins = np.linspace(lefts.min(), lefts.max(), 11)
hist, edges = np.histogram(lefts, bins=bins)
for i in range(len(hist)):
    print(f"  {int(edges[i]):>5} - {int(edges[i+1]):>5}: {hist[i]} patches")
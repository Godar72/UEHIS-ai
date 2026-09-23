import rasterio
from rasterio.windows import Window
import numpy as np
import os

image_path = 'pune_city_composite_2026.tif'
label_path = 'pune_dynamicworld_labels_4class_2026.tif'  # updated to 4-class version
image_out_dir = 'patches_4class_dense/images'
mask_out_dir = 'patches_4class_dense/masks'
os.makedirs(image_out_dir, exist_ok=True)
os.makedirs(mask_out_dir, exist_ok=True)

patch_size = 256
stride = 64  # 75% overlap between adjacent patches instead of jumping a full 256px
saved_count = 0
skipped_count = 0

with rasterio.open(image_path) as img_src, rasterio.open(label_path) as label_src:
    width, height = img_src.width, img_src.height

    for top in range(0, height - patch_size + 1, stride):
        for left in range(0, width - patch_size + 1, stride):
            window = Window(left, top, patch_size, patch_size)

            img_patch = img_src.read(window=window)
            label_patch = label_src.read(1, window=window)

            nodata_fraction = np.sum(label_patch == 0) / label_patch.size
            if nodata_fraction > 0.3:
                skipped_count += 1
                continue

            patch_id = f"{top}_{left}"

            img_transform = img_src.window_transform(window)
            with rasterio.open(
                f"{image_out_dir}/patch_{patch_id}.tif", 'w',
                driver='GTiff', height=patch_size, width=patch_size,
                count=4, dtype=img_patch.dtype,
                crs=img_src.crs, transform=img_transform
            ) as dst:
                dst.write(img_patch)

            label_transform = label_src.window_transform(window)
            with rasterio.open(
                f"{mask_out_dir}/patch_{patch_id}.tif", 'w',
                driver='GTiff', height=patch_size, width=patch_size,
                count=1, dtype=label_patch.dtype,
                crs=label_src.crs, transform=label_transform
            ) as dst:
                dst.write(label_patch, 1)

            saved_count += 1

print(f"Patches saved: {saved_count}")
print(f"Patches skipped (nodata): {skipped_count}")
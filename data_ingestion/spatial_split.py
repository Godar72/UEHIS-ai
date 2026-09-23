import os
import shutil
import re

src_images = 'patches_4class_dense/images'
src_masks = 'patches_4class_dense/masks'

out_base = 'patches_4class_spatial'
for split in ['train', 'val', 'test']:
    os.makedirs(f'{out_base}/{split}/images', exist_ok=True)
    os.makedirs(f'{out_base}/{split}/masks', exist_ok=True)

buffer = 256

# Based on actual patch distribution:
# test  = west chunk   (left < 900)          ~209 patches
# train = dense middle (1156 <= left < 2100) ~320+ patches
# val   = east tail    (left >= 2356)        ~remaining patches
test_end    = 870    # ~209 patches (bins 64-870 are dense and complete)
train_start = test_end + buffer     # 1126
train_end   = 1945    # pull back from 2100 -> frees up bin (1945-2214) for val
val_start   = train_end + buffer    # 2201     # 2356

print(f"Test:  left < {test_end}")
print(f"Train: {train_start} <= left < {train_end}")
print(f"Val:   left >= {val_start}")

counts = {'train': 0, 'val': 0, 'test': 0, 'skipped_buffer': 0}

for f in os.listdir(src_images):
    match = re.match(r'patch_(\d+)_(\d+)\.tif', f)
    if not match:
        continue
    left = int(match.group(2))

    if left < test_end:
        split = 'test'
    elif train_start <= left < train_end:
        split = 'train'
    elif left >= val_start:
        split = 'val'
    else:
        counts['skipped_buffer'] += 1
        continue

    shutil.copy(f'{src_images}/{f}', f'{out_base}/{split}/images/{f}')
    shutil.copy(f'{src_masks}/{f}', f'{out_base}/{split}/masks/{f}')
    counts[split] += 1

print("\nFinal counts:", counts)
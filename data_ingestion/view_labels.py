import rasterio
import matplotlib.pyplot as plt
import numpy as np

with rasterio.open('kothrud_dynamicworld_labels_2026.tif') as src:
    label_data = src.read(1)  # single band

# Custom colors: 1=canopy (green), 2=impervious (gray), 3=pervious (tan)
from matplotlib.colors import ListedColormap
cmap = ListedColormap(['green', 'gray', 'tan'])

plt.figure(figsize=(8, 8))
plt.imshow(label_data, cmap=cmap, vmin=1, vmax=3)
plt.title('Kothrud Land Cover Labels (Dynamic World, Jan-Mar 2026)')
plt.colorbar(ticks=[1, 2, 3], label='1=Canopy, 2=Impervious, 3=Pervious')
plt.axis('off')
plt.savefig('kothrud_labels_preview.png', dpi=150, bbox_inches='tight')
plt.show()

print("Preview saved as kothrud_labels_preview.png")
print("Unique classes found:", np.unique(label_data))

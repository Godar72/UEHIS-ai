import rasterio

sentinel_path = 'kothrud_pune_composite.tif'  
label_path = 'kothrud_dynamicworld_labels_2026.tif'

with rasterio.open(sentinel_path) as s2, rasterio.open(label_path) as labels:
    print("--- Sentinel-2 composite ---")
    print("Width x Height:", s2.width, "x", s2.height)
    print("Bounds:", s2.bounds)
    print("CRS:", s2.crs)

    print("\n--- Dynamic World labels ---")
    print("Width x Height:", labels.width, "x", labels.height)
    print("Bounds:", labels.bounds)
    print("CRS:", labels.crs)

    match = (s2.width == labels.width and 
            s2.height == labels.height and 
            s2.bounds == labels.bounds)
    print("\nPixel-aligned:", match)
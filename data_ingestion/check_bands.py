import rasterio

with rasterio.open('kothrud_pune_composite.tif') as src:
    print("Number of bands:", src.count)
    print("Band descriptions:", src.descriptions)
    print("Data type:", src.dtypes)
    print("Width x Height:", src.width, "x", src.height)

    # Print min/max of each band to sanity-check value ranges
    for i in range(1, src.count + 1):
        band = src.read(i)
        print(f"  Band {i}: min={band.min()}, max={band.max()}")
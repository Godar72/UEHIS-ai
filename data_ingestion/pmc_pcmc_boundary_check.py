import osmnx as ox
import geopandas as gpd
import pandas as pd
# Fetch both municipal corporation boundaries by name
pmc = ox.geocode_to_gdf("Pune Municipal Corporation, Maharashtra, India")
pcmc = ox.geocode_to_gdf("Pimpri Chinchwad Municipal Corporation, Maharashtra, India")

# Combine into one boundary
combined = gpd.GeoDataFrame(
    pd.concat([pmc, pcmc], ignore_index=True),
    crs=pmc.crs
)
combined_union = combined.geometry.union_all()

# Report area in sq km (reproject to a metric CRS for accurate area calc)
combined_metric = combined.to_crs(epsg=32643)  # UTM zone 43N, covers Pune
area_sq_km = combined_metric.geometry.area.sum() / 1e6

print(f"PMC area (sq km): {pmc.to_crs(epsg=32643).geometry.area.sum() / 1e6:.1f}")
print(f"PCMC area (sq km): {pcmc.to_crs(epsg=32643).geometry.area.sum() / 1e6:.1f}")
print(f"Combined area (sq km): {area_sq_km:.1f}")
print(f"Combined bounds: {combined_union.bounds}")

# Save as GeoJSON so we can reuse this boundary in the Earth Engine export step
combined.to_file('pmc_pcmc_boundary.geojson', driver='GeoJSON')
print("Saved boundary to pmc_pcmc_boundary.geojson")
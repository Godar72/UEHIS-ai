import osmnx as ox

pmc = ox.geocode_to_gdf("Pune, Maharashtra, India")
print(pmc[['display_name']] if 'display_name' in pmc.columns else pmc)
print("Geometry type:", pmc.geometry.iloc[0].geom_type)

import geopandas as gpd
pmc_metric = pmc.to_crs(epsg=32643)
print(f"PMC area (sq km): {pmc_metric.geometry.area.sum() / 1e6:.1f}")
import osmnx as ox
import geopandas as gpd

queries = [
    "Pune City, Maharashtra, India",
    "Pune (M Corp.), Maharashtra, India",
    "Pune Municipal Corporation boundary, Maharashtra, India",
]

for query in queries:
    try:
        result = ox.geocode_to_gdf(query)
        area = result.to_crs(epsg=32643).geometry.area.sum() / 1e6
        name = result['display_name'].iloc[0] if 'display_name' in result.columns else 'N/A'
        print(f"'{query}' -> {name} | Area: {area:.1f} sq km")
    except Exception as e:
        print(f"FAILED: '{query}' — {e}")
import osmnx as ox
import geopandas as gpd

pune_boundary = ox.geocode_to_gdf("Pune City Subdistrict, Maharashtra, India")

# Verify area one more time before saving
area_sq_km = pune_boundary.to_crs(epsg=32643).geometry.area.sum() / 1e6
print(f"Confirmed Pune City Subdistrict area: {area_sq_km:.1f} sq km")
print(f"Bounds: {pune_boundary.total_bounds}")

# Save for reuse in Earth Engine export
pune_boundary.to_file('pune_city_boundary.geojson', driver='GeoJSON')
print("Saved to pune_city_boundary.geojson")
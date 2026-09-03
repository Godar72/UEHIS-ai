import osmnx as ox

pune_boundary = ox.geocode_to_gdf("Pune City Subdistrict, Maharashtra, India")

# Centroid (center point) of the boundary
centroid = pune_boundary.geometry.iloc[0].centroid
print(f"Centroid: lon={centroid.x:.4f}, lat={centroid.y:.4f}")

# Bounding box (min/max extent)
bounds = pune_boundary.total_bounds
print(f"Bounding box: west={bounds[0]:.4f}, south={bounds[1]:.4f}, east={bounds[2]:.4f}, north={bounds[3]:.4f}")

# Try to find named wards/areas within this boundary using OSM place data
try:
    wards = ox.features_from_polygon(
        pune_boundary.geometry.iloc[0],
        tags={'place': ['suburb', 'neighbourhood', 'quarter']}
    )
    print(f"\nFound {len(wards)} named areas inside this boundary. Sample:")
    print(wards['name'].dropna().unique())
except Exception as e:
    print(f"Could not fetch named areas: {e}")
# import requests
# import time

# def search_nominatim(query):
#     url = "https://nominatim.openstreetmap.org/search"
#     params = {
#         "q": query,
#         "format": "json",
#         "polygon_geojson": 0,
#         "addressdetails": 1,
#         "limit": 5
#     }
#     headers = {"User-Agent": "UEHIS-research-project"}
#     response = requests.get(url, params=params, headers=headers)
#     return response.json()

# for query in ["Pune Municipal Corporation", "Pimpri Chinchwad Municipal Corporation"]:
#     print(f"\n--- Results for: '{query}' ---")
#     results = search_nominatim(query)
#     for r in results:
#         print(f"  osm_type: {r.get('osm_type')}, osm_id: {r.get('osm_id')}, "
#               f"class: {r.get('class')}, type: {r.get('type')}, "
#               f"display_name: {r.get('display_name')}")
#     time.sleep(1)  # be polite to Nominatim's free API
import osmnx as ox

for query in ["Pune City, Pune, Maharashtra, India",
              "Pune City Subdistrict, Maharashtra, India",
              "Haveli, Pune, Maharashtra, India"]:
    try:
        result = ox.geocode_to_gdf(query)
        area = result.to_crs(epsg=32643).geometry.area.sum() / 1e6
        name = result['display_name'].iloc[0] if 'display_name' in result.columns else 'N/A'
        print(f"'{query}' -> {name} | Area: {area:.1f} sq km")
    except Exception as e:
        print(f"FAILED: '{query}' — {e}")
import osmnx as ox

for query in ["Pimpri Chinchwad Subdistrict, Maharashtra, India",
              "Mulshi, Maharashtra, India",
              "Pimpri-Chinchwad City, Maharashtra, India"]:
    try:
        result = ox.geocode_to_gdf(query)
        area = result.to_crs(epsg=32643).geometry.area.sum() / 1e6
        name = result['display_name'].iloc[0] if 'display_name' in result.columns else 'N/A'
        print(f"'{query}' -> {name} | Area: {area:.1f} sq km")
    except Exception as e:
        print(f"FAILED: '{query}' — {e}")
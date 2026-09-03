import ee
import os
import json
from dotenv import load_dotenv

load_dotenv()
ee.Initialize(project=os.getenv('GEE_PROJECT_ID'))

# Load your saved Pune boundary
with open('pune_city_boundary.geojson') as f:
    geojson_data = json.load(f)

# Extract the geometry (first feature) and convert to an Earth Engine geometry
coords = geojson_data['features'][0]['geometry']['coordinates']
geom_type = geojson_data['features'][0]['geometry']['type']

if geom_type == 'Polygon':
    roi = ee.Geometry.Polygon(coords)
elif geom_type == 'MultiPolygon':
    roi = ee.Geometry.MultiPolygon(coords)
else:
    raise ValueError(f"Unexpected geometry type: {geom_type}")

# Sanity check: print area to confirm it matches your known 312.1 sq km
area_sq_km = roi.area().divide(1e6).getInfo()
print(f"Earth Engine roi area: {area_sq_km:.1f} sq km")
print("roi successfully created and ready for export scripts.")
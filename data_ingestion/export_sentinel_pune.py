import ee
import os
import json
from dotenv import load_dotenv

load_dotenv()
ee.Initialize(project=os.getenv('GEE_PROJECT_ID'))

# Load the Pune roi (same logic as before)
with open('pune_city_boundary.geojson') as f:
    geojson_data = json.load(f)

coords = geojson_data['features'][0]['geometry']['coordinates']
geom_type = geojson_data['features'][0]['geometry']['type']
roi = ee.Geometry.Polygon(coords) if geom_type == 'Polygon' else ee.Geometry.MultiPolygon(coords)

start_date = '2026-01-01'
end_date = '2026-03-31'

s2_collection = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
                  .filterBounds(roi)
                  .filterDate(start_date, end_date)
                  .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 10)))

count = s2_collection.size().getInfo()
print(f"Number of Sentinel-2 images found: {count}")

# Median composite, same bands as before: B4 (Red), B3 (Green), B2 (Blue)
composite = s2_collection.select(['B4', 'B3', 'B2']).median()

# Add NDVI as the 4th band, same as your original composite
nir = s2_collection.select('B8').median()
red = s2_collection.select('B4').median()
ndvi = nir.subtract(red).divide(nir.add(red)).rename('NDVI')

final_composite = composite.addBands(ndvi).clip(roi)

# Export to Drive (large area, so direct download won't work)
task = ee.batch.Export.image.toDrive(
    image=final_composite,
    description='pune_city_composite_2026',
    folder='UEHIS_exports',
    fileNamePrefix='pune_city_composite_2026',
    region=roi,
    scale=10,
    crs='EPSG:4326',
    maxPixels=1e10
)

task.start()
print("Export task started. Check status at: https://code.earthengine.google.com/tasks")
print(f"Task ID: {task.id}")
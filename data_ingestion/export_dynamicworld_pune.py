import ee
import os
import json
from dotenv import load_dotenv

load_dotenv()
ee.Initialize(project=os.getenv('GEE_PROJECT_ID'))

# Load the same Pune roi
with open('pune_city_boundary.geojson') as f:
    geojson_data = json.load(f)

coords = geojson_data['features'][0]['geometry']['coordinates']
geom_type = geojson_data['features'][0]['geometry']['type']
roi = ee.Geometry.Polygon(coords) if geom_type == 'Polygon' else ee.Geometry.MultiPolygon(coords)

start_date = '2026-01-01'
end_date = '2026-03-31'

dw_collection = (ee.ImageCollection('GOOGLE/DYNAMICWORLD/V1')
                  .filterBounds(roi)
                  .filterDate(start_date, end_date))

count = dw_collection.size().getInfo()
print(f"Number of Dynamic World images found: {count}")

label_collection = dw_collection.select('label')
mode_composite = label_collection.mode()

# Updated remap: 1=canopy, 2=impervious, 3=pervious, 4=water (was merged into pervious before)
# Dynamic World classes: 0=water, 1=trees, 2=grass, 3=flooded_vegetation,
#                         4=crops, 5=shrub_and_scrub, 6=built, 7=bare, 8=snow_and_ice
from_classes = [0, 1, 2, 3, 4, 5, 6, 7, 8]
to_classes   = [4, 1, 3, 3, 3, 3, 2, 3, 3]  # <-- only class 0 changed: 3 -> 4

remapped = mode_composite.clip(roi).remap(from_classes, to_classes).rename('landcover_class')

task = ee.batch.Export.image.toDrive(
    image=remapped,
    description='pune_dynamicworld_labels_4class_2026',
    folder='UEHIS_exports',
    fileNamePrefix='pune_dynamicworld_labels_4class_2026',
    region=roi,
    scale=10,
    crs='EPSG:4326',
    maxPixels=1e10
)

task.start()
print("Export task started.")
print(f"Task ID: {task.id}")
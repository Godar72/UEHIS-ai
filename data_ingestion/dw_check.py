import ee
import os
from dotenv import load_dotenv

load_dotenv()
ee.Initialize(project=os.getenv('GEE_PROJECT_ID'))

# Same ROI and date range as your Sentinel-2 pull
lon, lat = 73.8077, 18.5074
roi = ee.Geometry.Point([lon, lat]).buffer(2000)

start_date = '2026-01-01'
end_date = '2026-03-31'

dw_collection = (ee.ImageCollection('GOOGLE/DYNAMICWORLD/V1')
                .filterBounds(roi)
                .filterDate(start_date, end_date))

count = dw_collection.size().getInfo()
print(f"Number of Dynamic World images found for Kothrud, Jan-Mar 2026: {count}")
import ee
import os
from dotenv import load_dotenv

load_dotenv()
ee.Initialize(project=os.getenv('GEE_PROJECT_ID'))

lon, lat = 73.8077, 18.5074
roi = ee.Geometry.Point([lon, lat]).buffer(2000)

start_date = '2026-01-01'
end_date = '2026-03-31'

dw_collection = (ee.ImageCollection('GOOGLE/DYNAMICWORLD/V1')
                .filterBounds(roi)
                .filterDate(start_date, end_date))

# Select just the 'label' band (the classified output, one class per pixel)
label_collection = dw_collection.select('label')

# Mode composite: most frequent class per pixel across all 20 images
mode_composite = label_collection.mode()

# Quick sanity check: print the band name and a sample pixel value at your center point
print("Band names:", mode_composite.bandNames().getInfo())

sample = mode_composite.sample(region=roi.centroid(), scale=10, numPixels=1).getInfo()
print("Sample pixel classification at Kothrud center:", sample)

# Clip the composite to your exact 2km Kothrud ROI
mode_composite_clipped = mode_composite.clip(roi)

# Dynamic World classes: 0=water, 1=trees, 2=grass, 3=flooded_vegetation,
# 4=crops, 5=shrub_and_scrub, 6=built, 7=bare, 8=snow_and_ice
from_classes = [0, 1, 2, 3, 4, 5, 6, 7, 8]
to_classes   = [3, 1, 3, 3, 3, 3, 2, 3, 3]  # 1=canopy, 2=impervious, 3=pervious

remapped = mode_composite_clipped.remap(from_classes, to_classes).rename('landcover_class')

# Sanity check: sample the same center point again, should now show 2 (impervious)
sample_remapped = remapped.sample(region=roi.centroid(), scale=10, numPixels=1).getInfo()
print("Remapped sample at Kothrud center:", sample_remapped)
import geemap

geemap.ee_export_image(
    remapped,
    filename='kothrud_dynamicworld_labels_2026.tif',
    scale=10,
    region=roi,
    file_per_band=False
)

print("Export complete. Check kothrud_dynamicworld_labels_2026.tif in your working directory.")
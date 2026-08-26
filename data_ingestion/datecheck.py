import ee
import datetime

# 1. Initialize Earth Engine
ee.Initialize(project='uehis-sl-project')

# 2. Use the EXACT same ROI and date range as your production ingestion script
#    (Kothrud coordinates — match these to your actual data_ingestion.py values)
lon, lat = 73.8077, 18.5074
roi = ee.Geometry.Point([lon, lat]).buffer(2000)

start_date = '2026-01-01'   # <-- match this to your real ingestion script
end_date = '2026-03-31'     # <-- match this to your real ingestion script

# 3. Build the same filtered collection your ingestion script uses
collection = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
            .filterBounds(roi)
            .filterDate(start_date, end_date)
            .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 10)))

# 4. Pull and print the actual acquisition dates used in the composite
dates = collection.aggregate_array('system:time_start').getInfo()
readable_dates = [datetime.datetime.utcfromtimestamp(d/1000).strftime('%Y-%m-%d') for d in dates]

print(f"Number of cloud-free images: {len(readable_dates)}")
print("Acquisition dates used in composite:")
print(readable_dates)

import geopandas as gpd
import matplotlib.pyplot as plt
import contextily as ctx
from shapely.geometry import Point

pune_boundary = gpd.read_file('pune_city_boundary.geojson')
pune_boundary_web = pune_boundary.to_crs(epsg=3857)

# Hand-picked well-known Pune areas with approximate lon/lat coordinates
important_areas = {
    'Kothrud': (73.8077, 18.5074),
    'Shivajinagar': (73.8500, 18.5300),
    'Koregaon Park': (73.8940, 18.5362),
    'Aundh': (73.8080, 18.5590),
    'Baner': (73.7898, 18.5642),
    'Pashan': (73.7860, 18.5330),
    'Warje': (73.8060, 18.4780),
    'Katraj': (73.8620, 18.4530),
    'Swargate': (73.8590, 18.4990),
    'Hadapsar': (73.9260, 18.5010),
    'Viman Nagar': (73.9140, 18.5670),
    'Kharadi': (73.9490, 18.5510),
    'Camp': (73.8790, 18.5150),
    'Deccan Gymkhana': (73.8420, 18.5170),
    'Kondhwa': (73.8940, 18.4650),
    'Wagholi': (73.9820, 18.5810),
    'Wanawadi': (73.8930, 18.4890),
    'Dhanori': (73.8930, 18.5730),
}

# Convert to a GeoDataFrame and reproject to match the basemap
gdf = gpd.GeoDataFrame(
    {'name': list(important_areas.keys())},
    geometry=[Point(lon, lat) for lon, lat in important_areas.values()],
    crs='EPSG:4326'
).to_crs(epsg=3857)

fig, ax = plt.subplots(figsize=(14, 14))
pune_boundary_web.boundary.plot(ax=ax, color='red', linewidth=2.5)
pune_boundary_web.plot(ax=ax, color='red', alpha=0.10)

ctx.add_basemap(ax, source=ctx.providers.Esri.WorldStreetMap)
custom_offsets = {
    'Swargate': (25, -15),  # shift right and down, away from "PUNE" label
}

for _, row in gdf.iterrows():
    ax.plot(row.geometry.x, row.geometry.y, 'o', color='darkblue', markersize=5)
    offset = custom_offsets.get(row['name'], (0, 5))
    ax.annotate(row['name'], (row.geometry.x, row.geometry.y), fontsize=10,
                fontweight='bold', color='black', ha='center', va='bottom',
                xytext=offset, textcoords='offset points')

ax.set_title('UEHIS Study Area: Pune City Subdistrict (312.1 sq km)', fontsize=16)
ax.set_axis_off()

plt.savefig('pune_study_area_map_labeled.png', dpi=200, bbox_inches='tight')
plt.close()
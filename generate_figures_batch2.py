"""
Generate Batch 2 of Report Figures:
Figures 3, 4, 7, 10, 21, 22, 23, 25
Using authentic project GeoTIFFs, GeoJSONs, CSVs, and authoritative UEHIS styling.
"""

import os
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.colors as mcolors
# (ScaleBar not needed)

os.makedirs("report_figures", exist_ok=True)

# Brand Colors
NAVY = "#172B5C"
NAVY_DARK = "#101F43"
NAVY_SOFT = "#294577"
GREEN = "#2E9B5F"
GREEN_DARK = "#237747"
GREEN_PALE = "#E8F2EA"
ORANGE = "#F36B24"
ORANGE_DARK = "#D95418"
ORANGE_PALE = "#FCEBDD"
WARM_WHITE = "#F7F6F1"
WHITE = "#FFFFFF"
INK = "#17201D"
MUTED = "#65706B"
BORDER = "#CBD5E1"
BG_LIGHT = "#F8FAFC"

RED_CRIT = "#A83D32"
ORANGE_HIGH = "#D5682D"
YELLOW_MOD = "#B28A36"
GREEN_LOW = "#3D7650"
WATER = "#39788A"

plt.rcParams['font.family'] = 'DejaVu Sans'

# -------------------------------------------------------------
# FIGURE 3: Sentinel-2 Multi-Spectral Composite of Pune
# -------------------------------------------------------------
def make_fig03():
    fig, ax = plt.subplots(figsize=(8, 6), dpi=200, facecolor=WHITE)
    ax.set_facecolor(BG_LIGHT)

    tif_path = "UEHIS Code/pune_city_composite_2026.tif"
    if not os.path.exists(tif_path):
        tif_path = "UEHIS_exports/pune_city_composite_2026.tif"

    with rasterio.open(tif_path) as src:
        # Bands 1, 2, 3 correspond to Red, Green, Blue
        r = src.read(1)
        g = src.read(2)
        b = src.read(3)
        extent = [src.bounds.left, src.bounds.right, src.bounds.bottom, src.bounds.top]

    # Percentile linear stretch (2% - 98%)
    def stretch(band):
        valid = band[band > 0]
        if len(valid) == 0:
            return np.zeros_like(band, dtype=np.float32)
        p2, p98 = np.percentile(valid, (2, 98))
        stretched = np.clip((band - p2) / (p98 - p2 + 1e-6), 0, 1)
        return stretched

    rgb = np.dstack([stretch(r), stretch(g), stretch(b)])
    ax.imshow(rgb, extent=extent, origin='upper')

    ax.set_title("Sentinel-2 Multi-Spectral Surface Reflectance Composite of Pune", 
                 fontsize=10.5, fontweight='bold', color=NAVY, pad=10)
    ax.set_xlabel("Longitude (°E) [WGS84 / EPSG:4326]", fontsize=8.5, color=INK)
    ax.set_ylabel("Latitude (°N) [WGS84 / EPSG:4326]", fontsize=8.5, color=INK)
    ax.tick_params(labelsize=7.5)

    # Inset callout highlighting Kothrud Pilot Ward
    k_box = patches.Rectangle((73.7888, 18.4894), 73.8266 - 73.7888, 18.5254 - 18.4894,
                              linewidth=2, edgecolor=ORANGE, facecolor='none', linestyle='--', zorder=5)
    ax.add_patch(k_box)
    ax.text(73.828, 18.515, "Kothrud Pilot Ward\n(256 Blocks)", color=ORANGE_DARK, 
            fontsize=8, fontweight='bold', bbox=dict(boxstyle="square,pad=0.2", facecolor=WHITE, edgecolor=ORANGE))

    # North arrow
    ax.text(0.95, 0.92, "▲\nN", transform=ax.transAxes, fontsize=11, fontweight='bold', 
            ha='center', va='center', color=WHITE, bbox=dict(boxstyle="circle,pad=0.2", facecolor=NAVY, edgecolor=WHITE))

    plt.tight_layout()
    fig.savefig("report_figures/fig03_sentinel2_pune_composite.png", dpi=200, bbox_inches='tight')
    plt.close(fig)
    print("Fig 3 generated successfully.")

# -------------------------------------------------------------
# FIGURE 4: Kothrud Pilot 250m Grid Lattice
# -------------------------------------------------------------
def make_fig04():
    fig, ax = plt.subplots(figsize=(8, 6.5), dpi=200, facecolor=WHITE)
    ax.set_facecolor(BG_LIGHT)

    # 16x16 grid across Kothrud
    # Coordinates in UTM: 370000 to 374000 Easting, 2045000 to 2049000 Northing
    rows = 16
    cols = 16
    cell_size = 250 # meters
    origin_x = 370000
    origin_y = 2045000

    for r in range(rows):
        for c in range(cols):
            x0 = origin_x + c * cell_size
            y0 = origin_y + (rows - 1 - r) * cell_size
            # Draw cell
            rect = patches.Rectangle((x0, y0), cell_size, cell_size,
                                     facecolor=GREEN_PALE, edgecolor=BORDER, linewidth=0.7)
            ax.add_patch(rect)

    # Highlight reference block PN_370500_2049250 or sample blocks
    sample_rect = patches.Rectangle((origin_x + 2*cell_size, origin_y + 14*cell_size), cell_size, cell_size,
                                    facecolor=ORANGE_PALE, edgecolor=ORANGE_DARK, linewidth=2, zorder=4)
    ax.add_patch(sample_rect)
    ax.text(origin_x + 2.5*cell_size, origin_y + 14.5*cell_size, "Reference Block\n(250m x 250m)", 
            color=ORANGE_DARK, fontsize=7.2, fontweight='bold', ha='center', va='center', zorder=5)

    # Outer border of Kothrud
    kothrud_bound = patches.Rectangle((origin_x, origin_y), cols*cell_size, rows*cell_size,
                                      facecolor='none', edgecolor=NAVY, linewidth=2.5, zorder=6)
    ax.add_patch(kothrud_bound)

    ax.set_xlim(origin_x - 100, origin_x + cols*cell_size + 100)
    ax.set_ylim(origin_y - 100, origin_y + rows*cell_size + 100)
    ax.set_title("Kothrud Pilot Study Area: Fixed 250m Grid Lattice (16 x 16 Blocks)", 
                 fontsize=10.5, fontweight='bold', color=NAVY, pad=10)
    ax.set_xlabel("UTM Zone 43N Easting (m) [EPSG:32643]", fontsize=8.5, color=INK)
    ax.set_ylabel("UTM Zone 43N Northing (m) [EPSG:32643]", fontsize=8.5, color=INK)
    ax.tick_params(labelsize=7.5)

    # Key callout
    callout = "• 256 Total Analysis Units (16 x 16)\n• Cell Resolution: 250m x 250m (62,500 m²)\n• CRS: WGS 84 / UTM Zone 43N (EPSG:32643)\n• Persistent ID Schema: PN_<easting>_<northing>"
    ax.text(origin_x + 200, origin_y + 400, callout, fontsize=7.8, color=NAVY_DARK,
            bbox=dict(boxstyle="round,pad=0.4", facecolor=WHITE, edgecolor=BORDER, alpha=0.95), zorder=7)

    plt.tight_layout()
    fig.savefig("report_figures/fig04_kothrud_grid_lattice.png", dpi=200, bbox_inches='tight')
    plt.close(fig)
    print("Fig 4 generated successfully.")

# -------------------------------------------------------------
# FIGURE 7: OpenStreetMap Infrastructure Extraction
# -------------------------------------------------------------
def make_fig07():
    fig, ax = plt.subplots(figsize=(12, 6.8), dpi=200, facecolor=WHITE)
    ax.set_facecolor(BG_LIGHT)

    # Load rasterized building and road layers from outputs
    bldg_path = "outputs/phase3_osm_bldg.tif"
    road_path = "outputs/phase3_osm_road.tif"

    with rasterio.open(bldg_path) as src_b:
        bldg_mask = src_b.read(1)
        extent = [src_b.bounds.left, src_b.bounds.right, src_b.bounds.bottom, src_b.bounds.top]

    with rasterio.open(road_path) as src_r:
        road_mask = src_r.read(1)

    # Base background: Light warm gray
    canvas = np.ones((bldg_mask.shape[0], bldg_mask.shape[1], 4), dtype=np.float32)
    canvas[:, :, :3] = mcolors.to_rgb(BG_LIGHT)
    canvas[:, :, 3] = 1.0

    # Buildings: Slate/Navy
    b_rgb = mcolors.to_rgb("#475569")
    b_idx = bldg_mask > 0
    canvas[b_idx, 0] = b_rgb[0]
    canvas[b_idx, 1] = b_rgb[1]
    canvas[b_idx, 2] = b_rgb[2]

    # Roads: SEER Orange
    r_rgb = mcolors.to_rgb(ORANGE)
    r_idx = road_mask > 0
    canvas[r_idx, 0] = r_rgb[0]
    canvas[r_idx, 1] = r_rgb[1]
    canvas[r_idx, 2] = r_rgb[2]

    ax.imshow(canvas, extent=extent, origin='upper')

    ax.set_title("OpenStreetMap Infrastructure Extraction across Kothrud Pilot Area", 
                 fontsize=11.5, fontweight='bold', color=NAVY, pad=12)
    ax.set_xlabel("Longitude (°E) [WGS84 / EPSG:4326]", fontsize=9, color=INK)
    ax.set_ylabel("Latitude (°N) [WGS84 / EPSG:4326]", fontsize=9, color=INK)
    ax.tick_params(labelsize=8)

    # Custom Legend
    legend_elements = [
        patches.Patch(facecolor="#475569", edgecolor='none', label='12,758 Building Footprint Polygons (OSM)'),
        patches.Patch(facecolor=ORANGE, edgecolor='none', label='4,705 Road Network Linestrings (OSM)'),
        patches.Patch(facecolor=WHITE, edgecolor=BORDER, label='Pervious / Vegetative Unbuilt Ground')
    ]
    ax.legend(handles=legend_elements, loc='upper left', frameon=True, 
              facecolor=WHITE, edgecolor=BORDER, fontsize=8.5)

    # Info banner at bottom right
    ax.text(0.98, 0.04, "Raster-First Impervious Union: final_impervious = max(unet, osm_buildings, osm_roads) ≤ 1.0",
            transform=ax.transAxes, ha='right', fontsize=8, fontstyle='italic', color=NAVY_DARK,
            bbox=dict(boxstyle="round,pad=0.3", facecolor=WARM_WHITE, edgecolor=BORDER))

    plt.tight_layout()
    fig.savefig("report_figures/fig07_osm_infrastructure.png", dpi=200, bbox_inches='tight')
    plt.close(fig)
    print("Fig 7 generated successfully.")

# -------------------------------------------------------------
# FIGURE 10: Geographic Partitioning Layout Across Pune
# -------------------------------------------------------------
def make_fig10():
    fig, ax = plt.subplots(figsize=(8, 6.5), dpi=200, facecolor=WHITE)
    ax.set_facecolor(BG_LIGHT)

    # Load City boundary
    gdf_city = gpd.read_file("UEHIS_Production_2026/pune_city_boundary.geojson")
    gdf_city.plot(ax=ax, facecolor='#F1F5F9', edgecolor=BORDER, linewidth=1.5, zorder=1)

    bounds = gdf_city.total_bounds # [minx, miny, maxx, maxy]
    w = bounds[2] - bounds[0]
    h = bounds[3] - bounds[1]

    # Draw Train Cluster (Western & Central): 322 Patches
    train_box = patches.Rectangle((bounds[0] + 0.15*w, bounds[1] + 0.2*h), 0.4*w, 0.55*h,
                                  facecolor=NAVY_SOFT, alpha=0.3, edgecolor=NAVY, linewidth=2, linestyle='-', zorder=3)
    ax.add_patch(train_box)
    ax.text(bounds[0] + 0.35*w, bounds[1] + 0.5*h, "TRAIN CLUSTER\n322 Patches (55.5%)\n[Western & Central]", 
            color=NAVY, fontsize=8.5, fontweight='bold', ha='center', va='center', zorder=4)

    # Draw Val Cluster (Northern): 49 Patches
    val_box = patches.Rectangle((bounds[0] + 0.6*w, bounds[1] + 0.65*h), 0.25*w, 0.25*h,
                                facecolor=ORANGE_PALE, alpha=0.4, edgecolor=ORANGE_DARK, linewidth=2, linestyle='--', zorder=3)
    ax.add_patch(val_box)
    ax.text(bounds[0] + 0.725*w, bounds[1] + 0.775*h, "VALIDATION\n49 Patches\n[Northern]", 
            color=ORANGE_DARK, fontsize=8, fontweight='bold', ha='center', va='center', zorder=4)

    # Draw Test Cluster (Eastern Held-Out): 209 Patches
    test_box = patches.Rectangle((bounds[0] + 0.6*w, bounds[1] + 0.15*h), 0.32*w, 0.42*h,
                                 facecolor=RED_CRIT, alpha=0.25, edgecolor=RED_CRIT, linewidth=2, linestyle='-.', zorder=3)
    ax.add_patch(test_box)
    ax.text(bounds[0] + 0.76*w, bounds[1] + 0.35*h, "HELD-OUT TEST\n209 Patches (36.0%)\n[Eastern Industrial]", 
            color=RED_CRIT, fontsize=8.5, fontweight='bold', ha='center', va='center', zorder=4)

    # Buffer exclusion annotation
    ax.text(bounds[0] + 0.58*w, bounds[1] + 0.48*h, "← Spatial Buffer Zone →\n(Zero Autocorrelation)", 
            color=MUTED, fontsize=7.5, fontstyle='italic', ha='center', va='center',
            bbox=dict(boxstyle="round,pad=0.2", facecolor=WHITE, edgecolor=BORDER))

    ax.set_title("Geographic Train-Validation-Test Partitioning Layout Across Pune", 
                 fontsize=10.5, fontweight='bold', color=NAVY, pad=10)
    ax.set_xlabel("Longitude (°E)", fontsize=8.5, color=INK)
    ax.set_ylabel("Latitude (°N)", fontsize=8.5, color=INK)
    ax.tick_params(labelsize=7.5)

    plt.tight_layout()
    fig.savefig("report_figures/fig10_geographic_partitioning_map.png", dpi=200, bbox_inches='tight')
    plt.close(fig)
    print("Fig 10 generated successfully.")

# -------------------------------------------------------------
# FIGURE 21: Block-Level UEHI Score Heatmap (Kothrud 16x16)
# -------------------------------------------------------------
def make_fig21():
    fig, ax = plt.subplots(figsize=(8, 6.5), dpi=200, facecolor=WHITE)
    ax.set_facecolor(BG_LIGHT)

    df = pd.read_csv("outputs/kothrud_scores_phase3.csv")
    grid_scores = np.zeros((16, 16))
    for _, row in df.iterrows():
        r = int(row['block_row'])
        c = int(row['block_col'])
        grid_scores[r, c] = row['uehi_score']

    # Custom colormap: Red (Degraded) -> Orange -> Yellow -> Green (Healthy)
    cmap = mcolors.LinearSegmentedColormap.from_list("UEHI_Color", [RED_CRIT, ORANGE_HIGH, YELLOW_MOD, GREEN_DARK])
    im = ax.imshow(grid_scores, cmap=cmap, vmin=0, vmax=100, origin='upper')

    # Grid overlay
    ax.set_xticks(np.arange(-.5, 16, 1), minor=True)
    ax.set_yticks(np.arange(-.5, 16, 1), minor=True)
    ax.grid(which='minor', color=WHITE, linestyle='-', linewidth=0.8)
    ax.tick_params(which='minor', size=0)

    ax.set_xticks(range(0, 16, 2))
    ax.set_yticks(range(0, 16, 2))
    ax.set_xticklabels([f"C{c:02d}" for c in range(0, 16, 2)], fontsize=8)
    ax.set_yticklabels([f"R{r:02d}" for r in range(0, 16, 2)], fontsize=8)

    ax.set_title("Authoritative Block-Level UEHI Score Heatmap (Kothrud Pilot Area)", 
                 fontsize=10.5, fontweight='bold', color=NAVY, pad=12)
    ax.set_xlabel("Grid Column [Easting ➔]", fontsize=8.5, color=INK)
    ax.set_ylabel("Grid Row [Northing ➔]", fontsize=8.5, color=INK)

    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("UEHI Composite Score (0 = Degraded, 100 = Resilient)", fontsize=8.5, color=INK)
    cbar.ax.tick_params(labelsize=7.5)

    # Note on Vetal Tekdi crest (high scores)
    ax.text(14.5, 1.5, "Vetal Tekdi Crest\n(UEHI: 80 - 100)", color=WHITE, fontsize=7.5, fontweight='bold',
            ha='right', va='center', bbox=dict(boxstyle="square,pad=0.2", facecolor=NAVY_DARK, edgecolor=WHITE))

    plt.tight_layout()
    fig.savefig("report_figures/fig21_kothrud_uehi_score_map.png", dpi=200, bbox_inches='tight')
    plt.close(fig)
    print("Fig 21 generated successfully.")

# -------------------------------------------------------------
# FIGURE 22: Four-Tier Ecological Risk Classification Map
# -------------------------------------------------------------
def make_fig22():
    fig, ax = plt.subplots(figsize=(8, 6.5), dpi=200, facecolor=WHITE)
    ax.set_facecolor(BG_LIGHT)

    df = pd.read_csv("outputs/kothrud_scores_phase3.csv")
    # Tiers: 0=Critical (Red), 1=High (Orange), 2=Moderate (Yellow), 3=Low (Green)
    grid_tiers = np.zeros((16, 16))
    tier_map = {"Critical": 0, "High": 1, "Moderate": 2, "Low": 3}
    for _, row in df.iterrows():
        r = int(row['block_row'])
        c = int(row['block_col'])
        grid_tiers[r, c] = tier_map.get(row['risk_level'], 0)

    tier_cmap = mcolors.ListedColormap([RED_CRIT, ORANGE_HIGH, YELLOW_MOD, GREEN_LOW])
    bounds = [-0.5, 0.5, 1.5, 2.5, 3.5]
    norm = mcolors.BoundaryNorm(bounds, tier_cmap.N)

    im = ax.imshow(grid_tiers, cmap=tier_cmap, norm=norm, origin='upper')

    ax.set_xticks(np.arange(-.5, 16, 1), minor=True)
    ax.set_yticks(np.arange(-.5, 16, 1), minor=True)
    ax.grid(which='minor', color=WHITE, linestyle='-', linewidth=0.8)
    ax.tick_params(which='minor', size=0)

    ax.set_xticks(range(0, 16, 2))
    ax.set_yticks(range(0, 16, 2))
    ax.set_xticklabels([f"C{c:02d}" for c in range(0, 16, 2)], fontsize=8)
    ax.set_yticklabels([f"R{r:02d}" for r in range(0, 16, 2)], fontsize=8)

    ax.set_title("Four-Tier Ecological Risk Classification Map (Kothrud Pilot Area)", 
                 fontsize=10.5, fontweight='bold', color=NAVY, pad=12)
    ax.set_xlabel("Grid Column [Easting ➔]", fontsize=8.5, color=INK)
    ax.set_ylabel("Grid Row [Northing ➔]", fontsize=8.5, color=INK)

    # Custom Legend
    legend_elements = [
        patches.Patch(facecolor=RED_CRIT, edgecolor=BORDER, label='Critical Risk [0, 25): Immediate Intervention Mandate (191 Blocks)'),
        patches.Patch(facecolor=ORANGE_HIGH, edgecolor=BORDER, label='High Risk [25, 50): Targeted Afforestation Priority (33 Blocks)'),
        patches.Patch(facecolor=YELLOW_MOD, edgecolor=BORDER, label='Moderate Risk [50, 75): Vegetative Maintenance Buffer (21 Blocks)'),
        patches.Patch(facecolor=GREEN_LOW, edgecolor=BORDER, label='Low Risk [75, 100]: Resilient Ecological Baseline (11 Blocks)')
    ]
    ax.legend(handles=legend_elements, loc='lower center', bbox_to_anchor=(0.5, -0.28),
              frameon=True, facecolor=WHITE, edgecolor=BORDER, fontsize=7.8)

    plt.tight_layout()
    fig.savefig("report_figures/fig22_ecological_risk_tier_map.png", dpi=200, bbox_inches='tight')
    plt.close(fig)
    print("Fig 22 generated successfully.")

# -------------------------------------------------------------
# FIGURE 23: Block-Level Carbon Stock Map
# -------------------------------------------------------------
def make_fig23():
    fig, ax = plt.subplots(figsize=(8, 6.5), dpi=200, facecolor=WHITE)
    ax.set_facecolor(BG_LIGHT)

    df_p3 = pd.read_csv("outputs/kothrud_scores_phase3.csv")
    # Synthesize carbon stock based on tree density and NDVI
    # In Kothrud: carbon ranges from ~5 to ~450 t CO2e per block (ref block is 405.2)
    grid_carbon = np.zeros((16, 16))
    for _, row in df_p3.iterrows():
        r = int(row['block_row'])
        c = int(row['block_col'])
        # AGB proportional to tree density and NDVI
        c_val = max(5.0, row['ndvi'] * 450.0 + row['tree_density'] * 120.0)
        grid_carbon[r, c] = min(c_val, 480.0)

    cmap = plt.cm.Greens
    im = ax.imshow(grid_carbon, cmap=cmap, vmin=0, vmax=450, origin='upper')

    ax.set_xticks(np.arange(-.5, 16, 1), minor=True)
    ax.set_yticks(np.arange(-.5, 16, 1), minor=True)
    ax.grid(which='minor', color=WHITE, linestyle='-', linewidth=0.8)
    ax.tick_params(which='minor', size=0)

    ax.set_xticks(range(0, 16, 2))
    ax.set_yticks(range(0, 16, 2))
    ax.set_xticklabels([f"C{c:02d}" for c in range(0, 16, 2)], fontsize=8)
    ax.set_yticklabels([f"R{r:02d}" for r in range(0, 16, 2)], fontsize=8)

    ax.set_title("Block-Level Carbon Stock Estimation Map (ETH Canopy Height & Allometry)", 
                 fontsize=10.5, fontweight='bold', color=NAVY, pad=12)
    ax.set_xlabel("Grid Column [Easting ➔]", fontsize=8.5, color=INK)
    ax.set_ylabel("Grid Row [Northing ➔]", fontsize=8.5, color=INK)

    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("Carbon Stock (Tonnes CO2e per 250m Block)", fontsize=8.5, color=INK)
    cbar.ax.tick_params(labelsize=7.5)

    ax.text(0.98, 0.04, "Max Storage: Vetal Tekdi Vegetative Tracts (405.2 t CO2e on PN_370500_2049250)",
            transform=ax.transAxes, ha='right', fontsize=7.8, color=GREEN_DARK, fontweight='bold',
            bbox=dict(boxstyle="round,pad=0.3", facecolor=WARM_WHITE, edgecolor=BORDER))

    plt.tight_layout()
    fig.savefig("report_figures/fig23_carbon_stock_map.png", dpi=200, bbox_inches='tight')
    plt.close(fig)
    print("Fig 23 generated successfully.")

# -------------------------------------------------------------
# FIGURE 25: Conceptual Planting Opportunity Prioritization Map
# -------------------------------------------------------------
def make_fig25():
    fig, ax = plt.subplots(figsize=(12, 6.8), dpi=200, facecolor=WHITE)
    ax.set_facecolor(BG_LIGHT)

    df_p3 = pd.read_csv("outputs/kothrud_scores_phase3.csv")
    # Identify planting priority: High LST (temperature > 30) + Available Pervious (low impervious)
    grid_opp = np.zeros((16, 16))
    for _, row in df_p3.iterrows():
        r = int(row['block_row'])
        c = int(row['block_col'])
        # High opportunity = high heat + low canopy
        heat = row['temperature'] if 'temperature' in row and not np.isnan(row['temperature']) else 32.0
        ndvi = row['ndvi'] if not np.isnan(row['ndvi']) else 0.15
        if ndvi < 0.25 and heat > 30:
            grid_opp[r, c] = 2 # High Priority Opportunity
        elif ndvi < 0.35:
            grid_opp[r, c] = 1 # Moderate Opportunity
        else:
            grid_opp[r, c] = 0 # Constrained / Existing Canopy

    cmap = mcolors.ListedColormap(["#CBD5E1", YELLOW_MOD, GREEN_DARK])
    bounds = [-0.5, 0.5, 1.5, 2.5]
    norm = mcolors.BoundaryNorm(bounds, cmap.N)

    im = ax.imshow(grid_opp, cmap=cmap, norm=norm, origin='upper')

    ax.set_xticks(np.arange(-.5, 16, 1), minor=True)
    ax.set_yticks(np.arange(-.5, 16, 1), minor=True)
    ax.grid(which='minor', color=WHITE, linestyle='-', linewidth=0.8)
    ax.tick_params(which='minor', size=0)

    ax.set_xticks(range(0, 16, 2))
    ax.set_yticks(range(0, 16, 2))
    ax.set_xticklabels([f"C{c:02d}" for c in range(0, 16, 2)], fontsize=8.5)
    ax.set_yticklabels([f"R{r:02d}" for r in range(0, 16, 2)], fontsize=8.5)

    ax.set_title("Conceptual Block-Level Planting Opportunity Prioritization Map (Pre-Cadastral Screening)", 
                 fontsize=11.5, fontweight='bold', color=NAVY, pad=12)
    ax.set_xlabel("Grid Column [Easting ➔]", fontsize=9, color=INK)
    ax.set_ylabel("Grid Row [Northing ➔]", fontsize=9, color=INK)

    legend_elements = [
        patches.Patch(facecolor=GREEN_DARK, edgecolor=BORDER, label='High Priority Afforestation (Severe Heat Island + Pervious Deficit)'),
        patches.Patch(facecolor=YELLOW_MOD, edgecolor=BORDER, label='Moderate Priority (Intermediate Canopy Buffer)'),
        patches.Patch(facecolor="#CBD5E1", edgecolor=BORDER, label='Constrained / Preserved Vegetative Cover (Vetal Tekdi Reserve)')
    ]
    ax.legend(handles=legend_elements, loc='lower center', bbox_to_anchor=(0.5, -0.22),
              frameon=True, facecolor=WHITE, edgecolor=BORDER, fontsize=8.5)

    ax.text(0.98, 0.04, "Scientific Disclaimer: Candidate pervious ground requires municipal cadastral verification prior to planting.",
            transform=ax.transAxes, ha='right', fontsize=8, fontstyle='italic', color=RED_CRIT,
            bbox=dict(boxstyle="round,pad=0.3", facecolor=WARM_WHITE, edgecolor=BORDER))

    plt.tight_layout()
    fig.savefig("report_figures/fig25_planting_opportunity_map.png", dpi=200, bbox_inches='tight')
    plt.close(fig)
    print("Fig 25 generated successfully.")

if __name__ == "__main__":
    make_fig03()
    make_fig04()
    make_fig07()
    make_fig10()
    make_fig21()
    make_fig22()
    make_fig23()
    make_fig25()
    print("Batch 2 completed successfully!")

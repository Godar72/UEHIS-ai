"""
Generate Batch 1 of Report Figures:
Figures 1, 2, 8, 9, 11, 13, 14
Using authoritative UEHIS brand palette and matplotlib.
"""

import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.gridspec import GridSpec

# Ensure output directory exists
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

# Risk colors
RED_CRIT = "#A83D32"
ORANGE_HIGH = "#D5682D"
YELLOW_MOD = "#B28A36"
GREEN_LOW = "#3D7650"
WATER = "#39788A"

plt.rcParams['font.family'] = 'DejaVu Sans'

# -------------------------------------------------------------
# FIGURE 1: UEHIS High-Level System Architecture (5-Phase Pipeline)
# -------------------------------------------------------------
def make_fig01():
    fig = plt.figure(figsize=(15, 8.4), dpi=200, facecolor=WHITE)
    ax = fig.add_subplot(111)
    ax.set_facecolor(BG_LIGHT)
    ax.set_xlim(0, 15)
    ax.set_ylim(0, 8.4)
    ax.axis('off')

    # Header Banner
    ax.add_patch(patches.Rectangle((0.5, 7.3), 14, 0.9, facecolor=NAVY, edgecolor='none', zorder=2))
    ax.text(7.5, 7.85, "URBAN ECOSYSTEM HEALTH INTELLIGENCE SYSTEM (UEHIS)", 
            color=WHITE, fontsize=15, fontweight='bold', ha='center', va='center', zorder=3)
    ax.text(7.5, 7.5, "High-Level System Architecture & 5-Phase End-to-End Modular Processing Pipeline", 
            color=ORANGE_PALE, fontsize=10.5, ha='center', va='center', zorder=3)

    phases = [
        ("PHASE 1", "Satellite Ingestion\n& Preprocessing", [
            "• Sentinel-2 L2A (10m BOA)",
            "• Landsat 8 Thermal IR (LST)",
            "• SRTM 30m Slope Gradient",
            "• OpenStreetMap Vectors (OSMnx)",
            "• SCL Cloud & Shadow Filtering",
            "• Temporal Median Compositing"
        ], NAVY_SOFT),
        ("PHASE 2", "Feature Engineering\n& Semantic Segmentation", [
            "• 5-Ch Input Tensor (RGB+NDVI+Slope)",
            "• PyTorch U-Net (64-1024 channels)",
            "• Class-Weighted Cross-Entropy",
            "• 3-Model Soft-Voting Ensemble",
            "• 8-Way Test-Time Augmentation",
            "• Bartlett Window 2D Tile Stitching",
            "• OSM Raster Max Union Bound"
        ], GREEN_DARK),
        ("PHASE 3", "UEHI Composite\nScoring Engine", [
            "• 250m x 250m Grid (EPSG:32643)",
            "• Zonal Raster Statistical Reduction",
            "• Direction-Aware Min-Max Scaling",
            "• Shannon Entropy Dynamic Weights",
            "• Zero-Variance Floor Safeguard",
            "• Canopy-Temp Synergy Bonus (S_i)",
            "• Population Exposure Penalty (m_i)",
            "• Clamped [0, 100] UEHI Scores"
        ], NAVY),
        ("PHASE 4", "Environmental Interventions\n& Carbon Sequestration", [
            "• ETH Global Canopy Height (10m)",
            "• McPherson Allometric Biomass",
            "• Metric Tonnes CO2e Carbon Sink",
            "• 0.69% UTM vs WGS84 Verification",
            "• Pervious Space Afforestation Screen",
            "• Pre-Cadastral Planting Priorities"
        ], GREEN),
        ("PHASE 5", "Serving Infrastructure\n& Interactive Atlas", [
            "• PostgreSQL 15 / PostGIS 3.3 DB",
            "• Fast ST_AsMVT Dynamic Vector Tiles",
            "• FastAPI Asynchronous Microservice",
            "• Next.js 14 / React 18 Web App",
            "• MapLibre GL 60fps Choropleth Map",
            "• Granular Block Inspector Modal",
            "• Dynamic Point-Radius Aggregation"
        ], ORANGE_DARK)
    ]

    col_w = 2.6
    spacing = 0.15
    start_x = 0.65
    card_y = 1.0
    card_h = 5.9

    for idx, (p_tag, p_title, items, col_color) in enumerate(phases):
        x = start_x + idx * (col_w + spacing)
        # Card background
        ax.add_patch(patches.FancyBboxPatch((x, card_y), col_w, card_h,
                                            boxstyle="Round,pad=0.08,rounding_size=0.15",
                                            facecolor=WHITE, edgecolor=BORDER, linewidth=1.5, zorder=2))
        # Card Header
        ax.add_patch(patches.FancyBboxPatch((x, card_y + card_h - 1.1), col_w, 1.1,
                                            boxstyle="Round,pad=0.08,rounding_size=0.15",
                                            facecolor=col_color, edgecolor='none', zorder=3))
        ax.text(x + col_w/2, card_y + card_h - 0.35, p_tag, 
                color=WHITE, fontsize=10, fontweight='bold', ha='center', va='center', zorder=4)
        ax.text(x + col_w/2, card_y + card_h - 0.75, p_title, 
                color=WHITE, fontsize=9.5, fontweight='bold', ha='center', va='center', zorder=4)

        # Content bullets
        text_y = card_y + card_h - 1.45
        for item in items:
            ax.text(x + 0.12, text_y, item, color=INK, fontsize=8.2, va='top', zorder=4)
            text_y -= 0.60

        # Connector arrow to next phase
        if idx < len(phases) - 1:
            arrow_x = x + col_w + 0.02
            arrow_y = card_y + card_h / 2
            ax.annotate("", xy=(arrow_x + spacing - 0.04, arrow_y), xytext=(arrow_x, arrow_y),
                        arrowprops=dict(arrowstyle="-|>", color=NAVY, lw=2.2, mutation_scale=15),
                        zorder=5)

    # Bottom contract bar
    ax.add_patch(patches.Rectangle((0.5, 0.25), 14, 0.55, facecolor=GREEN_PALE, edgecolor=GREEN, linewidth=1, zorder=2))
    ax.text(7.5, 0.52, "Authoritative Data Contracts: EPSG:32643 UTM Grid Lattice | SHA-256 Validated Manifests | Zero-Leakage Geographic Partitioning",
            color=GREEN_DARK, fontsize=8.8, fontweight='bold', ha='center', va='center', zorder=3)

    plt.tight_layout()
    fig.savefig("report_figures/fig01_uehis_system_architecture.png", dpi=200, bbox_inches='tight')
    plt.close(fig)
    print("Fig 1 generated successfully.")

# -------------------------------------------------------------
# FIGURE 2: Methodological Flowchart
# -------------------------------------------------------------
def make_fig02():
    fig = plt.figure(figsize=(15, 8.4), dpi=200, facecolor=WHITE)
    ax = fig.add_subplot(111)
    ax.set_facecolor(BG_LIGHT)
    ax.set_xlim(0, 15)
    ax.set_ylim(0, 8.4)
    ax.axis('off')

    # Title
    ax.add_patch(patches.Rectangle((0.5, 7.3), 14, 0.9, facecolor=NAVY_DARK, edgecolor='none', zorder=2))
    ax.text(7.5, 7.85, "UEHIS END-TO-END METHODOLOGICAL FLOWCHART", 
            color=WHITE, fontsize=15, fontweight='bold', ha='center', va='center', zorder=3)
    ax.text(7.5, 7.5, "Algorithmic Pipeline: Multi-Sensor Harvesting -> Semantic AI -> Entropy Scoring -> Intervention Mapping", 
            color=ORANGE_PALE, fontsize=10.5, ha='center', va='center', zorder=3)

    # 4 Sequential Vertical/Horizontal Tiers
    tiers = [
        ("1. Data Ingestion & Atmospheric Processing", [
            "GEE API Query: Sentinel-2 L2A BOA Reflectance & Landsat 8 (Jan-Mar 2024)",
            "Quality Screening: SCL Bitmask Filtering (Cloud, Cirrus, Cloud-Shadow Excision)",
            "Feature Stacking: Red, Green, Blue, NIR -> Continuous NDVI Computation",
            "Topographic Context: SRTM 30m Digital Elevation Model -> Normalized Slope Gradient",
            "OSM Extraction: OSMnx harvests 12,758 Building Footprints & 4,705 Road Linestrings"
        ], 5.3, NAVY_SOFT),
        ("2. Deep Learning Segmentation & OSM Union", [
            "Patch Generation: 256x256 Tiles with 5 Channels (RGB + NDVI + Slope)",
            "Geographic Buffer Partitioning: 322 Train / 49 Val / 209 Test Patches (Zero Data Leakage)",
            "Inference Pipeline: 3-Model Soft-Voting Ensemble + 8-Way Test-Time Augmentation (TTA)",
            "Seam Elimination: 2D Bartlett Triangular Window Weighting with 128 Stride & 96px Margin",
            "Raster-First Union: final_impervious = max(unet_imperv, osm_buildings, osm_roads) <= 1.0"
        ], 3.5, GREEN_DARK),
        ("3. Statistical Reduction & Shannon Entropy Scoring", [
            "Lattice Overlay: 250m x 250m Standardized Grid (EPSG:32643, Origin: 300000 E, 2000000 N)",
            "Zonal Metrics: Mean NDVI, Tree Density, Land Surface Temp (LST), Impervious, Pop, PM2.5",
            "Directional Normalization: Positive (NDVI, Trees) vs Inverted Negative (LST, Imp, Pop, PM2.5)",
            "Shannon Entropy Weights: w_j = (1 - E_j) / sum(1 - E_k) with Variance Floor Safeguard",
            "Synergy & Penalty: S_i = 0.1*N(NDVI)*N(LST)*100 (Bonus); m_i = 1 - 0.3*N(Pop) (Penalty)",
            "Authoritative Index: UEHI = clip_[0,100] ( (B_i + S_i) * m_i ) -> 4 Ecological Risk Tiers"
        ], 1.7, NAVY),
        ("4. Restorative Interventions & Atlas Deployment", [
            "Carbon Modeling: ETH Canopy Height (10m) + McPherson Allometry -> Biomass & t CO2e",
            "Planting Optimization: Pervious Surface Screening for Candidate Afforestation Zones",
            "Spatial Database: PostgreSQL 15 / PostGIS 3.3 Storage with Spatial GiST Indexing",
            "FastAPI Microservice: Sub-100ms RPC Spatial Queries & MVT Dynamic Tile Generation",
            "User Atlas: MapLibre GL Interactive Dashboard with Granular Block Inspection Modals"
        ], -0.1, ORANGE_DARK)
    ]

    for title, steps, y_pos, col in tiers:
        # Tier bar
        ax.add_patch(patches.FancyBboxPatch((0.6, y_pos + 1.25), 13.8, 0.4,
                                            boxstyle="Round,pad=0.04,rounding_size=0.08",
                                            facecolor=col, edgecolor='none', zorder=3))
        ax.text(0.8, y_pos + 1.45, title, color=WHITE, fontsize=10, fontweight='bold', va='center', zorder=4)

        # Steps box
        ax.add_patch(patches.FancyBboxPatch((0.6, y_pos), 13.8, 1.25,
                                            boxstyle="Round,pad=0.04,rounding_size=0.08",
                                            facecolor=WHITE, edgecolor=BORDER, linewidth=1.2, zorder=2))
        
        step_str = "\n".join([f"  ▸  {s}" for s in steps])
        ax.text(0.8, y_pos + 1.15, step_str, color=INK, fontsize=8.2, va='top', linespacing=1.35, zorder=4)

        if y_pos > 0:
            ax.annotate("", xy=(7.5, y_pos - 0.05), xytext=(7.5, y_pos),
                        arrowprops=dict(arrowstyle="-|>", color=NAVY, lw=2.0, mutation_scale=12),
                        zorder=5)

    plt.tight_layout()
    fig.savefig("report_figures/fig02_methodological_flowchart.png", dpi=200, bbox_inches='tight')
    plt.close(fig)
    print("Fig 2 generated successfully.")

# -------------------------------------------------------------
# FIGURE 8: Dynamic World Remapping Scheme
# -------------------------------------------------------------
def make_fig08():
    fig = plt.figure(figsize=(10, 7.5), dpi=200, facecolor=WHITE)
    ax = fig.add_subplot(111)
    ax.set_facecolor(BG_LIGHT)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 7.5)
    ax.axis('off')

    # Header
    ax.add_patch(patches.Rectangle((0.4, 6.6), 9.2, 0.7, facecolor=NAVY, edgecolor='none'))
    ax.text(5.0, 7.05, "Google Dynamic World (9 Classes) ➔ UEHIS (4 Operational Classes)", 
            color=WHITE, fontsize=12, fontweight='bold', ha='center', va='center')
    ax.text(5.0, 6.78, "Authoritative Class Remapping Strategy for Urban Ecological Modeling", 
            color=ORANGE_PALE, fontsize=8.5, ha='center', va='center')

    # 9 DW Classes
    dw_classes = [
        ("0: Water", "#419BDF", 0),
        ("1: Trees", "#397D49", 1),
        ("2: Grass", "#88B053", 2),
        ("3: Flooded Veg", "#7A87C6", 0),
        ("4: Crops", "#E49635", 2),
        ("5: Shrub & Scrub", "#DFC35A", 1),
        ("6: Built-up", "#C4281B", 3),
        ("7: Bare Ground", "#A59B8F", 2),
        ("8: Snow & Ice", "#B39FE1", 0)
    ]

    uehis_classes = [
        ("Class 0: Tree Canopy", GREEN, "Trees, Shrub & Scrub (Native Urban Forests & Parks)"),
        ("Class 1: Impervious Surface", "#697078", "Built Structures, Concrete, Asphalt, Roadways"),
        ("Class 2: Pervious Ground", YELLOW_MOD, "Grass, Crops, Bare Ground (Unbuilt Soil Verges)"),
        ("Class 3: Water Bodies", WATER, "Rivers, Lakes, Reservoirs, Flooded Vegetation")
    ]

    # Map dynamic world indices to uehis index:
    # 0 -> 3 (Water), 1 -> 0 (Trees), 2 -> 2 (Grass), 3 -> 3 (Flooded), 4 -> 2 (Crops), 5 -> 0 (Shrub), 6 -> 1 (Built), 7 -> 2 (Bare), 8 -> 3 (Snow/Water)
    mapping = {0: 3, 1: 0, 2: 2, 3: 3, 4: 2, 5: 0, 6: 1, 7: 2, 8: 3}

    dw_y_start = 5.9
    dw_h = 0.45
    dw_step = 0.58

    # Left Column: DW Classes
    ax.text(2.0, 6.25, "Dynamic World 10m LULC", color=NAVY, fontsize=10.5, fontweight='bold', ha='center')
    dw_y_coords = {}
    for idx, (c_name, c_color, _) in enumerate(dw_classes):
        y = dw_y_start - idx * dw_step
        dw_y_coords[idx] = y + dw_h/2
        ax.add_patch(patches.FancyBboxPatch((0.6, y), 2.8, dw_h, boxstyle="Round,pad=0.03,rounding_size=0.06",
                                            facecolor=c_color, edgecolor=BORDER, linewidth=1))
        # Text
        txt_col = WHITE if idx in [0, 1, 3, 6, 7] else INK
        ax.text(2.0, y + dw_h/2, c_name, color=txt_col, fontsize=8.8, fontweight='bold', ha='center', va='center')

    # Right Column: UEHIS 4 Classes
    ax.text(7.6, 6.25, "UEHIS Operational 4-Class Scheme", color=GREEN_DARK, fontsize=10.5, fontweight='bold', ha='center')
    uehis_y_coords = {}
    u_y_start = 5.6
    u_h = 1.05
    u_step = 1.35
    for idx, (u_name, u_color, u_desc) in enumerate(uehis_classes):
        y = u_y_start - idx * u_step
        uehis_y_coords[idx] = y + u_h/2
        ax.add_patch(patches.FancyBboxPatch((5.8, y), 3.6, u_h, boxstyle="Round,pad=0.04,rounding_size=0.08",
                                            facecolor=u_color, edgecolor=BORDER, linewidth=1.5))
        ax.text(7.6, y + u_h*0.68, u_name, color=WHITE, fontsize=9.8, fontweight='bold', ha='center', va='center')
        ax.text(7.6, y + u_h*0.30, u_desc, color=WHITE, fontsize=7.2, ha='center', va='center')

    # Connecting Arrows
    for dw_idx, u_idx in mapping.items():
        y1 = dw_y_coords[dw_idx]
        y2 = uehis_y_coords[u_idx]
        color = uehis_classes[u_idx][1]
        ax.annotate("", xy=(5.75, y2), xytext=(3.45, y1),
                    arrowprops=dict(arrowstyle="-|>", color=color, lw=1.6, alpha=0.75, mutation_scale=10))

    # Bottom Callout Box
    ax.add_patch(patches.Rectangle((0.6, 0.25), 8.8, 0.45, facecolor=WARM_WHITE, edgecolor=BORDER, linewidth=1))
    ax.text(5.0, 0.47, "Note: Dry grass & barren soil merge into Pervious Ground (Class 2) to establish candidates for afforestation.",
            color=INK, fontsize=7.8, fontstyle='italic', ha='center', va='center')

    plt.tight_layout()
    fig.savefig("report_figures/fig08_dynamic_world_remapping.png", dpi=200, bbox_inches='tight')
    plt.close(fig)
    print("Fig 8 generated successfully.")

# -------------------------------------------------------------
# FIGURE 9: 75% Patch Overlap Leakage vs Buffer Split
# -------------------------------------------------------------
def make_fig09():
    fig = plt.figure(figsize=(10, 7.5), dpi=200, facecolor=WHITE)
    ax = fig.add_subplot(111)
    ax.set_facecolor(BG_LIGHT)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 7.5)
    ax.axis('off')

    # Title
    ax.add_patch(patches.Rectangle((0.4, 6.6), 9.2, 0.7, facecolor=NAVY, edgecolor='none'))
    ax.text(5.0, 7.05, "Discovery of 75% Spatial Patch Overlap Leakage vs. Buffer Split", 
            color=WHITE, fontsize=12, fontweight='bold', ha='center', va='center')
    ax.text(5.0, 6.78, "Eliminating Spatial Autocorrelation to Guarantee Scientifically Valid U-Net Validation", 
            color=ORANGE_PALE, fontsize=8.5, ha='center', va='center')

    # Left: Flawed 75% Overlap
    ax.add_patch(patches.FancyBboxPatch((0.5, 0.5), 4.2, 5.8, boxstyle="Round,pad=0.05,rounding_size=0.1",
                                        facecolor=WHITE, edgecolor=RED_CRIT, linewidth=1.5))
    ax.text(2.6, 6.0, "FLAWED: Sliding Stride Overlap", color=RED_CRIT, fontsize=10.5, fontweight='bold', ha='center')
    ax.text(2.6, 5.7, "128px Stride on 256x256 Patches = 75% Area Overlap", color=MUTED, fontsize=8, ha='center')

    # Draw Tile A
    ax.add_patch(patches.Rectangle((1.0, 3.2), 2.0, 2.0, facecolor='none', edgecolor=NAVY, linewidth=2, linestyle='--'))
    ax.text(1.3, 4.9, "Patch A (Train)", color=NAVY, fontsize=8.5, fontweight='bold')

    # Draw Tile B (shifted by 1.0 unit = 50% stride)
    ax.add_patch(patches.Rectangle((2.0, 2.2), 2.0, 2.0, facecolor='none', edgecolor=ORANGE, linewidth=2, linestyle='-.'))
    ax.text(3.0, 2.5, "Patch B (Val)", color=ORANGE_DARK, fontsize=8.5, fontweight='bold')

    # Shaded Overlap Region (1.0 x 1.0 = 50% * 50% = 25% single corner, or 50% 1D, 75% 2D mosaic)
    ax.add_patch(patches.Rectangle((2.0, 3.2), 1.0, 1.0, facecolor=RED_CRIT, alpha=0.35, edgecolor=RED_CRIT, hatch='//'))
    ax.text(2.5, 3.7, "75% Overlap\n(Shared Pixels)", color=RED_CRIT, fontsize=8, fontweight='bold', ha='center', va='center')

    # Flaw description
    flaw_text = (
        "• Stride = 128 px, Tile = 256 px\n"
        "• Overlap = 50% H × 50% V = 75% shared area\n"
        "• Identical buildings & streets appear in\n"
        "  BOTH Train and Validation sets!\n"
        "• Result: Artificial 92% validation accuracy\n"
        "  due to rote memorization (data leakage)."
    )
    ax.text(0.75, 1.85, flaw_text, color=INK, fontsize=8, va='top', linespacing=1.35)

    # Right: Corrected Geographic Buffer Partitioning
    ax.add_patch(patches.FancyBboxPatch((5.3, 0.5), 4.2, 5.8, boxstyle="Round,pad=0.05,rounding_size=0.1",
                                        facecolor=WHITE, edgecolor=GREEN_DARK, linewidth=1.5))
    ax.text(7.4, 6.0, "CORRECTED: Geographic Buffer Split", color=GREEN_DARK, fontsize=10.5, fontweight='bold', ha='center')
    ax.text(7.4, 5.7, "Zero-Leakage Spatial Polygon Clustering", color=MUTED, fontsize=8, ha='center')

    # Draw separate clusters with buffer
    ax.add_patch(patches.Rectangle((5.7, 3.5), 1.5, 1.5, facecolor=GREEN_PALE, edgecolor=GREEN_DARK, linewidth=1.8))
    ax.text(6.45, 4.25, "Train Cluster\n(322 Patches)", color=GREEN_DARK, fontsize=8.5, fontweight='bold', ha='center', va='center')

    ax.add_patch(patches.Rectangle((7.7, 3.5), 1.4, 1.5, facecolor=ORANGE_PALE, edgecolor=ORANGE_DARK, linewidth=1.8))
    ax.text(8.4, 4.25, "Test Cluster\n(209 Patches)", color=ORANGE_DARK, fontsize=8.5, fontweight='bold', ha='center', va='center')

    # Spatial Buffer Zone between them
    ax.add_patch(patches.Rectangle((7.2, 3.2), 0.5, 2.1, facecolor='#E2E8F0', edgecolor=BORDER, linestyle=':', hatch='..'))
    ax.text(7.45, 2.9, "Spatial Buffer\n(Zero Overlap)", color=MUTED, fontsize=7.5, fontweight='bold', ha='center')

    # Correction description
    fix_text = (
        "• Pune split into non-overlapping polygons\n"
        "• Broad spatial exclusion buffers isolate splits\n"
        "• Train Set: 322 Patches (Western & Central)\n"
        "• Validation Set: 49 Patches (Northern)\n"
        "• Test Set: 209 Patches (Held-Out Eastern)\n"
        "• Evaluates true spatial generalization\n"
        "  on 100% unseen urban terrain!"
    )
    ax.text(5.55, 1.85, fix_text, color=INK, fontsize=8, va='top', linespacing=1.35)

    plt.tight_layout()
    fig.savefig("report_figures/fig09_patch_leakage_vs_buffer_split.png", dpi=200, bbox_inches='tight')
    plt.close(fig)
    print("Fig 9 generated successfully.")

# -------------------------------------------------------------
# FIGURE 11: 5-Channel U-Net Architecture Diagram
# -------------------------------------------------------------
def make_fig11():
    fig = plt.figure(figsize=(15, 8.4), dpi=200, facecolor=WHITE)
    ax = fig.add_subplot(111)
    ax.set_facecolor(BG_LIGHT)
    ax.set_xlim(0, 15)
    ax.set_ylim(0, 8.4)
    ax.axis('off')

    # Header
    ax.add_patch(patches.Rectangle((0.5, 7.3), 14, 0.9, facecolor=NAVY, edgecolor='none'))
    ax.text(7.5, 7.85, "5-CHANNEL U-NET DEEP LEARNING ARCHITECTURE WITH SRTM SLOPE", 
            color=WHITE, fontsize=14, fontweight='bold', ha='center', va='center')
    ax.text(7.5, 7.5, "Contracting Encoder, 1024-Ch Bottleneck, Spatial Skip Connections & 4-Class Softmax Output", 
            color=ORANGE_PALE, fontsize=10, ha='center', va='center')

    # Input Block
    ax.add_patch(patches.FancyBboxPatch((0.6, 4.2), 1.8, 2.2, boxstyle="Round,pad=0.04,rounding_size=0.08",
                                        facecolor=WHITE, edgecolor=NAVY_SOFT, linewidth=1.8))
    ax.text(1.5, 6.1, "5-Ch Input Tensor\n(256 x 256)", color=NAVY, fontsize=9, fontweight='bold', ha='center')
    channels = ["1: Red (B4)", "2: Green (B3)", "3: Blue (B2)", "4: NDVI", "5: SRTM Slope"]
    for i, ch in enumerate(channels):
        ax.text(0.8, 5.5 - i*0.28, ch, color=GREEN_DARK if i >= 3 else INK, fontsize=8, fontweight='bold' if i >= 3 else 'normal')

    # Encoder Stages (Down)
    enc_x = [3.0, 4.5, 6.0, 7.5]
    enc_y = [4.8, 3.8, 2.8, 1.8]
    enc_ch = [64, 128, 256, 512]
    enc_dim = ["256x256", "128x128", "64x64", "32x32"]

    # Input -> Enc1
    ax.annotate("", xy=(3.0, 5.2), xytext=(2.4, 5.2), arrowprops=dict(arrowstyle="-|>", color=NAVY, lw=2))

    for i in range(4):
        # Double Conv Block
        ax.add_patch(patches.Rectangle((enc_x[i], enc_y[i]), 0.9, 1.2, facecolor=NAVY_SOFT, edgecolor=BORDER, linewidth=1))
        ax.text(enc_x[i]+0.45, enc_y[i]+0.6, f"{enc_ch[i]}\nch", color=WHITE, fontsize=8.5, fontweight='bold', ha='center', va='center')
        ax.text(enc_x[i]+0.45, enc_y[i]-0.25, enc_dim[i], color=MUTED, fontsize=7.5, ha='center')

        if i < 3:
            # Down arrow
            ax.annotate("", xy=(enc_x[i+1], enc_y[i+1]+1.0), xytext=(enc_x[i]+0.9, enc_y[i]+0.2),
                        arrowprops=dict(arrowstyle="-|>", color=RED_CRIT, lw=1.8))
            ax.text((enc_x[i]+enc_x[i+1])/2 + 0.35, (enc_y[i]+enc_y[i+1])/2 + 0.4, "MaxPool", color=RED_CRIT, fontsize=7, rotation=-25)

    # Bottleneck
    ax.add_patch(patches.Rectangle((7.5, 0.4), 1.3, 0.9, facecolor=NAVY_DARK, edgecolor=BORDER, linewidth=1))
    ax.text(8.15, 0.85, "Bottleneck\n1024 ch (16x16)", color=WHITE, fontsize=8.5, fontweight='bold', ha='center', va='center')

    # Down from Enc4 to Bottleneck
    ax.annotate("", xy=(7.9, 1.3), xytext=(7.9, 1.8), arrowprops=dict(arrowstyle="-|>", color=RED_CRIT, lw=1.8))
    # Up from Bottleneck to Dec4
    ax.annotate("", xy=(8.7, 1.8), xytext=(8.7, 1.3), arrowprops=dict(arrowstyle="-|>", color=GREEN, lw=1.8))

    # Decoder Stages (Up)
    dec_x = [8.8, 10.3, 11.8, 13.0]
    dec_y = [1.8, 2.8, 3.8, 4.8]
    dec_ch = [512, 256, 128, 64]
    dec_dim = ["32x32", "64x64", "128x128", "256x256"]

    for i in range(4):
        # Upconv Block
        ax.add_patch(patches.Rectangle((dec_x[i], dec_y[i]), 0.9, 1.2, facecolor=GREEN_DARK, edgecolor=BORDER, linewidth=1))
        ax.text(dec_x[i]+0.45, dec_y[i]+0.6, f"{dec_ch[i]}\nch", color=WHITE, fontsize=8.5, fontweight='bold', ha='center', va='center')
        ax.text(dec_x[i]+0.45, dec_y[i]-0.25, dec_dim[i], color=MUTED, fontsize=7.5, ha='center')

        # Skip Connections (Horizontal dashed arrows from Enc to Dec)
        rev_i = 3 - i
        ax.annotate("", xy=(dec_x[i], dec_y[i]+0.6), xytext=(enc_x[rev_i]+0.9, enc_y[rev_i]+0.6),
                    arrowprops=dict(arrowstyle="-|>", color=ORANGE, lw=1.5, linestyle="--"))
        ax.text((enc_x[rev_i]+dec_x[i])/2 + 0.45, enc_y[rev_i]+0.75, "Skip Connection", color=ORANGE_DARK, fontsize=7, ha='center')

        if i < 3:
            ax.annotate("", xy=(dec_x[i+1], dec_y[i+1]+0.2), xytext=(dec_x[i]+0.9, dec_y[i]+1.0),
                        arrowprops=dict(arrowstyle="-|>", color=GREEN, lw=1.8))
            ax.text((dec_x[i]+dec_x[i+1])/2 + 0.35, (dec_y[i]+dec_y[i+1])/2 + 0.4, "UpConv", color=GREEN_DARK, fontsize=7, rotation=25)

    # Final Output Layer
    ax.annotate("", xy=(14.2, 5.4), xytext=(13.9, 5.4), arrowprops=dict(arrowstyle="-|>", color=NAVY, lw=2))
    ax.add_patch(patches.FancyBboxPatch((14.1, 4.2), 0.75, 2.2, boxstyle="Round,pad=0.04,rounding_size=0.08",
                                        facecolor=WHITE, edgecolor=GREEN, linewidth=1.8))
    ax.text(14.47, 6.1, "4-Class\nSoftmax", color=GREEN_DARK, fontsize=8.5, fontweight='bold', ha='center')
    out_classes = ["0: Canopy", "1: Imperv", "2: Pervious", "3: Water"]
    out_cols = [GREEN, "#697078", YELLOW_MOD, WATER]
    for i, (oc, c) in enumerate(zip(out_classes, out_cols)):
        ax.text(14.47, 5.3 - i*0.28, oc, color=c, fontsize=7.5, fontweight='bold', ha='center')

    # Legend / Key notes
    ax.add_patch(patches.Rectangle((0.6, 0.4), 6.5, 0.9, facecolor=WHITE, edgecolor=BORDER, linewidth=1))
    ax.text(0.8, 1.05, "Key Architecture Controls:", color=NAVY, fontsize=8.5, fontweight='bold')
    ax.text(0.8, 0.8, "• Loss: Class-Weighted Cross-Entropy (Canopy 2.0, Imperv 1.0, Perv 1.5, Water 4.0)\n• Optimizer: Adam (lr=1e-3, weight_decay=1e-5, batch_size=8, 50 Epochs)\n• Topographic Channel: Normalized SRTM Slope eliminates false buildings on steep natural hills.", 
            color=INK, fontsize=7.2, va='top')

    plt.tight_layout()
    fig.savefig("report_figures/fig11_unet_architecture.png", dpi=200, bbox_inches='tight')
    plt.close(fig)
    print("Fig 11 generated successfully.")

# -------------------------------------------------------------
# FIGURE 13: 8-Way Test-Time Augmentation (TTA)
# -------------------------------------------------------------
def make_fig13():
    fig = plt.figure(figsize=(10, 7.5), dpi=200, facecolor=WHITE)
    ax = fig.add_subplot(111)
    ax.set_facecolor(BG_LIGHT)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 7.5)
    ax.axis('off')

    # Header
    ax.add_patch(patches.Rectangle((0.4, 6.6), 9.2, 0.7, facecolor=NAVY, edgecolor='none'))
    ax.text(5.0, 7.05, "8-Way Test-Time Augmentation (TTA) Transformation Scheme", 
            color=WHITE, fontsize=12, fontweight='bold', ha='center', va='center')
    ax.text(5.0, 6.78, "Evaluating Multi-View Spatial Invariance to Eliminate Prediction Orientation Bias", 
            color=ORANGE_PALE, fontsize=8.5, ha='center', va='center')

    transforms = [
        ("1. Identity", "T_0", "Native input patch"),
        ("2. Horizontal Flip", "T_h", "Mirror along vertical axis"),
        ("3. Vertical Flip", "T_v", "Mirror along horizontal axis"),
        ("4. Rotate 90°", "T_r90", "Quarter turn clockwise"),
        ("5. Rotate 180°", "T_r180", "Half turn clockwise"),
        ("6. Rotate 270°", "T_r270", "Three-quarter turn clockwise"),
        ("7. Transpose", "T_t", "Swap axes (x, y)"),
        ("8. Anti-Transpose", "T_at", "Swap axes + reverse")
    ]

    # 2 rows of 4 cards
    for idx, (t_name, t_code, t_desc) in enumerate(transforms):
        row = idx // 4
        col = idx % 4
        x = 0.6 + col * 2.25
        y = 4.7 - row * 1.6

        ax.add_patch(patches.FancyBboxPatch((x, y), 2.05, 1.35, boxstyle="Round,pad=0.03,rounding_size=0.06",
                                            facecolor=WHITE, edgecolor=BORDER, linewidth=1.2))
        ax.add_patch(patches.FancyBboxPatch((x, y+0.95), 2.05, 0.4, boxstyle="Round,pad=0.03,rounding_size=0.06",
                                            facecolor=NAVY_SOFT if row==0 else GREEN_DARK, edgecolor='none'))
        ax.text(x + 1.02, y + 1.15, t_name, color=WHITE, fontsize=8.2, fontweight='bold', ha='center', va='center')
        ax.text(x + 1.02, y + 0.65, f"[{t_code}]", color=ORANGE_DARK, fontsize=8.5, fontweight='bold', ha='center')
        ax.text(x + 1.02, y + 0.3, t_desc, color=MUTED, fontsize=7, ha='center')

    # Aggregation Flow at Bottom
    ax.add_patch(patches.FancyBboxPatch((0.6, 0.4), 8.8, 1.2, boxstyle="Round,pad=0.04,rounding_size=0.08",
                                        facecolor=WHITE, edgecolor=NAVY, linewidth=1.5))
    ax.text(5.0, 1.35, "Inference & Inverse Alignment Pipeline", color=NAVY, fontsize=9.5, fontweight='bold', ha='center')
    
    flow_steps = (
        "1. Apply 8 Spatial Transforms T_k(x)  ➔  "
        "2. Forward pass through 3-Model U-Net Ensemble  ➔  "
        "3. Apply Inverse Transform T_k^-1(P_k)\n"
        "4. Element-wise Probability Tensor Averaging:  P_final(x, y) = 1/8 Σ [ T_k^-1 ( Model_Ensemble( T_k(x) ) ) ]\n"
        "5. Final Prediction: argmax_c [ P_final(x, y, c) ]  ➔  Guarantees continuous, rotation-invariant segmentation!"
    )
    ax.text(5.0, 0.85, flow_steps, color=INK, fontsize=7.8, ha='center', va='center', linespacing=1.35)

    plt.tight_layout()
    fig.savefig("report_figures/fig13_tta_transformation_scheme.png", dpi=200, bbox_inches='tight')
    plt.close(fig)
    print("Fig 13 generated successfully.")

# -------------------------------------------------------------
# FIGURE 14: Sliding-Window Inference & Bartlett Blending
# -------------------------------------------------------------
def make_fig14():
    fig = plt.figure(figsize=(10, 7.5), dpi=200, facecolor=WHITE)
    ax = fig.add_subplot(111)
    ax.set_facecolor(BG_LIGHT)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 7.5)
    ax.axis('off')

    # Header
    ax.add_patch(patches.Rectangle((0.4, 6.6), 9.2, 0.7, facecolor=NAVY, edgecolor='none'))
    ax.text(5.0, 7.05, "Overlapping Sliding-Window Inference with 2D Bartlett Window Blending", 
            color=WHITE, fontsize=12, fontweight='bold', ha='center', va='center')
    ax.text(5.0, 6.78, "Triangular Weighting Matrix Eliminating Boundary Seams Across 256x256 Tiles", 
            color=ORANGE_PALE, fontsize=8.5, ha='center', va='center')

    # Left: Sliding Window Geometry
    ax.add_patch(patches.FancyBboxPatch((0.5, 0.5), 4.2, 5.8, boxstyle="Round,pad=0.04,rounding_size=0.08",
                                        facecolor=WHITE, edgecolor=BORDER, linewidth=1.5))
    ax.text(2.6, 6.0, "Sliding Window Geometry", color=NAVY, fontsize=10, fontweight='bold', ha='center')
    
    # Large Composite Box
    ax.add_patch(patches.Rectangle((0.8, 2.7), 3.6, 2.8, facecolor='#F1F5F9', edgecolor=BORDER, linewidth=1.5))
    ax.text(2.6, 5.25, "Full Scene Composite", color=MUTED, fontsize=8, ha='center')

    # Tile 1
    ax.add_patch(patches.Rectangle((1.0, 3.5), 1.8, 1.8, facecolor='none', edgecolor=NAVY, linewidth=2, linestyle='-'))
    ax.text(1.2, 5.05, "Tile (0,0)", color=NAVY, fontsize=8, fontweight='bold')

    # Tile 2 (128px shift = 50% stride)
    ax.add_patch(patches.Rectangle((1.9, 3.5), 1.8, 1.8, facecolor='none', edgecolor=ORANGE_DARK, linewidth=2, linestyle='--'))
    ax.text(2.8, 5.05, "Tile (0,1)", color=ORANGE_DARK, fontsize=8, fontweight='bold')

    # Stride & Padding labels
    ax.text(2.6, 3.2, "Stride = 128 px (50% Step)\nWindow = 256 x 256 px\nBorder Padding = 96 px Margin", 
            color=INK, fontsize=8, ha='center', va='center', bbox=dict(boxstyle="square,pad=0.3", facecolor=WARM_WHITE, edgecolor=BORDER))

    ax.text(2.6, 1.8, "Without Blending:\nHarsh discontinuous edge seams\nappear between adjacent tiles due to\nlack of receptive field at patch borders.",
            color=RED_CRIT, fontsize=7.8, ha='center', va='center')

    # Right: 2D Bartlett Function & Weighting
    ax.add_patch(patches.FancyBboxPatch((5.3, 0.5), 4.2, 5.8, boxstyle="Round,pad=0.04,rounding_size=0.08",
                                        facecolor=WHITE, edgecolor=BORDER, linewidth=1.5))
    ax.text(7.4, 6.0, "2D Bartlett Triangular Weighting", color=GREEN_DARK, fontsize=10, fontweight='bold', ha='center')

    # Triangular Weight Plot
    sub_ax = fig.add_axes([0.58, 0.42, 0.32, 0.28])
    x_w = np.linspace(-128, 128, 100)
    y_w = 1.0 - np.abs(x_w) / 128.0
    sub_ax.plot(x_w, y_w, color=GREEN_DARK, lw=2.5)
    sub_ax.fill_between(x_w, y_w, color=GREEN_PALE, alpha=0.5)
    sub_ax.set_title("1D Bartlett Function: w(x) = 1 - |x| / L", fontsize=7.5, color=NAVY)
    sub_ax.set_xlabel("Pixel Offset from Center (px)", fontsize=7)
    sub_ax.set_ylabel("Weight Value", fontsize=7)
    sub_ax.tick_params(labelsize=6.5)
    sub_ax.set_ylim(0, 1.1)

    right_text = (
        "2D Weight Matrix Formulation:\n"
        "W(x, y) = bartlett_2d(256, 256) = w(x) ⊗ w(y)\n\n"
        "• Center pixels receive weight = 1.0 (Maximum)\n"
        "• Edge pixels taper linearly to 0.0 (Zero seam)\n"
        "• Overlapping soft probability maps are accumulated:\n"
        "    P_scene += W × P_patch\n"
        "    Weight_acc += W\n"
        "• Normalization: P_final = P_scene / Weight_acc\n"
        "• argmax yields 100% seamless land-cover map!"
    )
    ax.text(5.5, 2.3, right_text, color=INK, fontsize=7.8, va='top', linespacing=1.35)

    plt.tight_layout()
    fig.savefig("report_figures/fig14_bartlett_window_blending.png", dpi=200, bbox_inches='tight')
    plt.close(fig)
    print("Fig 14 generated successfully.")

if __name__ == "__main__":
    make_fig01()
    make_fig02()
    make_fig08()
    make_fig09()
    make_fig11()
    make_fig13()
    make_fig14()
    print("Batch 1 completed!")

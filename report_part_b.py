"""
Part B: Technical Project Documentation Builder
Covers Sections 12 to 15 with deep academic rigor, technical code breakdowns,
mathematical derivations, audit findings, tables, and figure placeholders.
"""

import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

from report_generator_core import (
    COLOR_NAVY, COLOR_GREEN, COLOR_DARK_TEXT, COLOR_MUTED,
    format_paragraph,
    add_styled_heading, add_body_p, add_bullet_p,
    add_figure_placeholder, add_side_by_side_placeholders, create_styled_table
)
import report_data as rd

def build_part_b(doc):
    # PART B Title Header
    h_part = doc.add_paragraph()
    h_part.alignment = WD_ALIGN_PARAGRAPH.CENTER
    h_part.paragraph_format.space_before = Pt(16)
    h_part.paragraph_format.space_after = Pt(4)
    r_pb = h_part.add_run("PART B: TECHNICAL PROJECT DOCUMENTATION\n")
    r_pb.font.name = 'Times New Roman'
    r_pb.font.size = Pt(16)
    r_pb.font.bold = True
    r_pb.font.color.rgb = COLOR_NAVY
    
    r_pbs = h_part.add_run("Urban Ecosystem Health Intelligence System (UEHIS)\nComprehensive Architecture, Computer Vision Modeling, Scoring Derivations & Empirical Validation")
    r_pbs.font.name = 'Times New Roman'
    r_pbs.font.size = Pt(11)
    r_pbs.font.italic = True
    r_pbs.font.color.rgb = COLOR_DARK_TEXT

    # 12. Technical Project: UEHIS
    add_styled_heading(doc, "12. Technical Project: Urban Ecosystem Health Intelligence System", level=1)
    
    add_styled_heading(doc, "12.1 Project Overview & Repository Infrastructure", level=2)
    add_body_p(doc, 
        "The Urban Ecosystem Health Intelligence System (UEHIS) is an advanced geospatial decision-support platform engineered to transform raw multi-sensor satellite imagery and urban morphology data into verifiable, block-level ecological health intelligence. Operating across a standardized 250 m × 250 m grid lattice, the platform quantifies the severity of Urban Heat Islands (UHIs), computes localized tree canopy deficits, integrates infrastructure imperviousness, and calculates an authoritative composite index score scaled from 0 (severely degraded) to 100 (ecologically resilient).")

    add_body_p(doc, 
        "Repository Architecture: The complete source code, automated test suites, database migration schemas, and containerization recipes are maintained in the official version-controlled project repository: https://github.com/Godar72/uehis-project. The codebase is organized as a modular monorepo comprising five core Python packages (`data_ingestion/`, `feature_engineering/`, `scoring/`, `carbon_sink/`, `api/`), an interactive Next.js web application (`frontend/`), automated testing suites (`tests/`), and comprehensive architectural documentation (`docs/`).")

    add_styled_heading(doc, "12.2 UEHIS Core Team Structure & Task Allocation", level=2)
    add_body_p(doc, 
        "The development of UEHIS was executed by a collaborative four-member engineering team from the Department of AIML, SIT Pune. Technical responsibilities were cleanly decoupled across the architecture, ensuring that each member led an independent engineering domain while maintaining unified data contracts across interfaces. Table 4 outlines the team hierarchy, individual assignments, and core functional domains.")

    create_styled_table(doc, rd.TABLE_4_HEADERS, rd.TABLE_4_DATA, [Inches(w) for w in rd.TABLE_4_WIDTHS], 4, "UEHIS Core Team Structure, Individual Roles, and Domain Responsibilities.")

    add_styled_heading(doc, "12.3 Complete Technology Stack & Multi-Sensor Geospatial Datasets", level=2)
    add_body_p(doc, 
        "To satisfy the computational demands of high-resolution remote sensing, computer vision inference, and real-time spatial web mapping, UEHIS utilizes a production-grade, open-source technology stack. Python 3.12 serves as the core computational engine, integrating scientific computing libraries (NumPy, SciPy), raster manipulation wrappers (Rasterio, GDAL), vector engines (GeoPandas, Shapely), and deep learning frameworks (PyTorch). The serving and storage layer leverages PostgreSQL 15 with the PostGIS 3.3 spatial extension, while the user-facing atlas is constructed with Next.js 14 and MapLibre GL. Table 5 details each technology component and its functional role.")

    create_styled_table(doc, rd.TABLE_5_HEADERS, rd.TABLE_5_DATA, [Inches(w) for w in rd.TABLE_5_WIDTHS], 5, "Comprehensive Technology Stack, Software Libraries, and Functional Roles.")

    add_body_p(doc, 
        "The analytical integrity of UEHIS relies on multi-sensor geospatial datasets harvested from authoritative space agencies and global scientific repositories. Table 6 catalogs each ingested dataset, source authority, spatial and temporal resolutions, key bands, and its operational role within the processing pipeline.")

    create_styled_table(doc, rd.TABLE_6_HEADERS, rd.TABLE_6_DATA, [Inches(w) for w in rd.TABLE_6_WIDTHS], 6, "Primary Geospatial Datasets, Satellite Sensors, and Provenance Metadata.")

    add_styled_heading(doc, "12.4 Functional & Non-Functional System Requirements", level=2)
    add_body_p(doc, "The UEHIS architecture satisfies a rigorous set of functional and non-functional engineering requirements designed to guarantee scientific validity, operational resilience, and institutional utility:")
    
    add_bullet_p(doc, "The system must authenticate with Google Earth Engine and harvest Sentinel-2 Level-2A multi-spectral tiles and Landsat 8 Level 2 thermal rasters, applying bitmask cloud filtering to generate cloud-free median seasonal composites.", bold_prefix="FR1 (Multi-Sensor Ingestion): ")
    add_bullet_p(doc, "The computer vision module must perform pixel-level semantic segmentation on 10m satellite composites, classifying urban terrain into four physical classes: Tree Canopy, Impervious Surface, Pervious Ground, and Water Bodies.", bold_prefix="FR2 (Semantic Land-Cover Classification): ")
    add_bullet_p(doc, "The data pipeline must extract OpenStreetMap building polygons and highway linestrings, rasterize them to the 10m grid, and compute a logical OR union with U-Net predictions to ensure a physically bounded impervious surface fraction (≤ 1.0).", bold_prefix="FR3 (OSM Infrastructure Union): ")
    add_bullet_p(doc, "The scoring engine must aggregate raster zonal statistics over a permanent 250 m × 250 m lattice (EPSG:32643) anchored to fixed origin (E: 300000, N: 2000000), deriving persistent block IDs formatted as PN_<grid_x>_<grid_y>.", bold_prefix="FR4 (Authoritative Spatial Grid): ")
    add_bullet_p(doc, "The scoring module must normalize six active environmental indicators using direction-appropriate scaling, derive objective Shannon entropy dynamic weights with variance safeguards, and output clamped [0, 100] UEHI scores.", bold_prefix="FR5 (Objective UEHI Scoring): ")
    add_bullet_p(doc, "The system must categorize block scores into four ecological risk tiers (Critical, High, Moderate, Low) based on validated numerical intervals, providing tailored intervention mandates for afforestation planning.", bold_prefix="FR6 (Ecological Risk Tiering): ")
    add_bullet_p(doc, "The platform must integrate ETH Global Canopy Height data with urban allometric models to estimate above-ground biomass and localized carbon storage in metric tonnes of CO2 equivalent.", bold_prefix="FR7 (Biomass & Carbon Modeling): ")
    add_bullet_p(doc, "The web application must render dynamic vector tiles (MVT) via MapLibre GL, providing interactive ward filtering, block inspection modals, and point-radius spatial query tools.", bold_prefix="FR8 (Interactive GIS Dashboard): ")

    add_bullet_p(doc, "The web dashboard must render complex vector choropleths and handle spatial point-radius aggregations in under 2.5 seconds by leveraging PostGIS spatial indexes and server-side RPC functions.", bold_prefix="NFR1 (High-Performance Rendering): ")
    add_bullet_p(doc, "All metric geometric operations (distance, buffer, area calculation) must strictly use projected coordinate reference system EPSG:32643 (UTM Zone 43N). Degree-based spherical approximations are strictly prohibited.", bold_prefix="NFR2 (Rigorous Geodetic CRS): ")
    add_bullet_p(doc, "Every inference and scoring run must generate a machine-readable JSON manifest recording input raster paths, SHA-256 file hashes, model checkpoint hashes, and runtime execution environments.", bold_prefix="NFR3 (Scientific Reproducibility): ")
    add_bullet_p(doc, "The pipeline must support an offline mock mode (`UEHIS_TEST_NO_GEE=1`) enabling automated CI/CD pipeline execution and unit testing without active Earth Engine credentials or internet dependency.", bold_prefix="NFR4 (Offline Testing Resilience): ")
    add_bullet_p(doc, "The architecture must enforce institutional brand aesthetics, utilitarian data density, and zero superficial styling, adhering strictly to the UEHIS design rules.", bold_prefix="NFR5 (Institutional Brand Integrity): ")

    add_styled_heading(doc, "12.5 System Architecture & Modular 5-Phase Pipeline", level=2)
    add_body_p(doc, 
        "The system architecture is structured as a decoupled 5-phase data pipeline. Each phase operates as an autonomous Python package with explicit inputs, outputs, and validation contracts, preventing architectural monolithic lock-in.")

    # 12.6 Phase 1: Satellite Data Ingestion
    add_styled_heading(doc, "12.6 Phase 1: Satellite Data Ingestion & Geospatial Preprocessing", level=2)
    add_body_p(doc, 
        "Phase 1 (`data_ingestion/`) orchestrates the automated acquisition, radiometric filtering, and georeferencing of planetary remote sensing data via the Google Earth Engine Python API. The pipeline targets Sentinel-2 Level-2A Bottom-Of-Atmosphere (BOA) surface reflectance imagery and Landsat 8 Collection 2 Level 2 thermal data acquired between January 1, 2024, and March 31, 2024 — capturing the critical pre-monsoon dry season when vegetation stress and urban thermal anomalies reach maximum divergence.")

    add_body_p(doc, 
        "Cloud Filtering & Compositing: In `sentinel.py`, the ingestion engine queries the `COPERNICUS/S2_SR_HARMONIZED` image collection over the Pune Region of Interest (ROI). A scene-level metadata filter enforces `< 20%` cloud cover. Pixel-level quality screening leverages the Scene Classification Layer (SCL) bitmask, filtering out cloud shadows (bit 3), cirrus clouds (bit 8), high-probability clouds (bit 9), snow (bit 11), and saturated pixels. A temporal median reducer is applied across the filtered stack to construct a pristine, cloud-free 4-band composite (Red, Green, Blue, Near-Infrared) saved as `pune_city_composite_2026.tif`.")

    add_body_p(doc, 
        "Thermal & Infrastructure Ingestion: Landsat 8 thermal band 10 (ST_B10) is ingested to extract Land Surface Temperature (LST) in Kelvin, converted to Celsius, and calibrated via `QA_PIXEL` bitmasks. Concurrently, `osm_features.py` leverages OSMnx to harvest structural vector geometries across Pune, extracting 12,758 building polygons and 4,705 road linestrings across Kothrud alone.")

    add_side_by_side_placeholders(doc, 
        {
            "num": 3,
            "title": "Sentinel-2 Pune Composite",
            "dims": "3.1 in × 2.4 in | Aspect Ratio 4:3",
            "evidence": "Insert Sentinel-2 cloud-filtered multi-spectral composite covering Pune metropolitan area.",
            "caption": "Sentinel-2 Level-2A multi-spectral composite of Pune (Jan–Mar 2024 pre-monsoon window).",
            "image_path": "report_figures/fig03_sentinel2_pune_composite.png"
        },
        {
            "num": 4,
            "title": "Kothrud 250m Grid Lattice",
            "dims": "3.1 in × 2.4 in | Aspect Ratio 4:3",
            "evidence": "Insert spatial extent map of Kothrud pilot ward with fixed 250m grid block lattice.",
            "caption": "Kothrud pilot study area extent overlaid with the standardized 250m lattice (EPSG:32643).",
            "image_path": "report_figures/fig04_kothrud_grid_lattice.png"
        }
    )

    add_figure_placeholder(doc, 7, 
        "OpenStreetMap Infrastructure Extraction: 12,758 Building Polygons & 4,705 Road Segments", 
        "Full Page Width (6.5 in × 3.8 in) | Aspect Ratio: 16:9", 
        "Insert GIS map showing the ingested OpenStreetMap vector infrastructure: 12,758 building footprints in gray and 4,705 road network linestrings in orange overlaid across Kothrud.", 
        "Vector infrastructure layer harvested from OpenStreetMap across Kothrud, providing building and road footprints for impervious surface union.",
        image_path="report_figures/fig07_osm_infrastructure.png")

    # 12.7 Phase 2: Computer Vision, Land-Cover Classification & Modeling Experiments
    add_styled_heading(doc, "12.7 Phase 2: Computer Vision, Land-Cover Classification & Modeling Experiments", level=2)
    add_body_p(doc, 
        "Phase 2 (`feature_engineering/`) represents the core computer vision and machine learning domain of UEHIS, for which I held primary individual responsibility. The objective of this phase is to produce high-resolution, pixel-level semantic segmentations separating urban surfaces into functional ecological classes.")

    add_styled_heading(doc, "Interim NDVI Thresholding & Spectral Limitations", level=3)
    add_body_p(doc, 
        "The project initially established an interim land-cover baseline utilizing Normalized Difference Vegetation Index (NDVI) thresholding in `run_ndvi_classify.py`. NDVI is computed from Sentinel-2 bands as:")
    add_body_p(doc, "NDVI = (NIR - Red) / (NIR + Red) = (Band 8 - Band 4) / (Band 8 + Band 4)", bold_prefix="Equation (1): ")
    add_body_p(doc, 
        "The documented interim rule set categorized pixels into three classes: Tree Canopy for NDVI > 0.35, Impervious Artificial Surface for NDVI < 0.10, and Pervious Open Ground for intermediate values 0.10 ≤ NDVI ≤ 0.35. While computationally instantaneous and visually plausible over dense vegetative tracts like Vetal Tekdi, rigorous empirical auditing revealed severe classification failures. In urbanized tropical climates during the pre-monsoon period, dry senescent grass, compacted barren soil, and weathered concrete share almost identical red-to-NIR spectral reflectance profiles. Consequently, bare ground was frequently misclassified as concrete, while shadowed road verges were misclassified as vegetation, demonstrating that static spectral index thresholds cannot resolve complex urban morphologies.")

    add_side_by_side_placeholders(doc, 
        {
            "num": 5,
            "title": "Interim NDVI Heatmap",
            "dims": "3.1 in × 2.4 in | Aspect Ratio 4:3",
            "evidence": "Insert raster heatmap of Sentinel-2 NDVI across Kothrud showing vegetative gradients.",
            "caption": "Interim NDVI vegetation index raster heatmap across Kothrud (values -0.2 to +0.8).",
            "image_path": "report_figures/fig05_kothrud_ndvi_heatmap.png"
        },
        {
            "num": 6,
            "title": "Interim 3-Class Map",
            "dims": "3.1 in × 2.4 in | Aspect Ratio 4:3",
            "evidence": "Insert 3-class classified land-cover map generated by interim NDVI thresholding.",
            "caption": "Interim land-cover map: Canopy (green), Impervious (gray), and Pervious (yellow).",
            "image_path": "report_figures/fig06_interim_3class_landcover.png"
        }
    )

    add_styled_heading(doc, "Deep Learning U-Net Architecture & Multi-Modal Input Expansion", level=3)
    add_body_p(doc, 
        "To surpass scalar thresholding limitations, I designed and implemented a deep convolutional neural network based on the U-Net architecture (`unet.py`). The network follows an encoder-decoder structure with skip connections to preserve high-frequency spatial spatial boundaries:")
    add_bullet_p(doc, "Multi-Modal Input: Ingests 5 input channels: Red (Band 4), Green (Band 3), Blue (Band 2), NDVI, and SRTM-derived Topographic Slope gradient (normalized to [0, 1]). The addition of the slope channel provides essential topographic context, enabling the model to distinguish steep, unbuilt natural hillsides from low-reflectance flat asphalt.", bold_prefix="• Input Layer: ")
    add_bullet_p(doc, "Encoder (Contracting Path): 4 downsampling stages (Conv2D 3×3 -> BatchNorm -> ReLU -> Conv2D 3×3 -> BatchNorm -> ReLU -> MaxPool2D 2×2), progressively expanding feature channels: 64 -> 128 -> 256 -> 512.", bold_prefix="• Encoder: ")
    add_bullet_p(doc, "Bottleneck: 1024 channels at the lowest spatial resolution, capturing deep contextual urban spatial patterns across a wide receptive field (~200 pixels).", bold_prefix="• Bottleneck: ")
    add_bullet_p(doc, "Decoder (Expanding Path): 4 upsampling stages (TransposeConv2D 2×2 -> Concatenation of corresponding encoder skip connection -> Double ConvBlock), progressively decreasing feature dimensions: 512 -> 256 -> 128 -> 64.", bold_prefix="• Decoder: ")
    add_bullet_p(doc, "Output Layer: 1×1 convolution projecting the 64-channel feature map to 4 class logits, passed through a Softmax activation to yield class probability maps.", bold_prefix="• Output: ")

    add_figure_placeholder(doc, 11, 
        "5-Channel U-Net Deep Learning Semantic Segmentation Architecture with SRTM Slope Enhancement", 
        "Full Page Width (6.5 in × 3.8 in) | Aspect Ratio: 16:9", 
        "Insert the complete U-Net neural network architecture diagram illustrating the 5-channel input (RGB + NDVI + Slope), encoder stages (64 to 512), bottleneck (1024), skip connections, decoder stages, and 4-class output.", 
        "U-Net deep learning convolutional architecture designed for 5-channel satellite segmentation, incorporating SRTM topographic slope to resolve terrain ambiguity.",
        image_path="report_figures/fig11_unet_architecture.png")

    add_styled_heading(doc, "U-Net Hyperparameter Configuration & PyTorch Implementation", level=3)
    add_body_p(doc, 
        "The 5-channel U-Net model developed in `feature_engineering/unet.py` was trained and configured under strict hyperparameter controls:")
    add_bullet_p(doc, "Input Tensor: 5 Channels [Red (B4), Green (B3), Blue (B2), NDVI, SRTM Slope] at 256 × 256 pixel dimensions.", bold_prefix="• Input Dimensions: ")
    add_bullet_p(doc, "Batch Size & Optimization: Batch size of 8; Adam optimizer with initial learning rate = 1e-3, weight decay = 1e-5.", bold_prefix="• Optimization: ")
    add_bullet_p(doc, "Loss Objective: Class-weighted Cross-Entropy loss assigning inverse-frequency weights: Canopy (2.0), Impervious (1.0), Pervious (1.5), and Water (4.0).", bold_prefix="• Loss Function: ")
    add_bullet_p(doc, "Training Epochs & Checkpointing: 50 epochs on GPU compute; ModelCheckpoint saving best model based on minimum validation loss.", bold_prefix="• Training Lifecycle: ")
    add_bullet_p(doc, "Ensemble Strategy: 3-model soft-voting ensemble combined with 8-way Test-Time Augmentation (TTA).", bold_prefix="• Inference Mode: ")
    add_bullet_p(doc, "Tile Stitching: 2D Bartlett window (triangular weighting) with 128-pixel stride and 96-pixel boundary padding.", bold_prefix="• Blending: ")

    p_code = doc.add_paragraph()
    p_code.paragraph_format.left_indent = Inches(0.25)
    p_code.paragraph_format.space_before = Pt(4)
    p_code.paragraph_format.space_after = Pt(8)
    r_code = p_code.add_run(
        "class DoubleConv(nn.Module):\n"
        "    def __init__(self, in_channels, out_channels):\n"
        "        super().__init__()\n"
        "        self.conv = nn.Sequential(\n"
        "            nn.Conv2d(in_channels, out_channels, 3, padding=1),\n"
        "            nn.BatchNorm2d(out_channels),\n"
        "            nn.ReLU(inplace=True),\n"
        "            nn.Conv2d(out_channels, out_channels, 3, padding=1),\n"
        "            nn.BatchNorm2d(out_channels),\n"
        "            nn.ReLU(inplace=True)\n"
        "        )\n"
        "    def forward(self, x):\n"
        "        return self.conv(x)\n\n"
        "# 5 Input Channels: [Red, Green, Blue, NDVI, SRTM_Slope]\n"
        "self.inc = DoubleConv(5, 64)\n"
        "self.outc = nn.Conv2d(64, 4, kernel_size=1)  # 4 Output Classes: [Canopy, Imperv, Perv, Water]"
    )
    r_code.font.name = 'Consolas'
    r_code.font.size = Pt(8.5)
    r_code.font.color.rgb = COLOR_DARK_TEXT

    add_styled_heading(doc, "Discovery of 75% Patch Overlap Spatial Data Leakage & Geographic Buffer Partitioning", level=3)
    add_body_p(doc, 
        "During initial training experiments, multi-spectral patches (256 × 256 pixels) were extracted from the Pune composite using a sliding stride of 128 pixels. When evaluated using conventional random train/test splitting (80% train, 20% validation), the model exhibited deceptively outstanding metrics, achieving overall pixel accuracies between 88% and 92%.")

    add_body_p(doc, 
        "However, a critical scientific audit of the patch extraction geometry revealed a severe methodological flaw: because the stride (128 pixels) was exactly 50% of the tile dimension (256 pixels), neighboring patches shared a 75% spatial overlap (50% horizontal × 50% vertical overlap area). Under random dataset splitting, identical buildings, street segments, and tree clusters appeared simultaneously in both the training and validation sets. The neural network was merely memorizing geographically overlapping pixels rather than learning generalized land-cover representations — a classic case of spatial data leakage.")

    add_body_p(doc, 
        "To resolve this flaw, I formulated and executed a strict Geographic Buffer Partitioning strategy. Rather than shuffling overlapping tiles, the Pune study area was divided into geographically isolated polygons separated by significant spatial buffer zones. All patches falling within the designated training polygon were assigned to training (322 patches), while distinct geographic regions were strictly reserved for validation (49 patches) and final held-out testing (209 patches). This guaranteed that the model was evaluated exclusively on unseen urban terrain.")

    add_side_by_side_placeholders(doc, 
        {
            "num": 9,
            "title": "Spatial Leakage vs. Buffer Split",
            "dims": "3.1 in × 2.4 in | Aspect Ratio 4:3",
            "evidence": "Insert conceptual diagram showing 75% patch overlap leakage vs. buffer-separated geographic partition.",
            "caption": "Illustration of 75% spatial patch overlap causing data leakage vs. geographic buffer split.",
            "image_path": "report_figures/fig09_patch_leakage_vs_buffer_split.png"
        },
        {
            "num": 10,
            "title": "Geographic Partitioning Map",
            "dims": "3.1 in × 2.4 in | Aspect Ratio 4:3",
            "evidence": "Insert spatial map of Pune showing geographic train (322), val (49), and test (209) patch bounding boxes.",
            "caption": "Geographic partitioning across Pune ensuring zero spatial leakage between train and test domains.",
            "image_path": "report_figures/fig10_geographic_partitioning_map.png"
        }
    )

    add_side_by_side_placeholders(doc, 
        {
            "num": 8,
            "title": "Dynamic World Remapping",
            "dims": "3.1 in × 2.4 in | Aspect Ratio 4:3",
            "evidence": "Insert illustration of Dynamic World 9-class remapping to the project's 4 operational classes.",
            "caption": "Remapping scheme converting Google Dynamic World classes to UEHIS operational categories.",
            "image_path": "report_figures/fig08_dynamic_world_remapping.png"
        },
        {
            "num": 12,
            "title": "U-Net Loss Curves",
            "dims": "3.1 in × 2.4 in | Aspect Ratio 4:3",
            "evidence": "Insert PyTorch training and validation loss curves over 50 epochs with class-weighted loss.",
            "caption": "Training and validation loss progression over 50 epochs utilizing class-weighted Cross-Entropy.",
            "image_path": "report_figures/fig12_unet_loss_curves.png"
        }
    )

    add_styled_heading(doc, "3-Model Ensemble, 8-Way Test-Time Augmentation & Bartlett Window Blending", level=3)
    add_body_p(doc, 
        "To maximize segmentation stability and eliminate spatial variance, I developed an ensemble inference pipeline incorporating three distinct components:")
    add_bullet_p(doc, "3-Model Soft-Voting Ensemble: Ingests three independently trained slope-aware checkpoints (`unet_weights_slope_run1.pth`, `run2.pth`, `run3.pth`). For every patch, Softmax probability tensors are computed from each model and element-wise averaged before taking the argmax, preserving continuous probability distributions.", bold_prefix="1. Model Ensembling: ")
    add_bullet_p(doc, "8-Way Test-Time Augmentation (TTA): Each input tile undergoes eight geometric transformations (identity, horizontal flip, vertical flip, 90°, 180°, 270° rotations, transpose, and anti-transpose). Predictions are inverse-transformed back to their native spatial orientation and averaged across all 8 views prior to ensemble aggregation.", bold_prefix="2. Test-Time Augmentation: ")
    add_bullet_p(doc, "2D Bartlett Window (Triangle Weight) Blending: Full-scene inference in `run_inference.py` slides a 256×256 window with a 128-pixel stride across the composite, padded symmetrically by 96 pixels (`RECOMMENDED_BORDER_MARGIN`). Overlapping tiles are accumulated using a 2D Bartlett triangular weighting matrix, down-weighting edge pixels (which lack spatial context) in favor of center pixels from adjacent tiles, eliminating visible tile seam artifacts.", bold_prefix="3. Seamless Tile Stitching: ")

    add_side_by_side_placeholders(doc, 
        {
            "num": 13,
            "title": "8-Way TTA Scheme",
            "dims": "3.1 in × 2.4 in | Aspect Ratio 4:3",
            "evidence": "Insert schematic illustrating 8-way TTA transformations (rotations, flips, transpositions).",
            "caption": "8-way Test-Time Augmentation (TTA) transformation and inverse-alignment workflow.",
            "image_path": "report_figures/fig13_tta_transformation_scheme.png"
        },
        {
            "num": 14,
            "title": "Bartlett Window Blending",
            "dims": "3.1 in × 2.4 in | Aspect Ratio 4:3",
            "evidence": "Insert diagram illustrating overlapping tile stitching with 2D Bartlett triangular weighting.",
            "caption": "Sliding-window tile inference with 2D Bartlett window blending eliminating boundary seams.",
            "image_path": "report_figures/fig14_bartlett_window_blending.png"
        }
    )

    add_styled_heading(doc, "Quantitative Performance on Held-Out Geographic Test Set", level=3)
    add_body_p(doc, 
        "The quantitative evaluation of the final ensemble model on the 209 geographically separated held-out test patches is documented in Table 7. The model achieved exceptional precision on impervious artificial structures (94.6% IoU, 0.972 F1-score) and solid performance on tree canopy (67.9% IoU, 0.809 F1-score). Pervious ground represented the primary residual challenge (61.2% IoU) due to fine-scale transition boundaries. An external benchmark audit against Google Dynamic World revealed a 97% impervious agreement.")

    create_styled_table(doc, rd.TABLE_7_HEADERS, rd.TABLE_7_DATA, [Inches(w) for w in rd.TABLE_7_WIDTHS], 7, "Quantitative Evaluation Metrics of U-Net Semantic Segmentation on Geographic Test Set.")

    add_side_by_side_placeholders(doc, 
        {
            "num": 15,
            "title": "Test Set Confusion Matrix",
            "dims": "3.1 in × 2.4 in | Aspect Ratio 4:3",
            "evidence": "Insert normalized confusion matrix heatmap evaluating U-Net predictions on geographic test patches.",
            "caption": "Normalized confusion matrix on held-out test set showing class precision and recall.",
            "image_path": "report_figures/fig15_test_set_confusion_matrix.png"
        },
        {
            "num": 16,
            "title": "Dynamic World Benchmark",
            "dims": "3.1 in × 2.4 in | Aspect Ratio 4:3",
            "evidence": "Insert side-by-side visual comparison between U-Net segmentation and Google Dynamic World.",
            "caption": "Visual agreement comparison between U-Net inference and Google Dynamic World (97% impervious overlap).",
            "image_path": "report_figures/fig16_dynamic_world_benchmark.png"
        }
    )

    add_body_p(doc, 
        "Raster-First OSM Impervious Union: In `run_osm_raster_union.py`, the pipeline merges U-Net predictions with vector infrastructure via a pure raster-first operation. Building polygons and road linestrings are rasterized to the identical 10m grid, and the final impervious mask is computed as `final_impervious = max(unet_impervious, osm_buildings, osm_roads)`. This ensures that impervious fractions are strictly physically bounded (≤ 1.0) and avoids generating millions of intersecting vector polygons.")

    # 12.8 Phase 3: Urban Ecosystem Health Index (UEHI) Scoring Engine
    add_styled_heading(doc, "12.8 Phase 3: Urban Ecosystem Health Index (UEHI) Scoring Engine", level=2)
    add_body_p(doc, 
        "Phase 3 (`scoring/`) represents the mathematical and environmental core of the system. Operating on zonal statistics extracted across the 250 m × 250 m lattice, it computes the composite Urban Ecosystem Health Index (UEHI).")

    add_styled_heading(doc, "Authoritative 6-Factor Model & Direction-Aware Normalization", level=3)
    add_body_p(doc, 
        "The authoritative scoring pipeline evaluates six active environmental indicators, detailed in Table 8. All raw indicators are normalized to a uniform [0, 1] interval using direction-aware min-max scaling, where a value of 1.0 always represents maximum ecological health:")
    add_body_p(doc, "N_pos(x) = (x - x_min) / (x_max - x_min)   [For positive indicators: NDVI, Tree Density]", bold_prefix="Equation (2a): ")
    add_body_p(doc, "N_neg(x) = (x_max - x) / (x_max - x_min) = 1 - N_pos(x)   [For negative indicators: LST, Impervious, Pop, PM2.5]", bold_prefix="Equation (2b): ")

    create_styled_table(doc, rd.TABLE_8_HEADERS, rd.TABLE_8_DATA, [Inches(w) for w in rd.TABLE_8_WIDTHS], 8, "Active 6-Factor UEHI Indicator Configuration, Normalization Direction, and Weight Bounds.")

    add_styled_heading(doc, "Shannon Entropy Dynamic Weight Allocation", level=3)
    add_body_p(doc, 
        "Rather than assigning subjective, static weights, UEHIS employs Shannon Entropy Weighting (`entropy_weighting.py`) to derive purely objective, data-driven weights reflecting the empirical information dispersion of each indicator across the city:")
    add_bullet_p(doc, "Feature Proportion Matrix: For n blocks and m indicators, compute p_ij = N_j(x_i) / Σ_k N_j(x_k).", bold_prefix="Step 1: ")
    add_bullet_p(doc, "Information Entropy: Compute E_j = - (1 / ln(n)) Σ_i [p_ij × ln(p_ij)]. For near-zero p_ij, lim p ln(p) = 0.", bold_prefix="Step 2: ")
    add_bullet_p(doc, "Degree of Information Divergence: Compute d_j = 1 - E_j. Indicators with high spatial variability across blocks yield low entropy E_j, high divergence d_j, and consequently receive higher weights.", bold_prefix="Step 3: ")
    add_bullet_p(doc, "Normalized Objective Weights: Compute w_j = d_j / Σ_k d_k, where Σ w_j = 1.0.", bold_prefix="Step 4: ")
    add_bullet_p(doc, "Variance-Floor Safeguard: If an indicator exhibits near-zero spatial variance (e.g., regionally uniform air quality in offline test mode), d_j approaches 0. The engine activates a variance floor safeguard, preventing mathematical division-by-zero errors.", bold_prefix="Safeguard: ")

    add_side_by_side_placeholders(doc, 
        {
            "num": 17,
            "title": "Shannon Entropy Weights",
            "dims": "3.1 in × 2.4 in | Aspect Ratio 4:3",
            "evidence": "Insert bar chart illustrating entropy-derived weights across the 6 active indicators.",
            "caption": "Shannon entropy objective dynamic weight allocation across the 6 active indicators.",
            "image_path": "report_figures/fig17_shannon_entropy_weights.png"
        },
        {
            "num": 18,
            "title": "Normalization Curves",
            "dims": "3.1 in × 2.4 in | Aspect Ratio 4:3",
            "evidence": "Insert mathematical response curves illustrating positive vs. negative min-max normalization.",
            "caption": "Direction-aware min-max normalization curves mapping raw factors to the [0, 1] health interval.",
            "image_path": "report_figures/fig18_normalization_response_curves.png"
        }
    )

    add_styled_heading(doc, "Complete Scoring Formulation & Dual-Role Multipliers", level=3)
    add_body_p(doc, "The complete authoritative UEHI score for block i is computed according to Equation (3):")
    add_body_p(doc, "UEHI_i = clip_[0, 100]( (B_i + S_i) × m_i )", bold_prefix="Equation (3): ")
    add_body_p(doc, 
        "Base Score B_i: Represents the linear entropy-weighted environmental foundation, scaled to [0, 100]:\n"
        "B_i = [ Σ_j w_j × N_j(factor_j_i) ] × 100,   where B_i ∈ [0, 100].")
    add_body_p(doc, 
        "Canopy-Temperature Synergy S_i: Captures the real-world micro-climatic cooling synergy between vegetation and low surface temperatures. Blocks possessing both high vegetation and low temperature receive an additive bonus up to 10 points:\n"
        "S_i = α × N_pos(NDVI_i) × N_neg(LST_i) × 100,   with α = 0.1 and S_i ∈ [0, 10].")
    add_body_p(doc, 
        "Population Impact Multiplier m_i: Evaluates human exposure vulnerability. Because dense human exposure intensifies the public health urgency of environmental degradation, population acts as a penalty multiplier:\n"
        "m_i = 1 - β × N_pos(Pop_i),   with β = 0.3 and m_i ∈ [0.7, 1.0].\n"
        "Blocks with maximum population exposure receive a 30% score penalty (m_i = 0.7), whereas unpopulated blocks incur no penalty (m_i = 1.0).")

    add_styled_heading(doc, "Methodology Evolution & Prior Documentation Erratum", level=3)
    add_body_p(doc, 
        "To ensure complete academic transparency, this report clarifies the evolution of the UEHI methodology from preliminary project documents to the authoritative production implementation (`docs/scoring_methodology.md`):")
    add_bullet_p(doc, "Transition from 8 Indicators to 6 Factors: Preliminary conceptual drafts (`UEHI_Formula.pdf`) specified eight theoretical indicators including water_availability and biodiversity. During implementation, empirical geospatial auditing revealed that open water bodies were completely absent across vast expanses of inland urban blocks in Kothrud, causing mathematical degeneracy in entropy weighting. Consequently, water_availability was excluded from the core scoring matrix. Similarly, biodiversity is currently estimated via vegetative proxies rather than direct sensor feeds.", bold_prefix="1. Indicator Consolidation: ")
    add_bullet_p(doc, "Prior Documentation Erratum on Population Multiplier: Early documentation informally expressed the multiplier as m(i) = 1 + β × N(Pop). This formulation was mathematically erroneous regardless of normalization direction, as it rewarded rather than penalized population exposure. The authoritative formula implemented and validated in the codebase is strictly m_i = 1 - β × N_pos(Pop_i).", bold_prefix="2. Multiplier Erratum: ")

    add_styled_heading(doc, "Ecological Risk Tiers & Pilot Validation Results", level=3)
    add_body_p(doc, 
        "Final UEHI scores are classified into four actionable ecological risk tiers, detailed in Table 9. Across the Kothrud pilot study area, 256 valid blocks were evaluated, producing scores ranging from 7.4 (severely degraded commercial intersections) to 86.4 (pristine vegetative crest of Vetal Tekdi), with a normal-like mean score of 42.1. A strong Pearson correlation of 0.59 was measured between tree canopy fraction and final scores, confirming that the formula responds accurately to vegetative health.")

    create_styled_table(doc, rd.TABLE_9_HEADERS, rd.TABLE_9_DATA, [Inches(w) for w in rd.TABLE_9_WIDTHS], 9, "Ecological Risk Tier Categorization, Score Intervals, and Intervention Mandates.")

    add_side_by_side_placeholders(doc, 
        {
            "num": 19,
            "title": "Synergy & Multiplier Curves",
            "dims": "3.1 in × 2.4 in | Aspect Ratio 4:3",
            "evidence": "Insert mathematical plot illustrating Canopy-Temperature Synergy S_i and Multiplier m_i curves.",
            "caption": "Mathematical behavior of Canopy-Temperature Synergy (S_i) and Population Multiplier (m_i).",
            "image_path": "report_figures/fig19_synergy_and_multiplier_curves.png"
        },
        {
            "num": 20,
            "title": "Kothrud Score Distribution",
            "dims": "3.1 in × 2.4 in | Aspect Ratio 4:3",
            "evidence": "Insert histogram of verified UEHI scores across 256 Kothrud blocks (mean 42.1, range 7.4 to 86.4).",
            "caption": "Distribution histogram of UEHI scores across 256 validated Kothrud blocks (mean 42.1).",
            "image_path": "report_figures/fig20_kothrud_score_distribution.png"
        }
    )

    add_side_by_side_placeholders(doc, 
        {
            "num": 21,
            "title": "Kothrud UEHI Score Map",
            "dims": "3.1 in × 2.4 in | Aspect Ratio 4:3",
            "evidence": "Insert authoritative choropleth heatmap showing UEHI block scores across Kothrud ward.",
            "caption": "Authoritative block-level UEHI score choropleth map across Kothrud pilot ward.",
            "image_path": "report_figures/fig21_kothrud_uehi_score_map.png"
        },
        {
            "num": 22,
            "title": "Ecological Risk Tier Map",
            "dims": "3.1 in × 2.4 in | Aspect Ratio 4:3",
            "evidence": "Insert 4-tier risk classification map: Critical (red), High (orange), Moderate (yellow), Low (green).",
            "caption": "Four-tier ecological risk classification map identifying priority intervention zones.",
            "image_path": "report_figures/fig22_ecological_risk_tier_map.png"
        }
    )

    # 12.9 Phase 4: Environmental Interventions — Carbon Sequestration & Planting Audit
    add_styled_heading(doc, "12.9 Phase 4: Environmental Interventions — Carbon Sequestration & Planting Audit", level=2)
    add_body_p(doc, 
        "Phase 4 (`carbon_sink/`) operationalizes the environmental index into tangible restorative interventions: calculating urban carbon sequestration stocks and evaluating afforestation opportunities.")

    add_styled_heading(doc, "Biomass & Carbon Stock Estimation", level=3)
    add_body_p(doc, 
        "In `biomass.py`, localized above-ground biomass (AGB) is derived by fusing the 10m ETH Global Canopy Height 2020 raster with scientifically established urban allometric equations (McPherson et al., 2016, `urban_generic` model):")
    add_body_p(doc, "DBH = Canopy_Height / 0.45   [Diameter at Breast Height in cm, derived from height]", bold_prefix="Equation (4a): ")
    add_body_p(doc, "AGB = 0.1066 × (DBH)^2.4572   [Above-Ground Biomass in kg per tree equivalent]", bold_prefix="Equation (4b): ")
    add_body_p(doc, "Carbon_Stock = (AGB × 0.50 × (44 / 12)) / 1000   [Metric Tonnes of CO2 equivalent (t CO2e)]", bold_prefix="Equation (4c): ")

    add_body_p(doc, 
        "Validation Discrepancy Audit: An engineering audit documented in `UEHIS_FINAL_CARBON_AUDIT.md` verified that the frozen block-level production carbon path (computed via planar EPSG:32643 reductions) and the interactive study-area tool (computed via scalable spherical EPSG:4326 reductions in Earth Engine) exhibit an expected 0.69% variance on reference block `PN_370500_2049250` (405.20 t CO2e frozen vs. 402.40 t CO2e live). This discrepancy is a mathematically proven artifact of planar vs. spherical raster reprojections and represents verified system behavior.")

    add_side_by_side_placeholders(doc, 
        {
            "num": 23,
            "title": "Carbon Stock Map",
            "dims": "3.1 in × 2.4 in | Aspect Ratio 4:3",
            "evidence": "Insert block-level carbon stock estimation map across Kothrud in tonnes of CO2 equivalent.",
            "caption": "Block-level above-ground carbon stock map derived from ETH canopy height and urban allometry.",
            "image_path": "report_figures/fig23_carbon_stock_map.png"
        },
        {
            "num": 24,
            "title": "Carbon Reduction Discrepancy",
            "dims": "3.1 in × 2.4 in | Aspect Ratio 4:3",
            "evidence": "Insert visual comparison chart illustrating the 0.69% reprojection variance between planar and spherical reduction.",
            "caption": "Empirical comparison of planar UTM block reduction vs. live spherical WGS84 point-radius carbon recomputation.",
            "image_path": "report_figures/fig24_carbon_reduction_discrepancy.png"
        }
    )

    add_styled_heading(doc, "Planting-Opportunity Planning Audit & Scientific Limitations", level=3)
    add_body_p(doc, 
        "The codebase includes experimental planting recommendation algorithms (`planting_recommender.py` and `optimizer.py`). However, a rigorous scientific audit (`docs/planting_opportunity_audit.md`) established that claiming definitive 'Planting Sites' based solely on satellite pervious surface fractions is a geospatial fallacy. An unpaved road, railway easement, active sports turf, or private backyard is spectrally pervious but legally and structurally unplantable. True planting-opportunity modeling requires municipal cadastral boundaries, land ownership records, zoning laws, and underground utility easements. Consequently, UEHIS treats current planting outputs as conceptual potential maps rather than guaranteed planting sites.")

    add_figure_placeholder(doc, 25, 
        "Conceptual Block-Level Planting Opportunity Prioritization Map (Pre-Cadastral Screening)", 
        "Full Page Width (6.5 in × 3.8 in) | Aspect Ratio: 16:9", 
        "Insert GIS map showing candidate planting blocks ranked by canopy deficit and pervious surface availability prior to cadastral filtering.", 
        "Conceptual planting opportunity prioritization map screening blocks with high thermal stress and unbuilt pervious fractions.",
        image_path="report_figures/fig25_planting_opportunity_map.png")

    # 12.10 Phase 5: Interactive Web Dashboard & Spatial UI Integration
    add_styled_heading(doc, "12.10 Phase 5: Interactive Web Dashboard & Spatial UI Integration", level=2)
    add_body_p(doc, 
        "Phase 5 (`frontend/` and `api/`) delivers the public and NGO-facing interface of UEHIS. Constructed with Next.js 14, React 18, and MapLibre GL, the web application connects to a PostgreSQL/PostGIS database via an asynchronous FastAPI REST microservice.")

    add_body_p(doc, 
        "Key Interface Capabilities: The dashboard serves high-density Mapbox Vector Tiles (MVT) generated directly in PostGIS, rendering thousands of blocks smoothly at 60 FPS. Key capabilities include:")
    add_bullet_p(doc, "Interactive Vector Map: Dynamic choropleth visualization displaying block scores, risk tiers, LST heatmaps, and vegetative indices with instantaneous client-side color filtering.", bold_prefix="• ")
    add_bullet_p(doc, "Granular Block Inspector: Clicking any 250m block activates an authoritative modal deconstructing its persistent Block ID, ward affiliation, 6 normalized factor contributions, carbon stock, and recommended intervention mandate.", bold_prefix="• ")
    add_bullet_p(doc, "Point-Radius Spatial Analysis: Allows NGO coordinators to drop a pin or enter coordinates (e.g., Kothrud, Baner, Pashan) and dynamically recompute area-weighted environmental health metrics and carbon stocks across arbitrary 1km to 3km radii.", bold_prefix="• ")
    add_bullet_p(doc, "Utilitarian Institutional Design: Fully adheres to the UEHIS brand aesthetics, utilizing SEER Navy (#172B5C), UEHIS Green (#2E9B5F), high data density, and zero superficial visual clutter.", bold_prefix="• ")

    add_figure_placeholder(doc, 26, 
        "UEHIS Web Dashboard Home Interface Featuring Interactive Vector Map and Ward Filtering", 
        "Full Page Width (6.5 in × 3.8 in) | Aspect Ratio: 16:9", 
        "Insert full-width screenshot of the UEHIS interactive web dashboard home interface displaying the Pune choropleth map and ward filters.", 
        "UEHIS interactive GIS web dashboard homepage featuring high-performance MapLibre GL vector tile rendering and ward filtering.",
        image_path="report_figures/fig26_web_dashboard_home.png")

    add_side_by_side_placeholders(doc, 
        {
            "num": 27,
            "title": "Block Inspection Panel",
            "dims": "3.1 in × 2.4 in | Aspect Ratio 4:3",
            "evidence": "Insert screenshot of granular block inspection panel deconstructing factor scores and carbon.",
            "caption": "Granular block inspection panel displaying 6-factor scores, carbon stocks, and risk classification.",
            "image_path": "report_figures/fig27_block_inspection_modal.png"
        },
        {
            "num": 28,
            "title": "Point-Radius Tool",
            "dims": "3.1 in × 2.4 in | Aspect Ratio 4:3",
            "evidence": "Insert screenshot of the 1 km point-radius dynamic study area aggregation tool in action.",
            "caption": "Interactive point-radius spatial query tool aggregating area-weighted environmental scores.",
            "image_path": "report_figures/fig28_point_radius_tool.png"
        }
    )

    # 12.11 System Verification, Engineering Audits & Regression Testing
    add_styled_heading(doc, "12.11 System Verification, Engineering Audits & Regression Testing", level=2)
    add_body_p(doc, 
        "The complete UEHIS software ecosystem has undergone exhaustive engineering verification, certified in official project audit reports (`UEHIS_FINAL_PRODUCTION_AUDIT.md` and `UEHIS_FINAL_DATABASE_AUDIT_REPORT.md`):")
    add_bullet_p(doc, "Automated Test Suite: Complete Pytest test suite (`run_tests.py`) passed with 197 passing tests, 0 failures, and 1 skipped test, validating geodetic transformations, entropy weight bounds, MVT generators, and API response schemas.", bold_prefix="• Pytest Verification: ")
    add_bullet_p(doc, "Full-Scale Database Audit: Verified the complete ingestion of 5,309 Pune administrative blocks into PostGIS, confirming 5,298 scored blocks, 11 excluded boundary edge blocks, 0 duplicate IDs, 0 coordinate mismatches, and complete Row Level Security (RLS) preservation.", bold_prefix="• Database Full-Scale Audit: ")
    add_bullet_p(doc, "Phase 3 Legacy Regression: Verified that the raster-first pipeline intentionally diverges from the legacy Phase 1 vector baseline (Pearson -0.2318, median absolute difference 11.12) due to corrected building geometries and the physical OSM raster union.", bold_prefix="• Legacy Regression: ")
    add_bullet_p(doc, "Offline Testing Capability: The platform's `UEHIS_TEST_NO_GEE=1` fallback mode successfully bypasses cloud authentication, enabling robust offline execution.", bold_prefix="• Offline Fallback: ")

    add_side_by_side_placeholders(doc, 
        {
            "num": 29,
            "title": "Pytest Test Suite Report",
            "dims": "3.1 in × 2.4 in | Aspect Ratio 4:3",
            "evidence": "Insert terminal screenshot showing 197 passing Pytest tests with 0 failures.",
            "caption": "Automated software testing report: 197 unit and integration tests passing with zero failures.",
            "image_path": "report_figures/fig29_pytest_test_suite_report.png"
        },
        {
            "num": 30,
            "title": "GitHub Commit Progress",
            "dims": "3.1 in × 2.4 in | Aspect Ratio 4:3",
            "evidence": "Insert screenshot of GitHub repository commit history showing structured version control.",
            "caption": "Version control commit log from the official project repository (Godar72/uehis-project).",
            "image_path": "report_figures/fig30_github_commit_history.png"
        }
    )

    # 12.12 Individual Role & Detailed Contribution: Aditya Godar
    add_styled_heading(doc, "12.12 Individual Role & Detailed Contribution: Aditya Godar (Computer Vision)", level=2)
    add_body_p(doc, 
        "As the team member designated for Computer Vision & Modeling, my personal intellectual and technical contributions were vital to the scientific defensibility of UEHIS. In strict adherence to academic integrity guidelines, the following points detail the exact technical components conceived, engineered, and validated specifically by me:")
    
    add_bullet_p(doc, "Sentinel-2 Multi-Spectral Preprocessing & Radiometric Calibration: Engineered the Python data ingestion bridge interfacing with GEE, implementing Scene Classification Layer (SCL) bitmask filtering and median compositing to produce the cloud-free Pune multi-spectral raster.", bold_prefix="1. Satellite Preprocessing: ")
    add_bullet_p(doc, "NDVI Baseline Calibration & Spectral Failure Analysis: Implemented the initial scalar thresholding pipeline (`run_ndvi_classify.py`), and conducted the detailed radiometric error audit documenting severe spectral confusion between dry soil and concrete, establishing the empirical necessity for deep learning.", bold_prefix="2. Interim Baseline Audit: ")
    add_bullet_p(doc, "U-Net Neural Network Architecture Design: Programmed the 5-channel PyTorch U-Net semantic segmentation network (`unet.py`), configuring double convolutional blocks, batch normalization, max pooling, transpose convolutions, and skip-connection concatenations.", bold_prefix="3. Architecture Engineering: ")
    add_bullet_p(doc, "Discovery & Elimination of 75% Spatial Data Leakage: Uncovered that sliding-window patch extraction with a 128-pixel stride caused severe data leakage under random splitting. Conceived and programmed the Geographic Buffer Partitioning strategy (322 train, 49 val, 209 test patches), completely eliminating spatial autocorrelation.", bold_prefix="4. Spatial Leakage Resolution: ")
    add_bullet_p(doc, "Topographic Elevation Channel Integration: Ingested SRTM digital elevation data, derived slope gradient rasters, and incorporated slope as a 5th input channel to disambiguate steep natural hillsides from low-reflectance urban buildings.", bold_prefix="5. Topographic Enhancement: ")
    add_bullet_p(doc, "Class Imbalance Mitigation & Label Curation: Formulated class-weighted Cross-Entropy loss functions to penalize minority class errors. Audited candidate training masks and manually excised corrupted Dynamic World labels misclassifying institutional roofs as tree canopy.", bold_prefix="6. Imbalance & Quality Control: ")
    add_bullet_p(doc, "3-Model Soft-Voting Ensemble & 8-Way TTA Pipeline: Developed the multi-checkpoint model combination framework and engineered the 8-way Test-Time Augmentation transformation pipeline, substantially reducing prediction variance.", bold_prefix="7. Ensemble & TTA: ")
    add_bullet_p(doc, "Sliding-Window Inference with 2D Bartlett Window Blending: Engineered full-scene production inference (`run_inference.py`), implementing 2D triangular window weight accumulation across overlapping tiles to eliminate edge seam artifacts.", bold_prefix="8. Production Tile Blending: ")
    add_bullet_p(doc, "Benchmark Evaluation & Community Engagement: Conducted quantitative evaluations achieving 94.6% impervious and 67.9% canopy IoUs, validated 97% agreement against Dynamic World, authored unit tests, and actively participated in the 18-09-2026 field tree planting drive.", bold_prefix="9. Benchmark & Field Service: ")

    # 12.13 Known Limitations, Technical Gaps & Future Roadmaps
    add_styled_heading(doc, "12.13 Known Limitations, Technical Gaps & Future Roadmaps", level=2)
    add_body_p(doc, "In the spirit of rigorous academic and scientific integrity, several known limitations and technical gaps must be acknowledged:")
    add_bullet_p(doc, "Ground-Truth Validation Gap: Model validation was conducted against held-out geographic patches extracted from Google Dynamic World. While demonstrating 97% consistency with global benchmarks, true ground-truth validation requires physical RTK-GPS field canopy demarcations across diverse Pune wards.", bold_prefix="• ")
    add_bullet_p(doc, "Pervious-Ground Spectral Ambiguity: The pervious ground class achieved a moderate 61.2% IoU, reflecting persistent difficulty in distinguishing dry unpaved dirt from weathered concrete in single-date pre-monsoon imagery.", bold_prefix="• ")
    add_bullet_p(doc, "Absence of Cadastral Planting Masks: Planting opportunity models currently identify candidate pervious ground rather than legally accessible, public afforestation sites. Integrating municipal parcel ownership layers is an urgent future priority.", bold_prefix="• ")
    add_bullet_p(doc, "Temporal Snapshot Constraint: The current pipeline utilizes a single pre-monsoon seasonal composite (Jan–Mar 2024). Multi-temporal seasonal tracking across post-monsoon and summer windows will provide deeper phenological insights.", bold_prefix="• ")

    # 13. Summary of Work Table
    add_styled_heading(doc, "13. Summary of Work (Comparative Analysis)", level=1)
    add_body_p(doc, 
        "Table 10 provides a structured comparative synthesis contrasting the community service learning engagement (Part A) with the technical engineering architecture (Part B), summarizing the dual achievements of the UEHIS project.")
    
    create_styled_table(doc, rd.TABLE_10_HEADERS, rd.TABLE_10_DATA, [Inches(w) for w in rd.TABLE_10_WIDTHS], 10, "Comparative Summary of Service Learning (Part A) vs. Technical Engineering (Part B).")

    # 14. Conclusion & Learning Outcomes
    add_styled_heading(doc, "14. Conclusion & Learning Outcomes", level=1)
    
    add_styled_heading(doc, "14.1 Technical Learning Outcomes", level=2)
    add_body_p(doc, 
        "The conceptualization, implementation, and deployment of UEHIS afforded profound technical learning across multi-disciplinary engineering domains:")
    add_bullet_p(doc, "Planetary Remote Sensing: Mastered the Google Earth Engine Python API, multi-spectral band mathematics, scene classification bitmasks, and geodetic coordinate transformations (EPSG:4326 to EPSG:32643).", bold_prefix="1. Remote Sensing Expertise: ")
    add_bullet_p(doc, "Computer Vision in Geospatial Domains: Deepened practical expertise in designing, training, and regularizing deep convolutional neural networks (U-Net) for pixel-level semantic segmentation.", bold_prefix="2. Deep Learning Mastery: ")
    add_bullet_p(doc, "Spatial Data Science Integrity: Acquired a profound appreciation for spatial autocorrelation, discovering firsthand how overlapping satellite patch generation creates severe data leakage, and mastering geographic buffer partitioning.", bold_prefix="3. Scientific Rigor: ")
    add_bullet_p(doc, "Geospatial Database Engineering: Gained hands-on experience in PostgreSQL/PostGIS spatial indexing, PostGIS raster unions, and dynamic Mapbox Vector Tile (MVT) generation.", bold_prefix="4. Spatial Databases: ")

    add_styled_heading(doc, "14.2 Socio-Ecological & Community Implications", level=2)
    add_body_p(doc, 
        "Beyond technical competencies, this Service Learning project provided invaluable exposure to grassroots urban ecological realities. Collaborating with SEER Bharat Foundation illuminated the immense challenges non-profit organizations face when advocating for urban climate resilience. By equipping the Foundation with an objective, block-level environmental atlas, UEHIS directly transforms ad-hoc tree planting into targeted, science-backed ecological restoration, creating tangible social value for the citizens of Pune.")

    add_styled_heading(doc, "14.3 Obstacles & Overcoming Technical Challenges", level=2)
    add_body_p(doc, 
        "Multiple severe technical obstacles were encountered and successfully resolved: the discovery of 75% spatial data leakage was mitigated through geographic buffer partitioning; spectral confusion between steep barren hillsides and low-reflectance concrete was resolved by integrating SRTM slope as a 5th input channel; minority class rarity was addressed via class-weighted loss; and edge tile seam artifacts were eliminated using 2D Bartlett window blending.")

    add_styled_heading(doc, "14.4 Strategic Recommendations for SEER Bharat Foundation", level=2)
    add_bullet_p(doc, "Prioritize Afforestation in Critical Risk Blocks: Focus corporate CSR tree plantation drives strictly on blocks falling in the Critical Risk tier ([0, 25)), maximizing cooling and public health impacts.", bold_prefix="1. Priority Targeting: ")
    add_bullet_p(doc, "Pursue Municipal Cadastral Integration: Partner with the Pune Municipal Corporation (PMC) to acquire official municipal land-use and parcel ownership boundaries to construct defensible planting masks.", bold_prefix="2. Cadastral Partnerships: ")
    add_bullet_p(doc, "Leverage UEHI for Corporate CSR Funding: Utilize the system's objective baseline scores and carbon stock maps as empirical proof of need when pitching urban forestry proposals to corporate donors.", bold_prefix="3. Evidence-Based Funding: ")

    add_styled_heading(doc, "14.5 Personal Reflection", level=2)
    add_body_p(doc, 
        "Engaging in this Service Learning project has been an intensely rewarding experience that reshaped my perspective on the societal role of artificial intelligence. Transitioning from abstract machine learning benchmark datasets to messy, planetary-scale satellite imagery and on-ground tree planting demonstrated that true engineering excellence lies in solving real-world civic problems. Mentorship under Prof. Dr. Suvarna P. Patil reinforced the imperative of scientific honesty, ethical data validation, and dedicated community service.")

    # 15. References & Academic Bibliography
    add_styled_heading(doc, "15. References & Academic Bibliography", level=1)
    
    references = [
        "Brown, C. F., Brumby, S. P., Guzder-Williams, B., Birch, T., Hyde, S. B., Mazzariello, J., ... & Tait, A. M. (2022). Dynamic World, Near real-time global 10m land use land cover mapping. Scientific Data, 9(1), 251.",
        "Chave, J., Réjou-Méchain, M., Búrquez, A., Chave, E., Fyllas, N. M., Goodman, R. C., ... & Henry, M. (2014). Improved allometric models to estimate the aboveground biomass of tropical trees. Global Change Biology, 20(10), 3177-3190.",
        "Drusch, M., Del Bello, U., Carlier, S., Colin, O., Fernandez, V., Gascon, F., ... & Bargellini, P. (2012). Sentinel-2: ESA's optical high-resolution mission for GMES operational services. Remote Sensing of Environment, 120, 25-36.",
        "Gorelick, N., Hancher, M., Dixon, M., Ilyushchenko, S., Thau, D., & Moore, R. (2017). Google Earth Engine: Planetary-scale geospatial analysis for everyone. Remote Sensing of Environment, 202, 18-27.",
        "Lang, N., Jetz, W., Schindler, K., & Wegner, J. D. (2023). A high-resolution canopy height model of the Earth. Nature Ecology & Evolution, 7(11), 1778-1789.",
        "McPherson, E. G., van Doorn, N. S., & Peper, P. J. (2016). Urban tree database and allometric equations (General Technical Report PSW-GTR-253). Albany, CA: U.S. Department of Agriculture, Forest Service, Pacific Southwest Research Station.",
        "Oke, T. R. (1982). The energetic basis of the urban heat island. Quarterly Journal of the Royal Meteorological Society, 108(455), 1-24.",
        "Ronneberger, O., Fischer, P., & Brox, T. (2015). U-Net: Convolutional networks for biomedical image segmentation. In International Conference on Medical Image Computing and Computer-Assisted Intervention (pp. 234-241). Springer, Cham.",
        "Shannon, C. E. (1948). A mathematical theory of communication. The Bell System Technical Journal, 27(3), 379-423.",
        "Voogt, J. A., & Oke, T. R. (2003). Thermal remote sensing of urban climates. Remote Sensing of Environment, 86(3), 370-384.",
        "Zanaga, D., Van De Kerchove, R., De Keersmaecker, W., Souverijns, N., Brockmann, C., Quast, R., ... & Arino, O. (2021). ESA WorldCover 10 m 2020 v100. European Space Agency.",
        "SEER Bharat Foundation Records: Internship Guidelines, Progress Reports 1 to 6, Verified Logbook, and CA-2 Evaluation Dossier (Pune, 2026)."
    ]

    for idx, ref in enumerate(references):
        p_r = doc.add_paragraph()
        format_paragraph(p_r, space_before=2, space_after=4, line_spacing=1.05, align=WD_ALIGN_PARAGRAPH.JUSTIFY)
        p_r.paragraph_format.left_indent = Inches(0.3)
        p_r.paragraph_format.first_line_indent = Inches(-0.3)
        r_num = p_r.add_run(f"[{idx+1}] ")
        r_num.font.bold = True
        r_num.font.size = Pt(9.5)
        r_num.font.color.rgb = COLOR_NAVY
        r_txt = p_r.add_run(ref)
        r_txt.font.size = Pt(9.5)
        r_txt.font.color.rgb = COLOR_DARK_TEXT

    doc.add_page_break()

print("Part B builder configured successfully.")

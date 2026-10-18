"""
Part A: Service Learning Project Report Builder
Covers Sections 1 to 11 with comprehensive academic narrative, real logbook documentation across 15 weeks,
tables, and figure placeholders / real embedded logbook scans.
"""

import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

from report_generator_core import (
    COLOR_NAVY, COLOR_GREEN, COLOR_DARK_TEXT, COLOR_MUTED,
    add_styled_heading, add_body_p, add_bullet_p,
    add_figure_placeholder, add_side_by_side_placeholders, create_styled_table
)
import report_data as rd

def build_part_a(doc):
    # PART A Title Header
    h_part = doc.add_paragraph()
    h_part.alignment = WD_ALIGN_PARAGRAPH.CENTER
    h_part.paragraph_format.space_before = Pt(16)
    h_part.paragraph_format.space_after = Pt(4)
    r_pa = h_part.add_run("PART A: SERVICE LEARNING PROJECT REPORT\n")
    r_pa.font.name = 'Times New Roman'
    r_pa.font.size = Pt(16)
    r_pa.font.bold = True
    r_pa.font.color.rgb = COLOR_NAVY
    
    r_pas = h_part.add_run("Community-Engaged Environmental Data Science with SEER Bharat Foundation, Pune\nService Duration: 5th July 2026 to 16th October 2026 (120 Documented Service Hours across 15 Weeks)")
    r_pas.font.name = 'Times New Roman'
    r_pas.font.size = Pt(11)
    r_pas.font.italic = True
    r_pas.font.color.rgb = COLOR_DARK_TEXT

    # 1. About the NGO: SEER Bharat Foundation
    add_styled_heading(doc, "1. About the Project Partner: SEER Bharat Foundation", level=1)
    
    add_styled_heading(doc, "1.1 Organizational Profile, Vision, and Mission", level=2)
    add_body_p(doc, 
        "SEER Bharat Foundation is an established non-profit non-governmental organization registered under the Societies Registration Act (License No. 147561). Headquartered in Maharashtra, the Foundation maintains dual administrative and project offices: its primary operations office in Pune is situated at C-107, Armada, Parkhe Wasti, Wakad-Hinjewadi Road, Wakad, Pune – 411057, with an additional regional office at 22-A, Shram-Safalya, Ambazari Bypass Road, Near Futala Square, Nagpur – 440033. The organization operates under the digital identity of info@seerbharat.org and www.seerbharat.org.")

    add_body_p(doc, 
        "The overarching vision of SEER Bharat Foundation is to foster ecologically sustainable, climate-resilient, and socially equitable urban and semi-urban communities through scientific environmental stewardship, community empowerment, and data-driven ecological restoration. Its organizational mission encompasses four cardinal pillars:")
    
    add_bullet_p(doc, "Urban Ecological Regeneration: Restoring indigenous urban biodiversity, mitigating urban heat island intensities, and establishing micro-climate cooling buffers across densely built metropolitan zones.", bold_prefix="• ")
    add_bullet_p(doc, "Science-Backed Afforestation: Moving away from arbitrary mass sapling distribution toward ecologically optimized, native-species tree plantation strategies that ensure high survival rates and maximum carbon sequestration.", bold_prefix="• ")
    add_bullet_p(doc, "Climate Literacy & Citizen Engagement: Sensitizing urban populations, student communities, and civic stakeholders on the direct public health hazards of ambient heat stress, particulate air pollution, and tree canopy deficit.", bold_prefix="• ")
    add_bullet_p(doc, "Data-Driven Policy Advocacy: Bridging the critical gap between grassroots environmental action, municipal bodies such as the Pune Municipal Corporation (PMC), and corporate social responsibility (CSR) stakeholders through rigorous baseline data and spatial intelligence.", bold_prefix="• ")

    add_styled_heading(doc, "1.2 Leadership & Core Environmental Objectives", level=2)
    add_body_p(doc, 
        "SEER Bharat Foundation is directed under the leadership of Prof. Dr. Suvarna P. Patil (Director, SEER Bharat Foundation). Bringing extensive academic, research, and field expertise in environmental systems and sustainability, Dr. Patil has spearheaded multi-disciplinary ecological drives across Maharashtra. Under her guidance, the Foundation places paramount emphasis on methodological rigor, insisting that every on-ground ecological intervention must be grounded in empirical environmental metrics, satellite verification, and longitudinal impact tracking.")

    add_styled_heading(doc, "1.3 Key Ecological Programmes & Community Initiatives", level=2)
    add_body_p(doc, 
        "The Foundation manages multiple active environmental and community programmes across Pune and surrounding peri-urban belts:")
    
    add_bullet_p(doc, "Project Harit Pune: A city-wide afforestation campaign dedicated to planting and nurturing native Maharashtrian tree species (including Neem, Peepal, Banyan, Karanj, and Jamun) in public parks, institutional campuses, and degraded urban forest fringes such as the Vetal Tekdi and ARAI biodiversity corridors.", bold_prefix="1. ")
    add_bullet_p(doc, "Urban Carbon Sink Initiative: An environmental modeling program aimed at quantifying above-ground biomass and carbon storage across urban forest fragments, providing transparent carbon-offset auditing for CSR corporate partners.", bold_prefix="2. ")
    add_bullet_p(doc, "Community Micro-Climate Watch: Grassroots air quality and temperature observation campaigns conducted in collaboration with citizen science groups to map micro-heat pockets in high-density informal and commercial settlements.", bold_prefix="3. ")
    add_bullet_p(doc, "Youth Environmental Fellowship: An immersive service learning and internship initiative pairing engineering students with environmental practitioners to build technical solutions for urgent ecological challenges.", bold_prefix="4. ")

    add_styled_heading(doc, "1.4 Sustainable Development Goals (SDGs) Alignment", level=2)
    add_body_p(doc, 
        "The work undertaken through the UEHIS initiative directly advances multiple United Nations Sustainable Development Goals (SDGs). By quantifying urban thermal stress, vegetative canopy health, and population vulnerability, the project provides actionable tools aligned with international sustainability agendas.")
    
    create_styled_table(doc, rd.TABLE_1_HEADERS, rd.TABLE_1_DATA, [Inches(w) for w in rd.TABLE_1_WIDTHS], 1, "Alignment with United Nations Sustainable Development Goals (SDGs).")

    # 2. Introduction
    add_styled_heading(doc, "2. Introduction", level=1)
    add_body_p(doc, 
        "Rapid demographic growth, economic expansion, and physical infrastructure densification have transformed Pune from a historical garden city into a massive, heavily built metropolis. This rapid spatial expansion has generated acute environmental distress characterized by the Urban Heat Island (UHI) phenomenon — a condition where artificial built surfaces (asphalt, concrete, masonry) absorb solar radiation during daylight hours and re-radiate thermal energy overnight, resulting in ambient urban temperatures that are 3°C to 8°C higher than neighboring peri-urban and rural baselines.")

    add_body_p(doc, 
        "Compounding this thermal intensification is the widespread, uneven depletion of urban tree canopy. While elevated, protected natural reserves such as Vetal Tekdi maintain high vegetative health, adjacent residential and commercial corridors (such as Karve Road, Paud Road, and central Kothrud) suffer from severe canopy fragmentation, elevated impervious surface fractions (>75%), and chronic particulate pollution exposure. These intersecting ecological stressors degrade urban quality of life, heighten heat-related morbidity, increase residential cooling energy demand, and reduce urban climate resilience.")

    add_body_p(doc, 
        "The Urban Ecosystem Health Intelligence System (UEHIS) was conceived and developed as a collaborative Service Learning initiative between students of the Department of Artificial Intelligence and Machine Learning, Symbiosis Institute of Technology (SIT), Pune, and SEER Bharat Foundation. Designed as a geospatial decision-support platform, UEHIS combines multi-spectral satellite remote sensing, deep learning computer vision, urban infrastructure data, and advanced environmental index modeling to evaluate intra-urban ecological conditions at an unprecedented, standardized resolution of 250 m × 250 m grid blocks.")

    add_body_p(doc, 
        "Type of Work Done: Over the course of 120 officially documented service hours spanning 15 weeks (5th July 2026 to 16th October 2026), our team operated at the intersection of remote sensing data engineering, computer vision modeling, and community ecological engagement. As the team member responsible for Computer Vision & Modeling, my specific work entailed calibrating multi-spectral preprocessing pipelines, evaluating land-cover classification methodologies, uncovering and mitigating critical deep learning spatial data leakage flaws, designing a 5-channel slope-aware U-Net ensemble, validating model outputs against external benchmarks, and actively participating in on-field tree planting operations organized by SEER Bharat Foundation.")

    add_body_p(doc, 
        "Project Scope: The project established its empirical pilot baseline across the Kothrud ward of Pune (selected for its representative mosaic of dense residential fabric, commercial arteries, and adjacent hilly vegetative tracts), where a complete set of 256 validated block scores was generated. The system's architectural foundation was subsequently expanded toward the broader Pune municipal boundaries, establishing reproducible data contracts and spatial grids across 5,309 administrative blocks while maintaining a strict distinction between validated pilot baselines and broader city-wide scaling.")

    add_body_p(doc, 
        "Project Synopsis: UEHIS ingests Sentinel-2 multi-spectral composites and Landsat 8 thermal infrared imagery via Google Earth Engine, extracts 12,758 building footprints and 4,705 road segments via OpenStreetMap, applies deep learning semantic segmentation to classify urban surfaces into canopy, impervious, pervious, and water classes, and synthesizes these inputs into an authoritative 6-factor Urban Ecosystem Health Index (UEHI). The resulting block scores and ecological risk tiers are published via an interactive GIS web dashboard, directly empowering SEER Bharat Foundation to identify critical ecological vulnerability hotspots, optimize targeted tree-planting drives, and defend corporate CSR funding proposals with verifiable, scientific evidence.")

    # 3. Problems Faced in Urban Ecological Management
    add_styled_heading(doc, "3. Problems Faced in Urban Ecological Management", level=1)
    add_body_p(doc, 
        "During initial problem formulation sessions conducted with SEER Bharat Foundation leadership and field coordinators, our team identified several fundamental deficiencies plaguing contemporary urban environmental management in Pune:")
    
    add_bullet_p(doc, "Lack of Standardized, Granular Spatial Intelligence: Municipal environmental reports typically publish aggregated city-wide or ward-level indicators (e.g., average air quality or gross forest cover). These broad summaries obscure acute micro-climatic disparities, failing to reveal that one 250m block may suffer from severe heat-island stress while an adjacent block remains thermally stable.", bold_prefix="1. Spatial Resolution Deficit: ")
    add_bullet_p(doc, "Subjective & Ad-Hoc Afforestation Planning: Environmental NGOs and municipal bodies frequently select tree-planting sites based on convenience, administrative ease, or anecdotal observation rather than empirical need. Consequently, saplings are often planted in already well-shaded institutional campuses while severely heat-stressed, high-impervious residential pockets remain unmitigated.", bold_prefix="2. Arbitrary Interventions: ")
    add_bullet_p(doc, "Data Fragmentation Across Disparate Agencies: Satellite imagery, municipal building layouts, road networks, land surface temperatures, and demographic censuses exist in isolated silos across European Space Agency archives, OpenStreetMap, PMC planning records, and WorldPop datasets, with no unified computational pipeline synthesizing them.", bold_prefix="3. Siloed Geospatial Data: ")
    add_bullet_p(doc, "Absence of Transparent Baseline Metrics for Funding: Non-profit organizations face growing skepticism from corporate CSR committees and civic grant makers who demand verifiable, quantitative baselines before releasing environmental funds. Without digital maps and baseline index scores, proving intervention impact remains nearly impossible.", bold_prefix="4. Unverifiable CSR Advocacy: ")
    add_bullet_p(doc, "Failure to Account for Human Exposure Multipliers: Traditional ecological indices evaluate vegetation or temperature in isolation from human population density. An ecologically barren industrial wasteland and a densely populated informal residential settlement might share identical tree-density deficits, yet the public health urgency in the populated settlement is exponentially higher.", bold_prefix="5. Disconnected Vulnerability Modeling: ")

    # 4. Problem Statement and Objectives
    add_styled_heading(doc, "4. Problem Statement and Objectives", level=1)
    
    add_styled_heading(doc, "4.1 Problem Statement", level=2)
    add_body_p(doc, 
        "To develop, validate, and deploy an AI-driven, multi-sensor geospatial decision-support system — the Urban Ecosystem Health Intelligence System (UEHIS) — that ingests multi-spectral satellite imagery, derives high-resolution land-cover semantic segmentation, and applies an objective, entropy-weighted scoring methodology to quantify urban heat island intensity, assess ecological health at a 250m block scale, and provide SEER Bharat Foundation with a verifiable, data-driven foundation for prioritizing urban afforestation and climate resilience interventions in Pune.")

    add_styled_heading(doc, "4.2 Objectives of the Work", level=2)
    add_bullet_p(doc, "To establish an automated satellite data ingestion pipeline utilizing Google Earth Engine (GEE) to harvest cloud-masked Sentinel-2 multi-spectral surface reflectance composites and Landsat 8 thermal infrared (LST) rasters.", bold_prefix="Objective 1: ")
    add_bullet_p(doc, "To extract, cleanse, and spatially integrate urban infrastructure vector datasets (building footprints and multi-tiered road networks) from OpenStreetMap (OSM) across the study area.", bold_prefix="Objective 2: ")
    add_bullet_p(doc, "To investigate, train, and validate computer vision land-cover semantic segmentation models, specifically addressing spatial data leakage, topographic elevation effects, and class imbalance across canopy, impervious, pervious, and water categories.", bold_prefix="Objective 3: ")
    add_bullet_p(doc, "To formulate and implement the Urban Ecosystem Health Index (UEHI) scoring engine incorporating direction-aware normalization, Shannon entropy dynamic weighting, canopy-temperature synergy, and population exposure penalty multipliers.", bold_prefix="Objective 4: ")
    add_bullet_p(doc, "To execute an end-to-end empirical pilot validation across the Kothrud ward of Pune, generating validated baseline scores across 256 analysis blocks and classifying them into actionable ecological risk tiers.", bold_prefix="Objective 5: ")
    add_bullet_p(doc, "To integrate biomass allometry and canopy height models to estimate localized carbon stocks, while establishing defensible geospatial criteria for planting-opportunity planning.", bold_prefix="Objective 6: ")
    add_bullet_p(doc, "To develop a high-performance, interactive GIS web dashboard that serves vector tiles, granular block deconstructions, and point-radius spatial aggregations to non-technical NGO coordinators and civic stakeholders.", bold_prefix="Objective 7: ")
    add_bullet_p(doc, "To actively engage with SEER Bharat Foundation through 120 hours of documented service learning across 15 weeks, field stakeholder presentations, and on-ground afforestation drives.", bold_prefix="Objective 8: ")

    # 5. Project Details Table
    add_styled_heading(doc, "5. Project Administrative Details", level=1)
    add_body_p(doc, 
        "The administrative, academic, and organizational parameters governing this Service Learning project are systematically codified in Table 2 below, conforming to the prescribed documentation guidelines of the Department of AIML, Symbiosis Institute of Technology, Pune.")
    
    create_styled_table(doc, rd.TABLE_2_HEADERS, rd.TABLE_2_DATA, [Inches(w) for w in rd.TABLE_2_WIDTHS], 2, "Comprehensive Project and Service Learning Administrative Details.")

    # 6. Methodology
    add_styled_heading(doc, "6. Methodological Framework", level=1)
    add_body_p(doc, 
        "The execution of the UEHIS project follows a rigorous, multi-tiered architectural pipeline comprising five distinct, interdependent phases. The end-to-end workflow transitions seamlessly from planetary-scale satellite data harvesting to localized, block-by-block GIS decision intelligence.")

    add_body_p(doc, 
        "As illustrated in Figure 1 and Figure 2, the system pipeline is structured as follows:")
    add_bullet_p(doc, "Phase 1: Satellite Data Ingestion — Authenticates with Google Earth Engine to retrieve Sentinel-2 Level-2A multi-spectral tiles and Landsat 8 Collection 2 Level 2 thermal rasters. Applies Scene Classification Layer (SCL) cloud masking, computes Normalized Difference Vegetation Index (NDVI) bands, generates cloud-free median composites, and harvests OSM vector infrastructure layers.", bold_prefix="• ")
    add_bullet_p(doc, "Phase 2: Semantic Segmentation & Feature Engineering — Performs pixel-level land-cover classification using deep learning (U-Net) and interim NDVI thresholding, executes spatial raster unions with OSM building and road geometries, and computes urban morphology metrics.", bold_prefix="• ")
    add_bullet_p(doc, "Phase 3: UEHI Scoring Engine — Overlays an authoritative 250m × 250m grid lattice (EPSG:32643), extracts zonal raster statistics, applies direction-aware min-max normalization, computes objective Shannon entropy factor weights with variance safeguards, incorporates canopy-temperature synergy and population exposure multipliers, and outputs clipped [0, 100] UEHI scores categorized into four risk tiers.", bold_prefix="• ")
    add_bullet_p(doc, "Phase 4: Environmental Interventions & Carbon Planning — Integrates ETH Global Canopy Height data with urban allometric models (McPherson generic broadleaf equations) to calculate above-ground biomass and localized CO2 equivalent carbon stocks, while establishing geospatial constraints for planting optimization.", bold_prefix="• ")
    add_bullet_p(doc, "Phase 5: API Deployment & Interactive Dashboard — Serves vector tile endpoints, block-level inspector modals, and spatial point-radius recomputations via a FastAPI backend, Supabase PostGIS spatial database, and a Next.js / MapLibre GL frontend interface.", bold_prefix="• ")

    add_figure_placeholder(doc, 1, 
        "UEHIS High-Level System Architecture and 5-Phase Processing Pipeline", 
        "Full Page Width (6.5 in × 3.8 in) | Aspect Ratio: 16:9", 
        "Insert the authoritative UEHIS system architecture diagram illustrating Phase 1 (Ingestion), Phase 2 (CV Segmentation & OSM Union), Phase 3 (Scoring Engine), Phase 4 (Carbon & Planting), and Phase 5 (PostGIS & Dashboard).", 
        "Architectural schematic of the 5-phase UEHIS processing pipeline, showing the data flow from multi-sensor satellite ingestion to spatial decision support.",
        image_path="report_figures/fig01_uehis_system_architecture.png")

    add_figure_placeholder(doc, 2, 
        "End-to-End Methodological Workflow from Satellite Data Ingestion to Spatial Dashboard", 
        "Full Page Width (6.5 in × 3.8 in) | Aspect Ratio: 16:9", 
        "Insert the detailed methodological flowchart mapping raw satellite inputs, raster-first spatial joins, Shannon entropy weighting equations, risk classification, and final map visualization.", 
        "Detailed methodological flowchart outlining the analytical stages, algorithmic transitions, and mathematical transformations within UEHIS.",
        image_path="report_figures/fig02_methodological_flowchart.png")

    # 7. Work Done at the NGO (Weekly Documentation across 15 Weeks)
    add_styled_heading(doc, "7. Work Done at SEER Bharat Foundation (Weekly Documentation)", level=1)
    add_body_p(doc, 
        "The following section provides the comprehensive, week-by-week documentation of the Service Learning work performed under the mentorship of SEER Bharat Foundation, Pune. The documented activities span 15 continuous weeks from 5th July 2026 to 16th October 2026, totaling exactly 120 verified service hours as officially recorded in the student logbook and approved by Project Mentor Prof. Dr. Suvarna P. Patil. All entries reflect my assigned individual role as Computer Vision & Modeling engineer, documenting technical tasks, problem discoveries, team reviews, and on-field community participation.")

    # Week 1
    add_styled_heading(doc, "7.1 Week 1: Setup, Planning & Architecture Selection", level=2)
    add_body_p(doc, "Date: 05-07-2026 | Time: 4:00 PM – 9:00 PM | Hours: 5 Hours | Cumulative: 5 Hours", bold_prefix="Session Summary: ")
    add_body_p(doc, 
        "Initiated project engagement with SEER Bharat Foundation. Focused this week on researching semantic segmentation deep learning architectures suitable for satellite land-cover classification. Compared U-Net against alternatives including Mask R-CNN and DeepLabv3+, evaluating computational footprint, training dataset size requirements, and suitability for multi-spectral band inputs. Concluded that U-Net represents the optimal baseline architecture given its proven track record in remote sensing segmentation and effective spatial skip connections that preserve sharp building and tree boundaries. Studied multispectral band characteristics of Sentinel-2 (Red, Green, Blue, Near-Infrared) and reviewed the mathematical formulation of NDVI. Sketched the model's target input pipeline (4 channels: RGB + NDVI) and 3-class target output (canopy, impervious, pervious). Presented architectural options during the weekly team coordination meeting.")
    add_body_p(doc, "Future Scope: Implement U-Net encoder-decoder layers in PyTorch and establish dummy GeoTIFF forward-pass pipeline. Absent: None.", bold_prefix="Reflection & Action Plan: ")

    # Week 2
    add_styled_heading(doc, "7.2 Week 2: Initial U-Net Implementation & Satellite Pipeline", level=2)
    add_body_p(doc, "Date: 11-07-2026 | Time: 4:00 PM – 9:00 PM | Hours: 5 Hours | Cumulative: 10 Hours", bold_prefix="Session Summary: ")
    add_body_p(doc, 
        "Began implementing the U-Net convolutional architecture in code inside `feature_engineering/unet.py`. Constructed the double convolutional blocks, batch normalization, ReLU activations, max-pooling downsampling stages, and transposed convolution upsampling layers with skip concatenation. Configured the network for 4-channel input tensors and 3-class output probability maps. Formulated a dummy inference script capable of windowing GeoTIFF composites into patches and reconstructing full-scene predictions. Ran sanity checks using randomly initialized network weights to verify tensor dimension handling and coordinate integrity. Flagged the critical absence of high-quality labeled ground-truth segmentation masks for Pune as a major project risk requiring immediate attention.")
    add_body_p(doc, "Future Scope: Investigate global land-cover datasets to establish reliable pseudo-labels for network supervision. Absent: None.", bold_prefix="Reflection & Action Plan: ")

    # Week 3
    add_styled_heading(doc, "7.3 Week 3: Multispectral Preprocessing & Feature Extraction", level=2)
    add_body_p(doc, "Date: 18-07-2026 | Time: 4:00 PM – 9:00 PM | Hours: 5 Hours | Cumulative: 15 Hours", bold_prefix="Session Summary: ")
    add_body_p(doc, 
        "Explored multi-sensor feature extraction across Sentinel-2 Level-2A imagery. Calibrated atmospheric correction parameters and investigated Scene Classification Layer (SCL) masks to eliminate cloud and shadow pixels. Analyzed the spectral reflectance profiles of urban vegetation versus artificial construction across Pune. Investigated NIR/Red band ratios and identified that dry grass and barren terrain during pre-monsoon transitions produce intermediate NDVI values that overlap with weathered concrete pavements. Initiated discussions with NGO mentor Dr. Suvarna P. Patil regarding ecological ground realities in Kothrud and the necessity of separating urban tree canopy from seasonal ground shrubs.")
    add_body_p(doc, "Future Scope: Formulate interim NDVI scalar thresholds to establish a benchmark baseline before full deep learning training. Absent: None.", bold_prefix="Reflection & Action Plan: ")

    # Week 4
    add_styled_heading(doc, "7.4 Week 4: Interim NDVI Thresholding & Baseline Land-Cover Classification", level=2)
    add_body_p(doc, "Date: 25-07-2026 | Time: 4:00 PM – 9:00 PM | Hours: 5 Hours | Cumulative: 20 Hours", bold_prefix="Session Summary: ")
    add_body_p(doc, 
        "Developed and deployed the interim 3-class land-cover classification baseline in `run_ndvi_classify.py`. Derived continuous NDVI heatmaps from Sentinel-2 surface reflectance and applied calibrated scalar thresholding: Tree Canopy defined as NDVI > 0.35, Impervious Surfaces as NDVI < 0.10, and Pervious Ground as 0.10 <= NDVI <= 0.35. Exported classified GeoTIFF rasters for the Kothrud pilot ward and performed spatial overlay with OpenStreetMap building footprints. Quantified empirical classification error: static NDVI thresholding misclassified shaded building courtyards as pervious soil and barren hillsides as urban pavement. Confirmed that deep convolutional features are indispensable for resolving urban spatial context.")
    add_body_p(doc, "Future Scope: Ingest Google Dynamic World probabilistic land-cover labels to supervise deep learning training. Absent: None.", bold_prefix="Reflection & Action Plan: ")

    # Week 5
    add_styled_heading(doc, "7.5 Week 5: Pipeline Architecture & Preprocessing Synchronization", level=2)
    add_body_p(doc, "Date: 10-08-2026 | Time: 10:30 AM – 8:30 PM | Hours: 10 Hours | Cumulative: 30 Hours", bold_prefix="Session Summary: ")
    add_body_p(doc, 
        "Dedicated full-day sprint to synchronizing the data engineering and computer vision pipeline interfaces. Harmonized coordinate reference systems between GEE imagery (EPSG:4326) and projected analytical grids (UTM Zone 43N / EPSG:32643). Built automated affine transformation verifiers to prevent sub-pixel spatial drift. Formatted the master project directory structure, separating raw satellite bands, processed composite tiles, OpenStreetMap vectors, and derived segmentation masks. Conducted a mid-term technical presentation with SEER Bharat Foundation leadership, presenting interim NDVI maps and outlining the deep learning roadmap.")
    add_body_p(doc, "Future Scope: Prepare for post-CA2 model upgrade by remapping Dynamic World 9-class labels into operational project classes. Absent: None.", bold_prefix="Reflection & Action Plan: ")

    # Week 6
    add_styled_heading(doc, "7.6 Week 6: Post-CA2 Review, Dynamic World Label Ingestion & 4-Class Scheme", level=2)
    add_body_p(doc, "Dates: 16-08-2026 & 20-08-2026 | Time: 12:00 PM – 3:00 PM; 5:00 PM – 10:00 PM | Hours: 10 Hours | Cumulative: 40 Hours", bold_prefix="Session Summary: ")
    add_body_p(doc, 
        "16-08-2026 (5 Hours): Reviewed the status of the UEHIS land-cover classification component following academic CA-2 feedback. Examined the existing interim NDVI-threshold approach and conducted error analysis regarding its limitations for separating tree canopy, impervious artificial surfaces, and pervious ground. In particular, analyzed how bare soil, dry senescent grass, weathered asphalt, and concrete produce overlapping spectral characteristics, causing errors when a static threshold is used. Reviewed the codebase status of the planned U-Net model and confirmed that a scientifically validated training run on multi-spectral patches had not yet been executed.\n\n"
        "20-08-2026 (5 Hours): Investigated authoritative sources of training labels for satellite land-cover semantic segmentation across Pune. Evaluated Google Dynamic World (10m near-real-time probabilistic LULC) and ESA WorldCover. Selected Dynamic World as primary label source due to native alignment with Sentinel-2 acquisition dates. Defined the proposed four-class segmentation scheme tailored to urban ecological modeling: Class 0 = Tree Canopy, Class 1 = Impervious Surface, Class 2 = Pervious Ground, Class 3 = Water Bodies. Outlined patch-generation requirements and discussed strategy during weekly review.")
    add_body_p(doc, "Future Scope: Download Dynamic World label tiles for Pune, implement class remapping script, and generate synchronized 256×256 training patches. Absent: None.", bold_prefix="Reflection & Action Plan: ")

    # Week 7
    add_styled_heading(doc, "7.7 Week 7: Training Patch Preparation, Label Remapping & Class Imbalance Audit", level=2)
    add_body_p(doc, "Dates: 23-08-2026 & 26-08-2026 | Time: 10:00 AM – 4:00 PM; 5:00 PM – 10:00 PM | Hours: 11 Hours | Cumulative: 51 Hours", bold_prefix="Session Summary: ")
    add_body_p(doc, 
        "23-08-2026 (6 Hours): Developed the training dataset preparation pipeline for the 4-class segmentation model. Executed the label remapping script in Python, converting Dynamic World's 9 native probabilistic classes into the project's four operational classes: trees/shrub -> Canopy (0); built -> Impervious (1); grass/crops/bare ground -> Pervious (2); water/flooded veg -> Water (3). Processed the cloud-masked Sentinel-2 multi-spectral composite covering Pune and executed a sliding-window tile extraction script, cutting the composite into 256 × 256 pixel patches with an initial stride of 128 pixels. Verified that each extracted patch and label mask maintained identical spatial dimensions and geotransforms.\n\n"
        "26-08-2026 (5 Hours): Performed systematic data quality audits across the generated training patch repository. Evaluated the empirical pixel class distribution across the dataset, discovering extreme class imbalance: impervious surfaces and pervious ground dominated the urban matrix, tree canopy was moderately represented along riverfronts and hill slopes, while water bodies represented less than 3% of total pixels. Investigated model bias risks toward majority classes and organized PyTorch DataLoader pipelines.")
    add_body_p(doc, "Future Scope: Execute initial U-Net baseline training experiments and evaluate convergence behavior. Absent: None.", bold_prefix="Reflection & Action Plan: ")

    # Week 8
    add_styled_heading(doc, "7.8 Week 8: Initial Training, 75% Patch Overlap Spatial Leakage Discovery & Buffer Split", level=2)
    add_body_p(doc, "Dates: 30-08-2026 & 02-09-2026 | Time: 10:00 AM – 3:00 PM; 5:00 PM – 10:00 PM | Hours: 10 Hours | Cumulative: 61 Hours", bold_prefix="Session Summary: ")
    add_body_p(doc, 
        "30-08-2026 (5 Hours): Executed the initial baseline U-Net training experiments using standard 80/20 random patch splitting in PyTorch. Initial validation metrics appeared extraordinarily high, with overall pixel accuracy rapidly surpassing 88% to 92%. However, upon conducting a rigorous inspection of the spatial distribution of the training and validation patches, I uncovered a major scientific flaw: because the patch extraction script used a 128-pixel stride on 256×256 tiles, adjacent patches shared a 75% spatial overlap (50% horizontal × 50% vertical). Consequently, identical buildings, tree stands, and streets were simultaneously present in both the training set and the validation set. This constituted massive spatial data leakage, rendering the seemingly high accuracy metrics invalid.\n\n"
        "02-09-2026 (5 Hours): Conceptualized and formulated a geographically isolated train-validation-test partitioning strategy to completely eliminate spatial autocorrelation and leakage. Rather than randomly distributing overlapping tiles across splits, designed geographic bounding boxes separated by substantial spatial buffer zones. Commenced research into the Phase 4 carbon-sink module, investigating the ETH Global Canopy Height dataset and allometric equations (McPherson urban broadleaf model). Documented the spatial data leakage discovery in a formal technical note shared with the mentor.")
    add_body_p(doc, "Future Scope: Implement the geographic polygon partitioning script, divide the patches, and evaluate topographically enhanced inputs. Absent: None.", bold_prefix="Reflection & Action Plan: ")

    # Week 9
    add_styled_heading(doc, "7.9 Week 9: Geographic Partitioning, SRTM Slope Integration & Mask Curation", level=2)
    add_body_p(doc, "Dates: 06-09-2026 & 08-09-2026 | Time: 10:00 AM – 3:00 PM; 5:00 PM – 10:00 PM | Hours: 10 Hours | Cumulative: 71 Hours", bold_prefix="Session Summary: ")
    add_body_p(doc, 
        "06-09-2026 (5 Hours): Programmed and executed the geographic dataset partitioner in Python. Filtered the multi-spectral patches based on spatial containment within non-overlapping geographic polygons, resulting in a strictly partitioned dataset: 322 training patches, 49 validation patches, and 209 held-out test patches. To address persistent spectral ambiguity between steep barren hillsides (such as Vetal Tekdi flanks) and low-reflectance concrete structures, ingested the 30m SRTM Digital Elevation Model via GEE, derived the topographic slope gradient (0° to 90°), normalized it to [0, 1], and integrated it as a 5th input channel alongside Red, Green, Blue, and NDVI bands. Investigated class-weighted cross-entropy loss formulation.\n\n"
        "08-09-2026 (5 Hours): Integrated class-weighted Cross-Entropy loss into the PyTorch training pipeline, assigning inverse-frequency weights to penalize minority class misclassifications. Performed manual visual audits of candidate training masks against high-resolution Google Earth basemaps, uncovering three severely corrupted label patches where large, reflective institutional building roofs had been erroneously misclassified by Dynamic World as continuous dense tree canopy. Manually purged these corrupted patches from the training directory and re-indexed the dataset.")
    add_body_p(doc, "Future Scope: Train 5-channel slope-aware U-Net models on the curated dataset and analyze class-specific confusion matrices. Absent: None.", bold_prefix="Reflection & Action Plan: ")

    # Week 10
    add_styled_heading(doc, "7.10 Week 10: Slope-Aware U-Net Training, Class-Weighted Loss & Hyperparameter Tuning", level=2)
    add_body_p(doc, "Dates: 12-09-2026 & 13-09-2026 | Time: 5:00 PM – 10:00 PM; 10:00 PM – 4:00 AM | Hours: 11 Hours | Cumulative: 82 Hours", bold_prefix="Session Summary: ")
    add_body_p(doc, 
        "12-09-2026 (5 Hours): Conducted multiple training runs of the 5-channel slope-enhanced U-Net architecture across 50 epochs using the Adam optimizer (learning rate 1e-3, batch size 8). Monitored training loss, validation loss, and class-wise Intersection over Union (IoU) per epoch. Observed that the inclusion of the SRTM slope channel substantially reduced false-positive building classifications on steep natural slopes. Detailed examination of the validation error logs revealed persistent confusion between tree canopy and pervious ground along transition zones where sparse grass blends into unpaved verges.\n\n"
        "13-09-2026 (6 Hours, Overnight Run): Developed a multi-model ensemble and inference stabilization framework. Formulated a soft-voting ensemble strategy combining predictions across three independently trained slope-aware model checkpoints (`unet_weights_slope_run1.pth`, `run2.pth`, and `run3.pth`). Additionally, designed an 8-way Test-Time Augmentation (TTA) pipeline (comprising identity, horizontal flip, vertical flip, rotations by 90°, 180°, 270°, transpose, and anti-transpose) to evaluate multiple transformed orientations of each test tile. Completed overnight training runs and generated checkpoint weights.")
    add_body_p(doc, "Future Scope: Execute final held-out test set evaluation and participate in scheduled SEER Bharat Foundation field afforestation activities. Absent: None.", bold_prefix="Reflection & Action Plan: ")

    # Week 11
    add_styled_heading(doc, "7.11 Week 11: 3-Model Soft-Voting Ensemble, 8-Way TTA & On-Field Afforestation Activity", level=2)
    add_body_p(doc, "Dates: 26-09-2026 & 28-09-2026 | Time: 5:00 PM – 8:00 PM; 8:00 PM – 4:00 AM | Hours: 13 Hours | Cumulative: 95 Hours", bold_prefix="Session Summary: ")
    add_body_p(doc, 
        "26-09-2026 (5 Hours): Executed the comprehensive quantitative evaluation of the 3-model U-Net ensemble with 8-way TTA on the 209 geographically separated held-out test patches. Computed the complete confusion matrix and derived class-wise performance metrics: 94.6% IoU (0.972 F1-score) for Impervious Surfaces, 67.9% IoU (0.809 F1-score) for Tree Canopy, 73.5% IoU (0.847 F1-score) for Water Bodies, and 61.2% IoU (0.759 F1-score) for Pervious Ground, yielding an overall macro-average IoU of 74.3%. Confirmed that while canopy and impervious delineation are exceptionally sharp, pervious ground remains the primary source of residual ambiguity.\n\n"
        "28-09-2026 (8 Hours — On-Field Tree Plantation Drive): Participated directly in the community tree plantation drive organized by SEER Bharat Foundation in Pune. Engaged in hands-on field afforestation alongside Foundation volunteers, project mentor Dr. Suvarna P. Patil, and team members. Assisted in site clearing, soil preparation, digging standardized planting pits, applying organic compost, and planting native saplings (Neem, Jamun, and Karanj). Documented tree species selections and geo-locations, aligning field practices with urban forestry principles.")
    add_body_p(doc, "Future Scope: Finalize production sliding-window inference with tile blending, run pilot inference, and verify documentation. Absent: None.", bold_prefix="Reflection & Action Plan: ")

    # Week 12
    add_styled_heading(doc, "7.12 Week 12: Production Sliding-Window Inference, Bartlett Window Blending & Dynamic World Benchmark", level=2)
    add_body_p(doc, "Dates: 21-09-2026 & 27-09-2026 | Time: 5:00 PM – 10:00 PM; 10:00 AM – 3:00 PM | Hours: 10 Hours | Cumulative: 105 Hours", bold_prefix="Session Summary: ")
    add_body_p(doc, 
        "21-09-2026 (5 Hours): Implemented the production full-scene inference pipeline in `run_inference.py`. To eliminate harsh boundary seam artifacts between adjacent 256×256 tiles, implemented a 2D Bartlett window (triangular weighting) blending algorithm with a 128-pixel stride and a 96-pixel boundary margin, accumulating soft probability maps before taking the final argmax. Executed full-scene inference over the Kothrud pilot composite. Conducted an external cross-validation audit against Google Dynamic World, verifying that 97% of the model's predicted impervious pixels directly coincided with Dynamic World built-up footprints, providing strong external consistency.\n\n"
        "27-09-2026 (5 Hours): Finalized computer vision modeling technical documentation. Updated carbon-sink module to ensure canopy area is derived strictly from geometric polygon intersections rather than unclipped raster approximations. Authored unit tests in Pytest validating geometric transforms, nodata mask policies, and IoU metric computations. Prepared technical slides for project presentation and conducted review session with Project Mentor Dr. Suvarna P. Patil.")
    add_body_p(doc, "Future Scope: Transition outputs to full-stack team for PostGIS database loading and web dashboard coupling. Absent: None.", bold_prefix="Reflection & Action Plan: ")

    # Week 13
    add_styled_heading(doc, "7.13 Week 13: System Integration, PostGIS Aggregation & Web Dashboard Coupling", level=2)
    add_body_p(doc, "Date: 03-10-2026 | Time: 5:00 PM – 10:00 PM | Hours: 5 Hours | Cumulative: 110 Hours", bold_prefix="Session Summary: ")
    add_body_p(doc, 
        "Collaborated with backend and full-stack team members on database schema provisioning and spatial API integration. Ingested the finalized 256 Kothrud pilot block scores, risk tiers, and carbon stock estimates into PostgreSQL 15 / PostGIS 3.3. Configured Mapbox Vector Tile (MVT) generation pipelines (`ST_AsMVT`) to deliver fast, sub-100ms vector tile rendering to the Next.js / MapLibre GL frontend. Verified that block geometries perfectly overlay OpenStreetMap base layers without projection distortions. Built automated endpoint tests for the FastAPI service validating `/blocks`, `/blocks/{block_id}`, and `/analysis/point-radius` endpoints.")
    add_body_p(doc, "Future Scope: Conduct comprehensive municipal scenario testing and pilot demonstrations with SEER Bharat Foundation coordinators. Absent: None.", bold_prefix="Reflection & Action Plan: ")

    # Week 14
    add_styled_heading(doc, "7.14 Week 14: Municipal Stakeholder Evaluation, Kothrud Ward Validation & Stress Testing", level=2)
    add_body_p(doc, "Date: 10-10-2026 | Time: 10:00 AM – 3:00 PM | Hours: 5 Hours | Cumulative: 115 Hours", bold_prefix="Session Summary: ")
    add_body_p(doc, 
        "Conducted end-to-end stakeholder evaluation session with SEER Bharat Foundation field coordinators and community representatives. Demonstrated the interactive web dashboard, showcasing the multi-criteria block inspection modal, 1km point-radius aggregation tool, and planting opportunity screener across Kothrud. Evaluated system usability on desktop and tablet viewports. Conducted performance stress testing under concurrent API queries and verified that the database caching layer efficiently mitigates latency. Documented stakeholder feedback regarding localized sapling survival tracking and corporate CSR report generation.")
    add_body_p(doc, "Future Scope: Complete final documentation package, code freeze, logbook sign-off, and institutional handover. Absent: None.", bold_prefix="Reflection & Action Plan: ")

    # Week 15
    add_styled_heading(doc, "7.15 Week 15: Final Engineering Audit, Handover Documentation & Mentor Sign-Off", level=2)
    add_body_p(doc, "Date: 16-10-2026 | Time: 11:00 AM – 4:00 PM | Hours: 5 Hours | Cumulative: 120 Hours", bold_prefix="Session Summary: ")
    add_body_p(doc, 
        "Conducted final software audit and complete project handover. Verified that all 197 unit and integration tests execute successfully with zero regressions across satellite ingestion, deep learning inference, Shannon entropy weighting, and REST API endpoints. Consolidated repository documentation, environment configuration templates, and setup guides (`Godar72/uehis-project`). Completed final presentation review with Project Mentor Prof. Dr. Suvarna P. Patil, securing formal institutional sign-off for the cumulative 120 Service Learning hours across all 15 weeks. Formally handed over the operational UEHIS platform and pilot data assets to SEER Bharat Foundation to support ongoing urban ecological advocacy.")
    add_body_p(doc, "Final Service Learning Milestone: Successful completion and institutional verification of 120 hours of Service Learning across 15 weeks; delivery of an operational, validated geospatial AI platform to SEER Bharat Foundation. Absent: None.", bold_prefix="Milestone Completion: ")

    # 8. Day-wise and Week-wise Hours Summary Table
    add_styled_heading(doc, "8. Day-wise and Week-wise Service Learning Hours Summary", level=1)
    add_body_p(doc, 
        "Table 3 summarizes the complete distribution of the 120 officially documented service learning hours completed by Aditya Godar between 5th July 2026 and 16th October 2026 across 15 continuous weeks. The service engagement is structured into two distinct operational phases: Weeks 1 through 10 account for 82 verified hours (spanning architecture planning, baseline calibration, data leakage mitigation, and deep learning model training), while Weeks 11 through 15 account for 38 verified hours (encompassing ensemble evaluation, community afforestation fieldwork, PostGIS integration, stakeholder demonstrations, and final handover). All entries correspond strictly to verified logbook dates, approved attendance registers, and institutional progress documentation issued by SEER Bharat Foundation.")
    
    create_styled_table(doc, rd.TABLE_3_HEADERS, rd.TABLE_3_DATA, [Inches(w) for w in rd.TABLE_3_WIDTHS], 3, "Summary of Documented Service Learning Hours by Week (Aditya Godar, 120 Hours Total).")

    # 9. Student Time Log (Annexure-3)
    add_styled_heading(doc, "9. Student Time Log & Verification (Annexure-3)", level=1)
    add_body_p(doc, 
        "In compliance with the academic guidelines of Symbiosis Institute of Technology, Pune, the complete record of daily service learning hours is maintained on the official Student Time Log (Annexure-3). The log records student particulars, institutional affiliations, partner NGO coordinates, dates of service, daily task descriptions, individual hours rendered, and cumulative progress.")

    add_body_p(doc, 
        "The complete Annexure-3 record documents the full 15-week service engagement totaling exactly 120 verified hours. The records reflect subtotal milestones (82 hours for Weeks 1–10 and 38 hours for Weeks 11–15) and have been formally countersigned by Student Aditya Godar, Project Mentor Prof. Dr. Suvarna P. Patil (Director, SEER Bharat Foundation) with the official NGO seal, and Faculty Coordinator [FILL IN: Faculty Coordinator Name]. Scanned photographic evidence of institutional progress documentation is provided in Appendix A (Figures 50 and 51).")

    # 10. Photographic Evidence & Geotag Verification
    add_styled_heading(doc, "10. Photographic Evidence & Geotag Verification", level=1)
    add_body_p(doc, 
        "To satisfy institutional attendance verification standards and ensure absolute transparency, photographic evidence was captured during on-site activities, technical review meetings, and the community afforestation drive. Each image placeholder below represents a documented milestone in the Service Learning engagement.")

    add_side_by_side_placeholders(doc, 
        {
            "num": 31,
            "title": "Group Geotag Photo",
            "dims": "3.1 in × 2.4 in | Aspect Ratio 4:3",
            "evidence": "Insert group geotag photo of UEHIS student team at SEER Bharat Foundation office, Wakad, Pune.",
            "caption": "UEHIS project team at SEER Bharat Foundation office during technical review."
        },
        {
            "num": 32,
            "title": "Individual Work Geotag",
            "dims": "3.1 in × 2.4 in | Aspect Ratio 4:3",
            "evidence": "Insert individual geotag photo of Aditya Godar at the modeling workstation developing U-Net code.",
            "caption": "Aditya Godar conducting computer vision patch preparation and model training."
        }
    )

    add_side_by_side_placeholders(doc, 
        {
            "num": 33,
            "title": "Tree Plantation Drive",
            "dims": "3.1 in × 2.4 in | Aspect Ratio 4:3",
            "evidence": "Insert photo of on-field afforestation activity with SEER Bharat Foundation on 18-09-2026.",
            "caption": "Participation in SEER Bharat Foundation on-field tree plantation drive (18-09-2026)."
        },
        {
            "num": 34,
            "title": "Mentor Review Session",
            "dims": "3.1 in × 2.4 in | Aspect Ratio 4:3",
            "evidence": "Insert photo/screenshot of technical progress review with Project Mentor Prof. Dr. Suvarna P. Patil.",
            "caption": "Technical review session and presentation with Director Prof. Dr. Suvarna P. Patil."
        }
    )

    # 11. Logbook Scanned Documentation (All 15 Weeks)
    add_styled_heading(doc, "11. Logbook Scanned Documentation", level=1)
    add_body_p(doc, 
        "As mandated by the Service Learning curriculum, a physical handwritten logbook was maintained throughout the entire 15-week service engagement. The logbook records daily task summaries, problem statements, hours spent, and mentor verification stamps for every session. The complete sequential series of scanned logbook pages covering Weeks 1 through 15 (120 verified hours) is presented below:")

    # Weeks 1 & 2
    add_side_by_side_placeholders(doc, 
        {
            "num": 35,
            "title": "Logbook Scanned: Week 1",
            "dims": "3.1 in × 2.4 in | Aspect Ratio 4:3",
            "evidence": "Scanned page of signed handwritten logbook for Week 1 (05-07-2026, 5 Hours).",
            "caption": "Logbook Week 1: Setup and planning, U-Net research, and architecture selection.",
            "image_path": "Logbook_oriented/week_01.jpg"
        },
        {
            "num": 36,
            "title": "Logbook Scanned: Week 2",
            "dims": "3.1 in × 2.4 in | Aspect Ratio 4:3",
            "evidence": "Scanned page of signed handwritten logbook for Week 2 (11-07-2026, 5 Hours).",
            "caption": "Logbook Week 2: Data pipeline development, PyTorch U-Net implementation, and GeoTIFF I/O.",
            "image_path": "Logbook_oriented/week_02.jpg"
        }
    )

    # Weeks 3 & 4
    add_side_by_side_placeholders(doc, 
        {
            "num": 37,
            "title": "Logbook Scanned: Week 3",
            "dims": "3.1 in × 2.4 in | Aspect Ratio 4:3",
            "evidence": "Scanned page of signed handwritten logbook for Week 3 (18-07-2026, 5 Hours).",
            "caption": "Logbook Week 3: Multispectral preprocessing, atmospheric masking, and band ratios.",
            "image_path": "Logbook_oriented/week_03.jpg"
        },
        {
            "num": 38,
            "title": "Logbook Scanned: Week 4",
            "dims": "3.1 in × 2.4 in | Aspect Ratio 4:3",
            "evidence": "Scanned page of signed handwritten logbook for Week 4 (25-07-2026, 5 Hours).",
            "caption": "Logbook Week 4: Interim NDVI thresholding and baseline land-cover classification.",
            "image_path": "Logbook_oriented/week_04.jpg"
        }
    )

    # Weeks 5 & 6
    add_side_by_side_placeholders(doc, 
        {
            "num": 39,
            "title": "Logbook Scanned: Week 5",
            "dims": "3.1 in × 2.4 in | Aspect Ratio 4:3",
            "evidence": "Scanned page of signed handwritten logbook for Week 5 (10-08-2026, 10 Hours).",
            "caption": "Logbook Week 5: Pipeline architecture synchronization and mid-term technical review.",
            "image_path": "Logbook_oriented/week_05.jpg"
        },
        {
            "num": 40,
            "title": "Logbook Scanned: Week 6",
            "dims": "3.1 in × 2.4 in | Aspect Ratio 4:3",
            "evidence": "Scanned page of signed handwritten logbook for Week 6 (16-08 & 20-08-2026, 10 Hours).",
            "caption": "Logbook Week 6: Post-CA2 review, Dynamic World label ingestion, and 4-class scheme.",
            "image_path": "Logbook_oriented/week_06.jpg"
        }
    )

    # Weeks 7 & 8
    add_side_by_side_placeholders(doc, 
        {
            "num": 41,
            "title": "Logbook Scanned: Week 7",
            "dims": "3.1 in × 2.4 in | Aspect Ratio 4:3",
            "evidence": "Scanned page of signed handwritten logbook for Week 7 (23-08 & 26-08-2026, 11 Hours).",
            "caption": "Logbook Week 7: Training patch preparation (256x256), label remapping, and class audit.",
            "image_path": "Logbook_oriented/week_07.jpg"
        },
        {
            "num": 42,
            "title": "Logbook Scanned: Week 8",
            "dims": "3.1 in × 2.4 in | Aspect Ratio 4:3",
            "evidence": "Scanned page of signed handwritten logbook for Week 8 (30-08 & 02-09-2026, 10 Hours).",
            "caption": "Logbook Week 8: Initial training, 75% patch overlap spatial leakage discovery, and buffer split.",
            "image_path": "Logbook_oriented/week_08.jpg"
        }
    )

    # Weeks 9 & 10
    add_side_by_side_placeholders(doc, 
        {
            "num": 43,
            "title": "Logbook Scanned: Week 9",
            "dims": "3.1 in × 2.4 in | Aspect Ratio 4:3",
            "evidence": "Scanned page of signed handwritten logbook for Week 9 (06-09 & 08-09-2026, 10 Hours).",
            "caption": "Logbook Week 9: Geographic partitioning (322/49/209), SRTM slope addition, and mask curation.",
            "image_path": "Logbook_oriented/week_09.jpg"
        },
        {
            "num": 44,
            "title": "Logbook Scanned: Week 10",
            "dims": "3.1 in × 2.4 in | Aspect Ratio 4:3",
            "evidence": "Scanned page of signed handwritten logbook for Week 10 (12-09 & 13-09-2026, 11 Hours).",
            "caption": "Logbook Week 10: Slope-aware U-Net training, class-weighted loss, and hyperparameter tuning.",
            "image_path": "Logbook_oriented/week_10.jpg"
        }
    )

    # Weeks 11 & 12
    add_side_by_side_placeholders(doc, 
        {
            "num": 45,
            "title": "Logbook Scanned: Week 11",
            "dims": "3.1 in × 2.4 in | Aspect Ratio 4:3",
            "evidence": "Scanned page of signed handwritten logbook for Week 11 (26-09 & 28-09-2026, 13 Hours).",
            "caption": "Logbook Week 11: 3-model soft-voting ensemble, 8-way TTA, and on-field tree plantation.",
            "image_path": "Logbook_oriented/week_11.jpg"
        },
        {
            "num": 46,
            "title": "Logbook Scanned: Week 12",
            "dims": "3.1 in × 2.4 in | Aspect Ratio 4:3",
            "evidence": "Scanned page of signed handwritten logbook for Week 12 (21-09 & 27-09-2026, 10 Hours).",
            "caption": "Logbook Week 12: Production sliding-window inference, Bartlett window blending, and Dynamic World benchmark.",
            "image_path": "Logbook_oriented/week_12.jpg"
        }
    )

    # Weeks 13 & 14
    add_side_by_side_placeholders(doc, 
        {
            "num": 47,
            "title": "Logbook Scanned: Week 13",
            "dims": "3.1 in × 2.4 in | Aspect Ratio 4:3",
            "evidence": "Scanned page of signed handwritten logbook for Week 13 (03-10-2026, 5 Hours).",
            "caption": "Logbook Week 13: System integration, PostGIS spatial indexing, and web dashboard coupling.",
            "image_path": "Logbook_oriented/week_13.jpg"
        },
        {
            "num": 48,
            "title": "Logbook Scanned: Week 14",
            "dims": "3.1 in × 2.4 in | Aspect Ratio 4:3",
            "evidence": "Scanned page of signed handwritten logbook for Week 14 (10-10-2026, 5 Hours).",
            "caption": "Logbook Week 14: Municipal stakeholder evaluation, Kothrud ward validation, and usability testing.",
            "image_path": "Logbook_oriented/week_14.jpg"
        }
    )

    # Week 15 (Centered Portrait)
    add_figure_placeholder(doc, 49, 
        "Logbook Scanned Page: Week 15 Final Verification & Institutional Handover", 
        "Portrait Format (3.2 in × 4.2 in) | Aspect Ratio: 3:4", 
        "Scanned page of signed handwritten logbook for Week 15 (16-10-2026, 5 Hours) showing final mentor review, cumulative 120 hours completion sign-off, and official SEER Bharat Foundation stamp.", 
        "Logbook Week 15: Final software verification, project handover, cumulative 120 hours completion, and official SEER Bharat Foundation stamp.",
        image_path="Logbook_oriented/week_15.jpg")

    doc.add_page_break()

print("Part A builder configured successfully.")

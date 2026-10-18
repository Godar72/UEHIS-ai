"""
UEHIS Service Learning Report Data Structures and Text
Contains authentic data, tables, logbook entries, and detailed technical specifications.
"""

# Table 1: SDGs
TABLE_1_HEADERS = ["Sustainable Development Goal (SDG)", "Target & Global Focus", "SEER Bharat Foundation & UEHIS Alignment"]
TABLE_1_DATA = [
    [
        "SDG 11: Sustainable Cities and Communities",
        "Target 11.7: Provide universal access to safe, inclusive and accessible, green and public spaces.",
        "UEHIS quantifies intra-urban green canopy deficits across 250m blocks, identifying heat-stressed neighborhoods in Pune to prioritize public green space development."
    ],
    [
        "SDG 13: Climate Action",
        "Target 13.1: Strengthen resilience and adaptive capacity to climate-related hazards and natural disasters.",
        "Generates predictive heat island exposure metrics and multi-spectral vegetation indices to design urban cooling buffers against climate-induced heatwave extremes."
    ],
    [
        "SDG 15: Life on Land",
        "Target 15.2: Promote the implementation of sustainable management of all types of forests, halt deforestation, restore degraded forests.",
        "Calculates above-ground biomass and localized carbon sequestration potential using canopy height modeling to guide native afforestation and biodiversity corridors."
    ],
    [
        "SDG 3: Good Health and Well-Being",
        "Target 3.9: Substantially reduce the number of deaths and illnesses from hazardous chemicals and air, water and soil pollution and contamination.",
        "Fuses particulate matter (PM2.5) proxy distributions and land-surface temperature (LST) with population exposure density to mitigate urban micro-climatic respiratory stress."
    ]
]
TABLE_1_WIDTHS = [2.0, 2.0, 2.5]

# Table 2: Project Administrative Details (Matching College Submission Table)
TABLE_2_HEADERS = ["Administrative Parameter", "Institutional & Academic Specification"]
TABLE_2_DATA = [
    ["Course Name", "Service Learning (SL)"],
    ["Project Title", "Urban Ecosystem Health Intelligence System (UEHIS)"],
    ["Student Name", "Aditya Godar"],
    ["PRN Number", "24070126014"],
    ["Programme & Class", "B.Tech. Artificial Intelligence and Machine Learning | Class: AIML A1"],
    ["Group Number", "[FILL IN: Group Number]"],
    ["Individual Role", "Computer Vision & Modeling"],
    [
        "Team Members & Assigned Roles",
        "1. Aditya Singh Sengar (PRN: [FILL IN]) — Data Engineering & Infrastructure\n"
        "2. Aditya Godar (PRN: 24070126014) — Computer Vision & Modeling (Author)\n"
        "3. Abhay Chaturvedi (PRN: [FILL IN]) — Data Science, Formula Design & NGO Coordination\n"
        "4. Abhay Raj Mosaita (PRN: [FILL IN]) — Full-Stack Development, Documentation & NGO Coordination"
    ],
    ["Academic Year & Semester", "Academic Year 2026–27 | Semester V"],
    ["Faculty Coordinator", "[FILL IN: Faculty Coordinator Name], Faculty Coordinator, Service Learning"],
    ["Head of Department", "[FILL IN: Head of Department Name], Head of Department, AIML, SIT Pune"],
    [
        "Project Partner / NGO Details",
        "SEER Bharat Foundation (License No. 147561)\n"
        "Pune Office: C-107, Armada, Parkhe Wasti, Wakad-Hinjewadi Road, Wakad, Pune - 411057\n"
        "Nagpur Office: 22-A, Shram-Safalya, Ambazari Bypass Road, Near Futala Square, Nagpur-33\n"
        "Contact: info@seerbharat.org | +91 9511681037 | www.seerbharat.org"
    ],
    ["Project Mentor & NGO Director", "Prof. Dr. Suvarna P. Patil, Director, SEER Bharat Foundation (Mob: +91 9730030114)"],
    ["Duration of Service Work", "5th July 2026 to 16th October 2026 (15 Weeks)"],
    ["Total Service Learning Hours", "120 Hours (Officially Documented in Logbook and Verified by Mentor)"],
    ["Type of Work Done", "Geospatial Data Engineering, Deep Learning Semantic Segmentation, Environmental Index Modeling, On-Field Afforestation Activity"],
    ["One-Line Problem Statement", "Development of an AI-driven geospatial decision-support platform to quantify urban heat island intensity, assess ecological health, and optimize targeted afforestation interventions in Pune."]
]
TABLE_2_WIDTHS = [2.2, 4.3]

# Table 3: Summary of Service Learning Hours by Week
TABLE_3_HEADERS = ["Week No.", "Date(s)", "Scheduled Time & Modality", "Weekly Hours", "Cumulative Total"]
TABLE_3_DATA = [
    ["Week 1", "05/07/2026", "4:00 PM – 9:00 PM (Setup & Planning)", "5 Hours", "5 Hours"],
    ["Week 2", "11/07/2026", "4:00 PM – 9:00 PM (Data Pipeline Development)", "5 Hours", "10 Hours"],
    ["Week 3", "18/07/2026", "4:00 PM – 9:00 PM (Multispectral Preprocessing)", "5 Hours", "15 Hours"],
    ["Week 4", "25/07/2026", "4:00 PM – 9:00 PM (Interim Classification & Thresholds)", "5 Hours", "20 Hours"],
    ["Week 5", "10/08/2026", "10:30 AM – 8:30 PM (Pipeline Architecture & Review)", "10 Hours", "30 Hours"],
    ["Week 6", "16/08/2026, 20/08/2026", "12:00 PM – 3:00 PM; 5:00 PM – 10:00 PM", "10 Hours", "40 Hours"],
    ["Week 7", "23/08/2026, 26/08/2026", "10:00 AM – 4:00 PM; 5:00 PM – 10:00 PM", "11 Hours", "51 Hours"],
    ["Week 8", "30/08/2026, 02/09/2026", "10:00 AM – 3:00 PM; 5:00 PM – 10:00 PM", "10 Hours", "61 Hours"],
    ["Week 9", "06/09/2026, 08/09/2026", "10:00 AM – 3:00 PM; 5:00 PM – 10:00 PM", "10 Hours", "71 Hours"],
    ["Week 10", "12/09/2026, 13/09/2026", "5:00 PM – 10:00 PM; 10:00 PM – 4:00 AM", "11 Hours", "82 Hours"],
    ["Week 11", "26/09/2026, 28/09/2026", "5:00 PM – 8:00 PM; 8:00 PM – 4:00 AM", "13 Hours", "95 Hours"],
    ["Week 12", "21/09/2026, 27/09/2026", "5:00 PM – 10:00 PM; 10:00 AM – 3:00 PM", "10 Hours", "105 Hours"],
    ["Week 13", "03/10/2026", "5:00 PM – 10:00 PM (System Deployment & PostGIS)", "5 Hours", "110 Hours"],
    ["Week 14", "10/10/2026", "10:00 AM – 3:00 PM (Municipal Stakeholder Testing)", "5 Hours", "115 Hours"],
    ["Week 15", "16/10/2026", "11:00 AM – 4:00 PM (Final Handover & Verification)", "5 Hours", "120 Hours"]
]
TABLE_3_WIDTHS = [0.9, 1.8, 2.2, 0.8, 0.8]

# Table 4: UEHIS Core Team Structure
TABLE_4_HEADERS = ["Team Member", "Assigned Project Role", "Core Technical Domain & Key Responsibilities"]
TABLE_4_DATA = [
    [
        "Aditya Singh Sengar\n(PRN: [FILL IN])",
        "Data Engineering & Infrastructure",
        "Google Earth Engine (GEE) automated data ingestion pipeline; Sentinel-2 surface reflectance composite harvesting; OpenStreetMap (OSM) building and road vector extraction; PostGIS database provisioning, spatial indexing, and Docker container orchestration."
    ],
    [
        "Aditya Godar\n(PRN: 24070126014)\n[Author]",
        "Computer Vision & Modeling",
        "Interim NDVI threshold calibration; PyTorch U-Net deep learning semantic segmentation architecture; multi-spectral patch extraction; spatial data leakage discovery & resolution via geographic buffer partitioning; SRTM slope integration; 3-model soft-voting ensemble & 8-way TTA; sliding-window inference with 2D Bartlett window blending; Google Dynamic World benchmark validation."
    ],
    [
        "Abhay Chaturvedi\n(PRN: [FILL IN])",
        "Data Science, Formula Design & NGO Coordination",
        "Urban Ecosystem Health Index (UEHI) mathematical formulation; Shannon entropy-based objective dynamic weight allocation; zero-variance floor safeguards; canopy-temperature synergy formulation; population exposure penalty multiplier derivation; SEER Bharat Foundation stakeholder requirements alignment."
    ],
    [
        "Abhay Raj Mosaita\n(PRN: [FILL IN])",
        "Full-Stack Development, Documentation & NGO Coordination",
        "Interactive web dashboard development using Next.js 14 and React 18; MapLibre GL MVT vector tile rendering; FastAPI RESTful microservice development; PostGIS RPC spatial aggregation endpoints; technical documentation and NGO liaison."
    ]
]
TABLE_4_WIDTHS = [1.6, 1.6, 3.3]

# Table 5: Comprehensive Technology Stack
TABLE_5_HEADERS = ["Category", "Technology / Framework", "Version / Tool", "Architectural Function & Project Usage"]
TABLE_5_DATA = [
    ["Language", "Python", "3.12.x", "Core programming environment for data ingestion, machine learning, scoring algorithms, and backend API."],
    ["Satellite API", "Google Earth Engine", "earthengine-api 0.1.x", "Planetary-scale cloud processing of Sentinel-2 multi-spectral tiles and Landsat 8 thermal rasters."],
    ["Geospatial Rasters", "Rasterio & GDAL", "rasterio 1.5.x", "GeoTIFF I/O, CRS coordinate transformation (EPSG:4326 to EPSG:32643), windowed reads, affine transform mapping."],
    ["Geospatial Vectors", "GeoPandas & Shapely", "geopandas 0.14.x", "Vector polygon handling, spatial joins, OSM vector extraction, boundary validation, and geometric buffer computations."],
    ["Deep Learning", "PyTorch & Torchvision", "torch 2.1.x", "Building, training, and running inference for the 5-channel U-Net semantic segmentation models."],
    ["Urban Infrastructure", "OSMnx", "osmnx 1.9.x", "Querying and extracting municipal building footprints and multi-tiered street networks from OpenStreetMap."],
    ["Backend Web API", "FastAPI & Uvicorn", "fastapi 0.110.x", "High-performance asynchronous REST API serving block-level scores, risk tiers, and GeoJSON boundaries."],
    ["Spatial Database", "PostgreSQL & PostGIS", "PostgreSQL 15 + PostGIS 3.3", "ACID-compliant storage, R-Tree spatial indexing, Mapbox Vector Tiles (MVT) generation, and block-level aggregation."],
    ["Frontend UI", "Next.js & React", "Next.js 14 / React 18", "Modern map-centric interactive web interface providing geospatial visualization and ward-level filtering."],
    ["Mapping Engine", "MapLibre GL", "maplibre-gl 4.x", "Client-side WebGL rendering of high-density vector tiles, custom choropleth heatmaps, and spatial inspection panels."]
]
TABLE_5_WIDTHS = [1.2, 1.6, 1.4, 2.3]

# Table 6: Primary Geospatial Datasets
TABLE_6_HEADERS = ["Dataset / Sensor", "Source Authority", "Spatial / Temporal Resolution", "Key Bands & Attributes Used", "Role in UEHIS Pipeline"]
TABLE_6_DATA = [
    [
        "Sentinel-2 MSI (Level-2A)",
        "European Space Agency (ESA) via GEE",
        "10m native spatial resolution;\nJan–Mar 2024 composite",
        "B2 (Blue), B3 (Green), B4 (Red), B8 (NIR), Scene Classification Layer (SCL)",
        "Primary multispectral imagery for cloud-masked composite generation, NDVI calculation, and U-Net 4-class segmentation."
    ],
    [
        "Landsat 8 TIRS (Collection 2 L2)",
        "USGS / NASA via GEE",
        "30m native (resampled to 10m/250m);\nJan–Mar 2024 seasonal window",
        "Band 10 (Thermal Infrared),\nQA_PIXEL bitmask",
        "Quantification of Land Surface Temperature (LST) and urban heat island intensity across municipal blocks."
    ],
    [
        "SRTM Digital Elevation Model",
        "NASA / USGS via GEE",
        "30m spatial resolution;\nGlobal coverage",
        "Elevation (m), Derived Slope gradient (0°–90°)",
        "Topographic feature engineering; provides slope angle as 5th input channel to U-Net to disambiguate hilly terrain from urban structures."
    ],
    [
        "OpenStreetMap (OSM)",
        "OpenStreetMap Contributors via Overpass API",
        "Vector geometric primitives (polygons, linestrings)",
        "Building polygons, highway network classifications",
        "Urban infrastructure footprint extraction and physical impervious surface union calculation."
    ],
    [
        "WorldPop Population Density",
        "University of Southampton / WorldPop",
        "100m spatial resolution;\nConstrained 2020 dataset",
        "Estimated population count per grid cell",
        "Human exposure evaluation; serves as input for the negative-direction base score and the population penalty multiplier."
    ],
    [
        "Google Dynamic World",
        "Google & World Resources Institute",
        "10m spatial resolution;\nNear-real-time global LULC",
        "Probabilistic land-cover classes (built, trees, grass, water)",
        "Training label extraction and external benchmark validation for the U-Net computer vision segmentation pipeline."
    ],
    [
        "ETH Global Canopy Height",
        "ETH Zurich (Lang et al., 2023)",
        "10m spatial resolution;\nGlobal coverage",
        "Canopy height in meters (0–50m)",
        "Above-ground biomass modeling and block-level carbon stock estimation via allometric equations."
    ]
]
TABLE_6_WIDTHS = [1.3, 1.2, 1.3, 1.3, 1.4]

# Table 7: Quantitative Evaluation Metrics (U-Net on Geographic Test Set)
TABLE_7_HEADERS = ["Target Land-Cover Class", "Training Sample Support", "Intersection over Union (IoU)", "F1-Score / Dice Coeff.", "Classification Assessment"]
TABLE_7_DATA = [
    ["Impervious Surface (Built/Roads)", "High (Urban core dominant)", "94.6%", "0.972", "Outstanding precision; sharp delineation of building boundaries and arterial road networks."],
    ["Tree Canopy (Vegetation)", "Moderate (Parks, hill slopes)", "67.9%", "0.809", "Strong vegetative separation; minor boundary ambiguity along semi-dense urban verges."],
    ["Water Bodies (Rivers/Streams)", "Low (Mutha river corridor)", "73.5%", "0.847", "Reliable waterbody detection; stabilized via class-weighted loss despite severe pixel rarity."],
    ["Pervious Ground (Bare Soil/Grass)", "Moderate (Vacant plots, dry open)", "61.2%", "0.759", "Moderate performance; exhibits localized spectral confusion with weathered concrete and dry soil."],
    ["Overall Macro Average", "580 Patches Total", "74.3%", "0.847", "Robust spatial generalization verified on geographically separated held-out test patches."]
]
TABLE_7_WIDTHS = [1.8, 1.4, 1.1, 1.0, 1.2]

# Table 8: Active 6-Factor UEHI Indicator Configuration
TABLE_8_HEADERS = ["Indicator Code", "Environmental Indicator", "Mathematical Direction", "Measurement Unit", "Ecological & Health Rationale"]
TABLE_8_DATA = [
    ["NDVI", "Normalized Difference Vegetation Index", "Positive (Higher = Better)", "Dimensionless [-1.0, 1.0]", "Reflects photosynthetic chlorophyll activity and urban vegetative vitality."],
    ["TREE_DENS", "Tree Canopy Density Fraction", "Positive (Higher = Better)", "Area Fraction [0.0, 1.0]", "Direct canopy coverage providing shading, evapotranspiration, and micro-climate cooling."],
    ["LST", "Land Surface Temperature", "Negative (Lower = Better)", "Degrees Celsius (°C)", "Thermal radiation trapped by artificial urban surfaces; primary driver of heat stress."],
    ["IMPERV", "Impervious Surface Fraction", "Negative (Lower = Better)", "Area Fraction [0.0, 1.0]", "Artificial built surfaces preventing rainwater percolation and retaining thermal energy."],
    ["POP_EXP", "Population Exposure Density", "Negative (Lower = Better)", "Persons per Block (250m)", "Human vulnerability dimension; amplifies public health urgency under severe environmental stress."],
    ["PM25", "Particulate Matter (PM2.5 Proxy)", "Negative (Lower = Better)", "Concentration (µg/m³)", "Atmospheric particulate pollution representing chronic respiratory health hazard."]
]
TABLE_8_WIDTHS = [1.0, 1.8, 1.3, 1.1, 1.3]

# Table 9: Ecological Risk Tier Categorization
TABLE_9_HEADERS = ["UEHI Score Range", "Ecological Risk Tier", "Environmental Condition Description", "Recommended Intervention & Planning Mandate"]
TABLE_9_DATA = [
    [
        "[0, 25)",
        "Critical Ecological Risk",
        "Extreme urban heat island conditions; near-total impervious coverage (>80%), negligible tree canopy (<10%), elevated thermal radiation, and dense population exposure.",
        "High-priority municipal intervention mandate: Emergency afforestation corridors, reflective cool-roof retrofitting, green buffer mandates, and CSR urban forestry prioritization."
    ],
    [
        "[25, 50)",
        "High Ecological Risk",
        "Substantial environmental stress; high built density, fragmented vegetative patches, elevated surface temperatures, and significant population exposure.",
        "Targeted urban greening: Street verge tree planting, vacant plot micro-forests (Miyawaki method), institutional campus afforestation, and permeable pavement installation."
    ],
    [
        "[50, 75)",
        "Moderate Ecological Risk",
        "Balanced urban matrix; moderate tree canopy, intermediate thermal profiles, mixed residential development with dispersed open spaces.",
        "Preventative conservation: Protection of existing tree stands, enforcement of minimum green-cover zoning laws in redevelopment projects, and stormwater buffer maintenance."
    ],
    [
        "[75, 100]",
        "Low Ecological Risk",
        "Optimal ecological health; dense vegetative canopy (>50%), active evapotranspirative cooling, low artificial surface fraction, proximity to natural biodiversity reserves.",
        "Preservation and benchmark status: Demarcation as urban ecological refugia (e.g., Vetal Tekdi, ARAI hills); prohibition of high-density impervious encroachment."
    ]
]
TABLE_9_WIDTHS = [1.0, 1.3, 2.1, 2.1]

# Table 10: Comparative Summary of Work (Part A vs Part B)
TABLE_10_HEADERS = ["Report Dimension", "Part A: Service Learning (SEER Bharat Foundation)", "Part B: Technical Project (UEHIS Architecture)"]
TABLE_10_DATA = [
    [
        "Primary Focus",
        "Community-engaged service learning, partner NGO needs assessment, environmental problem definition, and field tree planting.",
        "Deep engineering, satellite data pipelines, computer vision U-Net segmentation, entropy formula derivation, PostGIS database architecture, and web dashboard."
    ],
    [
        "Work Modality & Location",
        "Hybrid collaboration: In-person coordination at SEER Bharat Foundation (Pune/Wakad), on-field tree plantation drive, and scheduled team reviews.",
        "Computational research, machine learning workstation development, remote sensing raster processing, GitHub version control, and containerized deployment."
    ],
    [
        "Documented Duration",
        "5th July 2026 to 16th October 2026 (15 Weeks, 120 Hours counted).",
        "Continuous technical engineering lifecycle extending across project phases (not strictly constrained to service hours)."
    ],
    [
        "Author's Key Deliverable",
        "Weekly verified logbook entries, attendance synchronization, tree plantation participation, NGO presentation deck, and progress confirmation letter.",
        "4-class satellite segmentation pipeline, spatial data leakage resolution via geographic buffer split, 3-model ensemble + 8-way TTA, sliding-window Bartlett blending, and Pytest test suite."
    ],
    [
        "Institutional Impact",
        "Direct contribution to SEER Bharat Foundation's urban ecological advocacy and actionable data foundation for municipal CSR funding proposals.",
        "Open-source geospatial decision-support repository (`Godar72/uehis-project`), reproducible multi-sensor data pipeline, and scalable environmental atlas for Pune."
    ]
]
TABLE_10_WIDTHS = [1.5, 2.5, 2.5]

print("Report data structures initialized successfully.")

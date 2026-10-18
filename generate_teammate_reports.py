"""
Master Generation Script for Teammates' Service Learning Reports:
1. UEHIS_Service_Learning_Report_Aditya_Singh_Sengar.docx (Data Engineering & Infrastructure)
2. UEHIS_Service_Learning_Report_Abhay_Chaturvedi.docx (Data Science, Formula Design & NGO Coordination)
3. UEHIS_Service_Learning_Report_Abhay_Raj_Mosaita.docx (Full-Stack Development, Documentation & NGO Coordination)

Clones the audited, formatted base report 'UEHIS_Service_Learning_Report_Aditya_Godar.docx',
generates crisp institutional image placeholders for workstation and logbooks,
and applies exhaustive role-specific updates across all sections, tables, figures, and weekly logs.
"""

import os
import sys
import shutil
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT

from generate_placeholder_images import (
    generate_workstation_image, generate_logbook_image, ensure_dir
)

BASE_DOCX = "UEHIS_Service_Learning_Report_Aditya_Godar.docx"
COLOR_NAVY = RGBColor(23, 43, 92)       # #172B5C
COLOR_DARK_TEXT = RGBColor(30, 41, 59)  # #1E293B
COLOR_MUTED = RGBColor(100, 116, 139)   # #64748B
COLOR_GREEN = RGBColor(46, 155, 95)     # #2E9B5F

STUDENT_DATA = {
    "aditya_singh_sengar": {
        "file_name": "UEHIS_Service_Learning_Report_Aditya_Singh_Sengar.docx",
        "key": "aditya_singh_sengar",
        "name": "Aditya Singh Sengar",
        "prn_placeholder": "[PRN: Enter PRN]",
        "role": "Data Engineering & Infrastructure",
        "role_short": "Data Engineering",
        "group_no": "17",
        "class_div": "AIML A1",
        "teammates_ack": "Aditya Godar, Abhay Chaturvedi, and Abhay Raj Mosaita",
        "subtitle_part_b": "Comprehensive Architecture, Geospatial Data Engineering, Spatial Infrastructure & Pipeline Harmonization",
        
        "abstract_p3": (
            "As the team member responsible for Data Engineering & Infrastructure, my individual intellectual and technical contributions "
            "focused on architecting and hardening the end-to-end geospatial data ingestion, transformation, and spatial database pipelines powering UEHIS. "
            "I engineered automated acquisition routines via the Google Earth Engine (GEE) Python API and cloud-native STAC catalogs to harvest multi-spectral "
            "Sentinel-2 Level-2A surface reflectance tiles and Landsat-8/9 Thermal Infrared Sensor (TIRS) radiance data for the entire Pune metropolitan extent. "
            "To resolve critical spatial misalignments across disparate raster and vector sources, I developed an automated geospatial harmonization pipeline "
            "that projected all inputs to a uniform Universal Transverse Mercator (UTM Zone 43N, EPSG:32643) coordinate reference system at a native 10 m raster resolution, "
            "implementing bicubic resampling, cloud/shadow masking via the Scene Classification Layer (SCL), and rigorous bounding-box alignment validation "
            "(`verify_alignment.py`). Furthermore, I engineered the multi-source vector and ancillary data ingestion pipelines—extracting OpenStreetMap (OSM) building "
            "footprints and road networks, ACAG atmospheric PM2.5 concentrations, and WorldPop 100 m population density surfaces. On the infrastructure tier, "
            "I architected and provisioned the enterprise-grade PostgreSQL 15 / PostGIS 3.3 spatial database, engineered the 250 m × 250 m analytical grid covering "
            "the Kothrud pilot (256 blocks) and greater Pune study areas, implemented GIST spatial indices for sub-millisecond query execution, and established "
            "reproducible Docker container orchestration to ensure seamless data handoffs to the computer vision, formula scoring, and web dashboard modules."
        ),
        
        "type_of_work_admin": (
            "Geospatial Data Engineering, Planetary Satellite Ingestion Pipelines, PostGIS Spatial Database Architecture, "
            "Coordinate Harmonization & On-Field Afforestation Activity"
        ),
        
        "type_of_work_sec2": (
            "Type of Work Done: Over the course of 120 officially documented service hours spanning 15 weeks (5th July 2026 to 16th October 2026), "
            "our team operated at the intersection of remote sensing data engineering, spatial infrastructure, and community ecological engagement. "
            "As the team member responsible for Data Engineering & Infrastructure, my specific work entailed establishing automated Google Earth Engine data ingestion routines, "
            "reprojecting disparate multi-sensor satellite rasters to a standardized UTM 43N coordinate reference system, automating cloud and cirrus masking via Sentinel-2 SCL layers, "
            "provisioning containerized PostgreSQL/PostGIS databases with spatial indexing, synthesizing multi-sensor environmental indicator matrices, "
            "and actively participating in on-field tree planting operations organized by SEER Bharat Foundation."
        ),
        
        "weekly_logs": [
            {
                "week": 1,
                "title": "Setup, Environmental Problem Definition & Data Infrastructure Architecture",
                "summary": "Session Summary: Date: 05-07-2026 | Time: 4:00 PM – 9:00 PM | Hours: 5 Hours | Cumulative: 5 Hours",
                "narrative": (
                    "Initiated project engagement with SEER Bharat Foundation at their Pune office. Focused this week on evaluating planetary "
                    "remote sensing data sources and architecting the primary data infrastructure required for UEHIS. Assessed cloud-native geospatial APIs, "
                    "comparing Google Earth Engine (GEE), Copernicus Open Access Hub, and Microsoft Planetary Computer for continuous Sentinel-2 Level-2A "
                    "and Landsat-8/9 data acquisition across the Pune metropolitan area. Designed the system's target data flow architecture, specifying "
                    "ingestion schemas, raster storage formats (Cloud-Optimized GeoTIFFs), coordinate reference system requirements (WGS84 EPSG:4326 to UTM Zone 43N EPSG:32643), "
                    "and spatial indexing strategies. Outlined the hardware requirements and directory hierarchy for the local spatial repository, establishing "
                    "the core `data_ingestion/` module structure."
                ),
                "reflection": "Reflection & Action Plan: Future Scope: Authenticate the Google Earth Engine Python API and script automated bounding-box image collection harvesting. Absent: None."
            },
            {
                "week": 2,
                "title": "Google Earth Engine API Ingestion & Multi-Spectral Sentinel-2 Harvesting",
                "summary": "Session Summary: Date: 11-07-2026 | Time: 4:00 PM – 9:00 PM | Hours: 5 Hours | Cumulative: 10 Hours",
                "narrative": (
                    "Programmed automated satellite ingestion routines using the Google Earth Engine Python API (`ee`) inside `data_ingestion/sentinel.py`. "
                    "Defined the spatial polygon bounding box for Pune and the pilot Kothrud study area. Scripted temporal filtering across the pre-monsoon "
                    "period (January to March 2024) to secure minimum cloud-cover imagery. Implemented multi-spectral band extraction for Sentinel-2 Level-2A "
                    "surface reflectance products, specifically harvesting Band 2 (Blue, 10 m), Band 3 (Green, 10 m), Band 4 (Red, 10 m), Band 8 (NIR, 10 m), "
                    "and the Scene Classification Layer (SCL, 20 m). Formulated automated GeoTIFF export pipelines and validated metadata consistency."
                ),
                "reflection": "Reflection & Action Plan: Future Scope: Implement automated radiometric quality control and cloud-masking algorithms using SCL bitmasks. Absent: None."
            },
            {
                "week": 3,
                "title": "Radiometric Calibration, Cloud-Masking & SCL Quality Filtering",
                "summary": "Session Summary: Date: 18-07-2026 | Time: 4:00 PM – 9:00 PM | Hours: 5 Hours | Cumulative: 15 Hours",
                "narrative": (
                    "Engineered robust radiometric filtering and automated pixel-quality masking algorithms for ingested Sentinel-2 tiles. Decoded the 20 m "
                    "Scene Classification Layer (SCL) bitmask to systematically detect and eliminate high-probability clouds (class 9), thin cirrus (class 10), "
                    "cloud shadows (class 3), and defective detector pixels. Resampled the 20 m SCL grid to the native 10 m resolution of Bands 2, 3, 4, and 8 "
                    "using nearest-neighbor interpolation to prevent edge-blurring artifacts. Evaluated atmospheric reflectance scaling factors (multiplying raw DN "
                    "values by 0.0001 to convert to physical surface reflectance). Reviewed data quality with NGO mentor Prof. Darshan Talhande."
                ),
                "reflection": "Reflection & Action Plan: Future Scope: Expand ingestion pipeline to capture thermal infrared data from Landsat-8/9 for Land Surface Temperature derivation. Absent: None."
            },
            {
                "week": 4,
                "title": "Landsat-8/9 Thermal Data Ingestion & Land Surface Temperature (LST) Extraction",
                "summary": "Session Summary: Date: 25-07-2026 | Time: 4:00 PM – 9:00 PM | Hours: 5 Hours | Cumulative: 20 Hours",
                "narrative": (
                    "Scripted thermal infrared data harvesting from the Landsat-8 and Landsat-9 Thermal Infrared Sensor (TIRS) inside `data_ingestion/landsat_lst.py`. "
                    "Ingested Band 10 Top-of-Atmosphere (TOA) spectral radiance and converted raw digital numbers into brightness temperatures using sensor-specific "
                    "calibration constants ($K_1 = 774.88$, $K_2 = 1321.08$). Implemented split-window atmospheric correction routines utilizing fractional vegetation cover (FVC) "
                    "derived from Sentinel-2 NDVI to compute land surface emissivity ($\epsilon$). Generated calibrated Land Surface Temperature (LST) raster maps in degrees Celsius "
                    "across Pune, identifying acute thermal hotspots exceeding 38°C in dense industrial and commercial zones."
                ),
                "reflection": "Reflection & Action Plan: Future Scope: Resolve coordinate system discrepancies between Landsat sinusoidal projections and Sentinel-2 UTM grids. Absent: None."
            },
            {
                "week": 5,
                "title": "Coordinate Reference System Harmonization & CRS Alignment Automation",
                "summary": "Session Summary: Date: 10-08-2026 | Time: 10:30 AM – 8:30 PM | Hours: 10 Hours | Cumulative: 30 Hours",
                "narrative": (
                    "Dedicated full-day sprint to resolving critical geospatial reprojection and raster alignment discrepancies across disparate sensors. "
                    "Constructed an automated GDAL and Rasterio reprojection utility that unifies all spatial layers from geographic coordinates (WGS84, EPSG:4326) "
                    "into the local projected Universal Transverse Mercator system (UTM Zone 43N, EPSG:32643). Addressed sub-pixel spatial shifts by enforcing "
                    "identical geotransform matrices, origin bounds, and an exact 10 m pixel lattice. Programmed `data_ingestion/verify_alignment.py` to assert "
                    "zero-offset bounding-box alignment, pixel-grid snapping, and NoData consistency across all raster stacks before handing off data to modeling."
                ),
                "reflection": "Reflection & Action Plan: Future Scope: Integrate external vector datasets from OpenStreetMap to augment building and road infrastructure data. Absent: None."
            },
            {
                "week": 6,
                "title": "Post-CA2 Data Architecture Review & OpenStreetMap (OSM) Vector Ingestion",
                "summary": "Session Summary: Dates: 16-08-2026 & 20-08-2026 | Time: 12:00 PM – 3:00 PM; 5:00 PM – 10:00 PM | Hours: 10 Hours | Cumulative: 40 Hours",
                "narrative": (
                    "16-08-2026 (5 Hours): Participated in the CA2 milestone review and integrated faculty feedback regarding geospatial data provenance. "
                    "Began developing the OpenStreetMap vector extraction pipeline inside `data_ingestion/osm_features.py` using the Overpass QL API.\n"
                    "20-08-2026 (5 Hours): Successfully extracted all municipal building footprints, primary/secondary road networks, and natural water bodies "
                    "for Pune. Implemented vector-to-raster rasterization at 10 m resolution matching the UTM 43N grid. Calculated fractional built-up infrastructure "
                    "densities per cell, creating a ground-truth structural layer for impervious surface validation."
                ),
                "reflection": "Reflection & Action Plan: Future Scope: Ingest socio-demographic population and air quality datasets to complete the multi-sensor indicator suite. Absent: None."
            },
            {
                "week": 7,
                "title": "WorldPop Population Raster Ingestion & Atmospheric PM2.5 Integration",
                "summary": "Session Summary: Dates: 23-08-2026 & 26-08-2026 | Time: 10:00 AM – 4:00 PM; 5:00 PM – 10:00 PM | Hours: 11 Hours | Cumulative: 51 Hours",
                "narrative": (
                    "23-08-2026 (6 Hours): Ingested the high-resolution WorldPop 2024 unconstrained individual population density surface (100 m resolution) "
                    "for Maharashtra inside `data_ingestion/worldpop.py`. Resampled the population counts to the 10 m UTM 43N lattice using mass-preserving "
                    "pycnophylactic volume allocation to ensure total ward census population figures remained mathematically invariant.\n"
                    "26-08-2026 (5 Hours): Integrated the Atmospheric Composition Analysis Group (ACAG) surface-level PM2.5 satellite-derived aerosol dataset "
                    "(`data_ingestion/acag_pm25.py`). Reprojected and interpolated particulate concentration fields across Pune, establishing the environmental exposure baseline."
                ),
                "reflection": "Reflection & Action Plan: Future Scope: Design and initialize the relational PostGIS database schema to store and index multi-layer attributes. Absent: None."
            },
            {
                "week": 8,
                "title": "PostgreSQL 15 / PostGIS 3.3 Spatial Database Provisioning & Schema Engineering",
                "summary": "Session Summary: Dates: 30-08-2026 & 02-09-2026 | Time: 10:00 AM – 3:00 PM; 5:00 PM – 10:00 PM | Hours: 10 Hours | Cumulative: 61 Hours",
                "narrative": (
                    "30-08-2026 (5 Hours): Provisioned the enterprise PostgreSQL 15 database instance with the PostGIS 3.3 spatial extension using Docker. "
                    "Engineered the primary spatial relational schema including `study_areas`, `blocks`, `environmental_metrics`, and `sensor_rasters` tables.\n"
                    "02-09-2026 (5 Hours): Formulated spatial constraints, foreign key relationships, and automated migration scripts. Implemented spatial "
                    "bounding geometry columns with SRID=32643. Verified that spatial insertions conform strictly to OpenGIS standards, establishing seamless "
                    "database connectivity for data scientists and frontend API services."
                ),
                "reflection": "Reflection & Action Plan: Future Scope: Generate the uniform 250 m × 250 m tessellation grid across Pune and load block geometries into PostGIS. Absent: None."
            },
            {
                "week": 9,
                "title": "250 m × 250 m Spatial Grid Partitioning & Geometry Generation for Pune/Kothrud",
                "summary": "Session Summary: Dates: 06-09-2026 & 08-09-2026 | Time: 10:00 AM – 3:00 PM; 5:00 PM – 10:00 PM | Hours: 10 Hours | Cumulative: 71 Hours",
                "narrative": (
                    "06-09-2026 (5 Hours): Programmed an algorithmic grid generation script using Shapely and GeoPandas to tessellate the Pune metropolitan "
                    "bounding polygon into a uniform lattice of 250 m × 250 m analytical blocks (each covering exactly 6.25 hectares). Generated unique deterministic "
                    "block identifiers (`block_id`) based on spatial matrix coordinates.\n"
                    "08-09-2026 (5 Hours): Clipped the lattice to the pilot Kothrud study area, yielding 256 valid analytical blocks. Ingested the block geometries "
                    "into the PostGIS `blocks` table and validated that all polygon boundaries snapped seamlessly with no overlapping geometries or spatial slivers."
                ),
                "reflection": "Reflection & Action Plan: Future Scope: Create GIST spatial indexes and automate zonal raster statistics aggregation per block. Absent: None."
            },
            {
                "week": 10,
                "title": "Spatial Index Optimization (GIST), Geometry Intersections & ETL Automation",
                "summary": "Session Summary: Dates: 12-09-2026 & 13-09-2026 | Time: 5:00 PM – 10:00 PM; 10:00 PM – 4:00 AM | Hours: 11 Hours | Cumulative: 82 Hours",
                "narrative": (
                    "12-09-2026 (5 Hours): Optimized the PostGIS spatial database for high-throughput spatial queries. Created Generalized Search Tree (GIST) "
                    "spatial indexes on all geometry columns. Benchmarked spatial intersection query performance, reducing block-in-polygon lookup times "
                    "from 420 ms to 12 ms.\n"
                    "13-09-2026 (6 Hours, Overnight Sprint): Developed automated Extract-Transform-Load (ETL) routines using Rasterio and Rasterstats to compute "
                    "zonal mean, min, max, and standard deviation metrics for all multi-sensor rasters (NDVI, LST, PM2.5, population) across each of the 256 Kothrud blocks. "
                    "Wrote automated integrity assertions to catch null values or out-of-bounds metrics."
                ),
                "reflection": "Reflection & Action Plan: Future Scope: Finalize multi-sensor indicator matrices and participate in the scheduled community tree plantation drive. Absent: None."
            },
            {
                "week": 11,
                "title": "Multi-Sensor Indicator Matrix Pipeline & On-Field Afforestation Activity",
                "summary": "Session Summary: Dates: 26-09-2026 & 28-09-2026 | Time: 5:00 PM – 8:00 PM; 8:00 PM – 4:00 AM | Hours: 13 Hours | Cumulative: 95 Hours",
                "narrative": (
                    "26-09-2026 (5 Hours): Consolidated the normalized multi-sensor indicator matrix combining Sentinel-2 canopy, impervious fraction, "
                    "Landsat LST, ACAG PM2.5, and WorldPop metrics into structured CSV and PostGIS formats for downstream entropy scoring by Abhay Chaturvedi.\n"
                    "Field Service Activity (18-09-2026, documented in logbook): Actively participated in SEER Bharat Foundation's community afforestation drive "
                    "at Godrej Green Vistas, Pune. Assisted in soil excavation, root-bed preparation, organic fertilization, and manual plantation of native saplings. "
                    "Distributed ecological awareness leaflets to local residents, gaining hands-on insight into physical afforestation logistics.\n"
                    "28-09-2026 (8 Hours, Overnight): Updated spatial database records with geotagged plantation site coordinates and synchronized field metadata."
                ),
                "reflection": "Reflection & Action Plan: Future Scope: Couple the data ingestion pipeline with the deep learning computer vision module for full-scene inference. Absent: None."
            },
            {
                "week": 12,
                "title": "Computer Vision Ingestion Pipeline Coupling & GeoTIFF Raster Export",
                "summary": "Session Summary: Dates: 21-09-2026 & 27-09-2026 | Time: 5:00 PM – 10:00 PM; 10:00 AM – 3:00 PM | Hours: 10 Hours | Cumulative: 105 Hours",
                "narrative": (
                    "21-09-2026 (5 Hours): Collaborated with teammate Aditya Godar to couple the data engineering ingestion pipeline with the deep learning "
                    "U-Net inference engine. Formulated automated 5-channel GeoTIFF raster exports stacking Sentinel-2 Red, Green, Blue, NIR, and SRTM slope bands.\n"
                    "27-09-2026 (5 Hours): Attended technical review and architecture demonstration with NGO Mentor Prof. Darshan Talhande at the SEER Bharat Foundation office. "
                    "Demonstrated the automated multi-sensor ingestion pipeline and verified coordinate alignment across Kothrud pilot layers. Received mentor validation "
                    "on data provenance and reproducibility standards."
                ),
                "reflection": "Reflection & Action Plan: Future Scope: Provide optimized spatial query endpoints and database connection pools for the FastAPI backend. Absent: None."
            },
            {
                "week": 13,
                "title": "Full-Scene Data Handover, API Database Connection & Spatial Query Optimization",
                "summary": "Session Summary: Date: 03-10-2026 | Time: 5:00 PM – 10:00 PM | Hours: 5 Hours | Cumulative: 110 Hours",
                "narrative": (
                    "Integrated the PostGIS database backend with the FastAPI microservice developed by Abhay Raj Mosaita. Configured asynchronous database "
                    "connection pooling using `asyncpg` and SQLAlchemy 2.0. Optimized complex spatial aggregation queries (`ST_Intersects`, `ST_Within`, `ST_Envelope`) "
                    "to deliver block-level environmental indicators and UEHI scores in sub-50 ms response times. Validated that API endpoints correctly serve "
                    "GeoJSON geometry features and structured attributes to the Next.js web map interface without memory leaks."
                ),
                "reflection": "Reflection & Action Plan: Future Scope: Perform stress testing, boundary edge-case audits, and data validation across greater Pune. Absent: None."
            },
            {
                "week": 14,
                "title": "Pipeline Reproducibility Testing, Boundary Integrity Audits & Performance Profiling",
                "summary": "Session Summary: Date: 10-10-2026 | Time: 10:00 AM – 3:00 PM | Hours: 5 Hours | Cumulative: 115 Hours",
                "narrative": (
                    "Conducted end-to-end reproducibility testing and data pipeline profiling across the entire repository. Executed cold-start database migrations "
                    "and automated data ingestion scripts within a clean Docker container environment to verify zero dependency failures. Audited spatial boundary "
                    "integrity along the perimeter of the Kothrud pilot zone, ensuring that marginal blocks with partial study area overlap handled NoData cells "
                    "gracefully without skewing mean indicator calculations. Validated 100% test pass rate across the `tests/` test suite."
                ),
                "reflection": "Reflection & Action Plan: Future Scope: Prepare comprehensive data engineering documentation and finalize project handover. Absent: None."
            },
            {
                "week": 15,
                "title": "Final Data Engineering Audit, Repository Packaging & Institutional Sign-Off",
                "summary": "Session Summary: Date: 16-10-2026 | Time: 11:00 AM – 4:00 PM | Hours: 5 Hours | Cumulative: 120 Hours",
                "narrative": (
                    "Conducted final data engineering audit, software packaging, and formal project handover with SEER Bharat Foundation. Met with NGO Mentor "
                    "Prof. Darshan Talhande at the SEER Bharat Foundation office for final review of the data architecture, PostGIS database dumps, and GEE ingestion scripts. "
                    "Verified that all datasets, Docker configurations, and pipeline code are fully documented and archived in the GitHub repository (`Godar72/uehis-project`). "
                    "Completed the formal project sign-off and verified cumulative 120 hours of Service Learning engagement across the full 15-week timeline."
                ),
                "reflection": "Milestone Completion: Final Service Learning Milestone: Successful completion and institutional verification of 120 hours of Service Learning across 15 weeks; delivery of an operational, reproducible geospatial data engineering pipeline to SEER Bharat Foundation. Absent: None."
            }
        ],
        
        "sec12_12_heading": "12.12 Individual Role & Detailed Contribution: Aditya Singh Sengar (Data Engineering & Infrastructure)",
        "sec12_12_intro": (
            "As the team member designated for Data Engineering & Infrastructure, my personal intellectual and technical contributions were "
            "foundational to the entire UEHIS platform, establishing the automated remote sensing ingestion pipelines, coordinate system harmonization, "
            "spatial database schemas, and data reliability frameworks that enabled downstream computer vision, formula scoring, and web visualization. "
            "My verified contributions span nine primary engineering domains:"
        ),
        "sec12_12_points": [
            (
                "•  1. Planetary Remote Sensing Ingestion Pipeline: Engineered the automated satellite data acquisition architecture using the Google Earth Engine (GEE) "
                "Python API and STAC catalogs. Formulated temporal and spatial query filters to harvest cloud-free Sentinel-2 Level-2A surface reflectance composites "
                "(Bands 2, 3, 4, 8) and Landsat-8/9 thermal radiance products across Pune for the January–March 2024 pre-monsoon baseline."
            ),
            (
                "•  2. Radiometric Calibration & Automated Cloud Masking: Implemented pixel-level quality control pipelines decoding Sentinel-2 Scene Classification Layer (SCL) "
                "bitmasks to eliminate high-probability clouds, thin cirrus, and cloud shadows. Resampled the 20 m SCL mask to 10 m using nearest-neighbor interpolation "
                "and applied physical surface reflectance scaling multipliers ($10^{-4}$) to ensure rigorous radiometric consistency."
            ),
            (
                "•  3. Thermal Infrared Land Surface Temperature (LST) Extraction: Developed the automated Landsat-8/9 Band 10 thermal conversion pipeline. Converted digital "
                "numbers to top-of-atmosphere spectral radiance and calculated at-sensor brightness temperatures. Implemented split-window emissivity correction routines "
                "parameterized by fractional vegetation cover (FVC) to derive calibrated, block-level surface temperature rasters."
            ),
            (
                "•  4. Coordinate Reference System (CRS) Harmonization: Resolved critical spatial misalignments between disparate satellite coordinate systems. Engineered an automated "
                "reprojection and resampling utility projecting geographic WGS84 (EPSG:4326) rasters into the projected Universal Transverse Mercator (UTM Zone 43N, EPSG:32643) "
                "coordinate system, enforcing identical 10 m pixel lattice bounds and zero-offset geotransform matrices."
            ),
            (
                "•  5. Ancillary Socio-Environmental Layer Ingestion: Programmed automated harvesting routines for external datasets: OpenStreetMap (OSM) building and road vectors "
                "via Overpass API, Atmospheric Composition Analysis Group (ACAG) surface PM2.5 concentrations, and WorldPop 2024 100 m population density rasters, utilizing "
                "mass-preserving pycnophylactic resampling to maintain census count fidelity."
            ),
            (
                "•  6. PostgreSQL 15 / PostGIS 3.3 Spatial Database Architecture: Architected, provisioned, and optimized the relational spatial database schema using PostGIS. "
                "Engineered primary tables (`study_areas`, `blocks`, `environmental_metrics`), established spatial geometry constraints (SRID=32643), and configured Generalized "
                "Search Tree (GIST) spatial indexing, accelerating spatial intersection queries from 420 ms to 12 ms."
            ),
            (
                "•  7. Analytical Grid Partitioning & Geometric Tessellation: Developed an algorithmic spatial tiling script in GeoPandas to generate the standardized 250 m × 250 m "
                "(6.25 ha) analytical grid lattice covering Pune and the Kothrud pilot area (256 blocks). Ensured topology compliance, eliminated spatial slivers, and assigned "
                "deterministic spatial identifiers (`block_id`) linking rasters to tabular attributes."
            ),
            (
                "•  8. Automated Alignment Verification & Quality Assurance: Authored `data_ingestion/verify_alignment.py` to automate strict spatial assertions prior to model ingestion. "
                "The test suite verifies identical raster dimensions, matching CRS codes, snapping to pixel grids, and the absence of unhandled NoData values across multi-layer stacks, "
                "preventing silent spatial corruption in downstream scoring."
            ),
            (
                "•  9. Containerization, ETL Pipelines & Multi-Disciplinary Integration: Packaged database services and data engineering environments using Docker Compose, "
                "ensuring cross-platform reproducibility. Built automated zonal statistics ETL pipelines feeding normalized indicator matrices to the scoring engine, "
                "and participated actively in SEER Bharat Foundation field afforestation and technical review meetings."
            )
        ],
        
        "tbl26_part_b": (
            "Automated GEE & STAC ingestion pipeline, multi-sensor CRS reprojection to UTM 43N (EPSG:32643), spatial alignment validation suite "
            "(`verify_alignment.py`), PostgreSQL 15 / PostGIS 3.3 schema with GIST indexing, 250 m grid tessellation, and Docker container orchestration."
        ),
        
        "learning_outcomes": [
            "1. Planetary Remote Sensing & Satellite Ingestion: Mastered the Google Earth Engine Python API, multi-spectral band characteristics of Sentinel-2 Level-2A, Landsat-8/9 thermal radiance physics, and automated STAC catalog harvesting across large urban extents.",
            "2. Geospatial Coordinate Reference Systems & Spatial Alignment: Gained deep expertise in cartographic projections, resolving complex spatial datum shifts between WGS84 and UTM Zone 43N, bicubic resampling, and pixel-lattice grid alignment.",
            "3. Spatial Database Engineering & PostGIS Optimization: Developed production proficiency in PostgreSQL 15 and PostGIS 3.3, authoring spatial SQL schemas, spatial constraints, and tuning GIST indexes for ultra-fast spatial bounding-box intersections.",
            "4. Pipeline Reliability, ETL Automation & Docker Orchestration: Acquired rigorous engineering discipline in building containerized, reproducible data pipelines, writing automated spatial integrity assertions, and managing end-to-end data contracts."
        ],
        
        "technical_challenges": (
            "Multiple severe technical obstacles were encountered and successfully resolved: the discovery of sub-pixel spatial datum misalignments "
            "between Landsat thermal grids and Sentinel-2 surface reflectance rasters was resolved by engineering a centralized GDAL/Rasterio reprojection "
            "pipeline enforcing UTM Zone 43N (EPSG:32643) snapping; unhandled NoData pixels along study area boundaries were mitigated by implementing "
            "automated boundary clipping and padding routines in `verify_alignment.py`; and severe spatial join latency during multi-layer block aggregations "
            "was eliminated by provisioning GIST spatial indexes and optimizing spatial SQL execution plans."
        ),
        
        "personal_reflection": (
            "[Personal Reflection — Aditya Singh Sengar (To be reviewed and personalised)]: Engaging in this Service Learning project has been an intensely "
            "rewarding academic and civic journey that fundamentally expanded my understanding of the power of data engineering in addressing pressing environmental crises. "
            "Prior to this engagement, I viewed data pipelines primarily as an abstract computational challenge. Working alongside SEER Bharat Foundation and NGO Mentor "
                    "Prof. Darshan Talhande grounded our technical efforts in real-world urban ecology, revealing that high-quality, reproducible geospatial infrastructure is "
            "the indispensable backbone of transparent climate decision-making. Developing automated satellite ingestion routines, wrestling with coordinate systems, "
            "and provisioning PostGIS databases gave me profound technical confidence, while participating in the physical community tree planting drive at Godrej Green Vistas "
            "instilled a deep personal sense of social responsibility. Collaborating with my teammates Aditya Godar, Abhay Chaturvedi, and Abhay Raj Mosaita demonstrated "
            "the transformative potential of interdisciplinary teamwork. I emerge from this project with sharpened technical mastery and an enduring commitment to applying "
            "data infrastructure for sustainable urban stewardship."
        )
    },
    
    "abhay_chaturvedi": {
        "file_name": "UEHIS_Service_Learning_Report_Abhay_Chaturvedi.docx",
        "key": "abhay_chaturvedi",
        "name": "Abhay Chaturvedi",
        "prn_placeholder": "[PRN: Enter PRN]",
        "role": "Data Science, Formula Design & NGO Coordination",
        "role_short": "Formula Design & Data Science",
        "group_no": "17",
        "class_div": "AIML A1",
        "teammates_ack": "Aditya Singh Sengar, Aditya Godar, and Abhay Raj Mosaita",
        "subtitle_part_b": "Comprehensive Architecture, Entropy-Based Scoring Derivations, Ecological Synergies & Empirical Validation",
        
        "abstract_p3": (
            "As the team member designated for Data Science, Formula Design & NGO Coordination, my core intellectual and technical contributions "
            "centered on conceptualizing, mathematically formulating, and empirically validating the Urban Ecosystem Health Index (UEHI) scoring methodology. "
            "Addressing SEER Bharat Foundation's requirement for an objective, reproducible environmental prioritization framework free from subjective weight assignments, "
            "I engineered a Multi-Criteria Decision Analysis (MCDA) model governed by Shannon Entropy. I formulated the mathematical pipeline that ingests "
            "six core environmental indicators—Canopy Cover, Impervious Surface, Water Proximity/Presence, Land Surface Temperature, Atmospheric PM2.5, "
            "and Population Density—standardizing diverse dimensional scales via linear min-max normalization with strict positive and inverted directionality handling. "
            "To overcome numerical divergence in regions with near-uniform spatial indicators, I engineered an algorithmic zero-variance floor ($\\epsilon = 10^{-6}$) "
            "and mathematically integrated non-linear ecological interaction terms: the Canopy-Temperature Synergy formulation ($S_i$) to reward localized microclimate "
            "cooling and the Population Impact Multiplier ($m_i$) to prioritize interventions in densely inhabited vulnerable neighborhoods. Validating the scoring engine "
            "across Kothrud's 256 pilot blocks, I conducted extensive sensitivity analyses, verified score stability (mean 42.1, standard deviation 12.8, spanning 7.4 to 86.4), "
            "and established a rigorous 5-tier environmental risk classification (Critical, High, Moderate, Good, Optimal). Furthermore, I spearheaded requirements "
            "gathering with SEER Bharat Foundation NGO Mentor Prof. Darshan Talhande, translated grassroots urban forestry objectives into mathematical constraints, "
            "and integrated biomass and carbon sequestration allometry to quantify the climate mitigation potential of afforestation interventions."
        ),
        
        "type_of_work_admin": (
            "Mathematical Modeling, Shannon Entropy Multi-Criteria Weighting, Environmental Risk Stratification, "
            "Carbon Sequestration Modeling, NGO Coordination & On-Field Afforestation Activity"
        ),
        
        "type_of_work_sec2": (
            "Type of Work Done: Over the course of 120 officially documented service hours spanning 15 weeks (5th July 2026 to 16th October 2026), "
            "our team operated at the intersection of mathematical data science, ecological index formulation, and community environmental engagement. "
            "As the team member responsible for Data Science, Formula Design & NGO Coordination, my specific work entailed establishing the mathematical equations "
            "governing the Urban Ecosystem Health Index (UEHI), formulating Shannon entropy objective weighting algorithms to eliminate subjective bias, "
            "engineering numerical zero-variance safeguards, deriving non-linear microclimatic synergy and population exposure multipliers, "
            "conducting statistical score validation across Kothrud, coordinating requirements with SEER Bharat Foundation, and participating in on-field tree planting drives."
        ),
        
        "weekly_logs": [
            {
                "week": 1,
                "title": "NGO Engagement, Problem Scoping & Environmental Indicator Selection",
                "summary": "Session Summary: Date: 05-07-2026 | Time: 4:00 PM – 9:00 PM | Hours: 5 Hours | Cumulative: 5 Hours",
                "narrative": (
                    "Initiated collaborative engagement with SEER Bharat Foundation at their Pune office. Met with NGO Mentor Prof. Darshan Talhande to understand "
                    "the core institutional challenges in urban afforestation planning. Identified that municipal greening drives currently suffer from subjective, "
                    "politically motivated site selection rather than data-driven ecological prioritization. Began defining the conceptual framework for the Urban "
                    "Ecosystem Health Index (UEHI). Evaluated prospective environmental indicators, establishing six fundamental pillars: vegetative tree canopy cover, "
                    "surface imperviousness, surface water proximity, land surface temperature (LST), atmospheric particulate matter (PM2.5), and human population density."
                ),
                "reflection": "Reflection & Action Plan: Future Scope: Research Multi-Criteria Decision Analysis (MCDA) weighting methodologies to objectively combine heterogeneous physical indicators. Absent: None."
            },
            {
                "week": 2,
                "title": "Multi-Criteria Decision Analysis (MCDA) Research & Entropy Weighting Formulation",
                "summary": "Session Summary: Date: 11-07-2026 | Time: 4:00 PM – 9:00 PM | Hours: 5 Hours | Cumulative: 10 Hours",
                "narrative": (
                    "Conducted extensive academic literature review on Multi-Criteria Decision Analysis (MCDA) applied to urban environmental modeling. "
                    "Evaluated the Analytic Hierarchy Process (AHP), Principal Component Analysis (PCA), and Shannon Entropy Weighting. Determined that AHP introduces "
                    "unacceptable subjective cognitive bias through arbitrary pairwise comparison matrices, while Shannon Entropy provides a mathematically rigorous, "
                    "purely objective weighting mechanism derived directly from the information dispersion of empirical observations. Sketched the mathematical equations "
                    "for information entropy ($E_j$), degree of divergence ($d_j$), and normalized objective weight allocation ($w_j$)."
                ),
                "reflection": "Reflection & Action Plan: Future Scope: Formulate normalization functions for positive and negative benefit indicators to standardize input scales. Absent: None."
            },
            {
                "week": 3,
                "title": "Mathematical Indicator Normalization & Directionality Architecture",
                "summary": "Session Summary: Date: 18-07-2026 | Time: 4:00 PM – 9:00 PM | Hours: 5 Hours | Cumulative: 15 Hours",
                "narrative": (
                    "Engineered the mathematical normalization framework inside `scoring/normalize.py`. Addressed the disparate physical units of input layers "
                    "(percentages for canopy/impervious, degrees Celsius for LST, $\\mu g/m^3$ for PM2.5, persons/$km^2$ for population) by designing linear min-max "
                    "feature scaling mapping all values onto dimensionless intervals $[0, 1]$. Established strict directional logic: positive benefit indicators "
                    "(Tree Canopy, Water Presence) where higher values enhance ecosystem health, and inverted cost indicators (Impervious Surface, LST, PM2.5, Population) "
                    "where higher values represent environmental degradation and human exposure risks."
                ),
                "reflection": "Reflection & Action Plan: Future Scope: Identify mathematical failure modes when spatial indicators exhibit zero variance across homogeneous terrain. Absent: None."
            },
            {
                "week": 4,
                "title": "Mathematical Safeguards: Zero-Variance Floor (\\epsilon) & Divergence Boundaries",
                "summary": "Session Summary: Date: 25-07-2026 | Time: 4:00 PM – 9:00 PM | Hours: 5 Hours | Cumulative: 20 Hours",
                "narrative": (
                    "Discovered a critical mathematical vulnerability during initial prototype testing: when an indicator exhibits zero or near-zero variance across "
                    "a spatial region (e.g., completely dry terrain with zero water bodies, or identical PM2.5 concentrations), the denominator in min-max normalization "
                    "collapses ($x_{max} - x_{min} \\rightarrow 0$), inducing division-by-zero errors. Furthermore, the term $f_{ij} \\ln(f_{ij})$ in Shannon entropy "
                    "becomes undefined when $f_{ij} = 0$. Formulated mathematical boundary safeguards, introducing an algorithmic zero-variance floor ($\\epsilon = 10^{-6}$) "
                    "and enforcing $\\lim_{f \\to 0^+} f \\ln(f) = 0$ via conditional probability bounds."
                ),
                "reflection": "Reflection & Action Plan: Future Scope: Program the complete Shannon Entropy calculation script in Python and validate weight convergence. Absent: None."
            },
            {
                "week": 5,
                "title": "Shannon Entropy Engine Implementation & Prototype Scoring Script",
                "summary": "Session Summary: Date: 10-08-2026 | Time: 10:30 AM – 8:30 PM | Hours: 10 Hours | Cumulative: 30 Hours",
                "narrative": (
                    "Dedicated full-day coding sprint to implementing the core Shannon Entropy weighting engine inside `scoring/entropy.py` and `scoring/uehi_score.py`. "
                    "Programmed the probability matrix transformation $P_{ij} = r_{ij} / \\sum r_{ij}$, computed information entropy $e_j = -k \\sum P_{ij} \\ln(P_{ij})$ "
                    "with constant $k = 1 / \\ln(n)$, and calculated the objective weights $w_j = (1 - e_j) / \\sum (1 - e_k)$. Ran automated convergence tests "
                    "across synthetic spatial matrices, verifying that indicators with higher variance (greater information content) received proportionally higher weights "
                    "while uniform indicators gracefully degraded without numeric instability."
                ),
                "reflection": "Reflection & Action Plan: Future Scope: Incorporate non-linear microclimatic interactions to account for the cooling synergy between canopy and heat. Absent: None."
            },
            {
                "week": 6,
                "title": "Post-CA2 Methodological Review & Non-Linear Synergy Modeling (S_i)",
                "summary": "Session Summary: Dates: 16-08-2026 & 20-08-2026 | Time: 12:00 PM – 3:00 PM; 5:00 PM – 10:00 PM | Hours: 10 Hours | Cumulative: 40 Hours",
                "narrative": (
                    "16-08-2026 (5 Hours): Participated in the CA2 presentation review and discussed environmental indicator formulation with faculty examiners. "
                    "Addressed feedback regarding linear model limitations by researching non-linear ecological interaction dynamics.\n"
                    "20-08-2026 (5 Hours): Formulated the mathematical Canopy-Temperature Synergy term ($S_i$). Recognized that in urban environments, dense vegetative "
                    "canopy provides disproportionate cooling benefits in extreme thermal environments compared to cooler zones. Derived the synergy formulation "
                    "$S_i = \\alpha \\cdot (C_i \\cdot LST_i)$ where $\\alpha$ is a calibrated coupling coefficient, rewarding blocks where tree canopy actively mitigates acute heat."
                ),
                "reflection": "Reflection & Action Plan: Future Scope: Formulate the population exposure penalty multiplier to prioritize vulnerable residential communities. Absent: None."
            },
            {
                "week": 7,
                "title": "Population Exposure Penalty Multiplier (m_i) Derivation & Demographic Weighting",
                "summary": "Session Summary: Dates: 23-08-2026 & 26-08-2026 | Time: 10:00 AM – 4:00 PM; 5:00 PM – 10:00 PM | Hours: 11 Hours | Cumulative: 51 Hours",
                "narrative": (
                    "23-08-2026 (6 Hours): Collaborated with SEER Bharat Foundation to establish socio-ecological equity principles in index scoring. "
                    "Concluded that an environmentally degraded block located in a densely populated residential slum represents far greater human vulnerability "
                    "than an identical physical deficit in an uninhabited rocky outcrop.\n"
                    "26-08-2026 (5 Hours): Mathematically derived the Population Impact Multiplier ($m_i = 1 + \\beta \\cdot PopNorm_i$). Structured $m_i$ as an exposure "
                    "amplification coefficient that modulates the baseline risk score, ensuring that high population density dynamically scales the urgency of intervention."
                ),
                "reflection": "Reflection & Action Plan: Future Scope: Test formula stability and evaluate score distributions across the 256 Kothrud pilot blocks. Absent: None."
            },
            {
                "week": 8,
                "title": "Formula Convergence Testing & Sensitivity Analysis on Kothrud Pilot Blocks",
                "summary": "Session Summary: Dates: 30-08-2026 & 02-09-2026 | Time: 10:00 AM – 3:00 PM; 5:00 PM – 10:00 PM | Hours: 10 Hours | Cumulative: 61 Hours",
                "narrative": (
                    "30-08-2026 (5 Hours): Ingested empirical zonal statistics from the 256 Kothrud pilot blocks provided by data engineering. Executed the complete "
                    "scoring pipeline and audited the resulting score distribution. Verified that scores spanned a smooth continuum from 7.4 to 86.4 with a mean of 42.1.\n"
                    "02-09-2026 (5 Hours): Conducted global sensitivity analysis (One-At-a-Time perturbation). Confirmed that tree canopy exhibited the strongest positive "
                    "sensitivity (+0.59 correlation), while impervious surface and LST exhibited strong negative sensitivity (-0.52 and -0.48), confirming theoretical consistency."
                ),
                "reflection": "Reflection & Action Plan: Future Scope: Establish clear categorical risk thresholds to classify blocks into actionable operational tiers. Absent: None."
            },
            {
                "week": 9,
                "title": "Five-Tier Environmental Risk Classification & Threshold Calibration",
                "summary": "Session Summary: Dates: 06-09-2026 & 08-09-2026 | Time: 10:00 AM – 3:00 PM; 5:00 PM – 10:00 PM | Hours: 10 Hours | Cumulative: 71 Hours",
                "narrative": (
                    "06-09-2026 (5 Hours): Formulated the standardized 5-tier environmental risk classification system: Critical Ecological Risk (0–20), "
                    "High Ecological Risk (20–40), Moderate Ecological Risk (40–60), Good Ecological Health (60–80), and Optimal Ecological Health (80–100). "
                    "Mapped each tier to specific municipal action recommendations.\n"
                    "08-09-2026 (5 Hours): Calibrated threshold boundaries using cumulative distribution percentiles across Kothrud. Identified 22 Critical blocks "
                    "characterized by <5% canopy cover and >36°C surface temperatures, establishing the primary target candidate list for NGO intervention."
                ),
                "reflection": "Reflection & Action Plan: Future Scope: Integrate biomass and carbon sequestration allometry to quantify the climate benefits of afforestation. Absent: None."
            },
            {
                "week": 10,
                "title": "Biomass Quantification & Urban Carbon Sequestration Modeling",
                "summary": "Session Summary: Dates: 12-09-2026 & 13-09-2026 | Time: 5:00 PM – 10:00 PM; 10:00 PM – 4:00 AM | Hours: 11 Hours | Cumulative: 82 Hours",
                "narrative": (
                    "12-09-2026 (5 Hours): Developed the urban biomass and carbon sequestration estimation module inside `carbon_sink/carbon_engine.py`. "
                    "Integrated canopy height data from the ETH Global Canopy Height model (Lang et al., 2023) at 10 m resolution.\n"
                    "13-09-2026 (6 Hours, Overnight Sprint): Programmed McPherson (2016) urban tree allometric equations to convert canopy crown area and height "
                    "into Above-Ground Biomass (AGB, tons). Applied standard carbon conversion factors (0.47 carbon fraction of dry biomass) to compute total stored carbon "
                    "($tCO_2e$) and annual sequestration rates across urban canopy patches in Kothrud, quantifying the tangible carbon value of existing tree stands."
                ),
                "reflection": "Reflection & Action Plan: Future Scope: Develop planting opportunity prioritization algorithms combining pervious area and heat deficit. Absent: None."
            },
            {
                "week": 11,
                "title": "Planting Opportunity Prioritization Logic & On-Field Afforestation Activity",
                "summary": "Session Summary: Dates: 26-09-2026 & 28-09-2026 | Time: 5:00 PM – 8:00 PM; 8:00 PM – 4:00 AM | Hours: 13 Hours | Cumulative: 95 Hours",
                "narrative": (
                    "26-09-2026 (5 Hours): Formulated the multi-factor Planting Opportunity Index inside `carbon_sink/planting.py`. Combined available pervious ground fraction, "
                    "thermal stress severity, and population exposure to rank blocks by afforestation feasibility and ecological return on investment.\n"
                    "Field Service Activity (18-09-2026, documented in logbook): Actively participated in SEER Bharat Foundation's community afforestation drive "
                    "at Godrej Green Vistas, Pune. Planted native tree saplings (Neem, Peepal, Karanj), prepared soil beds, and distributed environmental leaflets to residents. "
                    "Discussed sapling mortality rates and canopy growth trajectories with field arborists to refine allometric model assumptions.\n"
                    "28-09-2026 (8 Hours, Overnight): Updated carbon sequestration models with empirical sapling growth parameters from the field drive."
                ),
                "reflection": "Reflection & Action Plan: Future Scope: Refactor and package the scoring pipeline into production-grade Python modules with config JSON support. Absent: None."
            },
            {
                "week": 12,
                "title": "Scoring Script Optimization (uehi_score.py) & Validation against Ground Indicators",
                "summary": "Session Summary: Dates: 21-09-2026 & 27-09-2026 | Time: 5:00 PM – 10:00 PM; 10:00 AM – 3:00 PM | Hours: 10 Hours | Cumulative: 105 Hours",
                "narrative": (
                    "21-09-2026 (5 Hours): Hardened the production scoring module `scoring/uehi_score.py`. Configured external JSON configuration files (`scoring/uehi_config.json`) "
                    "allowing runtime adjustment of synergy coefficients, population weights, and boundary safeguards without code modification.\n"
                    "27-09-2026 (5 Hours): Participated in the technical review session with NGO Mentor Prof. Darshan Talhande at the SEER Bharat Foundation office. "
                    "Presented the mathematical derivation of entropy weights, the non-linear synergy formulations, and the Kothrud pilot score distribution. "
                    "The mentor formally commended the elimination of subjective bias through Shannon entropy and validated the practical relevance of the risk tiers."
                ),
                "reflection": "Reflection & Action Plan: Future Scope: Integrate scoring module with PostGIS database and support full-stack web visualizers. Absent: None."
            },
            {
                "week": 13,
                "title": "Formula Integration with PostGIS Backend & Full Pipeline Verification",
                "summary": "Session Summary: Date: 03-10-2026 | Time: 5:00 PM – 10:00 PM | Hours: 5 Hours | Cumulative: 110 Hours",
                "narrative": (
                    "Collaborated with data engineering and full-stack teammates to integrate the scoring engine directly into the automated data pipeline. "
                    "Scripted batch calculation routines computing UEHI composite scores for all 256 Kothrud blocks and persisting the computed weights, indicator "
                    "breakdowns, and risk tier labels directly into the PostGIS `blocks` table. Verified mathematical consistency between raw Python array calculations "
                    "and database-persisted values, ensuring zero floating-point precision loss across data transitions."
                ),
                "reflection": "Reflection & Action Plan: Future Scope: Prepare comprehensive methodology documentation and evaluate stakeholder feedback. Absent: None."
            },
            {
                "week": 14,
                "title": "SEER Bharat Foundation Stakeholder Review & Scoring Methodology Presentation",
                "summary": "Session Summary: Date: 10-10-2026 | Time: 10:00 AM – 3:00 PM | Hours: 5 Hours | Cumulative: 115 Hours",
                "narrative": (
                    "Led a dedicated stakeholder review and demonstration session with SEER Bharat Foundation executives. Walked through the complete mathematical "
                    "architecture of UEHIS, explaining how Shannon entropy dynamically weights environmental variables according to empirical information entropy. "
                    "Demonstrated how the 5-tier classification allows SEER Bharat to scientifically justify corporate CSR afforestation funding requests by "
                    "targeting demonstrably degraded 'Critical' blocks with quantified carbon sequestration projections. Incorporated stakeholder suggestions "
                    "regarding planting density assumptions."
                ),
                "reflection": "Reflection & Action Plan: Future Scope: Finalize mathematical documentation and compile final service learning report. Absent: None."
            },
            {
                "week": 15,
                "title": "Final Methodological Audit, Scientific Documentation & Institutional Sign-Off",
                "summary": "Session Summary: Date: 16-10-2026 | Time: 11:00 AM – 4:00 PM | Hours: 5 Hours | Cumulative: 120 Hours",
                "narrative": (
                    "Conducted final mathematical audit, code clean-up, and institutional project handover with SEER Bharat Foundation. Met with NGO Mentor "
                    "Prof. Darshan Talhande at the SEER Bharat Foundation office to review the finalized scoring methodology, carbon allometry equations, and "
                    "empirical validation reports. Confirmed that all mathematical scripts (`uehi_score.py`, `entropy.py`, `normalize.py`, `planting.py`) are fully "
                    "documented with docstrings, LaTeX equation formulations, and unit test suites in the GitHub repository (`Godar72/uehis-project`). "
                    "Secured formal mentor sign-off, concluding 120 verified hours of Service Learning engagement across 15 continuous weeks."
                ),
                "reflection": "Milestone Completion: Final Service Learning Milestone: Successful completion and institutional verification of 120 hours of Service Learning across 15 weeks; delivery of an objective, validated environmental scoring and carbon quantification methodology to SEER Bharat Foundation. Absent: None."
            }
        ],
        
        "sec12_12_heading": "12.12 Individual Role & Detailed Contribution: Abhay Chaturvedi (Formula Design & Data Science)",
        "sec12_12_intro": (
            "As the team member designated for Data Science, Formula Design & NGO Coordination, my personal intellectual and technical contributions "
            "were centered on conceptualizing, mathematically formulating, coding, and validating the Urban Ecosystem Health Index (UEHI) scoring engine. "
            "I bridged the critical gap between raw multi-sensor remote sensing data and actionable urban ecological decision-making, ensuring that the resulting "
            "composite index is mathematically defensible, purely objective, and directly aligned with SEER Bharat Foundation's afforestation mandate. "
            "My verified contributions span nine primary data science and modeling domains:"
        ),
        "sec12_12_points": [
            (
                "•  1. Ecological Indicator Selection & Conceptual Framework: Formulated the multi-dimensional environmental assessment architecture in collaboration "
                "with SEER Bharat Foundation. Selected and justified the six fundamental physical indicators: Tree Canopy Cover (NDVI/U-Net), Impervious Surface Fraction, "
                "Water Proximity/Presence (NDWI), Land Surface Temperature (LST), Atmospheric PM2.5, and Human Population Density, capturing ecological resilience, "
                "thermal distress, and demographic vulnerability."
            ),
            (
                "•  2. Mathematical Min-Max Normalization & Directionality Architecture: Engineered the mathematical scaling pipeline in `scoring/normalize.py`. "
                "Standardized heterogeneous units onto dimensionless intervals $[0, 1]$ while enforcing strict directionality: positive benefit functions "
                "($r_{ij} = (x_{ij} - x_{min}) / (x_{max} - x_{min})$) for canopy and water, and inverted cost functions ($r_{ij} = (x_{max} - x_{ij}) / (x_{max} - x_{min})$) "
                "for impervious cover, LST, PM2.5, and population, ensuring higher normalized values uniformly indicate superior ecological health."
            ),
            (
                "•  3. Shannon Entropy Dynamic Weight Allocation: Derived and implemented the objective Shannon Entropy weighting algorithm in `scoring/entropy.py`. "
                "Computed the probability distribution $P_{ij} = r_{ij} / \\sum r_{ij}$, information entropy $e_j = - (1 / \\ln n) \\sum P_{ij} \\ln(P_{ij})$, "
                "and degree of divergence $d_j = 1 - e_j$. Normalized divergence values yielded dynamic, purely data-driven indicator weights ($w_j = d_j / \\sum d_k$), "
                "eliminating subjective cognitive bias inherent in traditional AHP models."
            ),
            (
                "•  4. Zero-Variance Numerical Floor & Boundary Protection: Uncovered and mathematically resolved edge-case numerical collapses. In regions where an indicator "
                "exhibits near-zero variance across blocks, standard normalization suffers division by zero, while $P_{ij} = 0$ renders $\\ln(P_{ij})$ undefined. "
                "Engineered an algorithmic zero-variance floor ($\\epsilon = 10^{-6}$) and strictly enforced $\\lim_{P \\to 0^+} P \\ln P = 0$, guaranteeing numeric stability."
            ),
            (
                "•  5. Non-Linear Canopy-Temperature Synergy Modeling ($S_i$): Designed the mathematical synergy formulation capturing the localized microclimatic cooling "
                "effect of dense vegetation under high thermal stress. Modeled the interaction term $S_i = \\alpha \\cdot (C_i \\cdot LST_i)$, dynamically rewarding blocks "
                "where mature tree canopy actively suppresses acute urban heat island formation."
            ),
            (
                "•  6. Demographic Vulnerability & Population Multiplier ($m_i$): Formulated the Population Impact Multiplier ($m_i = 1 + \\beta \\cdot PopNorm_i$) to integrate "
                "socio-environmental equity into composite index scoring. The multiplier ensures that identical physical canopy deficits located in densely populated "
                "residential neighborhoods receive prioritized intervention weight compared to unpopulated industrial outskirts."
            ),
            (
                "•  7. Five-Tier Environmental Risk Stratification: Statistically calibrated the 5 operational risk tiers: Critical Ecological Risk (0–20), High Ecological Risk (20–40), "
                "Moderate Ecological Risk (40–60), Good Ecological Health (60–80), and Optimal Ecological Health (80–100). Applied the model across Kothrud's 256 pilot blocks, "
                "identifying 22 Critical blocks requiring immediate afforestation and corporate CSR funding intervention."
            ),
            (
                "•  8. Urban Carbon Sequestration & Biomass Allometry: Developed the carbon quantification module in `carbon_sink/carbon_engine.py`. Integrated the ETH Global Canopy "
                "Height model (10 m resolution) and implemented McPherson urban allometric equations to convert canopy crown area and tree height into Above-Ground Biomass (AGB) "
                "and metric tons of stored carbon ($tCO_2e$), establishing concrete carbon mitigation metrics for SEER Bharat drives."
            ),
            (
                "•  9. SEER Bharat Foundation Stakeholder Coordination & Translation: Led technical coordination with NGO Mentor Prof. Darshan Talhande, translating grassroots NGO "
                "field requirements into algorithmic parameters, participating actively in the Godrej Green Vistas tree plantation drive, and authoring comprehensive methodological "
                "guides for academic and non-technical environmental stakeholders."
            )
        ],
        
        "tbl26_part_b": (
            "Mathematical Shannon entropy dynamic weighting engine (`entropy.py`), zero-variance floor safeguards, canopy-temperature synergy model, "
            "population exposure multiplier, 5-tier risk classification, ETH canopy height carbon allometry, and scoring verification suite."
        ),
        
        "learning_outcomes": [
            "1. Information Theory & Objective Multi-Criteria Decision Analysis: Mastered the mathematical foundations of Shannon Entropy, probability matrices, and information divergence, learning how to objectively quantify information dispersion across complex spatial datasets without subjective human bias.",
            "2. Environmental Indicator Normalization & Directionality Architecture: Deepened expertise in data standardization, designing linear benefit and cost normalization functions, handling heterogeneous physical dimensions, and engineering algorithmic safeguards against division-by-zero numerical collapse.",
            "3. Non-Linear Ecological Systems & Microclimate Modeling: Gained advanced competencies in modeling non-linear environmental interactions, deriving coupled canopy-temperature synergy formulations, and integrating demographic exposure multipliers to reflect socio-ecological vulnerability.",
            "4. Urban Forestry Allometry & Carbon Accounting: Acquired practical mastery of urban biomass modeling, applying McPherson allometric equations and satellite canopy height models to accurately quantify carbon stock pools and annual sequestration rates."
        ],
        
        "technical_challenges": (
            "Multiple severe technical obstacles were encountered and successfully resolved: numerical division-by-zero errors occurring during min-max "
            "normalization on near-uniform spatial indicators were eliminated by introducing an algorithmic zero-variance floor ($\\epsilon = 10^{-6}$); "
            "the mathematical undefined behavior of $\\ln(0)$ in Shannon entropy probability matrices was resolved by enforcing analytic boundary limits; "
            "and linear model limitations in capturing real-world microclimatic cooling were overcome by deriving a non-linear canopy-temperature synergy "
            "formulation calibrated against empirical land surface temperature observations."
        ),
        
        "personal_reflection": (
            "[Personal Reflection — Abhay Chaturvedi (To be reviewed and personalised)]: Engaging in this Service Learning project has been an intellectually "
            "rigorous and deeply humbling experience that permanently altered my perspective on the civic responsibility of data scientists. "
            "Throughout my academic studies, machine learning and data science were often presented as abstract statistical optimizations on sanitized benchmark datasets. "
            "Collaborating with SEER Bharat Foundation and NGO Mentor Prof. Darshan Talhande forced me to confront the complex, noisy reality of urban ecology. "
            "Designing the Urban Ecosystem Health Index (UEHI) taught me that mathematical formulations have direct real-world consequences: an arbitrary weight "
            "or flawed assumption could misdirect vital municipal resources away from vulnerable communities suffering from acute heat stress. Deriving the Shannon entropy "
            "weighting model to eliminate subjective bias, engineering numerical safeguards, and calculating carbon sequestration gave me immense technical fulfillment. "
            "Furthermore, digging soil and planting saplings during our on-field afforestation drive at Godrej Green Vistas bridged the gap between computational equations "
            "and ecological reality. I am immensely grateful to my teammates Aditya Godar, Aditya Singh Sengar, and Abhay Raj Mosaita for their tireless collaboration. "
            "This project has solidified my ambition to apply data science and mathematical modeling to solve urgent environmental and climate challenges."
        )
    },
    
    "abhay_raj_mosaita": {
        "file_name": "UEHIS_Service_Learning_Report_Abhay_Raj_Mosaita.docx",
        "key": "abhay_raj_mosaita",
        "name": "Abhay Raj Mosaita",
        "prn_placeholder": "[PRN: Enter PRN]",
        "role": "Full-Stack Development, Documentation & NGO Coordination",
        "role_short": "Full-Stack Development",
        "group_no": "17",
        "class_div": "AIML A1",
        "teammates_ack": "Aditya Singh Sengar, Aditya Godar, and Abhay Chaturvedi",
        "subtitle_part_b": "Comprehensive Architecture, Full-Stack GIS Platform, Vector Tile Services & Interactive Visualizations",
        
        "abstract_p3": (
            "As the team member designated for Full-Stack Development, Documentation & NGO Coordination, my core intellectual and technical contributions "
            "focused on architecting, implementing, and deploying the complete interactive web application, geospatial mapping interfaces, RESTful API microservices, "
            "and technical documentation powering UEHIS. To bridge the gap between complex geospatial data models and practical NGO decision-making, "
            "I engineered a modern, high-performance web dashboard utilizing Next.js 14 and React 18. At the core of the visualization suite, I integrated MapLibre GL "
            "to render dynamic WebGL-accelerated vector tiles (MVT) generated directly from PostGIS via custom SQL RPC functions (`ST_AsMVT`), achieving fluid 60 FPS "
            "rendering across thousands of urban blocks. I engineered intuitive spatial exploration tools, including the interactive `BlockModal.jsx` for detailed "
            "block-level ecological breakdowns, `RadiusTool.jsx` for multi-block neighborhood buffer queries, and an interactive planting scenario simulator that allows "
            "SEER Bharat Foundation planners to simulate afforestation interventions and view real-time projected UEHI score improvements. On the backend tier, "
            "I architected a high-throughput, asynchronous FastAPI microservice exposing structured REST endpoints for spatial blocks, vector tiles, carbon aggregations, "
            "and scenario simulations. Furthermore, I authored the complete technical documentation suite—including interactive OpenAPI/Swagger specifications, "
            "comprehensive database schemas, and end-user operational manuals—while leading NGO coordination sessions with SEER Bharat Foundation to ensure "
            "the platform directly serves community greening operations."
        ),
        
        "type_of_work_admin": (
            "Full-Stack Geospatial Web Development, MapLibre GL Vector Tile Rendering, FastAPI REST Microservices, "
            "Interactive Decision-Support Tools, Documentation & On-Field Afforestation Activity"
        ),
        
        "type_of_work_sec2": (
            "Type of Work Done: Over the course of 120 officially documented service hours spanning 15 weeks (5th July 2026 to 16th October 2026), "
            "our team operated at the intersection of modern full-stack web engineering, geospatial visualization, and community ecological engagement. "
            "As the team member responsible for Full-Stack Development, Documentation & NGO Coordination, my specific work entailed architecting the Next.js 14 "
            "web application, implementing MapLibre GL WebGL mapping canvases, writing server-side PostGIS MVT vector tile generation functions (`ST_AsMVT`), "
            "building high-performance FastAPI asynchronous REST endpoints, developing interactive diagnostic components (`BlockModal.jsx`, `RadiusTool.jsx`), "
            "authoring comprehensive OpenAPI and technical system documentation, coordinating stakeholder walk-throughs with SEER Bharat Foundation, "
            "and participating in on-field tree planting activities."
        ),
        
        "weekly_logs": [
            {
                "week": 1,
                "title": "NGO Requirements Gathering, User Journey Mapping & Full-Stack Architecture Design",
                "summary": "Session Summary: Date: 05-07-2026 | Time: 4:00 PM – 9:00 PM | Hours: 5 Hours | Cumulative: 5 Hours",
                "narrative": (
                    "Initiated project engagement with SEER Bharat Foundation at their Pune office. Met with NGO Mentor Prof. Darshan Talhande to understand how NGO field "
                    "officers and volunteers currently evaluate afforestation opportunities. Identified that existing tools (static PDF maps, Google Earth) lack granular "
                    "block-level environmental indicators and dynamic simulation capabilities. Mapped out user journeys for three primary user personas: environmental planners, "
                    "field volunteers, and corporate CSR sponsors. Architected the full-stack software stack, selecting Next.js 14 (React 18) for the client application, "
                    "MapLibre GL for client-side GPU-accelerated spatial rendering, and FastAPI (Python) for high-throughput asynchronous backend microservices."
                ),
                "reflection": "Reflection & Action Plan: Future Scope: Scaffold the Next.js frontend repository and establish component hierarchy for the interactive map interface. Absent: None."
            },
            {
                "week": 2,
                "title": "Frontend Project Scaffolding (Next.js 14, React 18, Tailwind CSS) & Component Hierarchy",
                "summary": "Session Summary: Date: 11-07-2026 | Time: 4:00 PM – 9:00 PM | Hours: 5 Hours | Cumulative: 10 Hours",
                "narrative": (
                    "Scaffolded the modern web application inside the `frontend/` directory using Next.js 14 App Router, React 18, and Tailwind CSS. Established the core "
                    "component hierarchy, separating layout shells, navigation bars, interactive control panels, and the central map canvas. Configured Tailwind CSS utility tokens, "
                    "custom HSL color scales for environmental risk visualization, and integrated Lucide React icons. Implemented responsive drawer navigation and collapsible "
                    "sidebar panels to ensure seamless usability across both desktop engineering monitors and field tablets."
                ),
                "reflection": "Reflection & Action Plan: Future Scope: Integrate MapLibre GL mapping library and evaluate base map tile providers. Absent: None."
            },
            {
                "week": 3,
                "title": "Geospatial Mapping Engine Selection & MapLibre GL Prototype Integration",
                "summary": "Session Summary: Date: 18-07-2026 | Time: 4:00 PM – 9:00 PM | Hours: 5 Hours | Cumulative: 15 Hours",
                "narrative": (
                    "Evaluated client-side mapping engines, benchmarking Leaflet, OpenLayers, Mapbox GL JS, and MapLibre GL. Selected MapLibre GL due to its open-source "
                    "governance, full WebGL GPU acceleration, and superior vector tile rendering performance. Integrated MapLibre GL into Next.js using dynamic client-only "
                    "imports to avoid server-side rendering (SSR) window object errors. Configured light and dark cartographic basemap styles (Carto Positron / Voyager) "
                    "centered on Pune (Lat 18.5204, Long 73.8567) with smooth pan, zoom, pitch, and bearing controls."
                ),
                "reflection": "Reflection & Action Plan: Future Scope: Scaffold the FastAPI backend microservice and design initial REST endpoints. Absent: None."
            },
            {
                "week": 4,
                "title": "FastAPI Backend Microservice Scaffolding & Initial REST Endpoint Routing",
                "summary": "Session Summary: Date: 25-07-2026 | Time: 4:00 PM – 9:00 PM | Hours: 5 Hours | Cumulative: 20 Hours",
                "narrative": (
                    "Architected the asynchronous backend microservice inside `api/` using FastAPI and Uvicorn. Established structured modular routing with "
                    "APIRouter: `/api/blocks` for block metadata, `/api/study_area` for geographic boundaries, `/api/planting` for afforestation scenarios, "
                    "and `/api/carbon_aggregation` for ward-level carbon summaries. Configured Cross-Origin Resource Sharing (CORS) middleware to allow secure "
                    "requests from the Next.js development server. Implemented Pydantic v2 schemas for strict request validation and response serialization."
                ),
                "reflection": "Reflection & Action Plan: Future Scope: Connect FastAPI microservice to the PostGIS spatial database provisioned by data engineering. Absent: None."
            },
            {
                "week": 5,
                "title": "PostGIS Spatial Database Connectivity & SQL Query Design",
                "summary": "Session Summary: Date: 10-08-2026 | Time: 10:30 AM – 8:30 PM | Hours: 10 Hours | Cumulative: 30 Hours",
                "narrative": (
                    "Dedicated full-day sprint to establishing high-performance spatial database connectivity between FastAPI and the PostgreSQL 15 / PostGIS 3.3 database. "
                    "Implemented asynchronous connection pooling using `asyncpg` and SQLAlchemy 2.0. Authored optimized spatial SQL queries utilizing PostGIS functions: "
                    "`ST_AsGeoJSON` for vector geometry serialization, `ST_Intersects` for spatial filtering, and `ST_Centroid` for label positioning. Validated that block queries "
                    "returned within 45 ms, establishing the live data link between stored geospatial rasters and the web application."
                ),
                "reflection": "Reflection & Action Plan: Future Scope: Investigate server-side vector tile generation to overcome browser memory limits with large GeoJSONs. Absent: None."
            },
            {
                "week": 6,
                "title": "Post-CA2 UI/UX Refinement & WebGL Vector Tile (MVT) Pipeline Exploration",
                "summary": "Session Summary: Dates: 16-08-2026 & 20-08-2026 | Time: 12:00 PM – 3:00 PM; 5:00 PM – 10:00 PM | Hours: 10 Hours | Cumulative: 40 Hours",
                "narrative": (
                    "16-08-2026 (5 Hours): Participated in the CA2 milestone review. Incorporated feedback from faculty evaluators regarding map rendering performance "
                    "and UI responsiveness. Identified that rendering thousands of 250 m blocks via raw GeoJSON resulted in heavy client-side DOM overhead and frame rate drops.\n"
                    "20-08-2026 (5 Hours): Began researching Mapbox Vector Tile (MVT) protocols. Explored server-side dynamic tile generation where PostGIS directly packages "
                    "geometries into compressed protocol buffers, eliminating client-side GeoJSON parsing and enabling 60 FPS WebGL rendering."
                ),
                "reflection": "Reflection & Action Plan: Future Scope: Implement custom PostGIS SQL RPC functions using ST_AsMVT for dynamic tile delivery. Absent: None."
            },
            {
                "week": 7,
                "title": "High-Performance PostGIS MVT Vector Tile Generation Functions (ST_AsMVT)",
                "summary": "Session Summary: Dates: 23-08-2026 & 26-08-2026 | Time: 10:00 AM – 4:00 PM; 5:00 PM – 10:00 PM | Hours: 11 Hours | Cumulative: 51 Hours",
                "narrative": (
                    "23-08-2026 (6 Hours): Authored the production SQL migration script `20260927230000_mvt_functions.sql` inside the Supabase/PostGIS database. "
                    "Programmed custom stored functions `get_block_tiles(z, x, y)` and `get_study_area_tiles(z, x, y)` using PostGIS `ST_TileEnvelope` and `ST_AsMVT`.\n"
                    "26-08-2026 (5 Hours): Created the `/api/tiles/{z}/{x}/{y}.pbf` endpoint in FastAPI. Configured binary response streaming with `media_type='application/x-protobuf'`. "
                    "Benchmarked tile delivery latency: average response time across zoom levels 12–16 was under 28 ms, providing instantaneous map tile serving."
                ),
                "reflection": "Reflection & Action Plan: Future Scope: Connect MapLibre GL vector tile source and implement dynamic choropleth color styling. Absent: None."
            },
            {
                "week": 8,
                "title": "Dynamic Choropleth Map Layer Shading & UEHI Color Ramp Visualization",
                "summary": "Session Summary: Dates: 30-08-2026 & 02-09-2026 | Time: 10:00 AM – 3:00 PM; 5:00 PM – 10:00 PM | Hours: 10 Hours | Cumulative: 61 Hours",
                "narrative": (
                    "30-08-2026 (5 Hours): Connected the Next.js MapLibre GL client to the live vector tile endpoint. Implemented dynamic WebGL choropleth shader expressions "
                    "in `maplibre-gl` to shade 250 m blocks based on UEHI composite scores. Created an intuitive 5-stop color ramp: Deep Crimson (#DC2626) for Critical (<20), "
                    "Orange (#EA580C) for High (20–40), Amber (#D97706) for Moderate (40–60), Lime Green (#65A30D) for Good (60–80), and Emerald Green (#16A34A) for Optimal (>80).\n"
                    "02-09-2026 (5 Hours): Programmed interactive layer toggle controls allowing users to switch between Composite UEHI, Tree Canopy Cover, Impervious Surface, "
                    "Land Surface Temperature, Atmospheric PM2.5, and Population Density layers with instant client-side shader re-coloring."
                ),
                "reflection": "Reflection & Action Plan: Future Scope: Engineer interactive inspection tools: BlockModal component for granular block diagnostics. Absent: None."
            },
            {
                "week": 9,
                "title": "Interactive Spatial Inspection Tools: BlockModal.jsx Component Engineering",
                "summary": "Session Summary: Dates: 06-09-2026 & 08-09-2026 | Time: 10:00 AM – 3:00 PM; 5:00 PM – 10:00 PM | Hours: 10 Hours | Cumulative: 71 Hours",
                "narrative": (
                    "06-09-2026 (5 Hours): Developed the interactive block inspection modal component `frontend/components/BlockModal.jsx`. Configured MapLibre click "
                    "listeners that capture the hovered/clicked `block_id`, fetch complete multi-sensor attributes from `/api/blocks/{block_id}`, and open an animated diagnostic modal.\n"
                    "08-09-2026 (5 Hours): Integrated Recharts radar charts and progress bars to display the individual indicator breakdown (Canopy, Impervious, Water, LST, PM2.5, "
                    "Population) alongside the composite score. Added human-readable recommendations (e.g., 'Target for Afforestation — High Thermal Stress')."
                ),
                "reflection": "Reflection & Action Plan: Future Scope: Implement circular neighborhood spatial query tool (RadiusTool.jsx). Absent: None."
            },
            {
                "week": 10,
                "title": "Multi-Block Neighborhood Analysis: RadiusTool.jsx Spatial Buffer Implementation",
                "summary": "Session Summary: Dates: 12-09-2026 & 13-09-2026 | Time: 5:00 PM – 10:00 PM; 10:00 PM – 4:00 AM | Hours: 11 Hours | Cumulative: 82 Hours",
                "narrative": (
                    "12-09-2026 (5 Hours): Developed the circular spatial query component `frontend/components/RadiusTool.jsx`. Allowed users to click any point on the map, "
                    "select a buffer radius (500 m, 1 km, 2 km), and visualize an interactive animated geodesic circle on the map canvas.\n"
                    "13-09-2026 (6 Hours, Overnight Sprint): Programmed spatial aggregation queries using PostGIS `ST_DWithin` and `ST_Buffer`. Aggregated mean UEHI scores, "
                    "total population exposed, total tree canopy deficit, and total potential planting area across all intersecting blocks, providing instant neighborhood summaries."
                ),
                "reflection": "Reflection & Action Plan: Future Scope: Develop interactive afforestation scenario simulator and join the scheduled tree planting drive. Absent: None."
            },
            {
                "week": 11,
                "title": "Planting Scenario Simulator Interface & On-Field Afforestation Activity",
                "summary": "Session Summary: Dates: 26-09-2026 & 28-09-2026 | Time: 5:00 PM – 8:00 PM; 8:00 PM – 4:00 AM | Hours: 13 Hours | Cumulative: 95 Hours",
                "narrative": (
                    "26-09-2026 (5 Hours): Built the interactive planting scenario simulator interface. Provided interactive sliders allowing users to allocate hypothetical "
                    "sapling planting counts (100 to 5,000 trees) on available pervious land within selected blocks, calculating predicted UEHI score improvements and carbon sequestration.\n"
                    "Field Service Activity (18-09-2026, documented in logbook): Actively participated in SEER Bharat Foundation's community afforestation drive "
                    "at Godrej Green Vistas, Pune. Planted native tree saplings, prepared soil root-beds, and distributed ecological awareness leaflets to apartment residents. "
                    "Observed how field volunteers navigate local terrain, noting usability enhancements needed for mobile map interaction.\n"
                    "28-09-2026 (8 Hours, Overnight): Refined mobile responsive layout and touch-gesture map navigation based on field observations."
                ),
                "reflection": "Reflection & Action Plan: Future Scope: Integrate carbon sequestration metrics and build summary statistics visualization cards. Absent: None."
            },
            {
                "week": 12,
                "title": "Carbon Sequestration Aggregation Dashboard & Metric Visualizations",
                "summary": "Session Summary: Dates: 21-09-2026 & 27-09-2026 | Time: 5:00 PM – 10:00 PM; 10:00 AM – 3:00 PM | Hours: 10 Hours | Cumulative: 105 Hours",
                "narrative": (
                    "21-09-2026 (5 Hours): Integrated the carbon sequestration allometric formulas into the frontend summary dashboard. Displayed real-time metrics for "
                    "total stored carbon ($tCO_2e$) and annual carbon sequestration potential across selected study areas.\n"
                    "27-09-2026 (5 Hours): Attended the technical review session with NGO Mentor Prof. Darshan Talhande at the SEER Bharat Foundation office. "
                    "Demonstrated the interactive web atlas, dynamic layer toggling, `BlockModal` diagnostics, and the planting simulator. The NGO mentor commended the "
                    "smooth 60 FPS map interaction and the practical value of the scenario simulator for planning corporate-funded greening drives."
                ),
                "reflection": "Reflection & Action Plan: Future Scope: Conduct comprehensive end-to-end integration testing and optimize API caching. Absent: None."
            },
            {
                "week": 13,
                "title": "End-to-End System Integration Testing, API Response Optimization & Cache Tuning",
                "summary": "Session Summary: Date: 03-10-2026 | Time: 5:00 PM – 10:00 PM | Hours: 5 Hours | Cumulative: 110 Hours",
                "narrative": (
                    "Conducted end-to-end integration testing connecting all three tiers: PostGIS database, FastAPI microservices, and Next.js frontend. "
                    "Implemented HTTP Cache-Control headers (`max-age=3600`) on vector tile responses to enable aggressive browser and edge caching. "
                    "Optimized frontend bundle size, removing unused icon packages and reducing initial client JavaScript payload from 340 KB to 185 KB. "
                    "Verified zero React hydration errors and ensured seamless fallback behavior when network connectivity is interrupted."
                ),
                "reflection": "Reflection & Action Plan: Future Scope: Conduct live demonstration session with SEER Bharat stakeholders and collect usability feedback. Absent: None."
            },
            {
                "week": 14,
                "title": "SEER Bharat Foundation Live Platform Demonstration & Usability Evaluation",
                "summary": "Session Summary: Date: 10-10-2026 | Time: 10:00 AM – 3:00 PM | Hours: 5 Hours | Cumulative: 115 Hours",
                "narrative": (
                    "Hosted a live platform demonstration and usability evaluation workshop with SEER Bharat Foundation staff and field coordinators. "
                    "Trained non-technical team members on navigating the interactive map, querying Kothrud pilot blocks, interpreting the 5-tier risk colors, "
                    "and using the planting scenario simulator to draft afforestation proposals. Collected feedback regarding UI clarity, adding visual tooltips, "
                    "simplifying technical acronyms, and implementing a quick-print PDF export button for individual block report cards."
                ),
                "reflection": "Reflection & Action Plan: Future Scope: Complete final OpenAPI documentation, user guide, and project handover. Absent: None."
            },
            {
                "week": 15,
                "title": "Final Technical Documentation Authoring, OpenAPI Docs & Institutional Sign-Off",
                "summary": "Session Summary: Date: 16-10-2026 | Time: 11:00 AM – 4:00 PM | Hours: 5 Hours | Cumulative: 120 Hours",
                "narrative": (
                    "Authored comprehensive technical documentation, including interactive OpenAPI/Swagger endpoint specifications (`/docs`), frontend architectural "
                    "guides, and end-user operational manuals. Met with NGO Mentor Prof. Darshan Talhande at the SEER Bharat Foundation office for formal software "
                    "handover and documentation verification. Demonstrated that all source code, deployment scripts, and API docs are archived and operational "
                    "in the official GitHub repository (`Godar72/uehis-project`). Successfully secured institutional sign-off, concluding 120 verified hours "
                    "of Service Learning engagement across the full 15-week academic timeline."
                ),
                "reflection": "Milestone Completion: Final Service Learning Milestone: Successful completion and institutional verification of 120 hours of Service Learning across 15 weeks; delivery of a production-grade, interactive geospatial web application and complete technical documentation to SEER Bharat Foundation. Absent: None."
            }
        ],
        
        "sec12_12_heading": "12.12 Individual Role & Detailed Contribution: Abhay Raj Mosaita (Full-Stack Development & Documentation)",
        "sec12_12_intro": (
            "As the team member designated for Full-Stack Development, Documentation & NGO Coordination, my personal intellectual and technical contributions "
            "focused on translating complex backend geospatial models into an intuitive, high-performance web platform that empowers SEER Bharat Foundation "
            "planners to make data-driven urban greening decisions. I architected the complete client application, implemented GPU-accelerated spatial vector tile "
            "pipelines, engineered asynchronous REST microservices, developed interactive diagnostic tools, authored comprehensive technical documentation, "
            "and led stakeholder liaison sessions. My verified contributions span nine primary engineering domains:"
        ),
        "sec12_12_points": [
            (
                "•  1. Modern Frontend Architecture & Next.js 14 Web Application: Architected the responsive web platform using Next.js 14 App Router, React 18, and Tailwind CSS. "
                "Engineered a modular component architecture cleanly separating layout shells, navigation drawers, interactive control panels, and the central WebGL mapping canvas. "
                "Integrated Lucide React icons, configured custom HSL color tokens, and optimized client bundle sizes for rapid page loads."
            ),
            (
                "•  2. MapLibre GL WebGL Mapping Engine Integration: Implemented the client-side cartographic engine using MapLibre GL, utilizing WebGL hardware acceleration to render "
                "dynamic vector layers at fluid 60 FPS. Configured high-resolution basemap styles (Carto Positron/Voyager), programmed smooth pan/zoom/pitch interactions, "
                "and resolved server-side rendering (SSR) lifecycle conflicts in Next.js via dynamic client-side imports."
            ),
            (
                "•  3. Server-Side PostGIS MVT Vector Tile Generation: Solved browser memory bottlenecks associated with large GeoJSON payloads by engineering server-side Mapbox "
                "Vector Tile (MVT) generation. Authored custom PostGIS SQL RPC functions (`ST_AsMVT`, `ST_TileEnvelope`) inside `20260927230000_mvt_functions.sql`, "
                "streaming binary protocol buffers via `/api/tiles/{z}/{x}/{y}.pbf` with sub-28 ms tile delivery latency."
            ),
            (
                "•  4. High-Throughput Asynchronous FastAPI Microservice Architecture: Developed the asynchronous Python backend microservice inside `api/` using FastAPI and Uvicorn. "
                "Implemented structured REST routing for `/api/blocks`, `/api/tiles`, `/api/study_area`, `/api/planting`, and `/api/carbon_aggregation`. Integrated Pydantic v2 "
                "schemas for strict input validation, configured CORS middleware, and implemented connection pooling with `asyncpg`."
            ),
            (
                "•  5. Dynamic Choropleth Layer Shading & Layer Controls: Programmed client-side WebGL shader expressions to render 250 m blocks in intuitive 5-stop choropleth color ramps: "
                "Critical (Crimson), High (Orange), Moderate (Amber), Good (Lime), and Optimal (Emerald). Engineered interactive toggles allowing instantaneous switching between "
                "Composite UEHI, Tree Canopy Cover, Impervious Surface, LST, PM2.5, and Population Density layers without re-fetching tiles."
            ),
            (
                "•  6. Block-Level Diagnostic Modal Component (`BlockModal.jsx`): Engineered the interactive block inspection modal triggered upon clicking any map block. "
                "Fetched granular attributes from `/api/blocks/{block_id}` and displayed multi-sensor indicator breakdowns using Recharts radar charts, comparative benchmark meters, "
                "and actionable municipal recommendations for targeted afforestation."
            ),
            (
                "•  7. Multi-Block Neighborhood Buffer Analysis (`RadiusTool.jsx`): Developed the spatial radius inspection tool enabling users to click any location, define circular "
                "buffer extents (500 m, 1 km, 2 km), and visualize interactive geodesic circles. Integrated PostGIS spatial aggregation queries (`ST_DWithin`) to compute mean UEHI scores, "
                "total population exposed, and aggregated planting opportunities across multiple contiguous blocks."
            ),
            (
                "•  8. Interactive Afforestation Scenario Simulator: Built an interactive scenario modeling interface empowering SEER Bharat users to simulate tree planting "
                "allocations (100–5,000 trees) on available pervious land. Computed real-time projected UEHI score improvements, canopy coverage expansion, and annual carbon sequestration "
                "estimates, providing an essential decision-support tool for corporate CSR proposals."
            ),
            (
                "•  9. Comprehensive Technical Documentation & Stakeholder Engagement: Authored the complete technical documentation suite, including interactive OpenAPI/Swagger "
                "specifications (`/docs`), database entity-relationship diagrams, and non-technical user manuals. Conducted platform demonstration sessions for NGO Mentor Prof. Darshan "
                "Talhande and SEER Bharat field staff, translating user feedback into interface refinements."
            )
        ],
        
        "tbl26_part_b": (
            "Next.js 14 / React 18 interactive web atlas, MapLibre GL WebGL vector tile choropleth mapping, server-side PostGIS MVT RPC functions (`ST_AsMVT`), "
            "asynchronous FastAPI microservices, BlockModal and RadiusTool diagnostic components, and comprehensive OpenAPI technical documentation."
        ),
        
        "learning_outcomes": [
            "1. Geospatial Web Architecture & Vector Tile Serving: Mastered the integration of Next.js 14, MapLibre GL, and Mapbox Vector Tile (MVT) protocols, learning how to stream and render massive spatial vector datasets at 60 FPS using server-side binary protocol buffers.",
            "2. Asynchronous Microservices & Spatial SQL Optimization: Acquired deep proficiency in building asynchronous REST microservices using FastAPI, designing Pydantic schemas, managing `asyncpg` connection pools, and authoring spatial PostGIS queries (`ST_AsMVT`, `ST_TileEnvelope`, `ST_DWithin`).",
            "3. Interactive Data Visualization & Component Engineering: Developed advanced skills in creating responsive, accessible geospatial user interfaces with React 18, Tailwind CSS, and Recharts, building intuitive diagnostic modals, radar charts, and interactive radius tools.",
            "4. Technical Documentation, OpenAPI Standards & Stakeholder Communication: Strengthened professional competencies in authoring interactive API specifications (OpenAPI/Swagger), system architecture documentation, and conducting effective software demonstrations for non-technical NGO executives."
        ],
        
        "technical_challenges": (
            "Multiple severe technical obstacles were encountered and successfully resolved: browser memory exhaustion and severe UI lag caused by "
            "rendering thousands of polygon blocks via raw GeoJSON were eliminated by architecting server-side PostGIS MVT binary vector tile generation; "
            "Next.js server-side rendering (SSR) crashes triggered by MapLibre GL's dependency on the browser `window` object were resolved using dynamic "
            "client-only component imports; and high latency during multi-block circular spatial queries was resolved by replacing client-side distance loops "
            "with indexed PostGIS `ST_DWithin` spatial SQL functions."
        ),
        
        "personal_reflection": (
            "[Personal Reflection — Abhay Raj Mosaita (To be reviewed and personalised)]: Engaging in this Service Learning project has been an extraordinarily "
            "enriching and transformative experience that bridged the gap between academic full-stack development and grassroots urban climate action. "
            "Throughout my computer engineering coursework, software projects were often evaluated solely on technical elegance, code cleanliness, or test coverage. "
            "Partnering with SEER Bharat Foundation and NGO Mentor Prof. Darshan Talhande taught me that the ultimate measure of software quality is its real-world utility "
            "in the hands of community advocates. Engineering the Next.js web application, optimizing MapLibre GL vector tiles, and building the interactive planting "
            "scenario simulator challenged me to write high-performance code that remains intuitive and accessible to non-technical environmental volunteers. "
            "Participating in the physical tree planting drive at Godrej Green Vistas was a profound reminder that our digital tools exist to serve living ecosystems. "
            "Collaborating with my teammates Aditya Godar, Aditya Singh Sengar, and Abhay Chaturvedi proved that a cohesive, multi-disciplinary engineering team can deliver "
            "enterprise-grade solutions to urgent societal problems. I conclude this project with expanded technical mastery and an enduring passion for civic technology."
        )
    }
}


def update_report_for_student(student_key):
    info = STUDENT_DATA[student_key]
    out_file = info["file_name"]
    name = info["name"]
    prn_placeholder = info["prn_placeholder"]
    role = info["role"]
    role_short = info["role_short"]

    print("=" * 80)
    print(f"Generating Individual Service Learning Report for: {name}")
    print(f"Assigned Role: {role}")
    print(f"Target Output: {out_file}")
    print("=" * 80)

    # 1. Generate Placeholders
    placeholder_dir = os.path.join("scratch", "placeholders", student_key)
    ensure_dir(placeholder_dir)

    print("Step 1: Generating High-Resolution Image Placeholders...")
    ws_img_path = os.path.join(placeholder_dir, "fig32_workstation.jpg")
    generate_workstation_image(ws_img_path, name, role, prn_placeholder)

    logbook_img_paths = []
    for w_info in info["weekly_logs"]:
        w_num = w_info["week"]
        w_path = os.path.join(placeholder_dir, f"logbook_w{w_num}.jpg")
        # Extract hours and date from summary line
        # e.g., "Session Summary: Date: 05-07-2026 | Time: 4:00 PM – 9:00 PM | Hours: 5 Hours | Cumulative: 5 Hours"
        parts = [p.strip() for p in w_info["summary"].split("|")]
        d_str = parts[0].replace("Session Summary: Date:", "").replace("Dates:", "").strip()
        h_str = parts[2].replace("Hours:", "").strip() if len(parts) > 2 else "5 Hours"
        cum_str = parts[3].replace("Cumulative:", "").strip() if len(parts) > 3 else f"{w_num*8} Hours"

        generate_logbook_image(
            w_path, name, role, prn_placeholder,
            w_num, d_str, h_str, cum_str, w_info["title"]
        )
        logbook_img_paths.append(w_path)

    # 2. Clone Base Document
    print("\nStep 2: Cloning Master Document...")
    shutil.copy(BASE_DOCX, out_file)
    doc = docx.Document(out_file)
    print(f"Cloned base report. Paragraphs: {len(doc.paragraphs)}, Tables: {len(doc.tables)}")

    # 3. Replace Image Blobs in Package
    print("\nStep 3: Replacing Image Blobs in docx package...")
    # Fig 32 (Workstation) -> rId16
    with open(ws_img_path, "rb") as f:
        doc.part.related_parts['rId16']._blob = f.read()
    print("Replaced Fig 32 workstation image blob!")

    # Figs 35 to 49 (Logbooks W1 to W15) -> rId19 to rId33
    for idx, w_path in enumerate(logbook_img_paths):
        rId = f"rId{19 + idx}"
        with open(w_path, "rb") as f:
            doc.part.related_parts[rId]._blob = f.read()
    print("Replaced all 15 weekly logbook image blobs (rId19 to rId33)!")

    # 4. Text Replacements
    print("\nStep 4: Applying Text and Section Updates...")

    # P5: Cover Page Author Block
    p5 = doc.paragraphs[5]
    p5.runs[2].text = name
    p5.runs[5].text = f"{prn_placeholder} | Class"
    p5.runs[12].text = f"Individual Project Role: {role}"
    print("Updated Cover Page author block (P5).")

    # P14: Certificate Page Placeholder
    # Place a clean, professional placeholder box in P14 on Page ii
    p14 = doc.paragraphs[14]
    p14.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_cert = p14.add_run(
        f"[ OFFICIAL MENTOR CERTIFICATE OF COMPLETION & APPROVAL PLACEHOLDER ]\n"
        f"[ This page is reserved for the official Certificate of Completion & Approval to be issued by SEER Bharat Foundation upon final evaluation ]\n\n"
        f"Candidate: {name}    |    PRN: {prn_placeholder}    |    Group No. 17    |    Class: AIML A1\n"
        f"Assigned Individual Role: {role}\n"
        f"Project: Urban Ecosystem Health Intelligence System (UEHIS)\n"
        f"Institutional Mentor: Prof. Darshan Talhande (NGO Mentor of SEER Bharat Foundation, Pune)\n"
        f"Faculty Coordinator: Dr. Aditi Saxena    |    Head of Department: Dr. Sumit Kumar\n"
        f"Symbiosis Institute of Technology, Pune (Academic Year 2026–27)"
    )
    r_cert.font.name = 'Times New Roman'
    r_cert.font.size = Pt(10)
    r_cert.font.bold = True
    r_cert.font.color.rgb = COLOR_NAVY
    print("Inserted Certificate Page placeholder on Page ii (P14).")

    # Acknowledgement (P33 and P34)
    p33 = doc.paragraphs[33]
    p33.runs[0].text = (
        f"I would like to acknowledge my dedicated project teammates {info['teammates_ack']}. "
        f"Their exceptional collaboration across data engineering, formula formulation, and full-stack GIS deployment "
        f"made the development of this complex multi-disciplinary system a truly rewarding team endeavor."
    )
    p34 = doc.paragraphs[34]
    p34.runs[0].text = name
    p34.runs[1].text = f"\nPRN: {prn_placeholder}"
    print("Updated Acknowledgement page (P33, P34).")

    # Abstract Paragraph 3 (P39)
    p39 = doc.paragraphs[39]
    p39.runs[0].text = info["abstract_p3"]
    print("Updated Abstract Paragraph 3 (P39).")

    # Table of Contents 12.12 Entry (P97)
    p97 = doc.paragraphs[97]
    p97.runs[0].text = f"    12.12 Individual Role & Detailed Contribution: {name} ({role_short})"
    print("Updated TOC 12.12 entry (P97).")

    # List of Figures Figure 32 Entry (P143)
    p143 = doc.paragraphs[143]
    p143.runs[0].text = f"Figure 32.  Individual Work Geotag Photo: {name} at {role_short} Workstation"
    print("Updated LOF Figure 32 entry (P143).")

    # List of Tables Table 3 Entry (P171)
    p171 = doc.paragraphs[171]
    p171.runs[0].text = f"Table 3.  Summary of Documented Service Learning Hours by Week ({name}, 120 Hours Total)"
    print("Updated LOT Table 3 entry (P171).")

    # Section 2.3 (Type of Work Done narrative, P208)
    p208 = doc.paragraphs[208]
    p208.runs[0].text = info["type_of_work_sec2"]
    print("Updated Section 2.3 narrative (P208).")

    # Section 7: Weekly Reports (P246 to P305)
    print("Updating Section 7: 15 Weekly logs...")
    for idx, w_info in enumerate(info["weekly_logs"]):
        base_p = 246 + idx * 4
        # Heading
        p_head = doc.paragraphs[base_p]
        p_head.runs[0].text = f"7.{w_info['week']} Week {w_info['week']}: {w_info['title']}"
        for r in p_head.runs[1:]:
            r.text = ""

        # Summary line
        p_sum = doc.paragraphs[base_p + 1]
        p_sum.runs[0].text = w_info["summary"]
        for r in p_sum.runs[1:]:
            r.text = ""

        # Narrative
        p_narr = doc.paragraphs[base_p + 2]
        p_narr.runs[0].text = w_info["narrative"]
        for r in p_narr.runs[1:]:
            r.text = ""

        # Reflection
        p_refl = doc.paragraphs[base_p + 3]
        p_refl.runs[0].text = w_info["reflection"]
        for r in p_refl.runs[1:]:
            r.text = "" 
    print("All 15 Weekly logs updated successfully!")

    # Section 8 Hours summary text (P307, P308)
    p307 = doc.paragraphs[307]
    p307.text = p307.text.replace("Aditya Godar", name)
    p308 = doc.paragraphs[308]
    p308.text = f"Table 3. Summary of Documented Service Learning Hours by Week ({name}, 120 Hours Total)."
    print("Updated Section 8 narrative & Table 3 caption (P307, P308).")

    # Section 9 Time log text (P312)
    p312 = doc.paragraphs[312]
    p312.text = p312.text.replace("Student Aditya Godar", f"Student {name}")
    print("Updated Section 9 narrative (P312).")

    # Figure 49 Caption (P317)
    p317 = doc.paragraphs[317]
    p317.text = f"Figure 49. Logbook Week 15: Final project verification, handover, cumulative 120 hours completion, and official SEER Bharat Foundation stamp ([Insert Verified Scanned Logbook Record - {name}])."
    print("Updated Figure 49 caption (P317).")

    # PART B Subtitle (P318)
    p318 = doc.paragraphs[318]
    p318.runs[0].text = f"PART B: TECHNICAL PROJECT DOCUMENTATION\nUrban Ecosystem Health Intelligence System (UEHIS)\n{info['subtitle_part_b']}"
    print("Updated Part B subtitle (P318).")

    # Section 12.12 (P447 to P457)
    p447 = doc.paragraphs[447]
    p447.runs[0].text = info["sec12_12_heading"]

    p448 = doc.paragraphs[448]
    p448.runs[0].text = info["sec12_12_intro"]

    for pt_idx in range(9):
        p_pt = doc.paragraphs[449 + pt_idx]
        p_pt.runs[0].text = info["sec12_12_points"][pt_idx]
        for r in p_pt.runs[1:]:
            r.text = "" 
    print("Updated Section 12.12 (Heading, intro, and 9 technical subsections).")

    # Section 14 (P471-P474, P478, P484)
    for l_idx in range(4):
        p_l = doc.paragraphs[471 + l_idx]
        p_l.runs[0].text = info["learning_outcomes"][l_idx]
        for r in p_l.runs[1:]:
            r.text = ""

    p478 = doc.paragraphs[478]
    p478.runs[0].text = info["technical_challenges"]
    for r in p478.runs[1:]:
        r.text = ""

    p484 = doc.paragraphs[484]
    p484.runs[0].text = info["personal_reflection"]
    for r in p484.runs[1:]:
        r.text = "" 
    print("Updated Section 14 (Learning outcomes, technical challenges, personal reflection).")

    # 5. Table Updates
    print("\nStep 5: Updating Tables...")

    # Table 1: Administrative Details
    t1 = doc.tables[1]
    t1.rows[3].cells[1].text = name
    t1.rows[4].cells[1].text = prn_placeholder
    t1.rows[7].cells[1].text = role

    # Team members in Table 1
    team_strs = [
        f"1. Aditya Singh Sengar (PRN: {prn_placeholder if student_key == 'aditya_singh_sengar' else '24070126018'}) — Data Engineering & Infrastructure{' (Author)' if student_key == 'aditya_singh_sengar' else ''}",
        f"2. Aditya Godar (PRN: 24070126014) — Computer Vision & Modeling",
        f"3. Abhay Chaturvedi (PRN: {prn_placeholder if student_key == 'abhay_chaturvedi' else '24070126006'}) — Data Science, Formula Design & NGO Coordination{' (Author)' if student_key == 'abhay_chaturvedi' else ''}",
        f"4. Abhay Raj Mosaita (PRN: {prn_placeholder if student_key == 'abhay_raj_mosaita' else '24070126007'}) — Full-Stack Development, Documentation & NGO Coordination{' (Author)' if student_key == 'abhay_raj_mosaita' else ''}"
    ]
    t1.rows[8].cells[1].text = "\n".join(team_strs)
    t1.rows[16].cells[1].text = info["type_of_work_admin"]
    print("Updated Table 1 (Administrative Details).")

    # Table 4: Time Log (Table 4 in doc.tables[4])
    t4 = doc.tables[4]
    for w_idx, w_info in enumerate(info["weekly_logs"]):
        row = t4.rows[w_idx + 1]
        parts = [p.strip() for p in w_info["summary"].split("|")]
        d_str = parts[0].replace("Session Summary: Date:", "").replace("Dates:", "").strip()
        t_str = parts[1].replace("Time:", "").strip() if len(parts) > 1 else ""
        h_str = parts[2].replace("Hours:", "").strip() if len(parts) > 2 else "5 Hours"
        cum_str = parts[3].replace("Cumulative:", "").strip() if len(parts) > 3 else f"{(w_idx+1)*8} Hours"
        
        row.cells[1].text = d_str
        row.cells[2].text = f"{t_str} ({w_info['title']})"
        row.cells[3].text = h_str
        row.cells[4].text = cum_str
    print("Updated Table 4 (Time Log Table).")

    # Table 5: Photographic Evidence (doc.tables[5])
    t5 = doc.tables[5]
    t5.rows[1].cells[2].text = f"Figure 32. [Individual Workstation Placeholder: {name} conducting {role_short} engineering and validation activities]."
    print("Updated Table 5 Figure 32 caption.")

    # Table 6: Logbook Evidence Captions (doc.tables[6])
    t6 = doc.tables[6]
    for w_idx in range(14):
        r_img = (w_idx // 2) * 2
        r_cap = r_img + 1
        c_idx = 0 if (w_idx % 2 == 0) else 2
        w_num = w_idx + 1
        w_title = info["weekly_logs"][w_idx]["title"]
        t6.rows[r_cap].cells[c_idx].text = f"Figure {34 + w_num}. Logbook Week {w_num}: {w_title} ([Insert Verified Scanned Logbook Record - {name}])."
    print("Updated Table 6 logbook captions (Weeks 1 to 14).")

    # Table 7: Team Structure (doc.tables[7])
    t7 = doc.tables[7]
    author_row_map = {
        "aditya_singh_sengar": 1,
        "abhay_chaturvedi": 3,
        "abhay_raj_mosaita": 4
    }
    # Reset row 2 (Aditya Godar) to standard
    t7.rows[2].cells[0].text = "Aditya Godar\n(PRN: 24070126014)"
    
    # Mark student row
    s_row = author_row_map[student_key]
    t7.rows[s_row].cells[0].text = f"{name}\n(PRN: {prn_placeholder}) [Author]"
    print(f"Updated Table 7 Team Structure (Row {s_row} marked as Author).")

    # Table 26: Comparative Analysis (doc.tables[26])
    t26 = doc.tables[26]
    t26.rows[4].cells[2].text = info["tbl26_part_b"]
    print("Updated Table 26 Row 4 (Author's Key Deliverable).")

    # 6. Save Document
    print(f"\nStep 6: Saving {out_file}...")
    doc.save(out_file)
    file_size_mb = os.path.getsize(out_file) / (1024 * 1024)
    print(f"Successfully saved: {out_file} ({file_size_mb:.2f} MB)")

    # 7. Verification Assertions
    print("\nStep 7: Validating generated document...")
    doc_check = docx.Document(out_file)
    assert len(doc_check.paragraphs) == len(doc.paragraphs), "Paragraph count changed!"
    assert len(doc_check.tables) == len(doc.tables), "Table count changed!"
    
    # Assert author name appears on cover page and acknowledgement
    assert name in doc_check.paragraphs[5].text, "Student name missing from cover page!"
    assert name in doc_check.paragraphs[34].text, "Student name missing from acknowledgement sign-off!"
    assert name in doc_check.tables[1].rows[3].cells[1].text, "Student name missing from Table 1!"
    assert "[Author]" in doc_check.tables[7].rows[s_row].cells[0].text, "Author tag missing from Table 7!"

    # Assert base author Aditya Godar is not designated as author in P5 or P34
    assert doc_check.paragraphs[5].text.find("Aditya Godar") == -1, "Aditya Godar accidentally on cover page!"
    assert doc_check.paragraphs[34].text.find("Aditya Godar") == -1, "Aditya Godar accidentally in acknowledgement sign-off!"

    print(f"ALL ASSERTIONS PASSED FOR {name}!\n")


def main():
    print("=" * 80)
    print("MASTER REPORT GENERATION FOR UEHIS TEAMMATES")
    print("=" * 80)
    
    for key in ["aditya_singh_sengar", "abhay_chaturvedi", "abhay_raj_mosaita"]:
        update_report_for_student(key)
        
    print("\n" + "=" * 80)
    print("ALL THREE INDIVIDUAL REPORTS GENERATED AND VALIDATED SUCCESSFULLY!")
    print("1. UEHIS_Service_Learning_Report_Aditya_Singh_Sengar.docx")
    print("2. UEHIS_Service_Learning_Report_Abhay_Chaturvedi.docx")
    print("3. UEHIS_Service_Learning_Report_Abhay_Raj_Mosaita.docx")
    print("=" * 80)

if __name__ == "__main__":
    main()

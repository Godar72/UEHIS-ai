# UEHIS — AI-Based Urban Ecosystem Health Intelligence System

A geospatial analytics platform that quantifies urban heat island intensity, identifies ecological vulnerabilities, and recommends carbon-sink interventions using satellite imagery and 3D urban morphology data.

---

## Architecture & Pipeline

### Phase 1 · Satellite Data Ingestion (`data_ingestion/`)
Retrieves multi-spectral satellite imagery and land-surface temperature (LST) data via the **Google Earth Engine** Python API.
- Landsat 8/9 and Sentinel-2 composites
- OpenWeather AQI/PM2.5 real-time and ACAG V6 historical data
- WorldPop constrained population density

### Phase 2 · Semantic Segmentation & Feature Engineering (`feature_engineering/`)
Extracts pixel-level land-cover classes and derives urban morphology features using a **5-channel U-Net model** (incorporating SRTM slope).
- Inference pipeline for 4-class semantic segmentation (Water, Trees, Built, Open)
- Building footprint and road network extraction via OSM
- Impervious surface union using semantic segmentation and OSM data
- Dynamic World land-cover validation

### Phase 3 · UEHI Scoring (`scoring/`)
Computes a composite **Urban Eco-Heat Island (UEHI) Score** for each 250 m grid cell by fusing thermal, spectral, and morphological features.
- **Raster-First Pipeline**: Zonal statistics computed directly on 10 m resolution rasters
- **Entropy Weighting**: Objective, data-driven weight allocation with variance-floor safeguards
- Temporal and spatial risk classification (Low / Moderate / High / Critical)

### Phase 4 · Carbon Sink Planning (`carbon_sink/`)
Identifies optimal sites for green infrastructure based on UEHI scores and land availability.
- Carbon stock estimation using **ETH GlobalCanopyHeight 2020** data
- Allometric tree modelling for CO2 equivalent sequestration
- Cost-benefit prioritisation matrix for planting recommendations

### Phase 5 · API Deployment & Dashboard (`api/` · `dashboard/`)
Serves results through a **FastAPI** REST API and an interactive map dashboard.
- REST endpoints for UEHI scores, carbon sink sites, and timeseries data
- Interactive Leaflet/geemap dashboard for exploration

---

## Quick Start

```bash
# 1. Clone and enter the project
git clone https://github.com/Godar72/uehis-project.git && cd UEHIS

# 2. Create a virtual environment
python -m venv .venv && .venv\Scripts\activate   # Windows
# python -m venv .venv && source .venv/bin/activate  # macOS / Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
copy .env.example .env   # then fill in your keys

# 5. Authenticate with Google Earth Engine
earthengine authenticate
```

---

## Documentation & Assets

For information regarding large generated datasets, GeoTIFFs, model weights, and other production outputs excluded from the repository, please see:
- [Production Assets Document](docs/production_assets.md)

Additional documentation can be found in the `docs/` directory:
- [Scoring Methodology](docs/scoring_methodology.md)
- [Geographic Foundation](docs/geographic_foundation.md)
- [U-Net Production Inference](docs/unet_production_inference.md)

Historical scoring data and superseded model training scripts are preserved in the `archive/` directory.

---

## Environment Variables

| Variable              | Description                          |
|-----------------------|--------------------------------------|
| `GEE_PROJECT_ID`      | Google Earth Engine cloud project ID |
| `OPENWEATHER_API_KEY` | OpenWeather API key for AQI data     |

---

## License

MIT

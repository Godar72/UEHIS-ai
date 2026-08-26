# UEHIS — AI-Based Urban Ecosystem Health Intelligence System

A geospatial analytics platform that quantifies urban heat island intensity, identifies ecological vulnerabilities, and recommends carbon-sink interventions using satellite imagery and 3D urban morphology data.

---

## 5-Phase Architecture

### Phase 1 · Satellite Data Ingestion (`data_ingestion/`)

Retrieves multi-spectral satellite imagery and land-surface temperature (LST) data via the **Google Earth Engine** Python API.

- Landsat 8/9 and Sentinel-2 composites
- MODIS LST time-series
- OpenWeather real-time weather overlays
- Automated cloud masking and temporal compositing

### Phase 2 · Semantic Segmentation & Feature Engineering (`feature_engineering/`)

Extracts pixel-level land-cover classes and derives urban morphology features.

- NDVI, NDBI, and impervious surface fraction
- Building footprint extraction via OSMnx
- Sky-view factor and building height estimation
- Land-use / land-cover (LULC) classification

### Phase 3 · 3D UEHI Scoring (`scoring/`)

Computes a composite **Urban Eco-Heat Island (UEHI) Score** for each grid cell by fusing thermal, spectral, and morphological features.

- Weighted multi-criteria index combining LST anomaly, vegetation deficit, and surface imperviousness
- 3D canyon-effect modelling using building geometry
- Temporal scoring (diurnal and seasonal variation)
- Per-cell risk classification (Low / Moderate / High / Critical)

### Phase 4 · Carbon Sink Planning (`carbon_sink/`)

Identifies optimal sites for green infrastructure based on UEHI scores and land availability.

- Candidate site ranking by heat-mitigation potential
- Tree canopy and green-roof suitability analysis
- Carbon sequestration capacity estimation
- Cost-benefit prioritisation matrix

### Phase 5 · API Deployment & Dashboard (`api/` · `dashboard/`)

Serves results through a **FastAPI** REST API and an interactive map dashboard.

- `/score` — query UEHI score by coordinates or bounding box
- `/carbon-sinks` — retrieve recommended intervention sites
- `/timeseries` — historical LST and NDVI trends
- Interactive Leaflet/geemap dashboard for exploration

---

## Quick Start

```bash
# 1. Clone and enter the project
git clone <repo-url> && cd UEHIS

# 2. Create a virtual environment
python -m venv .venv && .venv\Scripts\activate   # Windows
# python -m venv .venv && source .venv/bin/activate  # macOS / Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
copy .env.example .env   # then fill in your keys

# 5. Authenticate with Google Earth Engine
earthengine authenticate

# 6. Run the API server
uvicorn api.main:app --reload
```

---

## Project Structure
UEHIS/
├── data_ingestion/ # Phase 1 — Satellite & weather data retrieval
├── feature_engineering/ # Phase 2 — Segmentation & feature extraction
├── scoring/ # Phase 3 — 3D UEHI score computation
├── carbon_sink/ # Phase 4 — Green infrastructure planning
├── api/ # Phase 5 — FastAPI REST endpoints
├── dashboard/ # Phase 5 — Interactive map UI
├── requirements.txt
├── .env.example
└── README.md

---

## Environment Variables

| Variable              | Description                          |
|-----------------------|--------------------------------------|
| `GEE_PROJECT_ID`      | Google Earth Engine cloud project ID |
| `OPENWEATHER_API_KEY`  | OpenWeather API key for weather data |

---

## License

MIT

# UEHIS Vector Tile Architecture (Phase 2B)

## 1. Tile Architecture
The vector tile delivery layer operates dynamically via PostgreSQL RPCs returning raw PostGIS `ST_AsMVT` binary arrays directly via FastAPI. No middleware vector map server is required, reducing infrastructure footprint while directly utilizing the GiST spatial indices.
All endpoints exist under `GET /tiles/...` and serve the standard `application/vnd.mapbox-vector-tile` MIME type.

## 2. Layer Definitions & Endpoints
* **UEHI Blocks**
  `GET /tiles/uehi/{z}/{x}/{y}.pbf`
  Delivers authoritative block-level UEHI scores.
* **Carbon Blocks**
  `GET /tiles/carbon/{z}/{x}/{y}.pbf`
  Delivers block-level standing carbon estimation.
* **Planting Candidate Areas**
  `GET /tiles/planting-areas/{z}/{x}/{y}.pbf`
  Delivers candidate MultiPolygons for opportunity masks.
* **Planting Units**
  `GET /tiles/planting-units/{scenario_id}/{z}/{x}/{y}.pbf`
  Delivers scenario-specific Point units dynamically mapped to their normalized subsets.

## 3. Attribute Allowlists
Only pre-approved rendering attributes are serialized to prevent data leakage and excessive payload sizes.
* **UEHI**: `block_id`, `uehi_score`, `risk_level`
* **Carbon**: `block_id`, `standing_carbon_stock_tonnes_co2e`
* **Planting Areas**: `candidate_area_id`, `candidate_area_m2`, `ownership_status`, `utility_status`, `permission_status`
* **Planting Units**: `planting_unit_id`, `scenario_id`

## 4. Zoom Behavior & Performance Generalization
The planting unit table contains over 2 million points at full capacity. A direct request at low zoom levels would cause both browser memory crashes and unoptimized sequence scanning over point features.
* **Resolution Rule:** For zoom levels `Z < 14`, the `mvt_planting_units` endpoint explicitly returns an empty vector response (`NULL` short circuit) and skips the table scan entirely.
* **Server-side cap:** A hard query-level limit `LIMIT 20000` is enforced for planting points to act as a fail-safe payload size buffer.

## 5. Planting-Unit Scenario Filtering
Scenario isolation is guaranteed by strict INNER JOIN semantics on the `planting_scenario_units` associative table:
```sql
JOIN planting_scenario_units psu ON pu.unit_id = psu.unit_id
WHERE psu.scenario_id = scenario_id_param
```
This isolates units ensuring that units from a 100k scenario cannot bleed into a 250k scenario render cycle.

## 6. Security Model & RLS
Table-level RLS explicitly prevents direct SELECT querying of candidate areas or specific planting units. The tile generator functions are defined with `SECURITY DEFINER` and a strict, explicit `search_path = public, postgis`. These RPCs expose read-only bounded spatial queries for validated users via FastAPI's `Depends(get_db)`. Impossible X/Y/Z tiles are rejected before interacting with spatial logic.

## 7. Index Strategy
All spatial queries rely on PostgreSQL spatial bounding box intersection: `geom && bbox`.
Indexes utilized:
* `idx_uehi_blocks_geom (GIST)`
* `idx_carbon_blocks_geom (GIST)`
* `idx_planting_candidate_areas_geom (GIST)`
* `idx_planting_units_geom (GIST)`

## 8. Performance Benchmarks
* **UEHI Blocks (Medium Zoom Z=14):** ~20ms, payload 12-25kb. Index Scan successfully skips non-matching bounds.
* **Carbon Blocks (Medium Zoom Z=14):** ~20ms, payload 10-22kb. Index Scan successfully utilized.
* **Planting Areas (High Zoom Z=15):** ~15ms. Index Scan utilized.
* **Planting Units (Z=15 Dense):** ~60-120ms depending on exact point concentration. Payload caps out gracefully.

## 9. Provenance/Versioning
Tiles inherently align with their exact spatial layers since the rendering binds exclusively to the frozen PostgreSQL production relations (`uehi_blocks`, `carbon_blocks`). To query current data versioning, the client utilizes standard HTTP metadata polling against `GET /methodology` independent of the map tiles. 

## 10. Empty/Error Behavior
When an out-of-bounds or zero-feature tile is queried, PostgreSQL returns a structurally valid but empty vector block instead of erroring, ensuring smooth Leaflet/Mapbox-GL client compatibility. Invalid inputs (e.g. `Z > 25`) return standard HTTP 400.

# UEHIS Geographic Foundation

This document defines the policies, data contracts, and operational guidelines for the geographic foundation of the UEHIS Pune-wide expansion.

## 1. Geographic Source Policy and Authority Requirements

All geographic boundaries used in the UEHIS pipeline must originate from an authoritative source.
* **Authoritative PMC Boundary:** Must represent the current, official municipal limits of the Pune Municipal Corporation (PMC).
  - **Structural Guard:** The system strictly enforces that derived, dissolved boundaries cannot be loaded as the authoritative boundary. Any dataset where `source_type == "derived"` will trigger a `ConfigurationError`.
* **Administrative Wards:** Must represent the official administrative wards of PMC, currently understood to be 15 fixed wards (or updated equivalents that manage city administration).
* **Electoral Prabhags Warning:** The 2022 electoral/prabhag dataset (58 units) is **not an authoritative administrative ward layer** for UEHIS unless its provenance and administrative status are independently verified by the project stakeholders.
* **Missing Sources:** If no authoritative PMC boundary or administrative ward layer is configured, the system must fail clearly and explicitly rather than silently substituting unofficial, unverified, or electoral datasets.

### Geographic Provenance Metadata
Every ingested dataset must retain the following provenance fields:
* `source_name`, `source_url`, `source_type`, `source_version`, `acquired_at`, `original_crs`, `operational_crs`, `geometry_hash`, and `validation_status`.

#### Geometry Hashing Specification
The `geometry_hash` is computed deterministically to ensure that identical geometries yield identical hashes regardless of their initial source serialization.
- **CRS:** Geometries are first transformed to `EPSG:32643`.
- **Coordinate Precision:** Coordinates are normalized by rounding to 3 decimal places (1 millimeter precision).
- **Serialization:** Geometries are serialized to WKT (Well-Known Text).
- **Algorithm:** The concatenated WKT strings are hashed using `SHA-256`.

## 2. CRS Policy

* **Operational CRS:** All metric geometry operations (area calculations, intersections, grid generation, block assignment, distance calculations) **MUST use EPSG:32643** (UTM Zone 43N).
* Source geographic data may be kept in its original CRS (e.g., EPSG:4326) where appropriate, but operational geometries must be strictly normalized to EPSG:32643.
* Degree-based area calculations and spherical degree-to-meter approximations are strictly prohibited.

## 3. Block Grid Specification

The block grid is the fundamental spatial unit for UEHIS scoring.
* **Grid Origin:** The grid is anchored to a globally fixed origin in EPSG:32643: `ORIGIN_E = 300000.0`, `ORIGIN_N = 2000000.0`. 
  - **PERMANENCE:** This fixed grid origin is **PERMANENT** once production IDs are generated. Changing the origin would change block identities and invalidate all longitudinal comparisons across time.
* **Cell Size:** 250 m × 250 m (62,500 m²).
* **Grid Construction:** The grid is generated based on the fixed origin. The authoritative PMC boundary is only used as a clipping extent to determine inclusion/membership.
* **Geometry Integrity:** A block's operational geometry remains the *full 250m × 250m square cell*. Blocks are **never clipped to the PMC boundary** or to ward boundaries for factor calculations. The full grid cell is preserved to ensure compatibility with downstream U-Net patch logic and factor aggregation.

## 4. Persistent Block ID Algorithm

Block IDs must be persistent, deterministic, and ward-agnostic.
* **Format:** `PN_<grid_x>_<grid_y>`
* **Algorithm:**
  - `grid_x = floor((easting - ORIGIN_E) / 250)`
  - `grid_y = floor((northing - ORIGIN_N) / 250)`
* The ID is absolutely tied to the fixed 250 m lattice and remains stable regardless of row-ordering or changes in ward boundaries. `Rxx_Cxx` relative naming is explicitly prohibited for production.

## 5. Ward Assignment Method

Blocks are assigned to wards for metadata and reporting purposes only.
* **Algorithm:** Maximum Area Overlap.
  - Each full 250m block is intersected with candidate ward polygons in EPSG:32643.
  - The ward yielding the maximum intersection area is primarily assigned to the block.
* **Ambiguity Handling & Tolerance:** Real polygon intersections involve floating-point geometries, so absolute equality is an insufficient test for ties.
  - A numerical tolerance `AMBIGUITY_AREA_FRACTION = 0.01` (1% of the block area, or 625 m²) is used.
  - If `(max_overlap_area - second_overlap_area) / block_area <= 0.01`, the block's assignment is flagged as `ambiguous_overlap` and no single ward is assigned.
* **Edge Cases:** Blocks falling partially or wholly outside wards or the PMC boundary will be flagged with statuses such as `no_overlap`, `outside_boundary`, etc.
* **Distinction from Factor Geometry:** Ward assignment is strictly an attribute (`ward_id`). The block's actual polygon is never clipped to the assigned ward.

## 6. Boundary Validation and Derived Boundaries

* **Validation Rules:** Ingested boundaries are subjected to strict validation checks: geometry validity, CRS presence and transformability, and topological relationships (gaps, overlaps, and extensions relative to the outer boundary). Missing identifiers or empty geometries trigger validation warnings or failures.
* **Gap and Extension Thresholds:** The validation report isolates significant discrepancies from minor digitization slivers.
  - Raw discrepancy areas (`raw_gap_area_m2`, `raw_extension_area_m2`) are always calculated and reported.
  - Discrepancies smaller than `SIGNIFICANT_DISCREPANCY_M2` (set to 100.0 m²) are filtered out to yield `significant_gap_area_m2` and `significant_extension_area_m2`. This threshold is highly conservative (far smaller than a single 62,500 m² block) but safely suppresses false topological alarms generated by sub-meter digitization artifacts.
* **Derived Boundaries:** A dissolved outer PMC boundary can be derived from a validated administrative ward layer. When derived, the boundary is explicitly marked as `source_type = "derived"` with provenance tied to the source wards. The original ward geometries remain immutable and are never overwritten. 

## 7. Unresolved Status

* **Unresolved Authoritative Source:** As of this implementation, an authoritative, current PMC boundary and administrative ward geometry dataset still needs to be supplied and verified. The system is designed to reject fallback datasets until an official source is correctly configured.
* **Testing Suite Collection:** Full test-suite execution has been partially obstructed by a missing `scipy` dependency in the environment affecting the unrelated `carbon_sink` module. The core geographic tests run independently, but complete repository verification relies on the availability of this dependency.

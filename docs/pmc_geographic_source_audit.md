# PMC Geographic Source Audit

## 1. Executive Finding
We **do not** currently possess a verified, authoritative geometry for the post-2021 Pune Municipal Corporation (PMC) administrative wards or its outer boundary. While a 15-ward administrative structure exists and governs the current city, the available 2017 geometry covers only ~251 km², representing the old urban core before the 2017 and 2021 village mergers expanded the city to ~518 km². The OpenCity 2017 dataset cannot safely be used as a production fallback for the entire current city.

## 2. OpenCity 15-Ward Dataset Details
* **Dataset Name:** Pune Administrative Wards Map 2017
* **Format:** KML (available locally as `admin_wards.geojson`)
* **Source Organization:** OpenCity (data.opencity.in)
* **Stated Year:** 2017
* **Features:** 15 administrative wards
* **CRS:** EPSG:4326 (projected to EPSG:32643 for analysis)

## 3. Geometry Audit
Analysis of the `admin_wards.geojson` dataset (EPSG:32643 metric operations):
* **Feature Count:** 15
* **Valid Geometries:** 15
* **Invalid Geometries:** 0
* **Empty Geometries:** 0
* **Total Union Area:** 251.02 km²

This area confirms the dataset represents the older Pune municipal boundary prior to the 11-village (2017) and 23-village (2021) mergers.

## 4. Existing UEHIS Boundary Comparison
Comparison of the 15-ward union (251.02 km²) against available repository boundaries:

* **`pune_city_boundary.geojson`**
  * **Area:** 312.11 km²
  * **Intersection with 15 Wards:** 246.06 km² (98% of the 15-ward area is inside this boundary).
  * **Boundary Area Outside 15 Wards:** 66.06 km²
  * **Note:** This likely represents the post-2017 merger extent (11 villages).

* **`elec_wards_22.geojson`** (DataMeet Electoral Wards)
  * **Area:** 506.91 km²
  * **Intersection with 15 Wards:** 249.79 km² (99.5% of the 15-ward area is inside this boundary).
  * **Boundary Area Outside 15 Wards:** 257.11 km²
  * **Note:** This represents the post-2021 merger extent (23 villages). The 15 wards only cover about half of this total city area.

## 5. PMC GIS / Source Investigation
* **Post-2021 Structure:** PMC maintained its 15-ward administrative office structure after the 2021 mergers. However, the geographic boundaries of these 15 offices were radically expanded to encompass the newly merged villages, increasing their jurisdictional footprint to ~518 km².
* **GIS Availability:** While official names for the 15 wards remain (e.g., Aundh-Baner, Kothrud-Bawdhan), the updated polygon shapefiles/GeoJSONs reflecting the post-2021 borders are not publicly hosted as direct downloads on PMC Open Data portals. They reside within PMC's internal Town Planning and IT GIS systems.

## 6. 2025 ISPRS Source Verification
The 2025 ISPRS paper ("Spatial Distribution and Coverage of Urban Green Spaces: Public Parks in Pune") analyzed parks across 15 administrative wards and validated against the PMC GIS portal. 
* **Details:** The paper does not provide a downloadable geometry or explicitly state whether it used the pre-2021 (~251 km²) or post-2021 (~518 km²) boundary extent. 
* **Limitation:** A scientific paper citing PMC GIS as a validation source does not make the underlying GIS data public or inherently transfer authority to older open-source datasets (like OpenCity 2017).

## 7. Administrative vs. Electoral Distinction
* **Administrative Wards (15 Units):** These are civic ward offices responsible for municipal service delivery, road maintenance, and tax collection. These are the units required by the UEHIS pipeline.
* **Electoral Wards / Prabhags (58 Units / 41 Units):** These are purely political voting districts (e.g., the 2022 DataMeet 58-unit dataset). They do not correspond to civic service delivery zones and must not be used for UEHIS scoring.

## 8. Boundary-Area Reconciliation
To clarify historical area discrepancies commonly cited for Pune:
* **~251 km²:** The pre-2017 PMC boundary, corresponding exactly to the OpenCity 15-ward dataset (`admin_wards.geojson`).
* **~312 km²:** The post-2017 PMC boundary after merging 11 villages (`pune_city_boundary.geojson`).
* **~506.91 km²:** The union area of the 2022 DataMeet electoral wards (`elec_wards_22.geojson`).
* **~516 - 518 km²:** The widely reported official area of PMC following the June 2021 merger of 23 villages. 

## 9. Candidate-Source Provenance Assessment
| Source | Authority | Recency | Admin/Electoral | Suitability for UEHIS |
| :--- | :--- | :--- | :--- | :--- |
| **OpenCity 15 Wards (2017)** | Third-Party | Outdated (Pre-2017/2021 Mergers) | Administrative | **NOT SUITABLE** (Misses >250 km² of the current city) |
| **DataMeet 58 Wards (2022)** | Third-Party | Recent (Post-2021) | Electoral / Prabhag | **NOT SUITABLE** (Wrong unit type) |
| **PMC Official GIS System** | Official | Current (Post-2021) | Administrative | **AUTHORITATIVE / VERIFIED** (Data not yet acquired) |
| **`pune_city_boundary.geojson`** | Unverified | Outdated (~312 km²) | Boundary Only | **NOT SUITABLE** |

## 10. Remaining Uncertainty
We know the PMC uses 15 administrative ward offices to govern the 518 km² city. What we lack are the exact digitized polygon coordinates (`EPSG:32643`) for those 15 updated boundaries. 

## 11. Next Technical Action
**Recommendation:** Do not configure any existing local file as the authoritative ward layer. Retain the strict validation guards implemented in the geographic foundation. The next step must be to formally request or acquire the updated post-2021 15-ward administrative GIS shapefile directly from the Pune Municipal Corporation IT/Town Planning department.

---

### Final Answers to User Questions

1. **Do we have a VERIFIED current PMC administrative ward geometry?** No.
2. **Do we have a VERIFIED current PMC municipal boundary geometry?** No.
3. **Can the OpenCity 2017 15-ward geometry safely be used as a production fallback?** No. It covers only ~251 km² and completely omits the ~260 km² of peripheral villages merged into the city between 2017 and 2021.
4. **If not, what exact evidence/source is still missing?** We are missing the updated post-2021 polygon dataset for the 15 administrative ward offices, which must total ~518 km² in area.
5. **What should the next UEHIS implementation step be?** Pause geographic block generation. The geographic foundation is ready and strictly guards against invalid data. The next step is to acquire the current official data directly from PMC.

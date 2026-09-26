# UEHIS Phase 4 Stage 1.2.2: Kothrud Modern Carbon Validation

## A. ETH Dataset Semantics

1. **Exact dataset ID:** `users/nlang/ETH_GlobalCanopyHeight_2020_10m_v1`
2. **Exact image band(s) used:** `b1`
3. **Band units:** Metres
4. **Meaning of the pixel value:** Top-of-canopy tree height in metres.
5. **Nominal spatial resolution:** 10m (approx 9.27m at equator).
6. **Nodata / masked-pixel behavior:** Areas without canopy (bare ground, water, urban surfaces) are effectively masked (`None`/Nodata) in the dataset, rather than being 0.
7. **Value range actually observed over Kothrud:** Positively distributed up to 15.32m mean block canopy height.
8. **Whether zero values represent non-canopy/non-tree areas:** Yes, non-tree areas are masked out/nodata.
9. **Implementation masking/handling:** GEE's `ee.Reducer.mean()` explicitly ignores masked pixels. Thus, the returned mean represents the mean canopy height of the trees within the block, **not** a diluted area-weighted mean over the entire block geometry.
10. **Authoritative citation:** Lang, N., et al. (2023). "A high-resolution canopy height model of the Earth". Nature Ecology & Evolution. Available via Google Earth Engine Community Catalog.

## B. Block-Level Height Aggregation

The pipeline operates as follows:
1. Block polygons (EPSG:32643) are passed to GEE with `proj="EPSG:32643"` and `evenOdd=False` constraints.
2. Earth Engine calculates the spatial intersection with the ETH GlobalCanopyHeight 10m raster.
3. `ee.Reducer.mean()` calculates the arithmetic mean of all valid (unmasked) canopy pixels within the block bounds.

**10 Representative Blocks (Top 10 by Carbon Stock):**

| Block ID | Block Area (m²) | Canopy Area (m²) | Canopy Frac | Mean Height (m) |
|---|---|---|---|---|
| PN_289_194 | 62,500.0 | 50,813.49 | 0.81 | 8.63 |
| PN_295_182 | 62,500.0 | 22,531.40 | 0.36 | 15.32 |
| PN_299_193 | 62,500.0 | 32,901.50 | 0.52 | 6.60 |
| PN_294_189 | 62,500.0 | 29,036.28 | 0.46 | 7.72 |
| PN_289_193 | 62,500.0 | 34,692.70 | 0.55 | 4.88 |
| PN_301_190 | 62,500.0 | 21,305.84 | 0.34 | 11.82 |
| PN_288_194 | 62,500.0 | 21,211.57 | 0.33 | 7.09 |
| PN_289_192 | 62,500.0 | 25,736.70 | 0.41 | 2.81 |
| PN_299_191 | 62,500.0 | 15,366.60 | 0.24 | 8.35 |
| PN_293_193 | 62,500.0 | 16,403.61 | 0.26 | 5.70 |

*Aggregation Statistic:* The system strictly uses the **mean** height of the unmasked canopy pixels within the block (`ee.Reducer.mean()`). This is correct and scientifically appropriate because it is paired with the U-Net spatial canopy area.

## C. Independent Carbon Recomputation

I independently re-implemented the carbon derivation logic from `biomass.py` to compare against the production output `outputs/unet_raster_production.csv`.

**Parameters:**
- `_HEIGHT_TO_CROWN_RATIO = 0.6`
- `_MIN_CROWN_AREA_M2 = 1.0`
- `crown_to_dbh_ratio = 20.0`
- Model: `urban_generic` (A = 0.1066, B = 2.4572)

**Results:**
- **Trees:** Independent = 181,031 | Production = 181,032 (Diff: 0.05, pass)
- **AGB:** Independent = 5,145,785 kg | Production = 5,145,785 kg (Diff: 0.01, pass)
- **CO2e:** Independent = 8,867.9026 t | Production = 8,867.9025 t (Diff: <0.0001, pass)

**Outcome:** PASS. The production pipeline is deterministically verified.

## D. Sanity Checks
- `canopy_area_m2 <= block_area_m2`: **PASS** (True for all)
- `canopy_fraction` in [0,1]: **PASS**
- `height >= 0`: **PASS**
- No negative trees/AGB: **PASS**
- No duplicate block IDs: **PASS**
- No fallback height source: **PASS**

## E. Important Comparison (Legacy vs Modern)

- **Legacy Baseline:** 75,980.0573 t CO2e
- **Modern Baseline:** 8,867.9025 t CO2e

**Decomposition of the difference:**
1. **Canopy Source & Area (Primary driver):** The legacy baseline used polygon digitization of Landsat, yielding ~379 hectares of canopy area. The modern U-Net segmentation found ~53.8 hectares. This is a dramatic ~7x reduction in recognized canopy spatial extent due to high-resolution AI strictness versus coarse Landsat polygons.
2. **Height Source (Secondary driver):** The legacy pipeline used an uncalibrated heuristic derived from area fraction, resulting in arbitrarily inflated height metrics. The modern ETH 2020 dataset supplies real empiric height, capping the block mean heights significantly lower in many dense but low-shrub blocks. 
3. **Block Count:** Legacy (256 blocks), Modern (283 blocks).

## F. Fallback / Production Safety

- `ALLOW_UNCALIBRATED_HEIGHT_FALLBACK` is OFF.
- `UEHIS_TEST_NO_GEE` is OFF.
- Every processed block in production reads `ETH_GlobalCanopyHeight_2020` in the `canopy_height_source` column.
- The failure mode test was explicitly run (`UEHIS_TEST_NO_GEE=1` and `ALLOW_UNCALIBRATED_HEIGHT_FALLBACK=false`). It successfully blocked generation with `RuntimeError: GEE canopy height data is unavailable...`

## H. Decision Gate

**PASS** — Kothrud modern Carbon is independently validated and ready to become the Pune-wide production method.

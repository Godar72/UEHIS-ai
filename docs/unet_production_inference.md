# U-Net Production Inference Architecture

This document details the production inference methodology implemented to ensure scientific accuracy and reproducibility in UEHIS, as approved by the scientific audit.

## Architecture & Raster-First Design

The inference pipeline is designed to be fully raster-based for Pune-wide production. Generating millions of polygons for spatial joins was deemed inefficient and prone to artifacts. 

The pipeline structure is:
`Sentinel/slope input -> U-Net raster inference -> probability/class raster -> OSM rasterization -> impervious raster union -> raster zonal statistics -> UEHIS block factors`

Polygonization remains available in legacy scripts (`run_osm_overlay.py`) as an optional debugging utility but is not part of the core production flow.

## 1. Inference Preprocessing

Inference preprocessing strictly matches the training preprocessing phase to prevent domain shift:
- **Raw Sentinel Reflectance Channels (B, G, R)**: Scaled using per-tile min-max to `[0, 1]`.
- **NDVI**: Fixed-range normalized via `(ndvi + 1.0) / 2.0`, clipped to `[0, 1]`.
- **Slope**: Fixed-range normalized via `slope / 90.0`, clipped to `[0, 1]`.

## 2. 3-Model Ensemble

To improve robustness, production inference utilizes an ensemble of 3 distinct U-Net models trained independently.
- Inference is run for each model on every tile.
- Softmax probability maps are extracted for each class.
- Probabilities are element-wise averaged across all 3 models *before* applying the final `argmax`.
- Hard-voting is explicitly avoided to preserve probability-space granularity.

## 3. 8-Way Test-Time Augmentation (TTA)

Each model runs inference on 8 augmented views of each tile:
- Identity
- Horizontal flip
- Vertical flip
- 90°, 180°, and 270° rotations
- Transpose (flip + rotation)
- Anti-transpose

The output probabilities are inverse-aligned to their original spatial orientation and averaged across all 8 views *before* the model ensemble average.

## 4. Overlapping Tile Stitching

- **Tile Size**: 256×256 pixels
- **Stride**: 128 pixels (yielding exactly 50% overlap in both X and Y dimensions).
- **Receptive Field Rationale**: The U-Net has a theoretical receptive field of ~200×200 pixels. We pad the source raster symmetrically by 96 pixels (the `RECOMMENDED_BORDER_MARGIN`). 
- **Stitching**: Overlapping regions are accumulated via a 2D Bartlett window function (triangle weight). This ensures edge predictions (which lack spatial context) are down-weighted in favor of center pixels from adjacent tiles.
- **Valid Pixels**: The 96-pixel padding is strictly excluded from probability averaging using a nodata mask. 

## 5. Nodata and Valid-Pixel Tracking

Explicit valid-data masks ensure that invalid pixels (from original raster nodata or padding) do not contribute to final outputs. 
- Invalid pixels retain a class ID of `255` (nodata).
- The pipeline tracks the `valid_pixel_count` and the `data_completeness_fraction` to enable later scoring mechanisms to threshold partially invalid blocks.

## 6. Impervious Raster Union

For impervious surfaces, the pipeline uses a raster-based pixel-wise union:
1. Extract the U-Net impervious class (`class_id = 1`) as a binary mask.
2. Rasterize OSM buildings onto the *same* 10m grid.
3. Rasterize OSM roads onto the *same* 10m grid.
4. Calculate the logical OR pixel-wise: `final_impervious = max(unet, osm_buildings, osm_roads)`.

This ensures that impervious fractions are strictly physically bounded (`<= 1.0`) and pixels contribute at most once.

## 7. Reproducibility Manifest

Every inference run automatically generates a machine-readable JSON manifest containing:
- Source raster path and SHA-256 hash
- Model weight paths and SHA-256 hashes
- Preprocessing and architectural parameters
- Nodata policies, exact CRS, and resolution
- Timestamp and execution environment details

## 8. Final Phase 3 Legacy-Baseline Engineering Regression

A full regression analysis was executed over the Kothrud ROI to compare the Phase 3 raster-first scoring pipeline against the legacy Phase 1/V4 vector baseline. The comparison over 256 matched 250m blocks revealed:
- **Score Stability**: The Pearson correlation was negative (`-0.2318`).
- **Divergence**: The median absolute score difference was ~11.12, with a max divergence of 92.61. 
- **Max-Difference Block**: R13_C01 (Note: this is a LEGACY regression identifier, not an authoritative final Pune block ID).

The raster-first pipeline produces substantial divergence from the legacy V4 baseline. Changes in tree-density, population-exposure, and impervious-surface distributions are associated with score differences. Because the V4 baseline contains a previously identified geometry error and the current offline regression does not contain real PM2.5 values, this comparison is treated as an engineering regression rather than scientific validation of the final UEHI scores.

## Limitations & Notes

- **Accuracy Metrics**: U-Net accuracy metrics are *not* being re-estimated by this implementation task. The 69.9% impervious fraction is accepted as the new scientific baseline pending ground-truth validation.
- **Frozen Weights**: The trained weights are treated as frozen. Retraining remains conditional on downstream validation.
- **PM2.5 Missing Data**: The production pipeline enforcing strict Jan-Feb-Mar 2024 seasonal averages via Google Earth Engine will yield `NaN` for any 250m block lacking valid readings in all three months. The pipeline relies on `UEHIS_TEST_NO_GEE=1` fallback mode to bypass GEE during offline tests, which injects empty placeholders.

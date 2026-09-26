# U-Net Production Inference Fix Plan

This document outlines the implementation plan for the U-Net production inference corrections mandated by the scientific audit.

## Files to be Changed
- `run_inference.py`: Will be heavily modified to implement correct preprocessing, 3-model ensemble, 8-way TTA, overlapping tile inference, nodata tracking, and machine-readable manifest generation.
- `feature_engineering/predict.py`: Will be modified or deprecated depending on how `run_inference.py` integrates with it. Currently, `predict.py` also contains sliding window inference and the `_normalise_tile` function that applies the incorrect per-patch min-max to all bands.
- `tests/test_inference.py` (NEW): Will be created to add focused tests for the new inference behaviors (preprocessing, TTA, inverse TTA, probability averaging, etc.).
- `docs/unet_production_inference.md` (NEW): Will be created to document the new production inference architecture and methodology.

## Files that will NOT be Changed
- `scoring/entropy.py`: Explicitly protected.
- `run_scoring.py`: The UEHI scoring formula and Kothrud V4 final score methodology will be preserved.
- `feature_engineering/unet.py`: The trained model architecture is frozen.
- `feature_engineering/train.py`: Training preprocessing and labels will not be modified.
- `outputs/kothrud_scores_v4_final.csv`: Will not be overwritten.
- All Kothrud V4 scoring baseline files.
- The geographic foundation and authoritative boundary logic.
- Training weights (e.g. `unet_weights_slope_run1.pth`, etc.).

## Current Behavior
1. **Preprocessing**: Inference uses a blanket per-patch min-max normalization (`_normalise_tile`) for all bands, which conflicts with the training logic (fixed-range for NDVI and slope).
2. **Inference**: Uses a single model (randomly initialized in `run_inference.py`), with no Test-Time Augmentation (TTA), and hard labels are argmaxed directly without averaging.
3. **Tiling**: Sliding window with `stride = 256` and `patch_size = 256` resulting in zero overlap.
4. **Nodata Tracking**: Lacks end-to-end explicit boolean valid-data masks and data-completeness tracking.
5. **Impervious Combination**: Polygon-based ad-hoc spatial joins are used (e.g., `run_osm_overlay.py` with GeoDataFrames).

## Intended New Behavior
1. **Phase 2 - Preprocessing Fix**: Inference preprocessing will precisely match training preprocessing. Raw bands use per-tile min-max, NDVI uses `(ndvi + 1) / 2`, and slope uses `slope / 90` (both clipped to `[0,1]`).
2. **Phase 3 & 4 - Ensemble & TTA**: Load 3 trained models. Apply 8-way TTA per model. Inverse-transform probability maps back to original orientation, average 8 TTA views per model, average 3 models together, and only then apply `argmax`.
3. **Phase 5 - Overlapping Tile Inference**: Keep tile size 256×256 but use stride 128 (50% overlap). Probabilities will be accumulated and normalized (`accumulated_probability / accumulated_weight`). A 96-pixel context margin (theoretical receptive field) will be factored into the stitching/padding logic without creating gaps.
4. **Phase 6 - Nodata Tracking**: Explicit boolean valid-data masks will exclude padded/invalid pixels from probability averaging. Output nodata will be 255. `valid_pixel_count` and `data_completeness_fraction` will be calculated per block.
5. **Phase 7 & 8 - Impervious Raster Union**: Move to a raster-first architecture. OSM buildings and roads will be rasterized to the SAME 10m grid. `final_impervious = unet_impervious OR osm_impervious` using pixel-wise max, ensuring impervious fractions remain <= 1.
6. **Phase 9 - Reproducibility**: Generate a machine-readable JSON manifest per inference run documenting all config, hashes, and provenance.
7. **Phase 11 - Kothrud Regression**: Perform a controlled regression test writing to an isolated output directory (e.g., `outputs/unet_inference_v2/`).

## Risks & Open Questions
- **Memory Consumption**: Accumulating probabilities for 3 models * 8 TTAs * large image sizes requires careful memory management, especially for large composite arrays.
- **LFS Weights**: The plan mandates that if the `.pth` files are Git LFS pointers instead of local weights, they should not be replaced. The implementation must gracefully handle missing files by allowing paths to be configurable.
- **Rasterizing OSM Data**: Moving from vector intersections to rasterization needs to accurately preserve the 10m alignment with the Sentinel-2 grid.

## Test Plan
Add focused tests in `tests/test_inference.py` utilizing small synthetic arrays (instead of full model inference) to verify:
- Fixed-range vs min-max preprocessing per channel.
- Channel order preservation.
- Correctness of 8-way TTA spatial transformations and inverse alignments.
- 3-model probability averaging behavior.
- Overlapping tile stitching (accumulation logic and boundary handling).
- Nodata exclusion and probability averaging logic avoiding invalid pixels.
- Impervious pixel-wise union correctness.
- Data completeness calculations.
Run the full repository test suite to ensure zero regressions in protected components.

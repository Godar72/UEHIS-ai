# Real Weight & Slope Validation Report

## Model weights
* **Availability**: REAL_TRAINED_WEIGHTS_AVAILABLE = YES
* **Paths**: 
  * `unet_weights_slope_run1.pth`
  * `unet_weights_slope_run2.pth`
  * `unet_weights_slope_run3.pth`
* **Sizes**: 124,246,803 bytes each (~124 MB). This confirms they are NOT Git LFS pointers but fully hydrated binaries.
* **SHA-256**: 
  * run1: `f6a1c4f266...` (Git object hash)
  * run2: `47709658f8...` (Git object hash)
  * run3: `74275566a4...` (Git object hash)
* **Load Status**: All three weights load successfully natively in PyTorch.
* **Input Channels**: 5 (B, G, R, NDVI, Slope).
* **Output Classes**: 4 (Canopy, Impervious, Pervious, Water).

## Slope
* **Availability**: REAL_SLOPE_AVAILABLE = NO
* **Source**: The project methodology specifies SRTM elevation via Earth Engine (`feature_engineering/train.py` references this), but no script exists within `data_ingestion/` to actually generate and export this SRTM slope raster for the inference composite. 
* **CRS**: N/A (Missing)
* **Resolution**: N/A (Missing)
* **Units**: N/A (Missing)
* **Min/Max/Mean**: N/A (Missing)
* **Nodata**: N/A (Missing)
* **Alignment with Sentinel raster**: N/A (Missing)

## Five-channel input
* **Ready Status**: FIVE_CHANNEL_INPUT_READY = NO
* **Exact Channel Order**: B, G, R, NDVI, Slope (Pending real slope data).
* **Dimensions / CRS / Resolution**: Awaiting generation of real slope.
* **Alignment Status**: Awaiting generation of real slope.

## Inference
* **Status**: SCIENTIFIC_KOTHRUD_VALIDATION_RUN = NO
* **Reason**: Due to the missing SRTM slope data for Kothrud, building a scientifically valid 5-channel input is impossible. We are strictly forbidden from substituting an arbitrary alternative DEM or falling back to a dummy zero-slope array for scientific validation. 
* **Safeguards**: The inference pipeline (`run_inference.py`) has been updated to completely remove the random-weight fallback. It will now fatally crash (`FileNotFoundError` / `ValueError`) if weights are missing, are LFS pointers, or fail to load.

## Scientific Status
**BLOCKED — REAL SLOPE UNAVAILABLE**

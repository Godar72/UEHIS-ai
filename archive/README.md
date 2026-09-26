# UEHIS Repository Archive

This directory stores historical experiments, superseded model training artifacts, and past scoring run outputs preserved for scientific provenance, audit trails, and reproducibility.

**Archival Date**: 2026-09-24  
**Auditor**: Antigravity Pair-Programmer / UEHIS Engineering

---

## 1. Historical Outputs (`archive/historical_outputs/`)

| Archived File Path | Original Path | Original Purpose | Reason for Archival | Superseded By / Current Authoritative File |
| :--- | :--- | :--- | :--- | :--- |
| `archive/historical_outputs/kothrud_scores_v2.csv` | `outputs/kothrud_scores_v2.csv` | Initial V2 UEHI scoring iteration output across 256 Kothrud blocks. | Superseded by V3 geometry corrections, V4 factor updates, and Phase 3 raster-first scoring pipeline. Kept for historical audit and score progression analysis. | `outputs/kothrud_scores_phase3.csv` / `outputs/kothrud_scores_v4_final.csv` |
| `archive/historical_outputs/kothrud_scores_geometry_v3.csv` | `outputs/kothrud_scores_geometry_v3.csv` | Geometry V3 scoring run output with interim block boundaries. | Superseded by V4 final scoring and Phase 3 raster-first zonal statistics pipeline. Kept for historical audit. | `outputs/kothrud_scores_phase3.csv` / `outputs/kothrud_scores_v4_final.csv` |
| `archive/historical_outputs/v4_run1.csv` | `outputs/v4_run1.csv` | Intermediate raw factor export from initial V4 testing run. | Superseded by authoritative factor outputs (`outputs/kothrud_factors_v4.csv` and `outputs/kothrud_factors_v4_final.csv`). Kept for historical audit. | `outputs/kothrud_factors_v4.csv` / `outputs/kothrud_factors_v4_final.csv` |
| `archive/historical_outputs/v4_score_run1.csv` | `outputs/v4_score_run1.csv` | Initial scoring run output for V4 factor matrix. | Identical in content to `outputs/kothrud_scores_v4_final.csv`. Preserved in archive as the historical run 1 artifact without cluttering active `outputs/`. | `outputs/kothrud_scores_v4_final.csv` / `outputs/kothrud_scores_phase3.csv` |

---

## 2. Old Experiments (`archive/old_experiments/`)

| Archived File Path | Original Path | Original Purpose | Reason for Archival | Superseded By / Current Authoritative File |
| :--- | :--- | :--- | :--- | :--- |
| `archive/old_experiments/UEHIS_training/patches_4class.zip` | `UEHIS_training/patches_4class.zip` | 4-channel training patch dataset (without SRTM slope band). | Superseded by 5-channel terrain-slope-augmented training dataset (`patches_4class_spatial_with_slope.zip`). Preserved for model lineage and provenance. | `patches_4class_spatial_with_slope.zip` |
| `archive/old_experiments/UEHIS_training/patches_4class_dense.zip` | `UEHIS_training/patches_4class_dense.zip` | Dense 4-channel training patch dataset. | Superseded by spatial-split 5-channel dataset (`patches_4class_spatial_with_slope.zip`). Preserved for model lineage. | `patches_4class_spatial_with_slope.zip` |
| `archive/old_experiments/UEHIS_training/patches_4class_spatial.zip` | `UEHIS_training/patches_4class_spatial.zip` | Spatially split 4-channel training patch dataset. | Superseded by 5-channel dataset with slope (`patches_4class_spatial_with_slope.zip`). Preserved for model lineage. | `patches_4class_spatial_with_slope.zip` |
| `archive/old_experiments/UEHIS_training/train.py` | `UEHIS_training/train.py` | Older 4-channel U-Net training script without slope channel, LR scheduler, or early stopping. | Superseded by production training script `feature_engineering/train.py` (which supports 5 channels, SRTM slope, LR scheduling, moving average validation loss, and early stopping). | `feature_engineering/train.py` |
| `archive/old_experiments/UEHIS_training/unet.py` | `UEHIS_training/unet.py` | Standalone U-Net architecture definition. | Superseded by active package module `feature_engineering/unet.py`. | `feature_engineering/unet.py` |

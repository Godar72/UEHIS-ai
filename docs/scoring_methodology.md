# UEHIS Scoring Methodology — Authoritative Reference

> [!IMPORTANT]
> This document is the **authoritative** scoring formula reference for UEHIS.
> It supersedes any conflicting formula in prior PDF documentation
> (including `UEHI_Formula.pdf` and `UEHIS_Complete_Technical_Documentation.pdf`).

## Score Semantics

- **UEHI_i ∈ [0, 100]**
- **100** = maximum ecological health (cool, green, permeable)
- **0** = severe heat-island conditions (hot, impervious, barren)

## Active Factors (6-factor model)

| Factor | Direction | Interpretation |
|--------|-----------|----------------|
| NDVI | positive | Higher vegetation index → better ecological health |
| Tree density | positive | Higher canopy fraction → better ecological health |
| PM2.5 | negative | Higher concentration → worse ecological health |
| Temperature (LST) | negative | Higher surface temperature → worse ecological health |
| Impervious surfaces | negative | Higher impervious fraction → worse ecological health |
| Population exposure | negative | Higher population density → worse ecological health |

**Excluded**: `water_availability` — no reliable block-scale open-water signal detected for Kothrud ROI.

## Normalization

All factors are normalized to [0, 1] using min-max scaling:

- **Positive-direction** factors: `N_pos(x) = (x − x_min) / (x_max − x_min)` → 1 = best
- **Negative-direction** factors: `N_neg(x) = (x_max − x) / (x_max − x_min)` → 1 = best

Identity: `N_neg(x) = 1 − N_pos(x)`

## Complete Scoring Formula

```
UEHI_i = clip[0,100]( (B_i + S_i) × m_i )
```

### Base Score

```
B_i = ( Σⱼ wⱼ × Nⱼ(factorⱼ_i) ) × 100
```

Where `wⱼ` are entropy-derived weights (sum to 1.0) and `Nⱼ` uses the
direction-appropriate normalization for each factor. `B_i ∈ [0, 100]`.

### Canopy–Temperature Synergy

```
S_i = α × N_pos(NDVI_i) × N_neg(Temperature_i) × 100
```

Rewards blocks with high vegetation AND low temperature. `α = 0.1`.
Maximum synergy = 10 points. `S_i ∈ [0, 10]`.

### Population Impact Multiplier

```
m_i = 1 − β × N_pos(Pop_i)
```

Where:
- `N_pos(Pop) = (Pop − Pop_min) / (Pop_max − Pop_min)` — standard min-max,
  mapping the **highest**-population block to 1.0 and the **lowest** to 0.0
- `β = 0.3`
- `m_i ∈ [0.7, 1.0]`

**Effect**: Higher population → lower multiplier → lower UEHI score.
The most densely populated block receives a 30% penalty; the least populated
block receives no penalty.

> [!WARNING]
> **Prior documentation erratum**: The formula was previously documented as
> `m(i) = 1 + β × N(Pop)` in early PDF documentation. This is **incorrect**
> regardless of the normalization direction used.
> The authoritative formula is `m(i) = 1 − β × N_pos(Pop_i)`.

### Population Dual-Role

Population exposure participates in the scoring formula **twice**:

1. **Base score**: As one of the 6 entropy-weighted factors with direction = "negative".
   High population → low `N_neg(Pop)` contribution → lower base score.

2. **Multiplier**: As the penalty multiplier `m_i`.
   High population → `m_i` closer to 0.7 → proportional reduction of the entire score.

This dual-role is a deliberate design choice: population density both degrades
ecological conditions directly (channel 1) and amplifies public-health urgency
(channel 2, the multiplier).

## Hyperparameters

| Parameter | Value | Role |
|-----------|-------|------|
| α | 0.1 | Canopy–temperature synergy coefficient |
| β | 0.3 | Population penalty multiplier coefficient |
| Block size | 250m | Spatial unit for scoring |

## Bounds Summary

| Quantity | Min | Max |
|----------|-----|-----|
| Base score B_i | 0 | 100 |
| Synergy S_i | 0 | 10 |
| Pre-multiplier (B + S) | 0 | 110 |
| Multiplier m_i | 0.7 | 1.0 |
| Post-multiplier (B + S) × m | 0 | 110 |
| Final UEHI (after clip) | **0** | **100** |

## Risk Classification

| Score Range | Risk Level |
|-------------|------------|
| [0, 25) | Critical |
| [25, 50) | High |
| [50, 75) | Moderate |
| [75, 100] | Low |

## Factor Data Sources and Metadata

### Landsat 8 (Temperature / LST)
- **Source**: Landsat 8 Collection 2 Level 2 (ST_B10 band)
- **Acquisition Date / Window**: 2024-01-01 to 2024-03-31 (or fallback to 2023-01-01 to 2024-12-31 if required for cloud-free composite).
- **QA/Cloud Masking**: `QA_PIXEL` bitmask used to filter out clouds (bit 3) and cloud shadows (bit 4). Scene-level cloud filter requires < 20% cloud cover.
- **Resolution**: 30m native (downscaled to 250m blocks using mean aggregation)

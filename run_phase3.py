import sys, math, os
from pathlib import Path
import json

# Force UTF-8 output on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import numpy as np
import pandas as pd
import datetime
import hashlib

from scoring.normalize import normalise_factor
from scoring.entropy import (
    entropy_weights,
    compute_factor_diagnostics,
    print_diagnostics_table,
    EntropyWeightError,
)

# Load Production Configuration
CONFIG_PATH = Path(__file__).parent / "configs" / "production_2026.json"
with open(CONFIG_PATH) as f:
    PROD_CONFIG = json.load(f)["production_artifacts"]

ALPHA = 0.1
BETA  = 0.3

FACTORS = {
    "ndvi":                 ("positive", "REAL"),
    "tree_density":         ("positive", "REAL"),
    "pm25":                 ("negative", "REAL"),
    "temperature":          ("negative", "REAL"),
    "impervious_surfaces":  ("negative", "REAL"),
    "population_exposure":  ("negative", "REAL"),
}

def validate_pm25_for_scoring(df: pd.DataFrame, is_offline_dev: bool):
    """
    Validates PM2.5 data for production scoring.
    Raises RuntimeError in production if PM2.5 is missing/NaN.
    """
    if "pm25" not in df.columns:
        if not is_offline_dev:
            raise RuntimeError("Production scoring failed: PM2.5 data is missing or incomplete. Real PM2.5 is required for production scoring.")
        else:
            print("[Warning] Offline test mode: PM2.5 is missing entirely. Proceeding with scoring for TEST ONLY.")
            return

    if df['pm25'].isnull().all() or df['pm25'].isnull().any():
        if not is_offline_dev:
            raise RuntimeError("Production scoring failed: PM2.5 data is missing or incomplete. Real PM2.5 is required for production scoring.")
        else:
            print("[Warning] Offline test mode: PM2.5 is missing/NaN. Proceeding with scoring for TEST ONLY.")

def sha256_file(path: str | Path) -> str:
    """Helper to consistently hash files on disk."""
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()

def merge_eligibility(df: pd.DataFrame, eligibility_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Merges eligibility map and asserts 1-to-1 match. Returns scoring and excluded dataframes."""
    merged = df.merge(eligibility_df[['block_id', 'score_status']], on='block_id', how='left', validate="one_to_one")
    if merged['score_status'].isna().any():
        raise RuntimeError("Eligibility merge failed: factor block lacks eligibility.")
        
    df_scoring = merged[merged['score_status'] == 'scorable'].copy()
    df_excluded = merged[merged['score_status'] == 'insufficient_source_coverage'].copy()
    return df_scoring, df_excluded

def validate_factor_data(df_scoring: pd.DataFrame, factor_cols: list[str], is_offline_dev: bool):
    """Enforces all scorable blocks have full factor data."""
    if not is_offline_dev:
        missing_mask = df_scoring[factor_cols].isna().any(axis=1)
        inf_mask = df_scoring[factor_cols].isin([np.inf, -np.inf]).any(axis=1)
        if missing_mask.any() or inf_mask.any():
            invalid_count = (missing_mask | inf_mask).sum()
            raise RuntimeError(f"Missing factor data for scorable blocks. Do not impute. Found {invalid_count} invalid blocks.")

def calculate_weights(df_scoring: pd.DataFrame, factor_cols: list[str], is_offline_dev: bool) -> dict:
    """Calculates entropy weights, overriding PM2.5 to 0.02 and scaling others."""
    validate_pm25_for_scoring(df_scoring, is_offline_dev)

    factor_cols_no_pm25 = [c for c in factor_cols if c != "pm25"]
    try:
        ew = entropy_weights(df_scoring, factor_cols_no_pm25)
    except EntropyWeightError as e:
        print(f"FATAL: Entropy weight error: {e}")
        sys.exit(1)

    for c in ew:
        ew[c] *= 0.98
    ew["pm25"] = 0.02
    return ew

def score_blocks(df_scoring: pd.DataFrame, factor_cols: list[str], ew: dict, factors_config: dict) -> pd.DataFrame:
    """Applies UEHI scoring formula."""
    weighted_sum = pd.Series(0.0, index=df_scoring.index)
    for col in factor_cols:
        direction = factors_config[col][0]
        normed = normalise_factor(df_scoring[col], direction)
        weighted_sum += (ew[col] * normed)

    base_score = (weighted_sum * 100).clip(0, 100)

    ndvi_norm = normalise_factor(df_scoring["ndvi"], "positive")
    temp_norm = normalise_factor(df_scoring["temperature"], "negative")
    synergy = ALPHA * ndvi_norm * temp_norm * 100
    
    pop_norm = normalise_factor(df_scoring["population_exposure"], "positive")
    pop_multiplier = 1 - BETA * pop_norm
    
    df_scoring["uehi_score"] = ((base_score + synergy) * pop_multiplier).clip(0, 100).round(2)
    
    def classify(s):
        if pd.isna(s) or np.isnan(s): return np.nan
        if s < 25: return "Critical"
        if s < 50: return "High"
        if s < 75: return "Moderate"
        return "Low"

    df_scoring["risk_level"] = df_scoring["uehi_score"].apply(classify)
    return df_scoring

def assemble_output(df_scoring: pd.DataFrame, df_excluded: pd.DataFrame) -> pd.DataFrame:
    """Combines scored and excluded blocks, wiping excluded scores."""
    if len(df_excluded) > 0:
        df_excluded["uehi_score"] = np.nan
        df_excluded["risk_level"] = np.nan
    final_df = pd.concat([df_scoring, df_excluded]).sort_values("block_id").reset_index(drop=True)
    return final_df

def generate_manifest_dict(final_df, df_scoring, df_excluded, factor_cols, ew, factors_config, out_path, factors_csv, eligibility_csv, config_path, prod_config) -> dict:
    """Generates the phase3_manifest dictionary including proper SHA256 footprints."""
    out_sha = sha256_file(out_path)
    factor_sha = sha256_file(factors_csv)
    eligibility_sha = sha256_file(eligibility_csv)
    
    manifest = {
        "execution_timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "git_commit": "unknown",
        "config_path": str(config_path),
        "factors_csv": prod_config["factors"],
        "factor_sha256": factor_sha,
        "eligibility_csv": prod_config["eligibility"],
        "eligibility_sha256": eligibility_sha,
        "total_blocks": len(final_df),
        "scorable_blocks": len(df_scoring),
        "excluded_blocks": len(df_excluded),
        "factor_list": factor_cols,
        "entropy_method": "shannon",
        "pm25_cv": "fixed_rule",
        "pm25_fixed_weight": 0.02,
        "final_entropy_weights": ew,
        "normalization_directions": {k: v[0] for k, v in factors_config.items()},
        "synergy_alpha": ALPHA,
        "population_beta": BETA,
        "risk_thresholds": "<25 Critical, <50 High, <75 Moderate, >=75 Low",
        "output_path": str(out_path),
        "output_sha256": out_sha
    }
    return manifest

def main():
    print("=" * 70)
    print("  UEHI Scoring Pipeline Phase 3 -- Production")
    print("=" * 70)
    
    is_offline_dev = os.environ.get("UEHIS_TEST_NO_GEE") == "1"
    
    # 1. Artifact Resolution
    data_root = os.environ.get("UEHIS_DATA_ROOT")
    if not data_root:
        raise RuntimeError("UEHIS_DATA_ROOT environment variable must be set to run Phase 3 production.")
    
    data_dir = Path(data_root)
    factors_csv = data_dir / PROD_CONFIG["factors"]
    eligibility_csv = data_dir / PROD_CONFIG["eligibility"]
    OUTPUT_CSV = data_dir / "pune_uehi_scores_phase3_production_2026.csv"
    
    print(f"\n[Load] Loading authoritative factors from: {factors_csv}")
    df = pd.read_csv(factors_csv)
    print(f"  Total blocks loaded: {len(df)}")
    
    print(f"\n[Load] Loading eligibility map from: {eligibility_csv}")
    eligibility_df = pd.read_csv(eligibility_csv)
    
    # Merge and filter 
    df_scoring, df_excluded = merge_eligibility(df, eligibility_df)
    
    print(f"\n[Filter] Excluded {len(df_excluded)} blocks due to insufficient coverage/eligibility rules.")
    print(f"  Remaining eligible blocks for scoring: {len(df_scoring)}")
    print(f"  Total blocks preserved for output: {len(df_scoring) + len(df_excluded)}")
    
    scoring_status = "production"
    if is_offline_dev:
        scoring_status = "offline_test_only"
        
    factor_cols = list(FACTORS.keys())
    
    # Assert missing factor data for scorable blocks
    validate_factor_data(df_scoring, factor_cols, is_offline_dev)
        
    # 7. Entropy Scoring
    print(f"\n[Entropy] Computing entropy-based weights for {len(factor_cols)} active factors...")
    ew = calculate_weights(df_scoring, factor_cols, is_offline_dev)

    print("\n[Weights] Entropy-based weights:")
    for col in factor_cols:
        print(f"  {col:25s}: {ew[col]:.4f}")
        
    df_scoring = score_blocks(df_scoring, factor_cols, ew, FACTORS)
    
    # Recombine with excluded blocks
    final_df = assemble_output(df_scoring, df_excluded)
    
    csv_cols = ["block_id", "geometry_hash", "block_area_m2",
                "ndvi", "tree_density", "pm25", "temperature", "impervious_surfaces", "population_exposure",
                "score_status", "uehi_score", "risk_level"]
    
    # Retain all cols that exist in the loaded CSV (like geometry_hash, area) plus the new scores
    out_cols = [c for c in csv_cols if c in final_df.columns]
    
    if scoring_status == "offline_test_only":
        TEST_OUTPUT_CSV = OUTPUT_CSV.parent / f"TEST_ONLY_{OUTPUT_CSV.name}"
        out_path = TEST_OUTPUT_CSV
        final_df[out_cols].to_csv(str(TEST_OUTPUT_CSV), index=False)
        print(f"\n[Output] Phase 3 OFFLINE TEST scores saved to {TEST_OUTPUT_CSV.resolve()}")
    else:
        out_path = OUTPUT_CSV
        final_df[out_cols].to_csv(str(OUTPUT_CSV), index=False)
        print(f"\n[Output] Phase 3 scores saved to {OUTPUT_CSV.resolve()}")
        
    # Generate Phase 3 Manifest
    manifest = generate_manifest_dict(
        final_df, df_scoring, df_excluded, factor_cols, ew, FACTORS,
        out_path, factors_csv, eligibility_csv, CONFIG_PATH, PROD_CONFIG
    )
    
    manifest_out = OUTPUT_CSV.parent / "phase3_manifest.json"
    with open(manifest_out, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"\n{'='*70}")
    print(f"  LEGACY-BASELINE ENGINEERING REGRESSION: Phase 3 Raster vs V4 Vector Baseline")
    print(f"{'='*70}")
    print("  Note: The raster-first pipeline produces substantial divergence from the legacy V4 baseline.")
    print("  Changes in tree-density, population-exposure, and impervious-surface distributions")
    print("  are associated with score differences. Because the V4 baseline contains a previously")
    print("  identified geometry error and the current offline regression does not contain real PM2.5")
    print("  values, this comparison is treated as an engineering regression rather than scientific")
    print("  validation of the final UEHI scores.")
    
    old_path = Path("outputs/kothrud_scores.csv")
    if old_path.exists():
        from scipy import stats as scipy_stats
        old = pd.read_csv(old_path)
        new = df.copy()
        merged_cmp = old.merge(new, on="block_id", suffixes=("_old", "_new"))
        if len(merged_cmp) > 0:
            old_scores = merged_cmp["uehi_score_old"]
            new_scores = merged_cmp["uehi_score_new"]
            pearson_r, _ = scipy_stats.pearsonr(old_scores, new_scores)
            abs_diff = (old_scores - new_scores).abs()
            print(f"  Score stability ({len(merged_cmp)} matched blocks):")
            print(f"    Pearson correlation:           {pearson_r:.4f}")
            print(f"    Max absolute score difference: {abs_diff.max():.4f}")
            print(f"    Median absolute difference:    {abs_diff.median():.4f}")
        else:
            print("  No matching blocks for comparison (likely due to block_id format changes).")
    else:
        print("  V4 baseline not found.")
        
    print("Done.")

if __name__ == "__main__":
    main()

import pandas as pd
import numpy as np
from scipy import stats as scipy_stats
import json
import os
import subprocess
from scoring.entropy import entropy_weights

def get_git_commit():
    try:
        return subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode('utf-8').strip()
    except Exception:
        return "unknown"

def main():
    old = pd.read_csv('outputs/kothrud_scores.csv')
    if 'aqi' in old.columns:
        old = old.rename(columns={'aqi': 'pm25'})
        
    new = pd.read_csv('outputs/kothrud_scores_phase3.csv')

    merged = old.merge(new, on='block_id', suffixes=('_old', '_new'))
    
    # Fill PM2.5 NaNs with 0 for entropy recalculation if DEV mode
    if merged['pm25_new'].isnull().all():
        merged['pm25_new_calc'] = 0.0
    else:
        merged['pm25_new_calc'] = merged['pm25_new']
        
    factors = ['ndvi', 'tree_density', 'pm25', 'temperature', 'impervious_surfaces', 'population_exposure']
    
    # 3. Old vs New Regression Data
    merged['score_difference'] = merged['uehi_score_old'] - merged['uehi_score_new']
    merged['absolute_difference'] = merged['score_difference'].abs()

    # Recompute entropy weights
    # New
    new_calc_df = merged[['pm25_new_calc' if f == 'pm25' else f + '_new' for f in factors]].copy()
    new_calc_df.columns = factors
    new_weights_recalc = entropy_weights(new_calc_df, factors)
    
    # Old (from V4 baseline)
    old_calc_df = merged[[f + '_old' for f in factors]].copy()
    old_calc_df.columns = factors
    # In V4, PM25 was probably NaN too, so fill with 0
    if old_calc_df['pm25'].isnull().all():
        old_calc_df['pm25'] = 0.0
    old_weights_recalc = entropy_weights(old_calc_df, factors)

    # Prepare CSV export
    csv_cols = ['block_id', 'uehi_score_old', 'uehi_score_new', 'score_difference', 'absolute_difference']
    for f in factors:
        csv_cols.append(f + '_old')
    for f in factors:
        csv_cols.append(f + '_new')
    
    merged[csv_cols].to_csv('outputs/audit_regression_256.csv', index=False)
    
    # 4. Top Outliers
    top10 = merged.nlargest(10, 'absolute_difference').copy()
    top10[csv_cols + ['block_row_new', 'block_col_new', 'block_area_m2_new']].to_csv('outputs/audit_top10_outliers.csv', index=False)
    
    # 5. Independent Recomputation
    p_r, _ = scipy_stats.pearsonr(merged['uehi_score_old'], merged['uehi_score_new'])
    med_diff = merged['absolute_difference'].median()
    max_diff = merged['absolute_difference'].max()
    max_diff_block = merged.loc[merged['absolute_difference'].idxmax(), 'block_id']
    
    recomp_data = {
        "pearson_r": p_r,
        "median_abs_diff": med_diff,
        "max_abs_diff": max_diff,
        "max_diff_block": max_diff_block,
        "new_weights_recalculated": new_weights_recalc,
        "old_weights_recalculated": old_weights_recalc
    }
    
    # 6. Factor Distribution Audit
    dist_data = {}
    for f in factors:
        dist_data[f] = {
            "old": {
                "min": float(merged[f + '_old'].min(skipna=True)),
                "max": float(merged[f + '_old'].max(skipna=True)),
                "mean": float(merged[f + '_old'].mean(skipna=True)),
                "median": float(merged[f + '_old'].median(skipna=True)),
                "std": float(merged[f + '_old'].std(skipna=True)),
                "uniques": int(merged[f + '_old'].nunique(dropna=True)),
                "cv": float(merged[f + '_old'].std(skipna=True) / merged[f + '_old'].mean(skipna=True)) if merged[f + '_old'].mean(skipna=True) != 0 and not np.isnan(merged[f + '_old'].mean(skipna=True)) else 0.0
            },
            "new": {
                "min": float(merged[f + '_new'].min(skipna=True)),
                "max": float(merged[f + '_new'].max(skipna=True)),
                "mean": float(merged[f + '_new'].mean(skipna=True)),
                "median": float(merged[f + '_new'].median(skipna=True)),
                "std": float(merged[f + '_new'].std(skipna=True)),
                "uniques": int(merged[f + '_new'].nunique(dropna=True)),
                "cv": float(merged[f + '_new'].std(skipna=True) / merged[f + '_new'].mean(skipna=True)) if merged[f + '_new'].mean(skipna=True) != 0 and not np.isnan(merged[f + '_new'].mean(skipna=True)) else 0.0
            }
        }
        
    # 7. Causality check bits
    # Correlate diff in impervious with diff in score
    merged['impervious_diff'] = merged['impervious_surfaces_new'] - merged['impervious_surfaces_old']
    p_r_imp_score, _ = scipy_stats.pearsonr(merged['impervious_diff'], merged['score_difference'])
    
    causality = {
        "impervious_diff_vs_score_diff_pearson": p_r_imp_score,
        "impervious_weight_change": new_weights_recalc['impervious_surfaces'] - old_weights_recalc['impervious_surfaces'],
        "tree_density_weight_change": new_weights_recalc['tree_density'] - old_weights_recalc['tree_density']
    }

    output = {
        "recomputation": recomp_data,
        "distributions": dist_data,
        "causality": causality,
        "git_commit": get_git_commit()
    }
    
    with open('outputs/audit_stats.json', 'w') as f:
        json.dump(output, f, indent=2)
        
if __name__ == "__main__":
    main()

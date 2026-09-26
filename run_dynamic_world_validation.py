import os
import json
import numpy as np
import pandas as pd
import rasterio
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from pathlib import Path
import ee
from dotenv import load_dotenv
import requests

load_dotenv()
ee.Initialize(project=os.getenv('GEE_PROJECT_ID'))

OUT_DIR = Path("outputs/unet_validation")
OUT_DIR.mkdir(parents=True, exist_ok=True)
UNET_TIF = OUT_DIR / "production_segmentation.tif"
DW_LABEL_TIF = OUT_DIR / "dw_label_kothrud.tif"
DW_PROB_TIF = OUT_DIR / "dw_built_prob_kothrud.tif"

DW_CLASSES = {
    0: "water",
    1: "trees",
    2: "grass",
    3: "flooded_vegetation",
    4: "crops",
    5: "shrub_and_scrub",
    6: "built",
    7: "bare",
    8: "snow_and_ice"
}
UNET_CLASSES = {0: "canopy", 1: "impervious", 2: "pervious", 3: "water"}

def get_ee_download_url(image, crs, transform_list, dimensions):
    try:
        url = image.getDownloadURL({
            'format': 'GEO_TIFF',
            'crs': crs,
            'crs_transform': transform_list,
            'dimensions': dimensions
        })
        return url
    except Exception as e:
        print(f"Error getting URL: {e}")
        raise

def fetch_dw_data():
    with rasterio.open(UNET_TIF) as src:
        prof = src.profile
        bounds = src.bounds
        width, height = src.width, src.height
        crs_str = src.crs.to_string()
        transform = src.transform
        
    transform_list = [transform.a, transform.b, transform.c, transform.d, transform.e, transform.f]
    dimensions = f"{width}x{height}"
    
    # Define ROI
    roi = ee.Geometry.Rectangle([bounds.left, bounds.bottom, bounds.right, bounds.top], proj=crs_str)
    
    # Query Dynamic World
    dw_col = (ee.ImageCollection("GOOGLE/DYNAMICWORLD/V1")
              .filterBounds(roi)
              .filterDate('2026-01-01', '2026-03-31'))
              
    # Aggregate temporally
    # For label, we take the mode (most common class)
    dw_label = dw_col.select('label').mode()
    
    # For built probability, take the median
    dw_built_prob = dw_col.select('built').median().resample('bilinear')
    
    print("Downloading DW Label...")
    url_label = get_ee_download_url(dw_label, crs_str, transform_list, dimensions)
    with open(DW_LABEL_TIF, 'wb') as f:
        f.write(requests.get(url_label).content)
        
    print("Downloading DW Built Prob...")
    url_prob = get_ee_download_url(dw_built_prob, crs_str, transform_list, dimensions)
    with open(DW_PROB_TIF, 'wb') as f:
        f.write(requests.get(url_prob).content)
        
    return prof

def analyze_data(prof):
    with rasterio.open(UNET_TIF) as src:
        unet_data = src.read(1)
        
    with rasterio.open(DW_LABEL_TIF) as src:
        dw_label_data = src.read(1)
        
    with rasterio.open(DW_PROB_TIF) as src:
        dw_built_prob = src.read(1)
        
    valid = unet_data != 255
    unet_valid = unet_data[valid]
    dw_valid = dw_label_data[valid]
    prob_valid = dw_built_prob[valid]
    
    total_valid = valid.sum()
    
    # Fractions
    unet_counts = {c: int((unet_valid == c).sum()) for c in UNET_CLASSES.keys()}
    dw_counts = {c: int((dw_valid == c).sum()) for c in DW_CLASSES.keys()}
    
    # Crosswalk
    crosswalk = []
    for uc, uname in UNET_CLASSES.items():
        for dc, dname in DW_CLASSES.items():
            count = int(((unet_valid == uc) & (dw_valid == dc)).sum())
            if count > 0:
                crosswalk.append({
                    "unet_class": uname,
                    "dw_class": dname,
                    "count": count,
                    "percent_of_roi": (count / total_valid) * 100,
                    "percent_of_unet_class": (count / max(1, unet_counts[uc])) * 100
                })
    df_cw = pd.DataFrame(crosswalk)
    df_cw.to_csv(OUT_DIR / "unet_dw_crosswalk.csv", index=False)
    
    # Probability check
    imp_prob = float(np.median(prob_valid[unet_valid == 1])) if unet_counts[1] > 0 else 0.0
    perv_prob = float(np.median(prob_valid[unet_valid == 2])) if unet_counts[2] > 0 else 0.0
    
    # Visuals
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    
    cmap_unet = ListedColormap(['#228B22', '#808080', '#D2B48C', '#0000FF'])
    axes[0].imshow(unet_data, cmap=cmap_unet, vmin=0, vmax=3)
    axes[0].set_title("U-Net Segmentation")
    axes[0].axis('off')
    
    # DW Built vs Bare map
    dw_viz = np.zeros_like(dw_label_data)
    dw_viz[dw_label_data == 6] = 1 # Built (Red)
    dw_viz[dw_label_data == 7] = 2 # Bare (Yellow)
    dw_viz[(dw_label_data != 6) & (dw_label_data != 7)] = 0 # Other (Grey)
    
    cmap_dw = ListedColormap(['#E0E0E0', '#FF0000', '#FFFF00'])
    axes[1].imshow(dw_viz, cmap=cmap_dw, vmin=0, vmax=2)
    axes[1].set_title("DW Built (Red) / Bare (Yellow)")
    axes[1].axis('off')
    
    axes[2].imshow(dw_built_prob, cmap='Reds', vmin=0, vmax=1)
    axes[2].set_title("DW Built Probability")
    axes[2].axis('off')
    
    plt.tight_layout()
    plt.savefig(OUT_DIR / "dynamic_world_comparison.png", dpi=300)
    plt.close()
    
    # Summary JSON
    summary = {
        "metadata": {
            "dataset": "GOOGLE/DYNAMICWORLD/V1",
            "date_range": "2026-01-01 to 2026-03-31",
            "aggregation": "mode (label), median (probabilities)",
            "total_valid_pixels": int(total_valid)
        },
        "unet_fractions": {k: float(v/total_valid) for k, v in unet_counts.items()},
        "dw_fractions": {DW_CLASSES[k]: float(v/total_valid) for k, v in dw_counts.items()},
        "dw_built_plus_bare": float((dw_counts.get(6,0) + dw_counts.get(7,0))/total_valid),
        "median_dw_built_prob": {
            "in_unet_impervious": imp_prob,
            "in_unet_pervious": perv_prob
        }
    }
    
    with open(OUT_DIR / "dynamic_world_summary.json", "w") as f:
        json.dump(summary, f, indent=2)
        
    # Write Report
    report = f"""# Dynamic World Validation Report

## 1. Context
- **Dataset**: GOOGLE/DYNAMICWORLD/V1
- **Date Range**: 2026-01-01 to 2026-03-31
- **Aggregation**: Mode (categorical label), Median (probabilities)
- **Total Valid Pixels**: {total_valid}

## 2. Global Fractions

**U-Net Fractions**:
- Canopy: {summary['unet_fractions'][0]*100:.1f}%
- Impervious: {summary['unet_fractions'][1]*100:.1f}%
- Pervious: {summary['unet_fractions'][2]*100:.1f}%
- Water: {summary['unet_fractions'][3]*100:.1f}%

**Dynamic World Fractions**:
- Built: {summary['dw_fractions']['built']*100:.1f}%
- Bare: {summary['dw_fractions']['bare']*100:.1f}%
- Built + Bare: {summary['dw_built_plus_bare']*100:.1f}%
- Trees: {summary['dw_fractions']['trees']*100:.1f}%
- Grass: {summary['dw_fractions']['grass']*100:.1f}%
- Crops: {summary['dw_fractions']['crops']*100:.1f}%
- Shrub/Scrub: {summary['dw_fractions']['shrub_and_scrub']*100:.1f}%

## 3. High-Confidence Check (Probability Distributions)
- **Median DW Built Prob (in U-Net Impervious)**: {imp_prob:.3f}
- **Median DW Built Prob (in U-Net Pervious)**: {perv_prob:.3f}

## 4. Key Cross-tabulation Findings
"""
    
    df_cw['unet_class'] = pd.Categorical(df_cw['unet_class'], categories=['canopy', 'impervious', 'pervious', 'water'], ordered=True)
    df_cw_sorted = df_cw.sort_values(['unet_class', 'percent_of_unet_class'], ascending=[True, False])
    
    for _, row in df_cw_sorted.iterrows():
        if row['percent_of_unet_class'] > 5.0:  # Only report >5% contributions
            report += f"- **U-Net {row['unet_class']}** is predominantly DW **{row['dw_class']}** ({row['percent_of_unet_class']:.1f}% of U-Net class, {row['percent_of_roi']:.1f}% of total ROI)\n"

    # Decision Logic
    # If U-Net Impervious (69.9%) is supported by DW Built or Built+Bare
    dw_support = summary['dw_fractions']['built'] + summary['dw_fractions']['bare']
    if abs(summary['unet_fractions'][1] - dw_support) < 0.15 and imp_prob > 0.4:
        decision = "A. Strong independent support for U-Net impervious distribution"
    elif abs(summary['unet_fractions'][1] - dw_support) < 0.3:
        decision = "B. Partial/ambiguous support"
    else:
        decision = "C. Independent evidence contradicts U-Net impervious distribution"
        
    report += f"\n## 5. Final Decision\n**{decision}**\n\n"
    report += "## 6. Limitations\n"
    report += "- Dynamic World has its own classification errors, particularly mixing bare soil, dry vegetation, and built structures.\n"
    report += "- Temporal mismatch (Jan-Mar 2026 vs DW continuous) may capture seasonal vegetation differences.\n"
    report += "- Semantic mismatch: 'Pervious' in U-Net covers grass/crops/bare, while 'Impervious' should ideally match DW 'Built', but DW 'Bare' often includes hard-packed soil or construction sites that might physically behave as impervious.\n"

    with open(OUT_DIR / "dynamic_world_validation_report.md", "w") as f:
        f.write(report)
        
    print("Done. Report saved.")

if __name__ == "__main__":
    prof = fetch_dw_data()
    analyze_data(prof)

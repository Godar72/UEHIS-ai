import pandas as pd
import numpy as np
import json
import math
import sys
import os
import hashlib

def get_hash(filepath):
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

data_root = "C:\\Users\\adity\\Desktop\\SL\\UEHIS_Production_2026"
carbon_csv = os.path.join(data_root, "pune_carbon_production_2026.csv")
scores_csv = os.path.join(data_root, "pune_uehi_scores_phase3_production_2026.csv")
grid_geojson = os.path.join(data_root, "pune_pn_grid_250m_2026.geojson")
unet_tif = os.path.join(data_root, "pune_unet_segmentation_FROZEN_2026.tif")
manifest_path = os.path.join(data_root, "pune_carbon_production_2026.json")

df = pd.read_csv(carbon_csv)
print("=== QA CHECKS ===")

# Structure
n_rows = len(df)
n_unique = df["block_id"].nunique()
print(f"Total rows: {n_rows}")
print(f"Unique block IDs: {n_unique}")
if n_rows != 5309 or n_unique != 5309:
    print("FAILED: Structure check")
    sys.exit(1)

# Canopy
missing_canopy = df["canopy_area_m2"].isna().sum()
neg_canopy = (df["canopy_area_m2"] < 0).sum()
print(f"Missing canopy areas: {missing_canopy}")
print(f"Negative canopy areas: {neg_canopy}")
if missing_canopy > 0 or neg_canopy > 0:
    print("FAILED: Canopy missing/negative")
    sys.exit(1)

# we need boundary_intersection_area_m2, it should be in the carbon csv or we load from scores/grid
if "boundary_intersection_area_m2" not in df.columns or "block_area_m2" not in df.columns:
    import geopandas as gpd
    grid_df = gpd.read_file(grid_geojson)
    cols_to_merge = ["block_id"]
    if "boundary_intersection_area_m2" not in df.columns: cols_to_merge.append("boundary_intersection_area_m2")
    if "block_area_m2" not in df.columns: cols_to_merge.append("block_area_m2")
    df = df.merge(grid_df[cols_to_merge], on="block_id", how="left")

eps = 1e-4
area_violations = (df["canopy_area_m2"] > df["boundary_intersection_area_m2"] + eps).sum()
print(f"Canopy area > boundary intersection area violations: {area_violations}")
if area_violations > 0:
    print("FAILED: Canopy area exceeds boundary area")
    sys.exit(1)

if "canopy_fraction" in df.columns:
    max_cf = df["canopy_fraction"].max()
else:
    max_cf = (df["canopy_area_m2"] / df["block_area_m2"]).max()
zero_canopy = (df["canopy_area_m2"] == 0).sum()
total_canopy_area = df["canopy_area_m2"].sum()
total_canopy_pixels = df["canopy_pixel_count"].sum() if "canopy_pixel_count" in df.columns else 0

print(f"Maximum canopy fraction: {max_cf}")
print(f"Blocks with zero canopy: {zero_canopy}")
print(f"Total canopy area: {total_canopy_area}")
print(f"Total canopy pixels: {total_canopy_pixels}")

# Height
missing_height = df["canopy_height_m"].isna().sum()
print(f"Missing heights: {missing_height}")
source_counts = df["canopy_height_source"].value_counts().to_dict()
print(f"Canopy height source distribution: {source_counts}")

if missing_height > 0:
    print("FAILED: Missing height")
    sys.exit(1)
for k in source_counts.keys():
    if "FALLBACK" in k.upper():
        print("FAILED: Fallback used")
        sys.exit(1)
    if k != "ETH_GlobalCanopyHeight_2020":
        print(f"FAILED: Unknown height source {k}")
        sys.exit(1)

# Carbon
print(f"Total estimated trees: {df['n_trees_est'].sum()}")
print(f"Total AGB kg: {df['agb_kg'].sum()}")
print(f"Total standing carbon stock (t CO2e): {df['carbon_stock_tonnes_co2e'].sum()}")
print(f"Min carbon stock: {df['carbon_stock_tonnes_co2e'].min()}")
print(f"Max carbon stock: {df['carbon_stock_tonnes_co2e'].max()}")
print(f"Mean carbon stock: {df['carbon_stock_tonnes_co2e'].mean()}")
print(f"Median carbon stock: {df['carbon_stock_tonnes_co2e'].median()}")
print(f"Non-zero-carbon blocks: {(df['carbon_stock_tonnes_co2e'] > 0).sum()}")

neg_carbon = (df["carbon_stock_tonnes_co2e"] < 0).sum()
if neg_carbon > 0:
    print("FAILED: Negative carbon")
    sys.exit(1)

# Independent calculation
calc_carbon = []
for _, row in df.iterrows():
    c_area = row["canopy_area_m2"]
    h = row["canopy_height_m"]
    if h <= 0.01:
        calc_carbon.append(0.0)
        continue
    crown_d = 0.6 * h
    crown_area = math.pi * (crown_d / 2.0) ** 2
    crown_area_safe = max(crown_area, 1.0)
    n_trees = c_area / crown_area_safe
    dbh_cm = crown_d * 100 / 20.0
    agb_per_tree = 0.1066 * (dbh_cm ** 2.4572)
    tot_agb = agb_per_tree * n_trees
    co2 = tot_agb * 0.47 * (44.0/12.0) / 1000.0
    calc_carbon.append(co2)

df["indep_carbon"] = calc_carbon
df["abs_diff"] = (df["carbon_stock_tonnes_co2e"] - df["indep_carbon"]).abs()
# Relative diff handling zeros
df["rel_diff"] = df.apply(lambda r: r["abs_diff"] / r["carbon_stock_tonnes_co2e"] if r["carbon_stock_tonnes_co2e"] > 0 else (0 if r["indep_carbon"] == 0 else 1), axis=1)

print(f"Max absolute diff: {df['abs_diff'].max()}")
print(f"Max relative diff: {df['rel_diff'].max()}")

if df['abs_diff'].max() > 0.1:
    print("FAILED: Independent verification of carbon failed")
    sys.exit(1)

# Provenance
with open(manifest_path, 'r') as f:
    manifest = json.load(f)
print("=== MANIFEST ===")
print(json.dumps(manifest, indent=2))
print("=== HASHES ===")
print(f"Scores CSV hash: {get_hash(scores_csv)}")
print(f"UNET TIF hash: {get_hash(unet_tif)}")
print(f"PN Grid hash: {get_hash(grid_geojson)}")
print(f"Output Carbon CSV hash: {get_hash(carbon_csv)}")
print("PHASE 4 CARBON PRODUCTION: PASS")

import os
import sys
import json
from pathlib import Path

def validate_production_artifacts():
    print("="*60)
    print("  UEHIS Production Artifact Validation")
    print("="*60)

def validate_production_artifacts(data_dir=None, config_path=None, **kwargs):
    if data_dir is None:
        data_root = os.environ.get("UEHIS_DATA_ROOT")
        if not data_root:
            print("[FAIL] UEHIS_DATA_ROOT environment variable is not set.")
            sys.exit(1)
        data_dir = Path(data_root)
        
    if not data_dir.exists() or not data_dir.is_dir():
        print(f"[FAIL] UEHIS_DATA_ROOT directory does not exist: {data_dir}")
        sys.exit(1)
        
    if config_path is None:
        config_path = Path(__file__).parent.parent / "configs" / "production_2026.json"
        
    if not config_path.exists():
        print(f"[FAIL] Configuration not found: {config_path}")
        sys.exit(1)
        
    with open(config_path) as f:
        config = json.load(f)
        
    artifacts = config.get("production_artifacts", {})
    all_exist = True
    
    block_ids = {}
    print(f"Checking artifacts in {data_dir}...\n")
    for key, filename in artifacts.items():
        filepath = data_dir / filename
        if filepath.exists():
            print(f"[OK] {key}: {filename} (Size: {filepath.stat().st_size} bytes)")
            
            if filepath.suffix == '.csv':
                try:
                    import pandas as pd
                    df = pd.read_csv(filepath)
                    if key == "factors" and len(df) != 5309:
                        print(f"  -> [WARNING] Expected 5309 rows in factors, got {len(df)}")
                    elif key == "eligibility" and len(df) != 5309:
                        print(f"  -> [WARNING] Expected 5309 rows in eligibility, got {len(df)}")
                        
                    if "block_id" in df.columns:
                        if not df["block_id"].is_unique:
                            print(f"  -> [FAIL] block_id is not unique in {filename}")
                            all_exist = False
                        else:
                            block_ids[key] = set(df["block_id"])
                except Exception as e:
                    print(f"  -> [FAIL] Could not parse CSV {filename}: {e}")
                    all_exist = False
            elif filepath.suffix == '.geojson':
                try:
                    with open(filepath, 'r', encoding='utf-8') as gf:
                        gj = json.load(gf)
                        ids = set(f["properties"]["block_id"] for f in gj.get("features", []) if "block_id" in f.get("properties", {}))
                        if ids:
                            block_ids[key] = ids
                except Exception as e:
                    print(f"  -> [FAIL] Could not parse GeoJSON {filename}: {e}")
                    all_exist = False
        else:
            print(f"[FAIL] {key}: {filename} is MISSING.")
            all_exist = False
            
    if all_exist and "pn_grid" in block_ids and "factors" in block_ids and "eligibility" in block_ids:
        if block_ids["pn_grid"] == block_ids["factors"] == block_ids["eligibility"]:
            print("  -> [OK] Block IDs match exactly across grid, factors, and eligibility.")
        else:
            print("  -> [FAIL] Block IDs DO NOT MATCH across grid, factors, and eligibility.")
            all_exist = False
            
    print("\n" + "="*60)
    if all_exist:
        print("  All production artifacts are present and structurally valid.")
        print("="*60)
    else:
        print("  Validation FAILED. Missing or invalid production artifacts.")
        print("  Cannot proceed with production workflow.")
        print("="*60)
        if kwargs.get('raise_on_error', False):
            raise RuntimeError("Validation FAILED")
        sys.exit(1)

if __name__ == "__main__":
    validate_production_artifacts()

import os
import sys

def main():
    print("=" * 60)
    print("  UEHIS Colab Bootstrap")
    print("=" * 60)

    # Note: Only works inside Google Colab environment.
    try:
        from google.colab import drive
        drive.mount('/content/drive')
        print("[OK] Google Drive mounted.")
    except ImportError:
        print("[INFO] Not running in Google Colab. Skipping drive mount.")

    prod_dir = "/content/drive/MyDrive/UEHIS/UEHIS_Production_2026"
    
    if os.environ.get("UEHIS_DATA_ROOT"):
        print(f"[INFO] UEHIS_DATA_ROOT already set to {os.environ.get('UEHIS_DATA_ROOT')}")
    else:
        os.environ["UEHIS_DATA_ROOT"] = prod_dir
        print(f"[INFO] Set UEHIS_DATA_ROOT to {prod_dir}")

    # Validate artifacts
    try:
        import utils.validate_production
        utils.validate_production.validate_production_artifacts()
    except Exception as e:
        print(f"[FAIL] Validation failed: {e}")
        sys.exit(1)

    print("\n[OK] Environment is ready. To run production phase 3:")
    print("!python run_phase3.py")

if __name__ == "__main__":
    main()

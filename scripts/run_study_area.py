import sys
import os
import json
import logging
from sqlalchemy import text
from dotenv import load_dotenv

load_dotenv()
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from api.database import get_db, SessionLocal
from api.carbon_aggregation import aggregate_study_area_carbon

logging.basicConfig(level=logging.ERROR)

import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['all', 'uehi', 'carbon'], default='all')
    args = parser.parse_args()

    try:
        input_data = sys.stdin.read()
        geom_wgs84 = json.loads(input_data)
        
        # 1. UEHI
        geom_str = json.dumps(geom_wgs84)
        # Note: Added ST_Transform and ST_Multi to safely cast to the required type
        uehi_result = None
        if args.mode in ['all', 'uehi']:
            query = text("""
                SELECT * FROM aggregate_study_area(
                    ST_Multi(ST_Transform(ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326), 32643))
                )
            """)
            
            db = SessionLocal()
            try:
                result = db.execute(query, {"geom": geom_str}).fetchone()
                if result:
                    mapping = dict(result._mapping)
                    if "aggregate_study_area" in mapping:
                        uehi_result = mapping["aggregate_study_area"].get("uehi")
                    else:
                        uehi_result = mapping.get("uehi")
            except Exception as e:
                uehi_result = {"error": str(e)}
            finally:
                db.close()
            
        # 2. Carbon
        carbon_data = None
        provenance = {}
        if args.mode in ['all', 'carbon']:
            try:
                carbon_result = aggregate_study_area_carbon(geom_wgs84)
                carbon_data = carbon_result.get("carbon")
                provenance = carbon_result.get("provenance")
            except Exception as e:
                carbon_data = {"error": str(e)}
                provenance = {}

        # 3. Output
        out = {
            "uehi": uehi_result,
            "carbon": carbon_data,
            "provenance": provenance
        }
        
        print(json.dumps(out))
    except Exception as e:
        print(json.dumps({"error": "Failed to process study area", "details": str(e)}))

if __name__ == "__main__":
    main()

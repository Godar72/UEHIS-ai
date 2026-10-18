import sys
import os
import json
import logging
from sqlalchemy import text
from dotenv import load_dotenv

load_dotenv()
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from api.database import get_db, SessionLocal

logging.basicConfig(level=logging.ERROR)
import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--scenario-id', required=True)
    args = parser.parse_args()

    try:
        input_data = sys.stdin.read()
        geom_wgs84 = json.loads(input_data)
        geom_str = json.dumps(geom_wgs84)

        db = SessionLocal()
        
        # We need to calculate:
        # - planting units inside selected area
        # - mean UEHI of those units
        # - candidate category distribution
        # - risk distribution
        # And return the GeoJSON of points.
        
        # In UEHIS, UEHI and Risk come from the blocks or are stored in planting_units?
        # `planting_units` only has `geom`, `unit_id`.
        # How does the frontend get display_class, uehi_score?
        # In MapView.tsx, they query rendered features from 'planting-areas-layer' and 'uehi-layer' dynamically on click!
        # Because planting units themselves don't store uehi_score or risk_level! 
        # But wait! If we do server-side spatial filtering, how do we get mean UEHI?
        # We can join with `blocks` using ST_Intersects, and join with `planting_candidate_areas` for candidate category.

        query = text("""
            WITH poly AS (
                SELECT ST_Transform(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326)), 32643) AS geom
            ),
            filtered_units AS (
                SELECT 
                    pu.unit_id,
                    pu.geom,
                    pu.properties
                FROM planting_units pu
                JOIN planting_scenario_units psu ON pu.unit_id = psu.unit_id
                CROSS JOIN poly
                WHERE psu.scenario_id = CAST(:scenario_id AS uuid)
                  AND ST_Intersects(pu.geom, poly.geom)
            )
            SELECT 
                json_build_object(
                    'type', 'FeatureCollection',
                    'features', COALESCE(json_agg(
                        json_build_object(
                            'type', 'Feature',
                            'geometry', ST_AsGeoJSON(ST_Transform(fu.geom, 4326))::json,
                            'properties', json_build_object(
                                'planting_unit_id', fu.properties->>'planting_unit_id',
                                'uehi_score', (fu.properties->>'uehi_score')::numeric,
                                'risk_level', fu.properties->>'risk_level',
                                'ownership_status', fu.properties->>'ownership_status',
                                'utility_status', fu.properties->>'utility_status',
                                'permission_status', fu.properties->>'planting_permission_status',
                                'candidate_class', fu.properties->>'candidate_class',
                                'distance_to_water_m', (fu.properties->>'distance_to_water_m')::numeric,
                                'carbon_assumption_type', fu.properties->>'carbon_assumption_type'
                            )
                        )
                    ), '[]'::json)
                ) AS geojson,
                COUNT(*) AS total_units,
                AVG((fu.properties->>'uehi_score')::numeric) AS mean_uehi
            FROM filtered_units fu;
        """)
        
        result = db.execute(query, {"geom": geom_str, "scenario_id": args.scenario_id}).fetchone()
        
        if result:
            geojson = result[0]
            total_units = result[1]
            mean_uehi = result[2]
            
            # Risk distribution and category distribution can be computed from the geojson features
            # or in a separate query, but let's just do it in python from the geojson properties.
            features = geojson.get("features", [])
            risk_dist = {}
            class_dist = {}
            for f in features:
                props = f["properties"]
                risk = props.get("risk_level")
                if risk:
                    risk_dist[risk] = risk_dist.get(risk, 0) + 1
                raw_cls = props.get("candidate_class") or props.get("display_class")
                if raw_cls:
                    display_cls = {
                        "candidate_other_open_space": "Other open space",
                        "candidate_public_like": "Public-like open space",
                        "candidate_context_dependent": "Context-dependent",
                        "other_open_space": "Other open space",
                        "public_like": "Public-like open space",
                        "context_dependent": "Context-dependent"
                    }.get(raw_cls, raw_cls.replace("candidate_", "").replace("_", " ").title())
                    if display_cls == "Context Dependent":
                        display_cls = "Context-dependent"
                    class_dist[display_cls] = class_dist.get(display_cls, 0) + 1
                    
            out = {
                "geojson": geojson,
                "summary": {
                    "total_units": total_units,
                    "mean_uehi": float(mean_uehi) if mean_uehi else None,
                    "risk_distribution": risk_dist,
                    "class_distribution": class_dist
                }
            }
            print(json.dumps(out))
        else:
            print(json.dumps({"error": "No result"}))
            
    except Exception as e:
        print(json.dumps({"error": "Failed to filter planting units", "details": str(e)}))
    finally:
        if 'db' in locals():
            db.close()

if __name__ == "__main__":
    main()

import os
import json
from fastapi import APIRouter, Depends, Body, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from api.database import get_db
from api.security import verify_internal_api_key

planting_router = APIRouter(prefix="/planting", tags=["planting"])

@planting_router.post("/filter")
async def filter_planting_units(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_internal_api_key),
):
    """
    Spatially filters planting units within a study area geometry for a given scenario.
    Returns GeoJSON FeatureCollection and summary metrics.
    """
    geometry = payload.get("geometry")
    scenario_id = payload.get("scenario_id")

    if not geometry or not scenario_id:
        raise HTTPException(status_code=400, detail="Missing geometry or scenario_id")

    geom_str = json.dumps(geometry)

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

    try:
        result = db.execute(query, {"geom": geom_str, "scenario_id": str(scenario_id)}).fetchone()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")

    if not result:
        return {
            "geojson": {"type": "FeatureCollection", "features": []},
            "summary": {
                "total_units": 0,
                "mean_uehi": None,
                "risk_distribution": {},
                "class_distribution": {}
            }
        }

    geojson = result[0]
    total_units = result[1] or 0
    mean_uehi = result[2]

    features = geojson.get("features", [])
    risk_dist = {}
    class_dist = {}
    for f in features:
        props = f.get("properties", {})
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

    return {
        "geojson": geojson,
        "summary": {
            "total_units": total_units,
            "mean_uehi": float(mean_uehi) if mean_uehi is not None else None,
            "risk_distribution": risk_dist,
            "class_distribution": class_dist
        }
    }

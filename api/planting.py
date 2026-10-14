import os
import json
import uuid
from fastapi import APIRouter, Depends, Body, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from api.database import get_db
from api.security import verify_internal_api_key

planting_router = APIRouter(prefix="/planting", tags=["planting"])

SCENARIO_MAP = {
    "100k": "583a8cea-95ea-4909-bd9a-8dbdc3e2a4cd",
    "250k": "b2d9a3f2-1a4c-4e8d-9b5a-1c8e3f2a7b6d",
    "500k": "f4a2b1c3-3d5e-4f6a-8b7c-2d9e4f5a6b7c",
}


@planting_router.post("/filter")
async def filter_planting_units(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_internal_api_key),
):
    """
    Spatially filters planting units within a study area geometry for a given scenario.
    Returns GeoJSON FeatureCollection and summary metrics based on the normalized production schema.
    """
    geometry = payload.get("geometry")
    raw_scenario_id = payload.get("scenario_id")

    if not geometry or not raw_scenario_id:
        raise HTTPException(status_code=400, detail="Missing geometry or scenario_id")

    resolved_id = SCENARIO_MAP.get(str(raw_scenario_id).strip().lower(), str(raw_scenario_id).strip())
    try:
        scenario_uuid = str(uuid.UUID(resolved_id))
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid scenario_id UUID")

    geom_str = json.dumps(geometry)

    query = text("""
        WITH poly AS (
            SELECT ST_Transform(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326)), 32643) AS geom
        ),
        filtered_units AS (
            SELECT 
                pu.unit_id,
                pu.geom,
                b.uehi_score,
                b.risk_level::text AS risk_level,
                ca.candidate_category AS candidate_class,
                ca.ownership_status,
                ca.utility_status,
                ca.permission_status,
                ps.assumption_type AS carbon_assumption_type
            FROM planting_units pu
            JOIN planting_scenario_units psu ON pu.unit_id = psu.unit_id
            JOIN planting_scenarios ps ON psu.scenario_id = ps.scenario_id
            CROSS JOIN poly
            LEFT JOIN LATERAL (
                SELECT b_inner.uehi_score, b_inner.risk_level
                FROM uehi_blocks b_inner
                WHERE ST_Intersects(pu.geom, b_inner.geom)
                ORDER BY ST_Contains(b_inner.geom, pu.geom) DESC, b_inner.block_id ASC
                LIMIT 1
            ) b ON true
            LEFT JOIN LATERAL (
                SELECT ca_inner.candidate_category, ca_inner.ownership_status, ca_inner.utility_status, ca_inner.permission_status
                FROM planting_candidate_areas ca_inner
                WHERE ST_Intersects(pu.geom, ca_inner.geom)
                ORDER BY ST_Contains(ca_inner.geom, pu.geom) DESC, ca_inner.area_id ASC
                LIMIT 1
            ) ca ON true
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
                            'planting_unit_id', fu.unit_id::text,
                            'uehi_score', fu.uehi_score,
                            'risk_level', fu.risk_level,
                            'ownership_status', COALESCE(fu.ownership_status, 'unknown'),
                            'utility_status', COALESCE(fu.utility_status, 'unknown'),
                            'permission_status', COALESCE(fu.permission_status, 'unknown'),
                            'candidate_class', COALESCE(fu.candidate_class, 'unknown'),
                            'distance_to_water_m', null,
                            'carbon_assumption_type', fu.carbon_assumption_type
                        )
                    )
                ), '[]'::json)
            ) AS geojson,
            COUNT(*) AS total_units,
            AVG(fu.uehi_score) AS mean_uehi
        FROM filtered_units fu;
    """)

    try:
        result = db.execute(query, {"geom": geom_str, "scenario_id": scenario_uuid}).fetchone()
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


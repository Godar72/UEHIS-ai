import os
import json
from fastapi import APIRouter, Depends, Body, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from api.database import get_db
from api.carbon_aggregation import aggregate_study_area_carbon
from api.security import verify_internal_api_key

study_area_router = APIRouter(tags=["study-area"])

@study_area_router.post("/study-area/aggregate")
async def aggregate_study_area(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_internal_api_key),
):
    """
    Aggregate UEHI scores and Carbon estimates for a user-drawn study area polygon.
    Accepts either:
    1) { "geometry": { ...GeoJSON... }, "mode": "all"|"uehi"|"carbon" }
    2) Raw GeoJSON geometry dict { "type": "Polygon", "coordinates": [...] }
    """
    if "geometry" in payload and isinstance(payload["geometry"], dict):
        geom_wgs84 = payload["geometry"]
        mode = payload.get("mode", "all")
    else:
        geom_wgs84 = payload
        mode = "all"

    if not geom_wgs84 or "type" not in geom_wgs84 or "coordinates" not in geom_wgs84:
        raise HTTPException(status_code=400, detail="Malformed geometry")

    uehi_result = None
    if mode in ["all", "uehi"]:
        geom_str = json.dumps(geom_wgs84)
        query = text("""
            SELECT * FROM aggregate_study_area(
                ST_Multi(ST_Transform(ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326), 32643))
            )
        """)
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

    carbon_data = None
    provenance = {}
    if mode in ["all", "carbon"]:
        try:
            carbon_result = aggregate_study_area_carbon(geom_wgs84)
            carbon_data = carbon_result.get("carbon")
            provenance = carbon_result.get("provenance", {})
        except Exception as e:
            carbon_data = {"error": str(e)}
            provenance = {}

    return {
        "uehi": uehi_result,
        "carbon": carbon_data,
        "provenance": provenance,
    }

import os
import json
from fastapi import APIRouter, Depends, Body, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from api.database import get_db
from api.carbon_aggregation import aggregate_study_area_carbon
from api.security import verify_internal_api_key

study_area_router = APIRouter(tags=["study-area"])


def query_candidate_blocks_in_area(db: Session, geom_wgs84: dict, limit: int = 50) -> list[dict]:
    """
    Retrieves real candidate blocks intersecting a study area polygon from uehi_blocks and carbon_blocks.
    Ranks them by ecological need and provides ground-truth data-driven explanations and feasibility disclosures.
    """
    geom_str = json.dumps(geom_wgs84)
    query = text("""
        SELECT 
            b.block_id,
            b.uehi_score,
            b.risk_level::text AS risk_level,
            b.tree_density,
            b.ndvi,
            b.impervious_surfaces,
            b.temperature,
            b.population_exposure,
            b.pm25,
            b.is_excluded,
            c.standing_carbon_stock,
            c.canopy_area_m2,
            c.estimated_tree_count,
            c.above_ground_biomass_kg,
            ST_X(ST_Centroid(ST_Transform(b.geom, 4326))) AS centroid_lng,
            ST_Y(ST_Centroid(ST_Transform(b.geom, 4326))) AS centroid_lat,
            ST_Area(ST_Intersection(b.geom, ST_Transform(ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326), 32643))) AS intersection_area_m2
        FROM uehi_blocks b
        LEFT JOIN carbon_blocks c ON b.block_id = c.block_id
        WHERE ST_Intersects(b.geom, ST_Transform(ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326), 32643))
        ORDER BY 
            b.is_excluded ASC,
            b.uehi_score ASC NULLS LAST
        LIMIT :limit
    """)

    rows = db.execute(query, {"geom": geom_str, "limit": limit}).fetchall()

    candidates = []
    for idx, r in enumerate(rows):
        block_id = r[0]
        uehi_score = float(r[1]) if r[1] is not None else None
        risk_level = r[2] or ("Unscored" if r[9] else "Unknown")
        tree_density = float(r[3]) if r[3] is not None else None
        ndvi = float(r[4]) if r[4] is not None else None
        impervious = float(r[5]) if r[5] is not None else None
        temp = float(r[6]) if r[6] is not None else None
        pop_exp = float(r[7]) if r[7] is not None else None
        pm25 = float(r[8]) if r[8] is not None else None
        is_excluded = bool(r[9])
        carbon_stock = float(r[10]) if r[10] is not None else None
        canopy_area = float(r[11]) if r[11] is not None else None
        tree_count = float(r[12]) if r[12] is not None else None
        biomass = float(r[13]) if r[13] is not None else None
        centroid_lng = float(r[14]) if r[14] is not None else None
        centroid_lat = float(r[15]) if r[15] is not None else None
        intersection_area = float(r[16]) if r[16] is not None else None

        # Build honest, data-grounded ranking explanation based on real values
        if is_excluded or uehi_score is None:
            explanation = "Unscored block — excluded from baseline evaluation (e.g. water body, quarry, or data gap)."
            need_tier = "Unscored"
        elif uehi_score < 25.0:
            imp_text = f"{impervious * 100:.0f}%" if impervious is not None else "High"
            temp_text = f"{temp:.1f}°C" if temp is not None else "Elevated"
            explanation = (
                f"Critical Ecological Need: Score {uehi_score:.1f} reflects severe vegetative deficit "
                f"with {imp_text} impervious cover and {temp_text} surface temperature."
            )
            need_tier = "Critical"
        elif uehi_score < 50.0:
            td_text = f"{tree_density:.2f}" if tree_density is not None else "Low"
            explanation = (
                f"High Intervention Need: Score {uehi_score:.1f} indicates high thermal and vegetative vulnerability "
                f"(tree density: {td_text}, population heat exposure: {pop_exp or 0:.2f})."
            )
            need_tier = "High"
        elif uehi_score < 75.0:
            canopy_text = f"{canopy_area:.0f} m²" if canopy_area is not None else "Moderate"
            explanation = (
                f"Moderate Stress: Score {uehi_score:.1f} with canopy baseline of {canopy_text}. "
                "Secondary candidate for selective canopy infill."
            )
            need_tier = "Moderate"
        else:
            stock_text = f"{carbon_stock:.1f} t CO₂e" if carbon_stock is not None else "Substantial"
            explanation = (
                f"Low Need / Stable: Score {uehi_score:.1f} indicates preserved vegetation "
                f"({stock_text} standing carbon). Priority is canopy conservation."
            )
            need_tier = "Low"

        candidates.append({
            "rank": idx + 1,
            "block_id": block_id,
            "uehi_score": uehi_score,
            "risk_level": risk_level,
            "need_tier": need_tier,
            "ranking_explanation": explanation,
            "indicators": {
                "tree_density": tree_density,
                "ndvi": ndvi,
                "impervious_surfaces": impervious,
                "temperature": temp,
                "population_exposure": pop_exp,
                "aqi": pm25,
            },
            "carbon": {
                "standing_carbon_stock_tonnes_co2e": carbon_stock,
                "canopy_area_m2": canopy_area,
                "estimated_tree_count": tree_count,
                "above_ground_biomass_kg": biomass,
            },
            "centroid": [centroid_lng, centroid_lat] if centroid_lng and centroid_lat else None,
            "intersection_area_m2": intersection_area,
            "is_excluded": is_excluded,
            "feasibility": {
                "ownership_status": "Verification required (cadastre unlinked)",
                "utility_status": "Verification required (subterranean clearance unverified)",
                "planting_permission_status": "Verification required (on-site survey required)",
                "disclaimer": "Ecological need does not establish legal or physical planting feasibility.",
            }
        })

    return candidates


@study_area_router.post("/study-area/aggregate")
async def aggregate_study_area(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_internal_api_key),
):
    """
    Aggregate UEHI scores, Carbon estimates, and candidate planting blocks for a study area polygon.
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
    candidate_blocks = []

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

        # Retrieve real candidate blocks intersecting the study area
        try:
            candidate_blocks = query_candidate_blocks_in_area(db, geom_wgs84, limit=50)
        except Exception as e:
            candidate_blocks = []

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
        "candidate_blocks": candidate_blocks,
    }


@study_area_router.post("/study-area/candidates")
async def get_study_area_candidates(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_internal_api_key),
):
    """
    Dedicated endpoint returning ranked candidate blocks within a study area geometry.
    """
    geom_wgs84 = payload.get("geometry", payload)
    if not geom_wgs84 or "type" not in geom_wgs84 or "coordinates" not in geom_wgs84:
        raise HTTPException(status_code=400, detail="Malformed geometry")

    limit = payload.get("limit", 50)
    try:
        limit = max(1, min(int(limit), 200))
    except (ValueError, TypeError):
        limit = 50

    try:
        candidates = query_candidate_blocks_in_area(db, geom_wgs84, limit=limit)
        return {
            "total_candidates": len(candidates),
            "candidates": candidates,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to query candidate blocks: {str(e)}")

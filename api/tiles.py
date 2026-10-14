import uuid
from fastapi import APIRouter, Depends, HTTPException, Path, Response
from sqlalchemy.orm import Session
from sqlalchemy import text
from api.database import get_db

tiles_router = APIRouter(prefix="/tiles", tags=["tiles"])

def validate_zxy(z: int, x: int, y: int):
    if z < 0 or z > 22:
        raise HTTPException(status_code=400, detail="Invalid zoom level")
    max_coord = (1 << z) - 1
    if x < 0 or x > max_coord or y < 0 or y > max_coord:
        raise HTTPException(status_code=400, detail="Invalid tile coordinates")

@tiles_router.get("/uehi/{z}/{x}/{y}.pbf")
async def get_uehi_tile(
    z: int = Path(...), 
    x: int = Path(...), 
    y: int = Path(...),
    db: Session = Depends(get_db)
):
    validate_zxy(z, x, y)
    query = text("SELECT mvt_uehi_blocks(:z, :x, :y) AS mvt")
    result = db.execute(query, {"z": z, "x": x, "y": y}).scalar()
    
    if not result:
        return Response(content=b"", media_type="application/vnd.mapbox-vector-tile")
    
    return Response(content=result, media_type="application/vnd.mapbox-vector-tile")

@tiles_router.get("/carbon/{z}/{x}/{y}.pbf")
async def get_carbon_tile(
    z: int = Path(...), 
    x: int = Path(...), 
    y: int = Path(...),
    db: Session = Depends(get_db)
):
    validate_zxy(z, x, y)
    query = text("SELECT mvt_carbon_blocks(:z, :x, :y) AS mvt")
    result = db.execute(query, {"z": z, "x": x, "y": y}).scalar()
    
    if not result:
        return Response(content=b"", media_type="application/vnd.mapbox-vector-tile")
    
    return Response(content=result, media_type="application/vnd.mapbox-vector-tile")

@tiles_router.get("/planting-areas/{z}/{x}/{y}.pbf")
async def get_planting_areas_tile(
    z: int = Path(...), 
    x: int = Path(...), 
    y: int = Path(...),
    db: Session = Depends(get_db)
):
    validate_zxy(z, x, y)
    query = text("SELECT mvt_planting_candidate_areas(:z, :x, :y) AS mvt")
    result = db.execute(query, {"z": z, "x": x, "y": y}).scalar()
    
    if not result:
        return Response(content=b"", media_type="application/vnd.mapbox-vector-tile")
    
    return Response(content=result, media_type="application/vnd.mapbox-vector-tile")

@tiles_router.get("/planting-units/{scenario_id}/{z}/{x}/{y}.pbf")
async def get_planting_units_tile(
    scenario_id: uuid.UUID = Path(...),
    z: int = Path(...), 
    x: int = Path(...), 
    y: int = Path(...),
    db: Session = Depends(get_db)
):
    validate_zxy(z, x, y)
    query = text("SELECT mvt_planting_units(:scenario_id, :z, :x, :y) AS mvt")
    result = db.execute(query, {"scenario_id": str(scenario_id), "z": z, "x": x, "y": y}).scalar()
    
    if not result:
        return Response(content=b"", media_type="application/vnd.mapbox-vector-tile")
    
    return Response(content=result, media_type="application/vnd.mapbox-vector-tile")

"""
api/main.py
───────────
FastAPI application for the UEHIS Urban Eco-Heat Island Scoring System.

Endpoints
---------
* ``GET  /health``                  — service health check
* ``GET  /blocks``                  — list all blocks (paginated)
* ``GET  /blocks/{block_id}``       — full block data
* ``GET  /blocks/{block_id}/score`` — UEHI score + risk level
* ``GET  /blocks/{block_id}/carbon``— carbon / biomass data
* ``POST /blocks``                  — create or update a block
"""

from __future__ import annotations

import json
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Query
from geoalchemy2.functions import ST_AsGeoJSON
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.database import get_db, init_db
from api.models import (
    BlockCreate,
    BlockDB,
    BlockResponse,
    CarbonResponse,
    HealthResponse,
    ScoreResponse,
    UEHIFactors,
)


# ---------------------------------------------------------------------------
# Lifespan (create tables on startup)
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise the database on application startup."""
    try:
        init_db()
        print("[API] Database tables initialised.")
    except Exception as exc:
        print(f"[API] Database init skipped ({exc}). Is PostGIS running?")
    yield


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="UEHIS API",
    description=(
        "Urban Eco-Heat Island Scoring System — "
        "query UEHI scores, carbon-sink data, and planting recommendations."
    ),
    version="0.1.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_block_or_404(block_id: str, db: Session) -> BlockDB:
    stmt = select(BlockDB).where(BlockDB.block_id == block_id)
    block = db.execute(stmt).scalar_one_or_none()
    if block is None:
        raise HTTPException(status_code=404, detail=f"Block '{block_id}' not found.")
    return block


def _block_to_factors(block: BlockDB) -> UEHIFactors:
    return UEHIFactors(
        ndvi=block.ndvi,
        tree_density=block.tree_density,
        biodiversity=block.biodiversity,
        aqi=block.aqi,
        temperature=block.temperature,
        impervious_surfaces=block.impervious_surfaces,
        water_availability=block.water_availability,
        population_exposure=block.population_exposure,
    )


def _block_geojson(block: BlockDB, db: Session) -> dict | None:
    if block.geom is None:
        return None
    result = db.execute(
        select(ST_AsGeoJSON(BlockDB.geom)).where(BlockDB.id == block.id)
    ).scalar()
    return json.loads(result) if result else None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health", response_model=HealthResponse, tags=["system"])
async def health_check():
    """Service health check."""
    return HealthResponse()


@app.get("/blocks", response_model=list[ScoreResponse], tags=["blocks"])
async def list_blocks(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """List all blocks with their UEHI scores (paginated)."""
    stmt = select(BlockDB).offset(skip).limit(limit)
    blocks = db.execute(stmt).scalars().all()
    return [
        ScoreResponse(
            block_id=b.block_id,
            uehi_score=b.uehi_score,
            risk_level=b.risk_level,
            factors=_block_to_factors(b),
        )
        for b in blocks
    ]


@app.get("/blocks/{block_id}", response_model=BlockResponse, tags=["blocks"])
async def get_block(block_id: str, db: Session = Depends(get_db)):
    """Get full data for a single city block."""
    block = _get_block_or_404(block_id, db)
    return BlockResponse(
        block_id=block.block_id,
        uehi_score=block.uehi_score,
        risk_level=block.risk_level,
        factors=_block_to_factors(block),
        canopy_volume=block.canopy_volume,
        agb_kg=block.agb_kg,
        co2_tonnes=block.co2_tonnes,
        geojson=_block_geojson(block, db),
    )


@app.get(
    "/blocks/{block_id}/score",
    response_model=ScoreResponse,
    tags=["scoring"],
)
async def get_block_score(block_id: str, db: Session = Depends(get_db)):
    """Get the UEHI score and risk level for a city block."""
    block = _get_block_or_404(block_id, db)
    return ScoreResponse(
        block_id=block.block_id,
        uehi_score=block.uehi_score,
        risk_level=block.risk_level,
        factors=_block_to_factors(block),
    )


@app.get(
    "/blocks/{block_id}/carbon",
    response_model=CarbonResponse,
    tags=["carbon"],
)
async def get_block_carbon(block_id: str, db: Session = Depends(get_db)):
    """Get carbon / biomass data for a city block."""
    block = _get_block_or_404(block_id, db)
    return CarbonResponse(
        block_id=block.block_id,
        canopy_volume=block.canopy_volume,
        agb_kg=block.agb_kg,
        co2_tonnes=block.co2_tonnes,
    )


@app.post("/blocks", response_model=BlockResponse, status_code=201, tags=["blocks"])
async def create_or_update_block(
    payload: BlockCreate,
    db: Session = Depends(get_db),
):
    """Create a new block or update an existing one (upsert by block_id)."""
    stmt = select(BlockDB).where(BlockDB.block_id == payload.block_id)
    block = db.execute(stmt).scalar_one_or_none()

    if block is None:
        block = BlockDB(block_id=payload.block_id)
        db.add(block)

    # Update scalar fields
    for field_name in [
        "ndvi", "tree_density", "biodiversity", "aqi",
        "temperature", "impervious_surfaces", "water_availability",
        "population_exposure", "uehi_score", "risk_level",
        "canopy_volume", "agb_kg", "co2_tonnes",
    ]:
        value = getattr(payload, field_name, None)
        if value is not None:
            setattr(block, field_name, value)

    # Handle GeoJSON geometry
    if payload.geojson is not None:
        from geoalchemy2.shape import from_shape
        from shapely.geometry import shape

        geom = shape(payload.geojson)
        block.geom = from_shape(geom, srid=4326)

    db.commit()
    db.refresh(block)

    return BlockResponse(
        block_id=block.block_id,
        uehi_score=block.uehi_score,
        risk_level=block.risk_level,
        factors=_block_to_factors(block),
        canopy_volume=block.canopy_volume,
        agb_kg=block.agb_kg,
        co2_tonnes=block.co2_tonnes,
        geojson=_block_geojson(block, db),
    )

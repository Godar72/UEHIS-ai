"""
api/models.py
─────────────
SQLAlchemy ORM models (PostGIS) and Pydantic response schemas
for city-block UEHI scores and carbon-sink data.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from geoalchemy2 import Geometry
from pydantic import BaseModel, Field
from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Integer,
    String,
    func,
)

from api.database import Base


# ═══════════════════════════════════════════════════════════════════════════
# ORM models (PostGIS)
# ═══════════════════════════════════════════════════════════════════════════

class BlockDB(Base):
    """Stores per-block UEHI scores, carbon data, and geometry."""

    __tablename__ = "blocks"

    id = Column(Integer, primary_key=True, index=True)
    block_id = Column(String, unique=True, nullable=False, index=True)

    # ── UEHI factors ────────────────────────────────────────────────────
    ndvi = Column(Float, nullable=True)
    tree_density = Column(Float, nullable=True)
    biodiversity = Column(Float, nullable=True)
    aqi = Column(Float, nullable=True)
    temperature = Column(Float, nullable=True)
    impervious_surfaces = Column(Float, nullable=True)
    water_availability = Column(Float, nullable=True)
    population_exposure = Column(Float, nullable=True)

    # ── Computed scores ─────────────────────────────────────────────────
    uehi_score = Column(Float, nullable=True)
    risk_level = Column(String, nullable=True)

    # ── Carbon / biomass ────────────────────────────────────────────────
    canopy_volume = Column(Float, nullable=True)
    agb_kg = Column(Float, nullable=True)
    co2_tonnes = Column(Float, nullable=True)

    # ── Geometry ────────────────────────────────────────────────────────
    geom = Column(Geometry("POLYGON", srid=4326), nullable=True)

    # ── Metadata ────────────────────────────────────────────────────────
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


# ═══════════════════════════════════════════════════════════════════════════
# Pydantic schemas
# ═══════════════════════════════════════════════════════════════════════════

class UEHIFactors(BaseModel):
    """Raw 8-factor values for a city block."""
    ndvi: float | None = None
    tree_density: float | None = None
    biodiversity: float | None = None
    aqi: float | None = None
    temperature: float | None = None
    impervious_surfaces: float | None = None
    water_availability: float | None = None
    population_exposure: float | None = None


class ScoreResponse(BaseModel):
    """UEHI score endpoint response."""
    block_id: str
    uehi_score: float | None = None
    risk_level: str | None = None
    factors: UEHIFactors = Field(default_factory=UEHIFactors)

    model_config = {"from_attributes": True}


class CarbonResponse(BaseModel):
    """Carbon / biomass endpoint response."""
    block_id: str
    canopy_volume: float | None = None
    agb_kg: float | None = None
    co2_tonnes: float | None = None

    model_config = {"from_attributes": True}


class BlockResponse(BaseModel):
    """Full block data (score + carbon + geometry)."""
    block_id: str
    uehi_score: float | None = None
    risk_level: str | None = None
    factors: UEHIFactors = Field(default_factory=UEHIFactors)
    canopy_volume: float | None = None
    agb_kg: float | None = None
    co2_tonnes: float | None = None
    geojson: dict[str, Any] | None = None

    model_config = {"from_attributes": True}


class BlockCreate(BaseModel):
    """Payload to create or update a block."""
    block_id: str
    ndvi: float | None = None
    tree_density: float | None = None
    biodiversity: float | None = None
    aqi: float | None = None
    temperature: float | None = None
    impervious_surfaces: float | None = None
    water_availability: float | None = None
    population_exposure: float | None = None
    uehi_score: float | None = None
    risk_level: str | None = None
    canopy_volume: float | None = None
    agb_kg: float | None = None
    co2_tonnes: float | None = None
    geojson: dict[str, Any] | None = None


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "ok"
    service: str = "uehis-api"
    version: str = "0.1.0"

"""
carbon_sink/biomass.py
──────────────────────
Converts canopy geometry into above-ground biomass (AGB) and estimates
tons of CO₂ sequestered using standard allometric equations.

References
----------
* Chave et al. (2014) — pantropical AGB model
* Jenkins et al. (2003) — temperate North-American AGB model
* IPCC default carbon fraction: 0.47
* CO₂/C molecular-weight ratio: 44 / 12 ≈ 3.667
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Literal

import geopandas as gpd
import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CARBON_FRACTION = 0.47          # kg C per kg dry biomass (IPCC default)
CO2_PER_CARBON = 44.0 / 12.0   # kg CO₂ per kg C  (≈ 3.667)
KG_PER_TONNE = 1000.0


# ---------------------------------------------------------------------------
# Allometric models
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AllometricModel:
    """
    Parameters for the power-law AGB equation:

        AGB (kg) = a × DBH^b

    where DBH is diameter at breast height in **cm**.
    """
    name: str
    a: float
    b: float
    description: str = ""


# Pre-defined models — users can also supply their own
MODELS: dict[str, AllometricModel] = {
    "tropical_chave": AllometricModel(
        name="tropical_chave",
        a=0.0673,
        b=2.616,
        description="Chave et al. (2014) pantropical moist forest",
    ),
    "temperate_jenkins": AllometricModel(
        name="temperate_jenkins",
        a=0.0346,
        b=2.9451,
        description="Jenkins et al. (2003) mixed hardwood, temperate",
    ),
    "urban_generic": AllometricModel(
        name="urban_generic",
        a=0.1066,
        b=2.4572,
        description="McPherson et al. (2016) urban broadleaf average",
    ),
}

DEFAULT_MODEL = "urban_generic"


# ---------------------------------------------------------------------------
# Canopy volume → DBH estimation
# ---------------------------------------------------------------------------

def estimate_dbh_from_crown(
    crown_diameter: float | np.ndarray,
    crown_to_dbh_ratio: float = 20.0,
) -> float | np.ndarray:
    """
    Estimate stem diameter at breast height (DBH, cm) from crown diameter (m).

    Uses the linear approximation:

        DBH (cm) = crown_diameter (m) × 100 / crown_to_dbh_ratio

    Parameters
    ----------
    crown_diameter : float or array
        Crown diameter in metres.
    crown_to_dbh_ratio : float
        Typical crown-to-DBH ratio (default 20 — common for urban broadleaf).

    Returns
    -------
    float or ndarray
        Estimated DBH in cm.
    """
    return np.asarray(crown_diameter) * 100.0 / crown_to_dbh_ratio


def estimate_dbh_from_volume(
    canopy_volume: float | np.ndarray,
    assumed_height: float = 8.0,
    crown_shape: Literal["sphere", "cone", "ellipsoid"] = "ellipsoid",
    crown_to_dbh_ratio: float = 20.0,
) -> float | np.ndarray:
    """
    Estimate DBH (cm) from canopy volume (m³) via crown geometry.

    The canopy is modelled as one of three solids to back-calculate a
    representative crown diameter, which is then converted to DBH.

    Parameters
    ----------
    canopy_volume : float or array
        Canopy volume in cubic metres.
    assumed_height : float
        Assumed tree height in metres (used for cone / ellipsoid models).
    crown_shape : {"sphere", "cone", "ellipsoid"}
        Geometric approximation of the crown shape.
    crown_to_dbh_ratio : float
        Crown-diameter-to-DBH ratio (default 20).

    Returns
    -------
    float or ndarray
        Estimated DBH in cm.
    """
    vol = np.asarray(canopy_volume, dtype=float)

    if crown_shape == "sphere":
        # V = (4/3)πr³  →  r = (3V / 4π)^(1/3)  →  d = 2r
        radius = np.cbrt(3.0 * vol / (4.0 * math.pi))
        crown_d = 2.0 * radius

    elif crown_shape == "cone":
        # V = (1/3)πr²h  →  r = sqrt(3V / πh)  →  d = 2r
        radius = np.sqrt(3.0 * vol / (math.pi * assumed_height))
        crown_d = 2.0 * radius

    elif crown_shape == "ellipsoid":
        # V = (4/3)π·a·b·c  with a=b=r (horizontal), c=h/2
        # V = (4/3)πr²(h/2) = (2/3)πr²h  →  r = sqrt(3V / 2πh)
        radius = np.sqrt(3.0 * vol / (2.0 * math.pi * assumed_height))
        crown_d = 2.0 * radius

    else:
        raise ValueError(f"Unknown crown_shape '{crown_shape}'.")

    return estimate_dbh_from_crown(crown_d, crown_to_dbh_ratio)


# ---------------------------------------------------------------------------
# AGB calculation
# ---------------------------------------------------------------------------

def compute_agb(
    dbh_cm: float | np.ndarray,
    model_name: str = DEFAULT_MODEL,
    model: AllometricModel | None = None,
) -> float | np.ndarray:
    """
    Compute above-ground biomass (AGB) in **kg** from DBH (cm).

    Parameters
    ----------
    dbh_cm : float or array
        Stem diameter at breast height in centimetres.
    model_name : str
        Key into the built-in ``MODELS`` dict (ignored if *model* is given).
    model : AllometricModel | None
        Custom allometric model.

    Returns
    -------
    float or ndarray
        AGB in kg.
    """
    if model is None:
        model = MODELS.get(model_name)
        if model is None:
            raise ValueError(
                f"Unknown model '{model_name}'. "
                f"Available: {list(MODELS.keys())}"
            )
    return model.a * np.power(np.asarray(dbh_cm, dtype=float), model.b)


# ---------------------------------------------------------------------------
# Standing CO₂ stock
# ---------------------------------------------------------------------------

def agb_to_co2_tonnes(agb_kg: float | np.ndarray) -> float | np.ndarray:
    """
    Convert AGB (kg) → standing carbon stock expressed as tonnes CO2-equivalent.

    AGB → carbon (×0.47) → CO₂ (×44/12) → tonnes (÷1000)
    """
    return np.asarray(agb_kg) * CARBON_FRACTION * CO2_PER_CARBON / KG_PER_TONNE


def canopy_volume_to_co2(
    canopy_volume: float | np.ndarray,
    assumed_height: float = 8.0,
    crown_shape: Literal["sphere", "cone", "ellipsoid"] = "ellipsoid",
    model_name: str = DEFAULT_MODEL,
) -> float | np.ndarray:
    """
    End-to-end: canopy volume (m³) → standing carbon stock expressed as tonnes CO2-equivalent.

    Parameters
    ----------
    canopy_volume : float or array
        Canopy volume in m³.
    assumed_height : float
        Tree height in metres for crown-geometry back-calculation.
    crown_shape : str
        Crown geometry model.
    model_name : str
        Allometric model name.

    Returns
    -------
    float or ndarray
        standing carbon stock expressed as tonnes CO2-equivalent.
    """
    dbh = estimate_dbh_from_volume(
        canopy_volume,
        assumed_height=assumed_height,
        crown_shape=crown_shape,
    )
    agb = compute_agb(dbh, model_name=model_name)
    return agb_to_co2_tonnes(agb)


# ---------------------------------------------------------------------------
# GeoDataFrame convenience
# ---------------------------------------------------------------------------

def compute_co2_for_geodataframe(
    gdf: gpd.GeoDataFrame,
    volume_column: str = "canopy_volume",
    assumed_height: float = 8.0,
    crown_shape: Literal["sphere", "cone", "ellipsoid"] = "ellipsoid",
    model_name: str = DEFAULT_MODEL,
    co2_column: str = "co2_tonnes",
    agb_column: str = "agb_kg",
) -> gpd.GeoDataFrame:
    """
    Add AGB and CO₂ columns to a GeoDataFrame that contains canopy volumes.

    Parameters
    ----------
    gdf : geopandas.GeoDataFrame
        Must contain *volume_column* (canopy volume in m³ per feature).
    volume_column : str
        Name of the canopy-volume column.
    co2_column / agb_column : str
        Names of the output columns.

    Returns
    -------
    geopandas.GeoDataFrame
        Copy of *gdf* with added *agb_column* and *co2_column*.
    """
    result = gdf.copy()
    dbh = estimate_dbh_from_volume(
        result[volume_column].values,
        assumed_height=assumed_height,
        crown_shape=crown_shape,
    )
    result[agb_column] = compute_agb(dbh, model_name=model_name)
    result[co2_column] = agb_to_co2_tonnes(result[agb_column].values)

    total = result[co2_column].sum()
    print(
        f"[Biomass] {len(result)} features  →  "
        f"total AGB = {result[agb_column].sum():,.0f} kg  |  "
        f"total CO₂ = {total:,.2f} tonnes"
    )
    return result

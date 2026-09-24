# UEHIS – Carbon Sink Planning Module
# Biomass estimation, CO2 sequestration, and optimal planting-site selection.

from carbon_sink.biomass import (
    AllometricModel,
    MODELS,
    estimate_dbh_from_crown,
    estimate_dbh_from_volume,
    compute_agb,
    agb_to_co2_tonnes,
    canopy_volume_to_co2,
    compute_co2_for_geodataframe,
    CARBON_FRACTION,
    CO2_PER_CARBON,
)
from carbon_sink.canopy_height import (
    fetch_canopy_height_ee,
    estimate_canopy_height_fallback,
    get_canopy_height,
    compute_block_co2,
    fallback_height_from_frac,
    carbon_from_canopy_params,
)
from carbon_sink.optimizer import (
    OptimizationResult,
    optimize_planting_sites,
    budget_sweep,
)
from carbon_sink.planting_recommender import (
    recommend_planting_sites,
)

__all__ = [
    # biomass
    "AllometricModel",
    "MODELS",
    "estimate_dbh_from_crown",
    "estimate_dbh_from_volume",
    "compute_agb",
    "agb_to_co2_tonnes",
    "canopy_volume_to_co2",
    "compute_co2_for_geodataframe",
    "CARBON_FRACTION",
    "CO2_PER_CARBON",
    # canopy height & carbon stock
    "fetch_canopy_height_ee",
    "estimate_canopy_height_fallback",
    "get_canopy_height",
    "compute_block_co2",
    "fallback_height_from_frac",
    "carbon_from_canopy_params",
    # optimizer
    "OptimizationResult",
    "optimize_planting_sites",
    "budget_sweep",
    # planting recommender
    "recommend_planting_sites",
]

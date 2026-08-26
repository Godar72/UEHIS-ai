# UEHIS – Carbon Sink Planning Module
# Biomass estimation, CO₂ sequestration, and optimal planting-site selection.

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
from carbon_sink.optimizer import (
    OptimizationResult,
    optimize_planting_sites,
    budget_sweep,
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
    # optimizer
    "OptimizationResult",
    "optimize_planting_sites",
    "budget_sweep",
]

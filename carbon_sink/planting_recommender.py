"""
carbon_sink/planting_recommender.py
────────────────────────────────────
DEPRECATED.

The block-level planting recommender has been removed in Phase 4 Stage 2.3.
It incorrectly treated arbitrary 250m block canopy deficits (e.g., < 15%) as 
physically and legally plantable space, and made arbitrary assumptions about 
reaching a 30% capacity target.

Please use `carbon_sink.optimizer` which operates on the Stage 2.2 
high-resolution planting candidate geometries.
"""

def recommend_planting_sites(*args, **kwargs):
    raise NotImplementedError(
        "Block-level planting recommendation is deprecated. "
        "Use carbon_sink.optimizer over Stage 2.2 candidate geometries instead."
    )

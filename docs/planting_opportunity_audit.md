### A. CURRENT IMPLEMENTATION
The current pipeline splits planting opportunity into two disconnected modules:
1. `planting_recommender.py`: Operates at the **250m block level**. It ranks blocks based on raw additional carbon stock potential.
2. `optimizer.py`: Operates at the **cell/pixel level** using a Mixed-Integer Linear Programming (MILP) approach. It selects specific cells to maximize a projected UEHI score improvement subject to a budget constraint.

### B. INPUT DATA ACTUALLY AVAILABLE
Currently, the models expect and consume:
- `canopy_frac` (or `tree_density`)
- `imperv_frac` (or `impervious_surfaces`)
- `block_area_m2`
- `canopy_height_m`
- `carbon_stock_tonnes_co2e` (derived)
- `class_id` (U-Net pixel classes: 1=impervious, 2=pervious)
- `uehi_score`
- Water feature geometries (used for distance calculation)

### C. ASSUMPTIONS
1. **Plantability:** 
   - Block level: Assumes any block with `< 15%` canopy and `< 80%` impervious surface is a valid candidate and can reach a flat `30%` canopy target.
   - Pixel level: Assumes *any* non-impervious cell (`class_id != 1`) within 200m of water is fully available for planting.
2. **Impact Projections:**
   - Assumes planting a tree provides exactly +0.35 NDVI, -0.40 impervious fraction, and a flat +2.0 evapotranspiration cooling bonus.
   - Assumes a mature canopy volume of 50.0m³ per new tree.
3. **Accessibility:**
   - Assumes a straight-line 200m distance to water guarantees irrigation access.

### D. SCIENTIFIC/GEOSPATIAL GAPS
The current pipeline equates "pervious surface" or "low canopy" directly with "plantable space." This is a major geospatial fallacy. 
It accidentally treats:
- Private vacant land, agricultural plots, or sports fields as automatically plantable.
- Unpaved roads, dirt pathways, or railway buffers as plantable.
- Bare soil in industrial zones as plantable.

### E. WHAT CAN BE SAFELY CLAIMED
We can only safely claim:
- The current distribution of existing canopy.
- The current distribution of pervious vs. impervious surfaces.
- Theoretical deficits (e.g., "This block has low canopy and high heat").

### F. WHAT CANNOT YET BE CLAIMED
We **cannot** claim actual "Planting Sites" or "Opportunities." We lack the contextual constraint layers to know if a pervious pixel is a public park, a private backyard, a road verge, or a protected wetland. 

### G. REQUIRED DATA FOR A DEFENSIBLE PLANTING-OPPORTUNITY MODEL
To generate scientifically defensible planting sites, we strictly require:
- Land ownership boundaries (Public vs. Private)
- Municipal zoning / Land-use information
- Parks and open spaces inventories
- Road network and verge demarcations
- Existing built footprints (to calculate setbacks)
- Underground/overhead utility constraints
- Water / drainage / easement constraints

### H. TESTING GAPS
- **Zero test coverage:** There are no tests (`test_planting_recommender.py` or `test_optimizer.py` do not exist).
- **Hardcoded paths:** `planting_recommender.py` defaults to Kothrud-specific output paths (`outputs/kothrud_planting_recommendations.csv`).
- **Disconnected logic:** The two modules use entirely different paradigms (Block-level carbon ranking vs. Pixel-level UEHI MILP) and do not integrate seamlessly.

### I. RECOMMENDED NEXT IMPLEMENTATION STEP
Pause all optimization and recommendation executions. The codebase must be refactored to introduce a formal `Plantability Mask` generator that ingests land-use and constraint layers (when available) before passing pixels to the optimizer. Planting opportunity should be modeled strictly at the **high-resolution pixel or parcel level**, not the 250m block level, as block-level averages cannot define a physical planting site.

PLANTING STAGE READINESS:
BLOCKED — DATA/METHODOLOGY GAP

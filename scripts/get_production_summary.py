import json
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import text
from api.database import SessionLocal

def get_summary():
    db = SessionLocal()
    try:
        # UEHI stats in single aggregate query
        uehi_row = db.execute(text("""
            SELECT 
                count(*),
                count(*) FILTER (WHERE is_excluded = false),
                avg(uehi_score) FILTER (WHERE is_excluded = false)
            FROM uehi_blocks
        """)).fetchone()
        total_blocks, scored_blocks, mean_uehi = uehi_row[0], uehi_row[1], uehi_row[2]
        
        # Carbon stats in single aggregate query
        carbon_row = db.execute(text("""
            SELECT 
                sum(standing_carbon_stock),
                sum(canopy_area_m2),
                sum(estimated_tree_count),
                sum(above_ground_biomass_kg),
                count(*) FILTER (WHERE standing_carbon_stock > 0)
            FROM carbon_blocks
        """)).fetchone()
        total_carbon, canopy_area, tree_count, biomass, carbon_blocks_count = (
            carbon_row[0], carbon_row[1], carbon_row[2], carbon_row[3], carbon_row[4]
        )
        
        return {
            "uehi": {
                "total_blocks": total_blocks,
                "scored_blocks": scored_blocks,
                "mean_score": float(mean_uehi) if mean_uehi is not None else None
            },
            "carbon": {
                "total_carbon": float(total_carbon) if total_carbon is not None else None,
                "canopy_area_km2": float(canopy_area) / 1000000.0 if canopy_area is not None else None,
                "tree_count": float(tree_count) if tree_count is not None else None,
                "biomass_kg": float(biomass) if biomass is not None else None,
                "nonzero_blocks": carbon_blocks_count
            }
        }
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)
    finally:
        db.close()

if __name__ == '__main__':
    print(json.dumps(get_summary()))

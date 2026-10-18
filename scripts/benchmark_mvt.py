import time
from sqlalchemy import text
from api.database import SessionLocal

def benchmark():
    db = SessionLocal()
    
    queries = [
        {
            "name": "UEHI Blocks - Low Zoom (z=8)",
            "query": "SELECT mvt_uehi_blocks(8, 181, 114)"
        },
        {
            "name": "UEHI Blocks - Medium Zoom (z=12)",
            "query": "SELECT mvt_uehi_blocks(12, 2906, 1827)"
        },
        {
            "name": "UEHI Blocks - High Zoom (z=15)",
            "query": "SELECT mvt_uehi_blocks(15, 23253, 14622)"
        },
        {
            "name": "Carbon Blocks - High Zoom (z=15)",
            "query": "SELECT mvt_carbon_blocks(15, 23253, 14622)"
        },
        {
            "name": "Candidate Areas - High Zoom (z=15)",
            "query": "SELECT mvt_planting_candidate_areas(15, 23253, 14622)"
        },
        {
            "name": "Planting Units - High Zoom Dense (z=15)",
            "query": "SELECT mvt_planting_units('00000000-0000-0000-0000-000000000000'::uuid, 15, 23253, 14622)" # Will be empty since fake uuid but still exercises plan
        }
    ]
    
    print("MVT Benchmarks")
    print("==============")
    
    for q in queries:
        start = time.time()
        res = db.execute(text(q["query"])).scalar()
        elapsed = time.time() - start
        size = len(res) if res else 0
        
        # Get EXPLAIN ANALYZE for the underlying query to see index usage
        # Extract the underlying SELECT from the function logically
        raw_query = q["query"].replace("mvt_", "")
        if "uehi" in raw_query:
            table = "uehi_blocks"
        elif "carbon" in raw_query:
            table = "carbon_blocks"
        elif "areas" in raw_query:
            table = "planting_candidate_areas"
        else:
            table = "planting_units"
            
        z, x, y = [int(i) for i in q["query"].split("(")[1].split(")")[0].split(",")[-3:]]
        
        explain_q = f"EXPLAIN ANALYZE SELECT 1 FROM {table} WHERE geom && ST_Transform(ST_TileEnvelope({z}, {x}, {y}), 32643)"
        
        plan_rows = []
        try:
            plan = db.execute(text(explain_q)).fetchall()
            plan_rows = [r[0] for r in plan]
            is_index_scan = any("Index" in row and table in row for row in plan_rows)
        except Exception as e:
            is_index_scan = "Unknown"
        
        print(f"Layer: {q['name']}")
        print(f"  Execution Time: {elapsed*1000:.2f} ms")
        print(f"  Payload Size: {size} bytes")
        print(f"  Index Scan Used: {is_index_scan}")
        print()

    db.close()

if __name__ == "__main__":
    benchmark()

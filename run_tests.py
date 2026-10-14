import subprocess
import json

def run_sql(query):
    cmd = ['docker', 'exec', '-i', 'supabase_db_SL', 'psql', '-U', 'postgres', '-d', 'postgres', '-t', '-q']
    result = subprocess.run(cmd, input=query, capture_output=True, text=True)
    return result.stdout.strip(), result.stderr.strip()

print("--- 1. UEHI Viewport Query Test ---")
out, err = run_sql("SELECT json_agg(row_to_json(t)) FROM get_blocks_in_viewport(73.7, 18.4, 74.0, 18.6, 5) t;")
print("Output:", out[:200] + "...")

print("\n--- 2. Block Detail Test ---")
out, err = run_sql("SELECT get_block_detail('PN_368000_2049250');")
print("Output:", out[:200] + "...")

print("\n--- 3. Point Radius Generator Test ---")
out, err = run_sql("SELECT ST_GeometryType(generate_point_radius_study_area(73.8567, 18.5204, 1000));")
print("Output:", out)

print("\n--- 4. Invalid Input Test (Radius < 10m) ---")
out, err = run_sql("SELECT generate_point_radius_study_area(73.8567, 18.5204, 5);")
print("Error Output:", err)

print("\n--- 5. Study Area Aggregation (DB RPC) ---")
rpc_out, _ = run_sql("SELECT aggregate_study_area(generate_point_radius_study_area(73.8567, 18.5204, 20000));")
print("RPC Output:", rpc_out)

print("\n--- 6. Independent Mathematical Test ---")
# Manually query intersections and compute area-weighted UEHI in Python
query = """
SELECT b.uehi_score, ST_Area(ST_Intersection(b.geom, generate_point_radius_study_area(73.8567, 18.5204, 20000))) as int_area, b.is_excluded
FROM public.uehi_blocks b
WHERE ST_Intersects(b.geom, generate_point_radius_study_area(73.8567, 18.5204, 20000));
"""
raw_data, err_data = run_sql(query)
if not raw_data.strip():
    print(f"ERROR: No raw data returned. Stderr: {err_data}")
sum_uehi_area = 0.0
sum_area = 0.0

for row in raw_data.strip().split('\n'):
    if not row.strip(): continue
    parts = row.split('|')
    try:
        uehi_str = parts[0].strip()
        uehi = float(uehi_str) if uehi_str else 0.0
        area = float(parts[1].strip())
    except ValueError:
        continue
    excluded = parts[2].strip() == 't'
    if not excluded and area > 0:
        sum_uehi_area += uehi * area
        sum_area += area

independent_score = sum_uehi_area / sum_area if sum_area > 0 else None
print(f"Independent Python calc: {independent_score:.4f}")

try:
    rpc_json = json.loads(rpc_out)
    db_score = rpc_json.get("uehi", {}).get("score")
    print(f"Database RPC calc: {db_score:.4f}")
    if abs(independent_score - db_score) < 0.0001:
        print("TOLERANCE MATCH: TRUE (Tolerance = 0.0001)")
    else:
        print("TOLERANCE MATCH: FALSE")
except Exception as e:
    print("Failed to parse JSON for tolerance match:", e)
    
print("\n--- 7. Provenance Test ---")
# Get a production run ID
pid, _ = run_sql("SELECT id FROM production_runs LIMIT 1;")
if pid:
    mid, _ = run_sql("SELECT id FROM methodology_versions LIMIT 1;")
    out, err = run_sql(f"SELECT get_provenance_info('{pid.strip()}', '{mid.strip()}');")
    print("Provenance Output:", out[:200] + "...")

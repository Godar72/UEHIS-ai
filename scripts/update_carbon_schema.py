import csv
import psycopg2

db_url = "postgresql://postgres:postgres@127.0.0.1:54223/postgres"
csv_path = r"C:\Users\adity\Desktop\SL\UEHIS_Production_2026\pune_carbon_production_2026.csv"

def main():
    conn = psycopg2.connect(db_url)
    conn.autocommit = True
    cursor = conn.cursor()

    # Alter table
    print("Altering table carbon_blocks...")
    cursor.execute("""
    ALTER TABLE carbon_blocks 
    ADD COLUMN IF NOT EXISTS canopy_area_m2 NUMERIC,
    ADD COLUMN IF NOT EXISTS estimated_tree_count NUMERIC,
    ADD COLUMN IF NOT EXISTS above_ground_biomass_kg NUMERIC;
    """)

    # Update rows
    print("Reading CSV and updating rows...")
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        updates = []
        for row in reader:
            block_id = row['block_id']
            canopy = row['canopy_area_m2']
            trees = row['n_trees_est']
            agb = row['agb_kg']
            if block_id and canopy and trees and agb:
                updates.append((float(canopy), float(trees), float(agb), block_id))
        
        # Batch update using psycopg2 execute_batch
        from psycopg2.extras import execute_batch
        
        update_query = """
        UPDATE carbon_blocks
        SET canopy_area_m2 = %s,
            estimated_tree_count = %s,
            above_ground_biomass_kg = %s
        WHERE block_id = %s;
        """
        execute_batch(cursor, update_query, updates)
        
    print(f"Successfully updated {len(updates)} blocks.")

if __name__ == "__main__":
    main()

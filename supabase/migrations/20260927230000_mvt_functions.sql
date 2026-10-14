-- ==============================================================================
-- UEHIS PRODUCTION DATABASE MIGRATION - MVT FUNCTIONS
-- Phase 2B: Vector Tile Delivery Layer
-- ==============================================================================

-- UEHI Blocks MVT
CREATE OR REPLACE FUNCTION mvt_uehi_blocks(z integer, x integer, y integer)
RETURNS bytea
LANGUAGE plpgsql
SECURITY DEFINER SET search_path = public, postgis
AS $$
DECLARE
    mvt bytea;
    bbox geometry;
BEGIN
    IF z < 0 OR z > 22 OR x < 0 OR x >= power(2, z) OR y < 0 OR y >= power(2, z) THEN
        RETURN NULL;
    END IF;

    bbox := ST_Transform(ST_TileEnvelope(z, x, y), 32643);

    SELECT ST_AsMVT(tile, 'uehi', 4096, 'mvt_geom') INTO mvt
    FROM (
        SELECT 
            block_id, 
            uehi_score, 
            risk_level,
            ST_AsMVTGeom(ST_Transform(geom, 3857), ST_TileEnvelope(z, x, y), 4096, 64, true) AS mvt_geom
        FROM uehi_blocks
        WHERE geom && bbox
    ) AS tile;

    RETURN mvt;
END;
$$;


-- Carbon Blocks MVT
CREATE OR REPLACE FUNCTION mvt_carbon_blocks(z integer, x integer, y integer)
RETURNS bytea
LANGUAGE plpgsql
SECURITY DEFINER SET search_path = public, postgis
AS $$
DECLARE
    mvt bytea;
    bbox geometry;
BEGIN
    IF z < 0 OR z > 22 OR x < 0 OR x >= power(2, z) OR y < 0 OR y >= power(2, z) THEN
        RETURN NULL;
    END IF;

    bbox := ST_Transform(ST_TileEnvelope(z, x, y), 32643);

    SELECT ST_AsMVT(tile, 'carbon', 4096, 'mvt_geom') INTO mvt
    FROM (
        SELECT 
            block_id, 
            standing_carbon_stock AS standing_carbon_stock_tonnes_co2e,
            ST_AsMVTGeom(ST_Transform(geom, 3857), ST_TileEnvelope(z, x, y), 4096, 64, true) AS mvt_geom
        FROM carbon_blocks
        WHERE geom && bbox
    ) AS tile;

    RETURN mvt;
END;
$$;


-- Planting Candidate Areas MVT
CREATE OR REPLACE FUNCTION mvt_planting_candidate_areas(z integer, x integer, y integer)
RETURNS bytea
LANGUAGE plpgsql
SECURITY DEFINER SET search_path = public, postgis
AS $$
DECLARE
    mvt bytea;
    bbox geometry;
BEGIN
    IF z < 0 OR z > 22 OR x < 0 OR x >= power(2, z) OR y < 0 OR y >= power(2, z) THEN
        RETURN NULL;
    END IF;

    bbox := ST_Transform(ST_TileEnvelope(z, x, y), 32643);

    SELECT ST_AsMVT(tile, 'planting_candidate_areas', 4096, 'mvt_geom') INTO mvt
    FROM (
        SELECT 
            area_id AS candidate_area_id, 
            ST_Area(geom) AS candidate_area_m2,
            candidate_category,
            ownership_status,
            utility_status,
            permission_status,
            ST_AsMVTGeom(ST_Transform(geom, 3857), ST_TileEnvelope(z, x, y), 4096, 64, true) AS mvt_geom
        FROM planting_candidate_areas
        WHERE geom && bbox
    ) AS tile;

    RETURN mvt;
END;
$$;


-- Planting Units MVT
CREATE OR REPLACE FUNCTION mvt_planting_units(scenario_id_param uuid, z integer, x integer, y integer)
RETURNS bytea
LANGUAGE plpgsql
SECURITY DEFINER SET search_path = public, postgis
AS $$
DECLARE
    mvt bytea;
    bbox geometry;
BEGIN
    IF z < 0 OR z > 22 OR x < 0 OR x >= power(2, z) OR y < 0 OR y >= power(2, z) THEN
        RETURN NULL;
    END IF;

    -- Implement Zoom-Dependent Visibility: do not show planting unit points at low zooms
    IF z < 14 THEN
        RETURN NULL; -- Return empty to avoid overloading browser and database
    END IF;

    bbox := ST_Transform(ST_TileEnvelope(z, x, y), 32643);

    SELECT ST_AsMVT(tile, 'planting_units', 4096, 'mvt_geom') INTO mvt
    FROM (
        SELECT 
            pu.unit_id AS planting_unit_id,
            psu.scenario_id,
            ST_AsMVTGeom(ST_Transform(pu.geom, 3857), ST_TileEnvelope(z, x, y), 4096, 64, true) AS mvt_geom
        FROM planting_units pu
        JOIN planting_scenario_units psu ON pu.unit_id = psu.unit_id
        WHERE psu.scenario_id = scenario_id_param
          AND pu.geom && bbox
        LIMIT 20000 -- Hard server-side limit for safety
    ) AS tile;

    RETURN mvt;
END;
$$;

-- Grant Execute Permissions
GRANT EXECUTE ON FUNCTION mvt_uehi_blocks(integer, integer, integer) TO public;
GRANT EXECUTE ON FUNCTION mvt_carbon_blocks(integer, integer, integer) TO public;
-- Candidates and units remain secure by requiring appropriate access logic.
-- The API endpoints will use the service role or an authenticated user context.
GRANT EXECUTE ON FUNCTION mvt_planting_candidate_areas(integer, integer, integer) TO authenticated;
GRANT EXECUTE ON FUNCTION mvt_planting_units(uuid, integer, integer, integer) TO authenticated;

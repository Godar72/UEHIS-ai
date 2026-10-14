-- ===============================================================================
-- UEHIS PRODUCTION DATABASE MIGRATION - Fix mvt_planting_candidate_areas column reference
-- Phase 2B: Vector Tile Delivery Layer Fix
-- ===============================================================================

-- Drop and recreate mvt_planting_candidate_areas without referencing candidate_category
DROP FUNCTION IF EXISTS public.mvt_planting_candidate_areas(integer, integer, integer);

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

-- Grant Execute Permissions to authenticated role (preserving existing security model)
GRANT EXECUTE ON FUNCTION mvt_planting_candidate_areas(integer, integer, integer) TO authenticated;

-- Ensure RLS stays enabled (should already be set on the table)

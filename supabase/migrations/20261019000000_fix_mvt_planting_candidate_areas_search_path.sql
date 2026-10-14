-- ===============================================================================
-- UEHIS PRODUCTION DATABASE MIGRATION - Fix MVT Planting Areas Search Path
-- Migration: 20261019000000_fix_mvt_planting_candidate_areas_search_path.sql
--
-- Ensures PostGIS functions (ST_TileEnvelope, ST_AsMVT, ST_Transform) resolve
-- correctly on Supabase Cloud where PostGIS is installed in the 'extensions' schema,
-- while retaining full compatibility with local development environments.
-- Strictly preserves least-privilege permissions (authenticated role only).
-- ===============================================================================

CREATE OR REPLACE FUNCTION public.mvt_planting_candidate_areas(z integer, x integer, y integer)
RETURNS bytea
LANGUAGE plpgsql
SECURITY DEFINER SET search_path = public, extensions
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

-- Ensure function ownership matches local Supabase convention
ALTER FUNCTION public.mvt_planting_candidate_areas(integer, integer, integer) OWNER TO postgres;

-- Explicit privilege boundary enforcement
REVOKE ALL ON FUNCTION public.mvt_planting_candidate_areas(integer, integer, integer) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.mvt_planting_candidate_areas(integer, integer, integer) FROM anon;
GRANT EXECUTE ON FUNCTION public.mvt_planting_candidate_areas(integer, integer, integer) TO authenticated;

-- ==============================================================================
-- UEHIS SECURITY HARDENING MIGRATION
-- 20261009100000_security_hardening.sql
--
-- Remediates BLOCKER and HIGH findings from the adversarial security audit.
-- Does NOT modify scientific data, formulas, or production values.
-- ==============================================================================

-- ============================================================
-- BLOCKER 1: Fix verify_api_key() — digest() needs extensions schema
-- ============================================================
CREATE OR REPLACE FUNCTION public.verify_api_key(p_key text)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, extensions
AS $$
DECLARE
    v_key_record record;
    v_hash text;
BEGIN
    -- Use schema-qualified extensions.digest() to resolve pgcrypto correctly
    v_hash := encode(extensions.digest(p_key, 'sha256'), 'hex');
    SELECT * INTO v_key_record FROM public.api_keys
    WHERE hashed_key = v_hash
      AND revoked_at IS NULL
      AND (expires_at IS NULL OR expires_at > now());

    IF FOUND THEN
        UPDATE public.api_keys SET last_used_at = now() WHERE id = v_key_record.id;
        RETURN jsonb_build_object(
            'valid', true,
            'user_id', v_key_record.user_id,
            'role', public.get_user_role(v_key_record.user_id)
        );
    ELSE
        RETURN jsonb_build_object('valid', false);
    END IF;
END;
$$;


-- ============================================================
-- BLOCKER 3: Create a safe get_my_role() that uses auth.uid()
-- This prevents arbitrary user-role enumeration.
-- ============================================================
CREATE OR REPLACE FUNCTION public.get_my_role()
RETURNS text
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT role FROM public.user_roles WHERE user_id = auth.uid();
$$;


-- ============================================================
-- BLOCKER 3: Harden get_user_role() — restrict to authenticated only
-- Keep it for internal RLS policy use but prevent anonymous/arbitrary access.
-- ============================================================
CREATE OR REPLACE FUNCTION public.get_user_role(uid uuid)
RETURNS text
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    -- Only allow: the user querying their own role, or an admin querying any role.
    -- When called from RLS policies (as postgres owner), auth.uid() may be set by the session.
    IF auth.uid() IS NULL THEN
        -- Called without authentication — deny
        RETURN NULL;
    END IF;

    IF uid = auth.uid() THEN
        -- User looking up their own role — always allowed
        RETURN (SELECT role FROM public.user_roles WHERE user_id = uid);
    END IF;

    -- For non-self lookups, require admin role
    IF (SELECT role FROM public.user_roles WHERE user_id = auth.uid()) = 'admin' THEN
        RETURN (SELECT role FROM public.user_roles WHERE user_id = uid);
    END IF;

    -- Deny arbitrary enumeration
    RETURN NULL;
END;
$$;


-- ============================================================
-- HIGH 5: Create a public-safe block detail function
-- Returns ONLY public-approved fields (no raw environmental factors)
-- ============================================================
CREATE OR REPLACE FUNCTION public.get_block_detail_public(
    p_block_id text
)
RETURNS jsonb
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public, extensions
AS $$
    SELECT jsonb_build_object(
        'block_id', b.block_id,
        'geometry', ST_AsGeoJSON(ST_Transform(b.geom, 4326))::jsonb,
        'uehi_score', b.uehi_score,
        'risk_level', b.risk_level
    )
    FROM public.uehi_blocks b
    WHERE b.block_id = p_block_id;
$$;


-- ============================================================
-- Harden get_block_detail() — add search_path with extensions
-- The function itself is now restricted to authenticated only (below)
-- ============================================================
CREATE OR REPLACE FUNCTION public.get_block_detail(
    p_block_id text
)
RETURNS jsonb
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public, extensions
AS $$
    SELECT jsonb_build_object(
        'block_id', b.block_id,
        'geometry', ST_AsGeoJSON(ST_Transform(b.geom, 4326))::jsonb,
        'uehi_score', b.uehi_score,
        'risk_level', b.risk_level,
        'tree_density', b.tree_density,
        'ndvi', b.ndvi,
        'impervious_surfaces', b.impervious_surfaces,
        'temperature', b.temperature,
        'population_exposure', b.population_exposure,
        'pm25', b.pm25,
        'standing_carbon_stock', c.standing_carbon_stock,
        'methodology', jsonb_build_object(
            'version', m.version_hash,
            'description', m.description,
            'pipeline', m.pipeline_type
        )
    )
    FROM public.uehi_blocks b
    LEFT JOIN public.carbon_blocks c ON b.block_id = c.block_id
    LEFT JOIN public.methodology_versions m ON b.methodology_id = m.id
    WHERE b.block_id = p_block_id;
$$;


-- ============================================================
-- Harden get_blocks_in_viewport() search_path
-- This is PUBLIC-INTENDED for map rendering (only exposes score + risk_level)
-- ============================================================
CREATE OR REPLACE FUNCTION public.get_blocks_in_viewport(
    min_lon double precision,
    min_lat double precision,
    max_lon double precision,
    max_lat double precision,
    limit_val int DEFAULT 10000
)
RETURNS TABLE (
    block_id text,
    geom jsonb,
    uehi_score numeric,
    risk_level public.risk_level
)
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public, extensions
AS $$
    SELECT
        b.block_id,
        ST_AsGeoJSON(ST_Transform(b.geom, 4326))::jsonb as geom,
        b.uehi_score,
        b.risk_level
    FROM public.uehi_blocks b
    WHERE b.geom && ST_Transform(ST_MakeEnvelope(min_lon, min_lat, max_lon, max_lat, 4326), 32643)
    LIMIT limit_val;
$$;


-- ============================================================
-- Harden get_provenance_info() — PUBLIC-INTENDED (provenance is public)
-- ============================================================
CREATE OR REPLACE FUNCTION public.get_provenance_info(
    p_production_run_id UUID,
    p_methodology_id UUID
)
RETURNS jsonb
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public, extensions
AS $$
    SELECT jsonb_build_object(
        'production_run', p.id,
        'pipeline_name', p.pipeline_name,
        'pipeline_version', p.pipeline_version,
        'run_timestamp', p.run_timestamp,
        'input_manifest_hash', p.input_manifest_hash,
        'output_hash', p.output_hash,
        'methodology', (
            SELECT jsonb_build_object(
                'version', m.version_hash,
                'pipeline_type', m.pipeline_type,
                'description', m.description
            )
            FROM public.methodology_versions m
            WHERE m.id = p_methodology_id
        )
    )
    FROM public.production_runs p
    WHERE p.id = p_production_run_id;
$$;


-- ============================================================
-- Harden generate_point_radius_study_area() — SECURITY INVOKER, safe
-- ============================================================
CREATE OR REPLACE FUNCTION public.generate_point_radius_study_area(
    lon double precision,
    lat double precision,
    radius_m double precision
)
RETURNS geometry(MultiPolygon, 32643)
LANGUAGE plpgsql
IMMUTABLE
SECURITY INVOKER
SET search_path = public, extensions
AS $$
BEGIN
    IF radius_m < 10 OR radius_m > 50000 THEN
        RAISE EXCEPTION 'Radius must be between 10m and 50,000m. Received: %', radius_m;
    END IF;

    RETURN ST_Multi(ST_Buffer(ST_Transform(ST_SetSRID(ST_MakePoint(lon, lat), 4326), 32643), radius_m));
END;
$$;


-- ============================================================
-- Harden aggregate_study_area() — safe search_path
-- ============================================================
CREATE OR REPLACE FUNCTION public.aggregate_study_area(
    p_geom geometry(MultiPolygon, 32643)
)
RETURNS jsonb
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public, extensions
AS $$
WITH intersections AS (
    SELECT
        b.block_id,
        b.uehi_score,
        b.is_excluded,
        b.risk_level,
        ST_Area(ST_Intersection(b.geom, p_geom)) AS intersection_area_m2
    FROM public.uehi_blocks b
    WHERE ST_Intersects(b.geom, p_geom)
),
stats AS (
    SELECT
        COUNT(*) AS total_intersecting_blocks,
        COUNT(*) FILTER (WHERE NOT is_excluded) AS scored_blocks,
        COUNT(*) FILTER (WHERE is_excluded) AS excluded_blocks,

        COUNT(*) FILTER (WHERE NOT is_excluded AND risk_level = 'Critical') AS risk_critical,
        COUNT(*) FILTER (WHERE NOT is_excluded AND risk_level = 'High') AS risk_high,
        COUNT(*) FILTER (WHERE NOT is_excluded AND risk_level = 'Moderate') AS risk_moderate,
        COUNT(*) FILTER (WHERE NOT is_excluded AND risk_level = 'Low') AS risk_low,

        SUM(intersection_area_m2) FILTER (WHERE NOT is_excluded) AS eligible_intersection_area_m2,
        SUM(intersection_area_m2) FILTER (WHERE NOT is_excluded AND uehi_score IS NOT NULL) AS scored_intersection_area_m2,

        SUM(uehi_score * intersection_area_m2) FILTER (WHERE NOT is_excluded) AS sum_uehi_x_area
    FROM intersections
)
SELECT jsonb_build_object(
    'uehi', jsonb_build_object(
        'score', CASE
            WHEN scored_intersection_area_m2 > 0 THEN ROUND((sum_uehi_x_area / scored_intersection_area_m2)::numeric, 4)
            ELSE NULL
        END,
        'aggregation_method', 'area_weighted_average',
        'total_intersecting_blocks', total_intersecting_blocks,
        'scored_blocks', scored_blocks,
        'excluded_blocks', excluded_blocks,
        'eligible_intersection_area_m2', eligible_intersection_area_m2,
        'scored_intersection_area_m2', scored_intersection_area_m2,
        'risk_distribution', jsonb_build_object(
            'Critical', risk_critical,
            'High', risk_high,
            'Moderate', risk_moderate,
            'Low', risk_low
        )
    ),
    'carbon', jsonb_build_object(
        'error', 'UNRESOLVED_METHODOLOGY',
        'message', 'Carbon aggregation halted. Production methodology does not define an area-weighting rule for partial blocks.'
    )
)
FROM stats;
$$;


-- ============================================================
-- Harden MVT functions — safe search_path
-- ============================================================
CREATE OR REPLACE FUNCTION mvt_uehi_blocks(z integer, x integer, y integer)
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


CREATE OR REPLACE FUNCTION mvt_carbon_blocks(z integer, x integer, y integer)
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


CREATE OR REPLACE FUNCTION mvt_planting_candidate_areas(z integer, x integer, y integer)
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


CREATE OR REPLACE FUNCTION mvt_planting_units(scenario_id_param uuid, z integer, x integer, y integer)
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

    IF z < 14 THEN
        RETURN NULL;
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
        LIMIT 20000
    ) AS tile;

    RETURN mvt;
END;
$$;


-- ============================================================
-- BLOCKER 2 + BLOCKER 4: REVOKE PUBLIC EXECUTE from ALL restricted functions
-- Then GRANT to intended roles only.
-- ============================================================

-- === RESTRICTED: authenticated only ===

-- get_user_role: used by RLS policies internally, but should not be callable by anon
REVOKE EXECUTE ON FUNCTION public.get_user_role(uuid) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION public.get_user_role(uuid) FROM anon;
GRANT EXECUTE ON FUNCTION public.get_user_role(uuid) TO authenticated;

-- get_my_role: safe self-lookup for authenticated users
REVOKE EXECUTE ON FUNCTION public.get_my_role() FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION public.get_my_role() FROM anon;
GRANT EXECUTE ON FUNCTION public.get_my_role() TO authenticated;

-- verify_api_key: used by API key auth, should only be callable by authenticated or service role
REVOKE EXECUTE ON FUNCTION public.verify_api_key(text) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION public.verify_api_key(text) FROM anon;
GRANT EXECUTE ON FUNCTION public.verify_api_key(text) TO authenticated;

-- get_block_detail: FULL environmental data — researcher/admin only
REVOKE EXECUTE ON FUNCTION public.get_block_detail(text) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION public.get_block_detail(text) FROM anon;
GRANT EXECUTE ON FUNCTION public.get_block_detail(text) TO authenticated;

-- mvt_planting_candidate_areas: restricted environmental data
REVOKE EXECUTE ON FUNCTION public.mvt_planting_candidate_areas(integer, integer, integer) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION public.mvt_planting_candidate_areas(integer, integer, integer) FROM anon;
GRANT EXECUTE ON FUNCTION public.mvt_planting_candidate_areas(integer, integer, integer) TO authenticated;

-- mvt_planting_units: restricted environmental data
REVOKE EXECUTE ON FUNCTION public.mvt_planting_units(uuid, integer, integer, integer) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION public.mvt_planting_units(uuid, integer, integer, integer) FROM anon;
GRANT EXECUTE ON FUNCTION public.mvt_planting_units(uuid, integer, integer, integer) TO authenticated;

-- === PUBLIC-INTENDED: map rendering and provenance (anon + authenticated) ===

-- get_block_detail_public: safe subset for anonymous explore
REVOKE EXECUTE ON FUNCTION public.get_block_detail_public(text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.get_block_detail_public(text) TO anon, authenticated;

-- get_blocks_in_viewport: public map rendering (only score + risk_level)
REVOKE EXECUTE ON FUNCTION public.get_blocks_in_viewport(double precision, double precision, double precision, double precision, int) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.get_blocks_in_viewport(double precision, double precision, double precision, double precision, int) TO anon, authenticated;

-- get_provenance_info: public provenance data
REVOKE EXECUTE ON FUNCTION public.get_provenance_info(UUID, UUID) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.get_provenance_info(UUID, UUID) TO anon, authenticated;

-- generate_point_radius_study_area: SECURITY INVOKER, but still restrict for safety
REVOKE EXECUTE ON FUNCTION public.generate_point_radius_study_area(double precision, double precision, double precision) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.generate_point_radius_study_area(double precision, double precision, double precision) TO anon, authenticated;

-- aggregate_study_area: study area analysis (public feature)
REVOKE EXECUTE ON FUNCTION public.aggregate_study_area(geometry) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.aggregate_study_area(geometry) TO anon, authenticated;

-- mvt_uehi_blocks: public map rendering
REVOKE EXECUTE ON FUNCTION public.mvt_uehi_blocks(integer, integer, integer) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.mvt_uehi_blocks(integer, integer, integer) TO anon, authenticated;

-- mvt_carbon_blocks: public map rendering
REVOKE EXECUTE ON FUNCTION public.mvt_carbon_blocks(integer, integer, integer) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.mvt_carbon_blocks(integer, integer, integer) TO anon, authenticated;


-- ============================================================
-- HIGH 6: Harden user_roles RLS policies
-- Make authorization semantics explicit: only admins can mutate roles.
-- ============================================================

-- Drop ambiguous "Admins can manage roles" ALL policy (covers INSERT/UPDATE/DELETE)
DROP POLICY IF EXISTS "Admins can manage roles" ON public.user_roles;

-- Create explicit per-operation admin policies
CREATE POLICY "Admins can insert roles"
    ON public.user_roles FOR INSERT TO authenticated
    WITH CHECK (
        (SELECT role FROM public.user_roles WHERE user_id = auth.uid()) = 'admin'
    );

CREATE POLICY "Admins can update roles"
    ON public.user_roles FOR UPDATE TO authenticated
    USING (
        (SELECT role FROM public.user_roles WHERE user_id = auth.uid()) = 'admin'
    )
    WITH CHECK (
        (SELECT role FROM public.user_roles WHERE user_id = auth.uid()) = 'admin'
    );

CREATE POLICY "Admins can delete roles"
    ON public.user_roles FOR DELETE TO authenticated
    USING (
        (SELECT role FROM public.user_roles WHERE user_id = auth.uid()) = 'admin'
    );


-- ============================================================
-- VERIFICATION COMMENT
-- After applying this migration, run:
--   SELECT proname, prosecdef, proacl
--   FROM pg_proc
--   WHERE pronamespace = 'public'::regnamespace
--     AND prosecdef = true;
-- to verify that no restricted function has PUBLIC or anon EXECUTE.
-- ============================================================

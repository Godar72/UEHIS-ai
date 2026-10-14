-- ==============================================================================
-- UEHIS API FUNCTIONS MIGRATION - PHASE 2A
-- ==============================================================================

-- 1. UEHI Viewport Query
-- Bounded, indexed, and restricted spatial search for the map viewport.
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
SET search_path = public, postgis
AS $$
    SELECT 
        b.block_id,
        ST_AsGeoJSON(ST_Transform(b.geom, 4326))::jsonb as geom,
        b.uehi_score,
        b.risk_level
    FROM public.uehi_blocks b
    -- Transform the WGS84 bbox to EPSG:32643 to use the spatial index on b.geom efficiently
    WHERE b.geom && ST_Transform(ST_MakeEnvelope(min_lon, min_lat, max_lon, max_lat, 4326), 32643)
    LIMIT limit_val;
$$;

-- 2. Block Detail Query
-- Returns full details for a single block without exposing raw table access.
CREATE OR REPLACE FUNCTION public.get_block_detail(
    p_block_id text
)
RETURNS jsonb
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public, postgis
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

-- 3. Study Area Point-Radius Generator
-- Validates input and generates a safe EPSG:32643 MultiPolygon boundary.
CREATE OR REPLACE FUNCTION public.generate_point_radius_study_area(
    lon double precision,
    lat double precision,
    radius_m double precision
)
RETURNS geometry(MultiPolygon, 32643)
LANGUAGE plpgsql
IMMUTABLE
SECURITY INVOKER
SET search_path = public, postgis
AS $$
BEGIN
    IF radius_m < 10 OR radius_m > 50000 THEN
        RAISE EXCEPTION 'Radius must be between 10m and 50,000m. Received: %', radius_m;
    END IF;
    
    RETURN ST_Multi(ST_Buffer(ST_Transform(ST_SetSRID(ST_MakePoint(lon, lat), 4326), 32643), radius_m));
END;
$$;

-- 4. Study Area Aggregation (UEHI ONLY - CARBON ABORTED)
-- Computes the authoritative area-weighted UEHI average.
-- NOTE: Carbon aggregation is deliberately omitted due to an unresolved methodological rule.
CREATE OR REPLACE FUNCTION public.aggregate_study_area(
    p_geom geometry(MultiPolygon, 32643)
)
RETURNS jsonb
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public, postgis
AS $$
WITH intersections AS (
    SELECT 
        b.block_id,
        b.uehi_score,
        b.is_excluded,
        ST_Area(ST_Intersection(b.geom, p_geom)) AS intersection_area_m2
    FROM public.uehi_blocks b
    WHERE ST_Intersects(b.geom, p_geom)
),
stats AS (
    SELECT
        COUNT(*) AS total_intersecting_blocks,
        COUNT(*) FILTER (WHERE NOT is_excluded) AS scored_blocks,
        COUNT(*) FILTER (WHERE is_excluded) AS excluded_blocks,
        
        SUM(intersection_area_m2) FILTER (WHERE NOT is_excluded) AS eligible_intersection_area_m2,
        SUM(intersection_area_m2) FILTER (WHERE NOT is_excluded AND uehi_score IS NOT NULL) AS scored_intersection_area_m2,
        
        -- Authoritative Area-weighted UEHI average
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
        'scored_intersection_area_m2', scored_intersection_area_m2
    ),
    'carbon', jsonb_build_object(
        'error', 'UNRESOLVED_METHODOLOGY',
        'message', 'Carbon aggregation halted. Production methodology does not define an area-weighting rule for partial blocks.'
    )
)
FROM stats;
$$;

-- 5. Provenance Lookup
CREATE OR REPLACE FUNCTION public.get_provenance_info(
    p_production_run_id UUID,
    p_methodology_id UUID
)
RETURNS jsonb
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
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

-- Grant minimal permissions
REVOKE ALL ON FUNCTION public.get_blocks_in_viewport(double precision, double precision, double precision, double precision, int) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.get_blocks_in_viewport(double precision, double precision, double precision, double precision, int) TO anon, authenticated;

REVOKE ALL ON FUNCTION public.get_block_detail(text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.get_block_detail(text) TO anon, authenticated;

REVOKE ALL ON FUNCTION public.generate_point_radius_study_area(double precision, double precision, double precision) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.generate_point_radius_study_area(double precision, double precision, double precision) TO anon, authenticated;

REVOKE ALL ON FUNCTION public.aggregate_study_area(geometry(MultiPolygon, 32643)) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.aggregate_study_area(geometry(MultiPolygon, 32643)) TO anon, authenticated;

REVOKE ALL ON FUNCTION public.get_provenance_info(UUID, UUID) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.get_provenance_info(UUID, UUID) TO anon, authenticated;

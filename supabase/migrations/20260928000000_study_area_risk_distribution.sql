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

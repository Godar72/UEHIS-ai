-- ==============================================================================
-- UEHIS MIGRATION: USER PROFILES & RESEARCH ACTIVITY DASHBOARD
-- 20261017000000_user_profiles_and_activity.sql
--
-- 1. public.user_profiles: Stores editable display names & preferences.
-- 2. public.user_activity: Stores persistent immutable research & audit logs.
-- 3. Hardened RLS policies ensuring users access strictly their own data.
-- 4. Centralized RPC functions with SECURITY DEFINER and empty search_path.
-- ==============================================================================

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ------------------------------------------------------------------------------
-- 1. USER PROFILES TABLE
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.user_profiles (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    display_name text NOT NULL CHECK (char_length(trim(display_name)) >= 2 AND char_length(trim(display_name)) <= 50),
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now(),
    CONSTRAINT unique_user_profile UNIQUE (user_id)
);

ALTER TABLE public.user_profiles ENABLE ROW LEVEL SECURITY;

-- Policies for user_profiles
DROP POLICY IF EXISTS "Users can view their own profile" ON public.user_profiles;
CREATE POLICY "Users can view their own profile" 
    ON public.user_profiles 
    FOR SELECT 
    TO authenticated 
    USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can insert their own profile" ON public.user_profiles;
CREATE POLICY "Users can insert their own profile" 
    ON public.user_profiles 
    FOR INSERT 
    TO authenticated 
    WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can update their own profile" ON public.user_profiles;
CREATE POLICY "Users can update their own profile" 
    ON public.user_profiles 
    FOR UPDATE 
    TO authenticated 
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- Restrict anon & public
REVOKE ALL ON TABLE public.user_profiles FROM anon, PUBLIC;
GRANT SELECT, INSERT, UPDATE ON TABLE public.user_profiles TO authenticated;

-- ------------------------------------------------------------------------------
-- 2. USER RESEARCH ACTIVITY TABLE
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.user_activity (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    activity_type text NOT NULL CHECK (activity_type IN (
        'viewed_block', 
        'analyzed_study_area', 
        'viewed_carbon', 
        'viewed_scenario', 
        'viewed_planting_opportunity', 
        'exported_report', 
        'research_saved'
    )),
    category text NOT NULL CHECK (category IN ('explore', 'carbon', 'analysis', 'planting')),
    action_type text NOT NULL DEFAULT 'viewed' CHECK (action_type IN ('viewed', 'analyzed', 'saved', 'exported')),
    title text NOT NULL,
    description text,
    entity_type text CHECK (entity_type IN ('block', 'study_area', 'ward', 'scenario', 'planting_unit', 'report', 'session')),
    entity_id text,
    metadata jsonb DEFAULT '{}'::jsonb,
    created_at timestamptz DEFAULT now()
);

-- Optimize queries for user timeline, category filtering, and deduplication
CREATE INDEX IF NOT EXISTS idx_user_activity_user_created 
    ON public.user_activity (user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_user_activity_category 
    ON public.user_activity (user_id, category, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_user_activity_dedup 
    ON public.user_activity (user_id, activity_type, entity_id, created_at DESC);

ALTER TABLE public.user_activity ENABLE ROW LEVEL SECURITY;

-- Policy: Users can strictly read only their own activity
DROP POLICY IF EXISTS "Users can read own activity" ON public.user_activity;
CREATE POLICY "Users can read own activity" 
    ON public.user_activity 
    FOR SELECT 
    TO authenticated 
    USING (auth.uid() = user_id);

-- Explicit privilege boundary: Revoke direct client mutations on activity log
REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON TABLE public.user_activity FROM anon, authenticated, PUBLIC;
GRANT SELECT ON TABLE public.user_activity TO authenticated;

-- ------------------------------------------------------------------------------
-- 3. SECURE PROFILE UPDATE RPC
-- ------------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.update_my_profile(
    p_display_name text
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
    v_caller_id uuid;
    v_trimmed text;
BEGIN
    v_caller_id := auth.uid();
    IF v_caller_id IS NULL THEN
        RAISE EXCEPTION 'Authentication required: caller must be authenticated'
            USING ERRCODE = '42501';
    END IF;

    v_trimmed := pg_catalog.btrim(p_display_name);
    IF v_trimmed IS NULL OR pg_catalog.char_length(v_trimmed) < 2 OR pg_catalog.char_length(v_trimmed) > 50 THEN
        RAISE EXCEPTION 'Invalid display name: must be between 2 and 50 characters'
            USING ERRCODE = '22023';
    END IF;

    INSERT INTO public.user_profiles (user_id, display_name, updated_at)
    VALUES (v_caller_id, v_trimmed, pg_catalog.now())
    ON CONFLICT (user_id)
    DO UPDATE SET 
        display_name = EXCLUDED.display_name,
        updated_at = pg_catalog.now();

    RETURN pg_catalog.jsonb_build_object(
        'success', true,
        'user_id', v_caller_id,
        'display_name', v_trimmed
    );
END;
$$;

ALTER FUNCTION public.update_my_profile(text) OWNER TO postgres;
REVOKE ALL ON FUNCTION public.update_my_profile(text) FROM anon, PUBLIC;
GRANT EXECUTE ON FUNCTION public.update_my_profile(text) TO authenticated;

-- ------------------------------------------------------------------------------
-- 4. SECURE ACTIVITY RECORDING RPC WITH DEDUPLICATION & PRIVILEGE CHECKS
-- ------------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.record_user_activity(
    p_activity_type text,
    p_category text,
    p_action_type text,
    p_title text,
    p_description text DEFAULT NULL,
    p_entity_type text DEFAULT NULL,
    p_entity_id text DEFAULT NULL,
    p_metadata jsonb DEFAULT '{}'::jsonb
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
    v_caller_id uuid;
    v_caller_role text;
    v_recent_id uuid;
    v_new_id uuid;
BEGIN
    v_caller_id := auth.uid();
    IF v_caller_id IS NULL THEN
        RAISE EXCEPTION 'Authentication required: caller must be authenticated'
            USING ERRCODE = '42501';
    END IF;

    -- Validate role if attempting planting-related activity
    IF p_category = 'planting' OR p_activity_type = 'viewed_planting_opportunity' THEN
        SELECT role INTO v_caller_role
        FROM public.user_roles
        WHERE user_id = v_caller_id;

        IF v_caller_role IS NULL OR v_caller_role NOT IN ('researcher', 'admin') THEN
            RAISE EXCEPTION 'Authorization denied: planting activities restricted to researchers or administrators'
                USING ERRCODE = '42501';
        END IF;
    END IF;

    -- Deduplication: if identical user, activity_type, and entity_id occurred in last 60s, update timestamp
    IF p_entity_id IS NOT NULL THEN
        SELECT id INTO v_recent_id
        FROM public.user_activity
        WHERE user_id = v_caller_id
          AND activity_type = p_activity_type
          AND entity_id = p_entity_id
          AND created_at > (pg_catalog.now() - INTERVAL '60 seconds')
        ORDER BY created_at DESC
        LIMIT 1;

        IF v_recent_id IS NOT NULL THEN
            UPDATE public.user_activity
            SET created_at = pg_catalog.now()
            WHERE id = v_recent_id;

            RETURN pg_catalog.jsonb_build_object(
                'success', true,
                'deduplicated', true,
                'id', v_recent_id
            );
        END IF;
    END IF;

    -- Insert new verified activity record
    INSERT INTO public.user_activity (
        user_id,
        activity_type,
        category,
        action_type,
        title,
        description,
        entity_type,
        entity_id,
        metadata,
        created_at
    )
    VALUES (
        v_caller_id,
        p_activity_type,
        p_category,
        p_action_type,
        p_title,
        p_description,
        p_entity_type,
        p_entity_id,
        p_metadata,
        pg_catalog.now()
    )
    RETURNING id INTO v_new_id;

    RETURN pg_catalog.jsonb_build_object(
        'success', true,
        'deduplicated', false,
        'id', v_new_id
    );
END;
$$;

ALTER FUNCTION public.record_user_activity(text, text, text, text, text, text, text, jsonb) OWNER TO postgres;
REVOKE ALL ON FUNCTION public.record_user_activity(text, text, text, text, text, text, text, jsonb) FROM anon, PUBLIC;
GRANT EXECUTE ON FUNCTION public.record_user_activity(text, text, text, text, text, text, text, jsonb) TO authenticated;

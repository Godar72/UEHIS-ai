-- Migration: 20261009000000_auth_rbac_api_keys.sql

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- 1. Create Roles Table
CREATE TABLE public.user_roles (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid REFERENCES auth.users(id) ON DELETE CASCADE,
    role text NOT NULL CHECK (role IN ('public', 'researcher', 'admin')),
    created_at timestamptz DEFAULT now(),
    CONSTRAINT unique_user_role UNIQUE (user_id)
);

-- Enable RLS on user_roles
ALTER TABLE public.user_roles ENABLE ROW LEVEL SECURITY;

-- Helper function to check roles
CREATE OR REPLACE FUNCTION public.get_user_role(uid uuid)
RETURNS text
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT role FROM public.user_roles WHERE user_id = uid;
$$;

-- Policies for user_roles
CREATE POLICY "Users can view their own role" ON public.user_roles FOR SELECT TO authenticated USING (auth.uid() = user_id);
CREATE POLICY "Admins can view all roles" ON public.user_roles FOR SELECT TO authenticated USING (public.get_user_role(auth.uid()) = 'admin');
CREATE POLICY "Admins can manage roles" ON public.user_roles FOR ALL TO authenticated USING (public.get_user_role(auth.uid()) = 'admin');

-- 2. Create API Keys Table
CREATE TABLE public.api_keys (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid REFERENCES auth.users(id) ON DELETE CASCADE,
    name text NOT NULL,
    key_prefix text NOT NULL,
    hashed_key text NOT NULL,
    created_at timestamptz DEFAULT now(),
    expires_at timestamptz,
    revoked_at timestamptz,
    last_used_at timestamptz
);

ALTER TABLE public.api_keys ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own API keys" ON public.api_keys FOR SELECT TO authenticated USING (auth.uid() = user_id);
CREATE POLICY "Users can manage their own API keys" ON public.api_keys FOR ALL TO authenticated USING (auth.uid() = user_id);
CREATE POLICY "Admins can manage all API keys" ON public.api_keys FOR ALL TO authenticated USING (public.get_user_role(auth.uid()) = 'admin');

-- 3. Update Policies on Environmental Tables
-- Drop all existing public select policies
DROP POLICY IF EXISTS "Public select on data_sources" ON data_sources;
DROP POLICY IF EXISTS "Public select on methodology_versions" ON methodology_versions;
DROP POLICY IF EXISTS "Public select on production_runs" ON production_runs;
DROP POLICY IF EXISTS "Public select on uehi_blocks" ON uehi_blocks;
DROP POLICY IF EXISTS "Public select on carbon_blocks" ON carbon_blocks;
DROP POLICY IF EXISTS "Public select on planting_scenarios" ON planting_scenarios;

-- We want metadata tables to remain public so the app can display provenance info.
CREATE POLICY "Public select on data_sources" ON data_sources FOR SELECT TO public USING (true);
CREATE POLICY "Public select on methodology_versions" ON methodology_versions FOR SELECT TO public USING (true);
CREATE POLICY "Public select on production_runs" ON production_runs FOR SELECT TO public USING (true);
CREATE POLICY "Public select on planting_scenarios" ON planting_scenarios FOR SELECT TO public USING (true);

-- Restricted tables
CREATE POLICY "Restricted select on uehi_blocks" ON uehi_blocks FOR SELECT TO authenticated USING (public.get_user_role(auth.uid()) IN ('researcher', 'admin'));
CREATE POLICY "Restricted select on carbon_blocks" ON carbon_blocks FOR SELECT TO authenticated USING (public.get_user_role(auth.uid()) IN ('researcher', 'admin'));
CREATE POLICY "Restricted select on planting_candidate_areas" ON planting_candidate_areas FOR SELECT TO authenticated USING (public.get_user_role(auth.uid()) IN ('researcher', 'admin'));
CREATE POLICY "Restricted select on planting_units" ON planting_units FOR SELECT TO authenticated USING (public.get_user_role(auth.uid()) IN ('researcher', 'admin'));
CREATE POLICY "Restricted select on planting_scenario_units" ON planting_scenario_units FOR SELECT TO authenticated USING (public.get_user_role(auth.uid()) IN ('researcher', 'admin'));

-- 4. API Key Verification Helper
CREATE OR REPLACE FUNCTION public.verify_api_key(p_key text)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_key_record record;
    v_hash text;
BEGIN
    v_hash := encode(digest(p_key, 'sha256'), 'hex');
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

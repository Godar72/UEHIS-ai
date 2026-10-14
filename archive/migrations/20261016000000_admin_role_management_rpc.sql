-- ==============================================================================
-- UEHIS MIGRATION: SECURE ADMIN ROLE MANAGEMENT RPC (OPTION B)
-- 20261016000000_admin_role_management_rpc.sql
--
-- Dedicated administrative RPC: public.admin_set_user_role(target_user_id, new_role)
-- Hardened SECURITY DEFINER function with empty search_path,
-- shared transaction-level advisory locking for concurrency serialization,
-- caller authorization, self-demotion prevention, defensive last-admin check,
-- atomic upsert, and explicit privilege boundary revoking direct mutations.
-- ==============================================================================

DROP FUNCTION IF EXISTS public.admin_set_user_role(uuid, text);

CREATE OR REPLACE FUNCTION public.admin_set_user_role(
    target_user_id uuid,
    new_role text
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
    v_caller_id uuid;
    v_caller_role text;
    v_target_current_role text;
    v_admin_count bigint;
BEGIN
    -- 1. Shared transaction-level advisory lock to serialize role modifications.
    -- Dedicated lock key (842210001) shared across all admin_set_user_role invocations.
    -- Automatically released at transaction commit or rollback.
    PERFORM pg_catalog.pg_advisory_xact_lock(842210001);

    -- 2. Validate authenticated caller
    v_caller_id := auth.uid();
    IF v_caller_id IS NULL THEN
        RAISE EXCEPTION 'Authentication required: caller must be authenticated'
            USING ERRCODE = '42501';
    END IF;

    -- 3. Validate caller administrator authorization
    SELECT role INTO v_caller_role
    FROM public.user_roles
    WHERE user_id = v_caller_id;

    IF v_caller_role IS NULL OR v_caller_role <> 'admin' THEN
        RAISE EXCEPTION 'Authorization denied: administrator privileges required'
            USING ERRCODE = '42501';
    END IF;

    -- 4. Target user validation: non-null target UUID
    IF target_user_id IS NULL THEN
        RAISE EXCEPTION 'Target user ID cannot be null'
            USING ERRCODE = '22023';
    END IF;

    -- 5. Role value validation: accept only public, researcher, and admin
    IF new_role IS NULL OR new_role NOT IN ('public', 'researcher', 'admin') THEN
        RAISE EXCEPTION 'Invalid role: %, allowed roles are public, researcher, or admin', new_role
            USING ERRCODE = '22023';
    END IF;

    -- 6. Self-modification denial: reject attempts by caller to alter own role
    IF target_user_id = v_caller_id THEN
        RAISE EXCEPTION 'Self-modification denied: administrators cannot alter or demote their own role'
            USING ERRCODE = '42501';
    END IF;

    -- 7. Validate target user exists in auth.users
    IF NOT EXISTS (
        SELECT 1
        FROM auth.users
        WHERE id = target_user_id
    ) THEN
        RAISE EXCEPTION 'Target user not found: user does not exist in auth.users'
            USING ERRCODE = 'P0002';
    END IF;

    -- 8. Defensive last-administrator check:
    -- If demoting a user whose current role is admin, ensure another administrator remains
    SELECT role INTO v_target_current_role
    FROM public.user_roles
    WHERE user_id = target_user_id;

    IF v_target_current_role = 'admin' AND new_role <> 'admin' THEN
        SELECT pg_catalog.count(*) INTO v_admin_count
        FROM public.user_roles
        WHERE role = 'admin';

        IF v_admin_count <= 1 THEN
            RAISE EXCEPTION 'Cannot demote the last remaining administrator'
                USING ERRCODE = '22023';
        END IF;
    END IF;

    -- 9. Atomic insert/update using existing unique constraint on user_id
    INSERT INTO public.user_roles (user_id, role)
    VALUES (target_user_id, new_role)
    ON CONFLICT (user_id)
    DO UPDATE SET role = EXCLUDED.role;

    -- 10. Minimal success result
    RETURN pg_catalog.jsonb_build_object(
        'success', true,
        'user_id', target_user_id,
        'role', new_role
    );
END;
$$;

-- Ensure function ownership matches local Supabase convention
ALTER FUNCTION public.admin_set_user_role(uuid, text) OWNER TO postgres;

-- Privilege Boundary Enforcement:
-- 1. Revoke direct mutations on public.user_roles from authenticated, anon, and PUBLIC
REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON TABLE public.user_roles FROM authenticated, anon, PUBLIC;

-- 2. Revoke execute on admin_set_user_role from PUBLIC and anon
REVOKE ALL ON FUNCTION public.admin_set_user_role(uuid, text) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.admin_set_user_role(uuid, text) FROM anon;

-- 3. Grant execute to authenticated (caller must be an authenticated admin to proceed past internal check)
GRANT EXECUTE ON FUNCTION public.admin_set_user_role(uuid, text) TO authenticated;

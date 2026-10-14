-- ==============================================================================
-- UEHIS MIGRATION: DISTRIBUTED & ATOMIC RATE LIMITING
-- 20261018000000_auth_rate_limiting.sql
--
-- Provides concurrency-safe atomic counters in PostgreSQL for multi-instance
-- production protection, account-aware login protection, and network flood defense.
-- ==============================================================================

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- 1. Table for rate limit counters
CREATE TABLE IF NOT EXISTS public.auth_rate_limits (
    key text PRIMARY KEY,
    count integer NOT NULL DEFAULT 1,
    created_at timestamptz NOT NULL DEFAULT now(),
    expires_at timestamptz NOT NULL
);

-- Optimize queries on expiration
CREATE INDEX IF NOT EXISTS idx_auth_rate_limits_expires_at 
    ON public.auth_rate_limits (expires_at);

-- Restrict direct client access
REVOKE ALL ON TABLE public.auth_rate_limits FROM anon, authenticated, PUBLIC;
GRANT ALL ON TABLE public.auth_rate_limits TO service_role;

-- 2. Atomic check-and-increment function
CREATE OR REPLACE FUNCTION public.check_rate_limit_atomic(
    p_key text,
    p_limit int,
    p_window_seconds int
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, extensions
AS $$
DECLARE
    v_now timestamptz := now();
    v_rec public.auth_rate_limits%ROWTYPE;
    v_retry_after int;
BEGIN
    -- Delete if expired
    DELETE FROM public.auth_rate_limits WHERE key = p_key AND expires_at < v_now;

    -- Upsert atomic counter
    INSERT INTO public.auth_rate_limits (key, count, created_at, expires_at)
    VALUES (p_key, 1, v_now, v_now + (p_window_seconds || ' seconds')::interval)
    ON CONFLICT (key) DO UPDATE
    SET count = public.auth_rate_limits.count + 1
    RETURNING * INTO v_rec;

    IF v_rec.count > p_limit THEN
        v_retry_after := GREATEST(1, EXTRACT(EPOCH FROM (v_rec.expires_at - v_now))::int);
        RETURN jsonb_build_object(
            'allowed', false,
            'remaining', 0,
            'retry_after_seconds', v_retry_after
        );
    ELSE
        RETURN jsonb_build_object(
            'allowed', true,
            'remaining', p_limit - v_rec.count,
            'retry_after_seconds', 0
        );
    END IF;
END;
$$;

-- 3. Non-incrementing status check (peeking active lockout)
CREATE OR REPLACE FUNCTION public.get_rate_limit_status(
    p_key text,
    p_limit int
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, extensions
AS $$
DECLARE
    v_now timestamptz := now();
    v_rec public.auth_rate_limits%ROWTYPE;
BEGIN
    SELECT * INTO v_rec FROM public.auth_rate_limits WHERE key = p_key;
    IF NOT FOUND OR v_rec.expires_at < v_now THEN
        RETURN jsonb_build_object(
            'allowed', true,
            'remaining', p_limit,
            'retry_after_seconds', 0
        );
    END IF;

    IF v_rec.count >= p_limit THEN
        RETURN jsonb_build_object(
            'allowed', false,
            'remaining', 0,
            'retry_after_seconds', GREATEST(1, EXTRACT(EPOCH FROM (v_rec.expires_at - v_now))::int)
        );
    ELSE
        RETURN jsonb_build_object(
            'allowed', true,
            'remaining', p_limit - v_rec.count,
            'retry_after_seconds', 0
        );
    END IF;
END;
$$;

-- 4. Atomic reset function (wiping key on successful auth)
CREATE OR REPLACE FUNCTION public.reset_rate_limit_atomic(p_key text)
RETURNS void
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$
    DELETE FROM public.auth_rate_limits WHERE key = p_key;
$$;

-- Secure execution privileges
REVOKE ALL ON FUNCTION public.check_rate_limit_atomic(text, int, int) FROM anon, authenticated, PUBLIC;
GRANT EXECUTE ON FUNCTION public.check_rate_limit_atomic(text, int, int) TO service_role;

REVOKE ALL ON FUNCTION public.get_rate_limit_status(text, int) FROM anon, authenticated, PUBLIC;
GRANT EXECUTE ON FUNCTION public.get_rate_limit_status(text, int) TO service_role;

REVOKE ALL ON FUNCTION public.reset_rate_limit_atomic(text) FROM anon, authenticated, PUBLIC;
GRANT EXECUTE ON FUNCTION public.reset_rate_limit_atomic(text) TO service_role;

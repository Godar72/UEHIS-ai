/**
 * UEHIS Rate Limiter — Atomic Distributed & Process-Local Rate Limiting.
 *
 * Provides:
 * 1. Synchronous process-local sliding-window rate limiting for fast/unit-test use.
 * 2. Distributed, atomic PostgreSQL-backed rate limiting for multi-instance production.
 * 3. Strict endpoint-level key namespacing to eliminate cross-endpoint bucket collisions.
 * 4. Account-aware and network-aware protection to prevent university IP lockouts.
 * 5. Accurate Retry-After header & JSON payload generation.
 */

import { createAdminClient } from '@/lib/supabase/admin';

interface RateLimitRecord {
  count: number;
  expiresAt: number;
}

const requestCounts = new Map<string, RateLimitRecord>();

/**
 * Check if a request is within the rate limit for a given key (in-memory).
 * @param key - Unique namespaced identifier
 * @param limit - Maximum number of requests allowed in the window
 * @param windowMs - Time window in milliseconds
 * @returns Object with `allowed` boolean, `remaining` count, and `retryAfterMs`
 */
export function checkRateLimit(
  key: string,
  limit: number,
  windowMs: number
): { allowed: boolean; remaining: number; retryAfterMs: number } {
  const now = Date.now();
  const record = requestCounts.get(key);

  if (!record || record.expiresAt < now) {
    requestCounts.set(key, { count: 1, expiresAt: now + windowMs });
    return { allowed: true, remaining: limit - 1, retryAfterMs: 0 };
  }

  if (record.count >= limit) {
    return {
      allowed: false,
      remaining: 0,
      retryAfterMs: Math.max(0, record.expiresAt - now),
    };
  }

  record.count += 1;
  return { allowed: true, remaining: limit - record.count, retryAfterMs: 0 };
}

/**
 * Check rate limit status without incrementing (peek active lockout).
 */
export function getRateLimitStatus(
  key: string,
  limit: number
): { allowed: boolean; remaining: number; retryAfterMs: number } {
  const now = Date.now();
  const record = requestCounts.get(key);

  if (!record || record.expiresAt < now) {
    return { allowed: true, remaining: limit, retryAfterMs: 0 };
  }

  if (record.count >= limit) {
    return {
      allowed: false,
      remaining: 0,
      retryAfterMs: Math.max(0, record.expiresAt - now),
    };
  }

  return { allowed: true, remaining: limit - record.count, retryAfterMs: 0 };
}

/**
 * Reset rate limit for a key (e.g. upon successful authentication).
 */
export function resetRateLimit(key: string): void {
  requestCounts.delete(key);
}

/**
 * Distributed, concurrency-safe atomic rate limit check via PostgreSQL.
 * Falls back to process-local store if database is unreachable.
 */
export async function checkRateLimitDistributed(
  key: string,
  limit: number,
  windowMs: number
): Promise<{ allowed: boolean; remaining: number; retryAfterMs: number }> {
  try {
    const admin = createAdminClient();
    const windowSeconds = Math.max(1, Math.ceil(windowMs / 1000));
    const { data, error } = await admin.rpc('check_rate_limit_atomic', {
      p_key: key,
      p_limit: limit,
      p_window_seconds: windowSeconds,
    });

    if (!error && data) {
      const allowed = Boolean(data.allowed);
      const remaining = Number(data.remaining ?? 0);
      const retryAfterMs = Number(data.retry_after_seconds ?? 0) * 1000;
      return { allowed, remaining, retryAfterMs };
    }
  } catch {
    // Graceful fallback to memory store
  }

  return checkRateLimit(key, limit, windowMs);
}

/**
 * Distributed rate limit status check without incrementing counter.
 */
export async function getRateLimitStatusDistributed(
  key: string,
  limit: number
): Promise<{ allowed: boolean; remaining: number; retryAfterMs: number }> {
  try {
    const admin = createAdminClient();
    const { data, error } = await admin.rpc('get_rate_limit_status', {
      p_key: key,
      p_limit: limit,
    });

    if (!error && data) {
      const allowed = Boolean(data.allowed);
      const remaining = Number(data.remaining ?? 0);
      const retryAfterMs = Number(data.retry_after_seconds ?? 0) * 1000;
      return { allowed, remaining, retryAfterMs };
    }
  } catch {
    // Graceful fallback to memory store
  }

  return getRateLimitStatus(key, limit);
}

/**
 * Distributed rate limit reset.
 */
export async function resetRateLimitDistributed(key: string): Promise<void> {
  resetRateLimit(key);
  try {
    const admin = createAdminClient();
    await admin.rpc('reset_rate_limit_atomic', { p_key: key });
  } catch {
    // Ignore DB error on reset
  }
}

/**
 * Create a rate limiter with strict namespace prefixing to prevent cross-endpoint key collision.
 */
export function createRateLimiter(
  prefixOrLimit: string | number,
  limitOrWindowMs?: number,
  windowMs?: number
) {
  if (typeof prefixOrLimit === 'string') {
    const prefix = prefixOrLimit;
    const limit = limitOrWindowMs ?? 10;
    const win = windowMs ?? 60_000;
    return (id: string) => checkRateLimit(`${prefix}:${id}`, limit, win);
  } else {
    const limit = prefixOrLimit;
    const win = limitOrWindowMs ?? 60_000;
    return (id: string) => checkRateLimit(id, limit, win);
  }
}

// Pre-configured isolated limiters for different endpoint categories
export const rateLimiters = {
  /** Login IP flood: 30 requests per minute per IP */
  loginIp: createRateLimiter('login_ip', 30, 60_000),
  /** Login attempts: 5 per minute per identity */
  login: createRateLimiter('login_attempt', 5, 60_000),
  /** Registration attempts: 5 per minute per IP */
  register: createRateLimiter('register', 5, 60_000),
  /** Password reset attempts: 3 per minute per IP */
  passwordReset: createRateLimiter('password_reset', 3, 60_000),
  /** API key generation: 3 per minute per IP */
  apiKeyGeneration: createRateLimiter('api_key_gen', 3, 60_000),
  /** Admin API key management: 20 per minute per IP */
  apiKeyManagement: createRateLimiter('api_key_mgmt', 20, 60_000),
  /** Block detail: 60 per minute per IP */
  blockDetail: createRateLimiter('block_detail', 60, 60_000),
  /** Restricted analytical endpoints: 30 per minute per IP */
  restrictedAnalytical: createRateLimiter('restricted', 30, 60_000),
  /** Geocode: 60 per minute per IP */
  geocode: createRateLimiter('geocode', 60, 60_000),
  /** Study area analysis: 20 per minute per IP */
  studyArea: createRateLimiter('study_area', 20, 60_000),
  /** Production summary: 10 per minute per IP */
  summary: createRateLimiter('summary', 10, 60_000),
};

/**
 * Extract client IP from request headers.
 * Resolves standard proxy forwarding headers, falling back to '127.0.0.1'.
 */
export function getClientIP(request: Request): string {
  const xForwardedFor = request.headers.get('x-forwarded-for');
  if (xForwardedFor) {
    const firstIp = xForwardedFor.split(',')[0].trim();
    if (firstIp && firstIp !== 'unknown') return firstIp;
  }
  const xRealIp = request.headers.get('x-real-ip');
  if (xRealIp?.trim() && xRealIp !== 'unknown') return xRealIp.trim();
  const cfConnectingIp = request.headers.get('cf-connecting-ip');
  if (cfConnectingIp?.trim()) return cfConnectingIp.trim();
  return '127.0.0.1';
}

/**
 * Create an accurate 429 response with Retry-After header and detailed JSON payload.
 */
export function rateLimitResponse(retryAfterMs: number, customMessage?: string): Response {
  const retryAfterSec = Math.max(1, Math.ceil(retryAfterMs / 1000));
  return new Response(
    JSON.stringify({
      error: customMessage || 'Too many requests. Please try again later.',
      retryAfter: retryAfterSec,
    }),
    {
      status: 429,
      headers: {
        'Content-Type': 'application/json',
        'Retry-After': String(retryAfterSec),
      },
    }
  );
}

// Clean up expired entries periodically to prevent memory leaks
if (typeof setInterval !== 'undefined') {
  const interval = setInterval(() => {
    const now = Date.now();
    for (const [key, value] of requestCounts.entries()) {
      if (value.expiresAt < now) {
        requestCounts.delete(key);
      }
    }
  }, 60_000);
  if (interval.unref) {
    interval.unref();
  }
}

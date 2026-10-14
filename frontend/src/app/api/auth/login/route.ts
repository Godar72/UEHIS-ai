import { NextResponse } from 'next/server';
import { createClient } from '@/lib/supabase/server';
import {
  getClientIP,
  checkRateLimitDistributed,
  getRateLimitStatusDistributed,
  resetRateLimitDistributed,
  rateLimitResponse,
} from '@/lib/rate-limit';

/**
 * Server-side login proxy with account-aware and network-aware rate limiting.
 *
 * Architecture:
 * 1. Network-aware protection: Throttles extreme automated request flooding per IP.
 * 2. Account-aware protection: Tracks consecutive failed password attempts per account & network.
 * 3. Typo resilience: Legitimate users with occasional typos are not locked out;
 *    successful logins immediately reset their failed attempt counters.
 * 4. Campus protection: Legitimate users sharing a university NAT/proxy IP are not
 *    blocked by an unrelated user's mistyped passphrase.
 * 5. Multi-instance safety: Uses concurrency-safe atomic counters in PostgreSQL.
 * 6. Enumeration resistance: Returns generic 'Invalid credentials' on all auth failures.
 */
export async function POST(request: Request) {
  try {
    const ip = getClientIP(request);

    // 1. Network Flood Protection (protects against rapid automated flooding)
    const ipLimit = parseInt(process.env.AUTH_IP_FLOOD_LIMIT || '30', 10);
    const ipWindowMs = parseInt(process.env.AUTH_IP_FLOOD_WINDOW_MS || '60000', 10);
    const ipCheck = await checkRateLimitDistributed(`login_ip:${ip}`, ipLimit, ipWindowMs);
    if (!ipCheck.allowed) {
      return rateLimitResponse(
        ipCheck.retryAfterMs,
        'Too many requests from this network. Please try again later.'
      );
    }

    // 2. Input Validation
    const body = await request.json().catch(() => null);
    if (!body) {
      return NextResponse.json({ error: 'Invalid request body' }, { status: 400 });
    }

    const { email, password } = body;
    if (!email || !password) {
      return NextResponse.json({ error: 'Email and password are required' }, { status: 400 });
    }

    if (typeof email !== 'string' || typeof password !== 'string') {
      return NextResponse.json({ error: 'Invalid input types' }, { status: 400 });
    }

    if (email.length > 254 || password.length > 256) {
      return NextResponse.json({ error: 'Input exceeds maximum length' }, { status: 400 });
    }

    const normalizedEmail = email.trim().toLowerCase();

    // 3. Account-aware lockout check (peeks if this account is currently locked out)
    const maxFailedAttempts = parseInt(process.env.AUTH_LOGIN_MAX_FAILED_ATTEMPTS || '5', 10);
    const failedWindowMs = parseInt(process.env.AUTH_LOGIN_WINDOW_MS || '60000', 10);
    const attemptKey = `login_attempt:${normalizedEmail}:${ip}`;

    const currentLockout = await getRateLimitStatusDistributed(attemptKey, maxFailedAttempts);
    if (!currentLockout.allowed) {
      return rateLimitResponse(
        currentLockout.retryAfterMs,
        'Too many login attempts. Please try again later.'
      );
    }

    // 4. Authenticate via Supabase Auth
    const supabase = await createClient();
    const { data, error } = await supabase.auth.signInWithPassword({
      email: normalizedEmail,
      password,
    });

    // 5. Handle Authentication SUCCESS
    if (!error && data?.user) {
      // Clear failed attempt counter for this account & network
      await resetRateLimitDistributed(attemptKey);

      return NextResponse.json({
        user: {
          id: data.user.id,
          email: data.user.email,
        },
      });
    }

    // 6. Handle Authentication FAILURE
    // Check if Supabase itself returned a rate limit
    if (
      error?.status === 429 ||
      error?.message?.toLowerCase().includes('rate limit') ||
      (error as { code?: string })?.code === 'over_request_rate_limit' ||
      (error as { code?: string })?.code === 'over_email_send_rate_limit'
    ) {
      return rateLimitResponse(failedWindowMs, 'Too many login attempts. Please try again later.');
    }

    // Increment failed attempt counter
    const failResult = await checkRateLimitDistributed(attemptKey, maxFailedAttempts, failedWindowMs);
    if (!failResult.allowed) {
      return rateLimitResponse(
        failResult.retryAfterMs,
        'Too many login attempts. Please try again later.'
      );
    }

    // Generic invalid credentials response to prevent account enumeration
    return NextResponse.json(
      { error: 'Invalid credentials' },
      { status: 401 }
    );
  } catch {
    console.error('Login processing notice: internal error occurred during authentication handling');
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}

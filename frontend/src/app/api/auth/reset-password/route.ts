import { NextResponse } from 'next/server';
import { createClient } from '@/lib/supabase/server';
import { rateLimiters, getClientIP, rateLimitResponse } from '@/lib/rate-limit';
import { isValidEmail } from '@/lib/auth-utils';

export async function POST(request: Request) {
  try {
    const ip = getClientIP(request);
    const rl = rateLimiters.passwordReset(ip);
    if (!rl.allowed) {
      return rateLimitResponse(rl.retryAfterMs);
    }

    const body = await request.json().catch(() => null);
    if (!body || !body.email || typeof body.email !== 'string') {
      return NextResponse.json({ error: 'Valid email address is required' }, { status: 400 });
    }

    const trimmedEmail = body.email.trim().toLowerCase();
    if (!isValidEmail(trimmedEmail)) {
      return NextResponse.json({ error: 'Valid email address is required' }, { status: 400 });
    }

    const supabase = await createClient();
    const origin = request.headers.get('origin') || process.env.NEXT_PUBLIC_SITE_URL || 'http://localhost:3000';
    
    // Request password reset without leaking whether email exists
    await supabase.auth.resetPasswordForEmail(trimmedEmail, {
      redirectTo: `${origin}/reset-password`,
    });

    return NextResponse.json({
      success: true,
      message: 'If an account exists with this email address, password reset instructions have been dispatched.',
    });
  } catch (error) {
    console.error('Password reset request error:', error);
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}

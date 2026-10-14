import { NextResponse } from 'next/server';
import { createClient } from '@/lib/supabase/server';
import { createAdminClient } from '@/lib/supabase/admin';
import { rateLimiters, getClientIP, rateLimitResponse } from '@/lib/rate-limit';
import { isValidEmail } from '@/lib/auth-utils';

export async function POST(request: Request) {
  try {
    // Rate limit: registration attempts (5 per minute per IP)
    const ip = getClientIP(request);
    const rl = rateLimiters.register(ip);
    if (!rl.allowed) {
      return rateLimitResponse(rl.retryAfterMs);
    }

    const body = await request.json().catch(() => null);
    if (!body) {
      return NextResponse.json({ error: 'Invalid request body' }, { status: 400 });
    }

    const { email, password, confirmPassword, name } = body;

    // Field existence and type validation
    if (!email || !password || !confirmPassword) {
      return NextResponse.json(
        { error: 'Email, password, and confirmation are required' },
        { status: 400 }
      );
    }

    if (
      typeof email !== 'string' ||
      typeof password !== 'string' ||
      typeof confirmPassword !== 'string'
    ) {
      return NextResponse.json({ error: 'Invalid input types' }, { status: 400 });
    }

    const trimmedEmail = email.trim().toLowerCase();
    const trimmedName = typeof name === 'string' ? name.trim() : '';

    if (!isValidEmail(trimmedEmail)) {
      return NextResponse.json({ error: 'Please provide a valid email address' }, { status: 400 });
    }

    if (password.length < 6) {
      return NextResponse.json(
        { error: 'Passphrase must be at least 6 characters in length' },
        { status: 400 }
      );
    }

    if (password.length > 256) {
      return NextResponse.json({ error: 'Passphrase exceeds maximum length' }, { status: 400 });
    }

    if (password !== confirmPassword) {
      return NextResponse.json({ error: 'Passphrases do not match' }, { status: 400 });
    }

    const supabase = await createClient();
    const { data, error } = await supabase.auth.signUp({
      email: trimmedEmail,
      password,
      options: {
        data: {
          full_name: trimmedName || undefined,
        },
      },
    });

    if (error) {
      const lowerErr = error.message.toLowerCase();
      if (lowerErr.includes('already registered') || lowerErr.includes('exists')) {
        return NextResponse.json(
          { error: 'An account with this email address cannot be registered. Please sign in or use password recovery.' },
          { status: 400 }
        );
      }
      return NextResponse.json(
        { error: error.message || 'Failed to complete registration' },
        { status: 400 }
      );
    }

    if (data?.user?.id) {
      // Authoritative default role assignment:
      // Newly registered users receive strictly the least-privilege 'public' role.
      // Roles are never taken from client input or request parameters.
      try {
        const adminClient = createAdminClient();
        await adminClient.from('user_roles').upsert(
          { user_id: data.user.id, role: 'public' },
          { onConflict: 'user_id', ignoreDuplicates: true }
        );
      } catch (roleErr) {
        console.error('Failed to assign default role on registration:', roleErr);
      }
    }

    const confirmationRequired = data?.session === null;

    return NextResponse.json({
      success: true,
      confirmationRequired,
      message: confirmationRequired
        ? 'Account registration initiated. Please verify your email inbox to confirm your account.'
        : 'Account registered successfully.',
      user: data?.user ? { id: data.user.id, email: data.user.email } : null,
    });
  } catch (error) {
    console.error('Registration server error:', error);
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}

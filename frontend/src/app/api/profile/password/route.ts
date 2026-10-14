import { NextResponse } from 'next/server';
import { createClient } from '@/lib/supabase/server';

export const dynamic = 'force-dynamic';

/**
 * POST /api/profile/password
 * Secure password change for authenticated users using Supabase Auth.
 * Rejects requests from Google OAuth-only accounts and validates policies.
 */
export async function POST(request: Request) {
  try {
    const supabase = await createClient();
    const { data: { user }, error: authError } = await supabase.auth.getUser();

    if (authError || !user) {
      return NextResponse.json(
        { error: 'Unauthorized: an active authenticated session is required' },
        { status: 401, headers: { 'Cache-Control': 'private, no-store, max-age=0' } }
      );
    }

    // Check if user is an OAuth-only account
    const providers: string[] = (user.app_metadata?.providers as string[]) || 
      (user.app_metadata?.provider ? [user.app_metadata.provider as string] : ['email']);
    const isOAuthOnly = providers.includes('google') && !providers.includes('email');

    if (isOAuthOnly) {
      return NextResponse.json(
        { error: 'Google OAuth accounts manage authentication credentials via Google. Passphrase management is not applicable.' },
        { status: 400 }
      );
    }

    const body = await request.json().catch(() => null);
    if (!body) {
      return NextResponse.json({ error: 'Invalid request body' }, { status: 400 });
    }

    const { currentPassword, newPassword, confirmPassword } = body;

    if (!newPassword || typeof newPassword !== 'string' || !confirmPassword || typeof confirmPassword !== 'string') {
      return NextResponse.json(
        { error: 'New passphrase and confirmation are required' },
        { status: 400 }
      );
    }

    if (newPassword.length < 6) {
      return NextResponse.json(
        { error: 'New passphrase must be at least 6 characters in length' },
        { status: 400 }
      );
    }

    if (newPassword.length > 256) {
      return NextResponse.json(
        { error: 'New passphrase exceeds maximum permissible length' },
        { status: 400 }
      );
    }

    if (newPassword !== confirmPassword) {
      return NextResponse.json(
        { error: 'Passphrases do not match' },
        { status: 400 }
      );
    }

    // If current password provided, verify it first against Supabase Auth
    if (currentPassword && typeof currentPassword === 'string' && user.email) {
      const { error: verifyError } = await supabase.auth.signInWithPassword({
        email: user.email,
        password: currentPassword,
      });

      if (verifyError) {
        return NextResponse.json(
          { error: 'Current passphrase verification failed. Please check your existing passphrase.' },
          { status: 400 }
        );
      }
    }

    // Update password using Supabase Auth
    const { error: updateError } = await supabase.auth.updateUser({
      password: newPassword,
    });

    if (updateError) {
      return NextResponse.json(
        { error: updateError.message || 'Failed to update passphrase' },
        { status: 400 }
      );
    }

    return NextResponse.json({
      success: true,
      message: 'Passphrase successfully updated.',
    });
  } catch (error) {
    console.error('Password change error:', error);
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}

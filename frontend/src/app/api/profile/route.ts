import { NextResponse } from 'next/server';
import { createClient } from '@/lib/supabase/server';
import { createAdminClient } from '@/lib/supabase/admin';

export const dynamic = 'force-dynamic';

/**
 * GET /api/profile
 * Returns authenticated user profile details, authoritative role, and identity metadata.
 */
export async function GET() {
  try {
    const supabase = await createClient();
    const { data: { user }, error: authError } = await supabase.auth.getUser();

    if (authError || !user) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401, headers: { 'Cache-Control': 'private, no-store, max-age=0' } }
      );
    }

    // Authoritative role lookup
    const { data: roleData } = await supabase.rpc('get_my_role');
    const role = roleData || 'public';

    // Profile display name lookup from user_profiles table
    const { data: profileData } = await supabase
      .from('user_profiles')
      .select('display_name')
      .eq('user_id', user.id)
      .maybeSingle();

    // Fallback order: user_profiles -> auth user_metadata -> email prefix
    const metaName = user.user_metadata?.full_name || user.user_metadata?.name;
    const emailPrefix = user.email ? user.email.split('@')[0] : 'User';
    const displayName = profileData?.display_name || metaName || emailPrefix;

    // Detect OAuth-only status
    const providers: string[] = (user.app_metadata?.providers as string[]) || 
      (user.app_metadata?.provider ? [user.app_metadata.provider as string] : ['email']);
    const isOAuthOnly = providers.includes('google') && !providers.includes('email');

    return NextResponse.json(
      {
        user: {
          id: user.id,
          email: user.email,
          displayName,
          role,
          createdAt: user.created_at,
          lastSignInAt: user.last_sign_in_at,
          isOAuthOnly,
          providers,
        },
      },
      {
        headers: {
          'Cache-Control': 'private, no-store, max-age=0',
        },
      }
    );
  } catch (error) {
    console.error('GET /api/profile error:', error);
    return NextResponse.json(
      { error: 'Internal Server Error' },
      { status: 500, headers: { 'Cache-Control': 'private, no-store, max-age=0' } }
    );
  }
}

/**
 * PATCH /api/profile
 * Updates the user's display name securely in both user_profiles and auth metadata.
 * Does not allow altering roles, emails, or other users' profiles.
 */
export async function PATCH(request: Request) {
  try {
    const supabase = await createClient();
    const { data: { user }, error: authError } = await supabase.auth.getUser();

    if (authError || !user) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401, headers: { 'Cache-Control': 'private, no-store, max-age=0' } }
      );
    }

    const body = await request.json().catch(() => null);
    if (!body || typeof body.displayName !== 'string') {
      return NextResponse.json(
        { error: 'Display name is required and must be a string' },
        { status: 400 }
      );
    }

    const trimmed = body.displayName.trim();

    // Enforce reasonable display name constraints (2–50 characters)
    if (trimmed.length < 2 || trimmed.length > 50) {
      return NextResponse.json(
        { error: 'Display name must be between 2 and 50 characters' },
        { status: 400 }
      );
    }

    // Reject control characters or newlines
    if (/[\u0000-\u001F\u007F]/.test(trimmed)) {
      return NextResponse.json(
        { error: 'Display name contains prohibited control characters' },
        { status: 400 }
      );
    }

    // 1. Update public.user_profiles using secure RPC
    const { error: rpcError } = await supabase.rpc('update_my_profile', {
      p_display_name: trimmed,
    });

    if (rpcError) {
      console.error('update_my_profile RPC error:', rpcError);
      return NextResponse.json(
        { error: 'Failed to update profile record' },
        { status: 500 }
      );
    }

    // 2. Synchronize auth.users user_metadata for backward compatibility
    await supabase.auth.updateUser({
      data: {
        full_name: trimmed,
        name: trimmed,
      },
    });

    return NextResponse.json(
      {
        success: true,
        displayName: trimmed,
      },
      {
        headers: {
          'Cache-Control': 'private, no-store, max-age=0',
        },
      }
    );
  } catch (error) {
    console.error('PATCH /api/profile error:', error);
    return NextResponse.json(
      { error: 'Internal Server Error' },
      { status: 500, headers: { 'Cache-Control': 'private, no-store, max-age=0' } }
    );
  }
}

/**
 * DELETE /api/profile
 * Authenticated user account self-deletion (GDPR Right-to-Erasure).
 * Deletes user account from auth.users via admin client, triggering CASCADE
 * deletion on user_profiles, user_roles, user_activity, study_areas, and api_keys.
 */
export async function DELETE() {
  try {
    const supabase = await createClient();
    const { data: { user }, error: authError } = await supabase.auth.getUser();

    if (authError || !user) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401, headers: { 'Cache-Control': 'private, no-store, max-age=0' } }
      );
    }

    // Delete user via admin client (requires service role key to manage auth.users)
    const adminClient = createAdminClient();

    // Explicitly purge user-owned study areas (which do not have a hard FK cascade)
    await adminClient.from('study_areas').delete().eq('user_id', user.id);

    const { error: deleteError } = await adminClient.auth.admin.deleteUser(user.id);

    if (deleteError) {
      console.error('Account deletion error:', deleteError);
      return NextResponse.json(
        { error: 'Failed to complete account deletion' },
        { status: 500 }
      );
    }

    // Sign out caller and invalidate session cookies
    await supabase.auth.signOut();

    return NextResponse.json({
      success: true,
      message: 'Account and associated personal records successfully deleted.',
    });
  } catch (error) {
    console.error('DELETE /api/profile error:', error);
    return NextResponse.json(
      { error: 'Internal Server Error' },
      { status: 500 }
    );
  }
}

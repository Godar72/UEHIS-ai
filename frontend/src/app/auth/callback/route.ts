import { NextResponse, type NextRequest } from 'next/server';
import { createClient } from '@/lib/supabase/server';
import { createAdminClient } from '@/lib/supabase/admin';
import { isSafeRedirect } from '@/lib/auth-utils';

function getCanonicalBase(request: NextRequest): string {
  const forwardedProto = request.headers.get('x-forwarded-proto');
  const forwardedHost = request.headers.get('x-forwarded-host') || request.headers.get('host');
  const isHttps = forwardedProto === 'https' || process.env.NODE_ENV === 'production';
  return `${isHttps ? 'https' : 'http'}://${forwardedHost || request.nextUrl.host}`;
}

export async function GET(request: NextRequest) {
  const requestUrl = new URL(request.url);
  const canonicalBase = getCanonicalBase(request);
  const code = requestUrl.searchParams.get('code');
  const error = requestUrl.searchParams.get('error');
  const errorDescription = requestUrl.searchParams.get('error_description');
  const nextParam = requestUrl.searchParams.get('next');

  // Validate next destination
  const destination = (nextParam && isSafeRedirect(nextParam)) ? nextParam : '/explore';

  const nextQuery = destination !== '/explore' ? `&next=${encodeURIComponent(destination)}` : '';

  // Handle OAuth provider error or user cancellation
  if (error) {
    const message = errorDescription || error;
    console.warn('OAuth callback provider notice:', message);
    return NextResponse.redirect(new URL(`/login?error=${encodeURIComponent(message)}${nextQuery}`, canonicalBase));
  }

  // Exchange code for Supabase authenticated session
  if (code) {
    try {
      const supabase = await createClient();
      const { data, error: exchangeError } = await supabase.auth.exchangeCodeForSession(code);

      if (exchangeError) {
        console.error('OAuth code exchange failed:', exchangeError.message);
        return NextResponse.redirect(
          new URL(`/login?error=${encodeURIComponent('Failed to complete authentication. Code may have expired.')}${nextQuery}`, canonicalBase)
        );
      }

      if (data?.user?.id) {
        // Authoritative default role assignment for first-time user:
        // Use least-privilege 'public' role. ignoreDuplicates ensures existing researcher/admin roles are NEVER demoted.
        try {
          const adminClient = createAdminClient();
          await adminClient.from('user_roles').upsert(
            { user_id: data.user.id, role: 'public' },
            { onConflict: 'user_id', ignoreDuplicates: true }
          );
        } catch (roleErr) {
          console.error('Error assigning least-privilege role to OAuth user:', roleErr);
        }
      }

      return NextResponse.redirect(new URL(destination, canonicalBase));
    } catch (err: unknown) {
      console.error('Unexpected error in auth callback:', err);
      return NextResponse.redirect(
        new URL(`/login?error=${encodeURIComponent('Authentication processing error. Please try again.')}${nextQuery}`, canonicalBase)
      );
    }
  }

  // Fallback if no code and no error provided
  return NextResponse.redirect(new URL(`/login${nextQuery}`, canonicalBase));
}

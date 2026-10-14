import { createServerClient } from '@supabase/ssr'
import { NextResponse, type NextRequest } from 'next/server'
import { isSafeRedirect } from '@/lib/auth-utils'

function getCanonicalBase(request: NextRequest): string {
  const forwardedProto = request.headers.get('x-forwarded-proto');
  const forwardedHost = request.headers.get('x-forwarded-host') || request.headers.get('host');
  const isHttps = forwardedProto === 'https' || process.env.NODE_ENV === 'production';
  return `${isHttps ? 'https' : 'http'}://${forwardedHost || request.nextUrl.host}`;
}

export async function updateSession(request: NextRequest) {
  let supabaseResponse = NextResponse.next({
    request,
  })

  const canonicalBase = getCanonicalBase(request);

  // Route paths
  const rawPath = request.nextUrl.pathname
  const normalizedPath = rawPath.replace(/\/+/g, '/').replace(/\/+$/, '') || '/'
  const lowerPath = normalizedPath.toLowerCase()

  // 1. Only the exact public scenario-metadata endpoint is exempt from researcher-only protection
  const isPublicPlantingScenarios = lowerPath === '/api/planting/scenarios'

  // Admin routes: require authenticated session with role === 'admin'
  const isAdminRoute =
    lowerPath === '/admin' || lowerPath.startsWith('/admin/') ||
    lowerPath === '/api/admin' || lowerPath.startsWith('/api/admin/')

  // Researcher routes: require authenticated session with role in ['researcher', 'admin']
  const isResearcherRoute =
    lowerPath === '/restricted' || lowerPath.startsWith('/restricted/') ||
    lowerPath === '/api/restricted' || lowerPath.startsWith('/api/restricted/') ||
    lowerPath === '/planting' || lowerPath.startsWith('/planting/') ||
    (lowerPath.startsWith('/api/planting') && !isPublicPlantingScenarios)

  // Planting tile routes are restricted to authenticated researcher/admin
  const isPlantingTileRoute =
    lowerPath.startsWith('/tiles/planting-areas') ||
    lowerPath.startsWith('/tiles/planting-units')

  // Protected public application routes: require any valid authenticated session
  const isProtectedAppRoute =
    lowerPath === '/explore' || lowerPath.startsWith('/explore/') ||
    lowerPath === '/carbon' || lowerPath.startsWith('/carbon/') ||
    lowerPath === '/scenarios' || lowerPath.startsWith('/scenarios/') ||
    lowerPath === '/account' || lowerPath.startsWith('/account/') ||
    lowerPath === '/profile' || lowerPath.startsWith('/profile/');

  const isProtectedRoute = isAdminRoute || isResearcherRoute || isPlantingTileRoute || isProtectedAppRoute

  // Fail-closed enforcement: if Supabase config is missing, NEVER permit access to protected routes
  if (!process.env.NEXT_PUBLIC_SUPABASE_URL || !process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY) {
    if (isProtectedRoute) {
      if (lowerPath.startsWith('/api/') || lowerPath.startsWith('/tiles/')) {
        return new NextResponse(
          JSON.stringify({ error: 'Authentication service configuration is missing or incomplete.' }),
          { status: 503, headers: { 'Content-Type': 'application/json' } }
        )
      }
      return new NextResponse(
        'Authentication service is misconfigured. Protected application routes are unavailable.',
        { status: 503, headers: { 'Content-Type': 'text/plain; charset=utf-8' } }
      )
    }
    return supabaseResponse;
  }

  const supabase = createServerClient(
    process.env.SUPABASE_INTERNAL_URL || process.env.NEXT_PUBLIC_SUPABASE_URL,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY,
    {
      cookies: {
        getAll() {
          return request.cookies.getAll()
        },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value }) => request.cookies.set(name, value))
          supabaseResponse = NextResponse.next({
            request,
          })
          cookiesToSet.forEach(({ name, value, options }) => {
            const secureOptions = process.env.NODE_ENV === 'production'
              ? { ...options, secure: true, sameSite: (options.sameSite || 'lax') as 'lax' | 'strict' | 'none' }
              : options;
            supabaseResponse.cookies.set(name, value, secureOptions)
          })
        },
      },
    }
  )

  // Refresh session if expired
  const { data: { user } } = await supabase.auth.getUser()

  // Auth pages: /login, /register
  const isAuthPage =
    lowerPath === '/login' || lowerPath === '/register'

  // 2. If authenticated user visits /login or /register, redirect to safe 'next' or /explore
  if (isAuthPage && user) {
    const nextParam = request.nextUrl.searchParams.get('next');
    const destination = (nextParam && isSafeRedirect(nextParam)) ? nextParam : '/explore';
    return NextResponse.redirect(new URL(destination, canonicalBase));
  }

  // 3. Unauthenticated access to protected core application routes (/explore, /carbon, /scenarios)
  if (isProtectedAppRoute && !user) {
    return NextResponse.redirect(new URL(`/login?next=${encodeURIComponent(rawPath)}`, canonicalBase))
  }

  // 4. Unauthenticated access to Admin, Researcher, or Planting Tile routes
  if ((isAdminRoute || isResearcherRoute || isPlantingTileRoute) && !user) {
    if (lowerPath.startsWith('/api/') || lowerPath.startsWith('/tiles/')) {
      return new NextResponse(
        JSON.stringify({ error: 'Unauthorized' }),
        { status: 401, headers: { 'Content-Type': 'application/json' } }
      )
    }
    return NextResponse.redirect(new URL(`/login?next=${encodeURIComponent(rawPath)}`, canonicalBase))
  }

  // 5. Role verification for Admin, Researcher, and Planting Tile routes
  if (isAdminRoute || isResearcherRoute || isPlantingTileRoute) {
    // Use get_my_role() — safe self-lookup using auth.uid()
    const { data: role } = await supabase.rpc('get_my_role')
    
    if (isAdminRoute && role !== 'admin') {
      if (lowerPath.startsWith('/api/')) {
        return new NextResponse(
          JSON.stringify({ error: 'Forbidden' }),
          { status: 403, headers: { 'Content-Type': 'application/json' } }
        )
      }
      return NextResponse.redirect(new URL('/explore', canonicalBase))
    }
    
    if ((isResearcherRoute || isPlantingTileRoute) && !['admin', 'researcher'].includes(role)) {
      if (lowerPath.startsWith('/api/') || lowerPath.startsWith('/tiles/')) {
        return new NextResponse(
          JSON.stringify({ error: 'Forbidden' }),
          { status: 403, headers: { 'Content-Type': 'application/json' } }
        )
      }
      return NextResponse.redirect(new URL('/explore', canonicalBase))
    }
  }

  return supabaseResponse
}

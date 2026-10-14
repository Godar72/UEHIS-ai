import { createClient } from '@/lib/supabase/server';

interface AuthCacheEntry {
  role: string;
  expiresAt: number;
}

const authCache = new Map<string, AuthCacheEntry>();
const AUTH_CACHE_TTL_MS = 60 * 1000; // 60 seconds
const MAX_AUTH_ENTRIES = 500;

export async function verifyTileAuth(request: Request): Promise<{ authorized: boolean; status?: number; error?: string }> {
  const cookieHeader = request.headers.get('cookie') || '';
  if (!cookieHeader) {
    return { authorized: false, status: 401, error: 'Unauthorized' };
  }

  // Look for supabase auth token in cookie header
  const authMatch = cookieHeader.match(/sb-[a-zA-Z0-9_-]+-auth-token=([^;]+)/);
  const cacheKey = authMatch ? authMatch[1].slice(0, 64) : null;

  if (cacheKey && authCache.has(cacheKey)) {
    const entry = authCache.get(cacheKey)!;
    if (Date.now() < entry.expiresAt) {
      if (entry.role === 'researcher' || entry.role === 'admin') {
        return { authorized: true };
      }
      return { authorized: false, status: 403, error: 'Forbidden' };
    }
    authCache.delete(cacheKey);
  }

  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();

  if (!user) {
    return { authorized: false, status: 401, error: 'Unauthorized' };
  }

  const { data: role } = await supabase.rpc('get_my_role');
  if (role !== 'researcher' && role !== 'admin') {
    return { authorized: false, status: 403, error: 'Forbidden' };
  }

  if (cacheKey) {
    if (authCache.size >= MAX_AUTH_ENTRIES) {
      const first = authCache.keys().next().value;
      if (first) authCache.delete(first);
    }
    authCache.set(cacheKey, { role: role as string, expiresAt: Date.now() + AUTH_CACHE_TTL_MS });
  }

  return { authorized: true };
}

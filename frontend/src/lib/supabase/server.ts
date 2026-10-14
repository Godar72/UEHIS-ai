import { createServerClient } from '@supabase/ssr'
import { cookies } from 'next/headers'

export async function createClient() {
  const cookieStore = await cookies()

  if (!process.env.NEXT_PUBLIC_SUPABASE_URL || !process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY) {
    throw new Error('Missing Supabase environment variables');
  }

  const supabaseUrl = process.env.SUPABASE_INTERNAL_URL || process.env.NEXT_PUBLIC_SUPABASE_URL;

  const isProduction = (process.env.ENVIRONMENT || '').toLowerCase() === 'production';
  if (isProduction) {
    if (!supabaseUrl || supabaseUrl.includes('localhost') || supabaseUrl.includes('127.0.0.1') || supabaseUrl.includes('host.docker.internal')) {
      throw new Error(
        'CRITICAL CONFIGURATION ERROR: SUPABASE_INTERNAL_URL / NEXT_PUBLIC_SUPABASE_URL cannot point to localhost or host.docker.internal in production.'
      );
    }
  }

  return createServerClient(
    supabaseUrl,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY,
    {
      cookies: {
        getAll() {
          return cookieStore.getAll()
        },
        setAll(cookiesToSet) {
          try {
            cookiesToSet.forEach(({ name, value, options }) => {
              const secureOptions = process.env.NODE_ENV === 'production'
                ? { ...options, secure: true, sameSite: (options.sameSite || 'lax') as 'lax' | 'strict' | 'none' }
                : options;
              cookieStore.set(name, value, secureOptions);
            });
          } catch {
            // The `setAll` method was called from a Server Component.
            // This can be ignored if you have middleware refreshing
            // user sessions.
          }
        },
      },
    }
  )
}

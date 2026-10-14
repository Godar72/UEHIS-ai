import { createClient } from '@supabase/supabase-js';

export function createAdminClient() {
  const url = process.env.SUPABASE_INTERNAL_URL || process.env.NEXT_PUBLIC_SUPABASE_URL;

  const isProduction = (process.env.ENVIRONMENT || '').toLowerCase() === 'production';
  if (isProduction) {
    if (!url || url.includes('localhost') || url.includes('127.0.0.1') || url.includes('host.docker.internal')) {
      throw new Error(
        'CRITICAL CONFIGURATION ERROR: SUPABASE_INTERNAL_URL / NEXT_PUBLIC_SUPABASE_URL cannot point to localhost or host.docker.internal in production.'
      );
    }
  }

  const effectiveUrl = url || 'http://127.0.0.1:54221';
  const serviceKey = process.env.SUPABASE_SERVICE_ROLE_KEY;

  if (!serviceKey) {
    throw new Error('Missing SUPABASE_SERVICE_ROLE_KEY environment variable');
  }

  return createClient(effectiveUrl, serviceKey, {
    auth: {
      persistSession: false,
      autoRefreshToken: false,
    },
  });
}

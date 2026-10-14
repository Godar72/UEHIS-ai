import { NextResponse } from 'next/server';
import { createClient } from '@/lib/supabase/server';
import { randomBytes, createHash } from 'crypto';
import { rateLimiters, getClientIP, rateLimitResponse } from '@/lib/rate-limit';

export async function GET(request: Request) {
  try {
    // Rate limit: admin key management
    const ip = getClientIP(request);
    const rl = rateLimiters.apiKeyManagement(ip);
    if (!rl.allowed) return rateLimitResponse(rl.retryAfterMs);

    const supabase = await createClient();
    const { data: { user } } = await supabase.auth.getUser();

    if (!user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    // Verify admin role
    const { data: role } = await supabase.rpc('get_my_role');
    if (role !== 'admin') {
      return NextResponse.json({ error: 'Forbidden' }, { status: 403 });
    }

    const { data: keys, error } = await supabase
      .from('api_keys')
      .select('id, name, key_prefix, created_at, expires_at, revoked_at, last_used_at')
      .eq('user_id', user.id)
      .order('created_at', { ascending: false });

    if (error) throw error;

    return NextResponse.json(keys);
  } catch (error) {
    console.error('Error fetching API keys:', error);
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}

export async function POST(request: Request) {
  try {
    // Rate limit: API key generation (stricter)
    const ip = getClientIP(request);
    const rl = rateLimiters.apiKeyGeneration(ip);
    if (!rl.allowed) return rateLimitResponse(rl.retryAfterMs);

    const supabase = await createClient();
    const { data: { user } } = await supabase.auth.getUser();

    if (!user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    // Verify admin role
    const { data: role } = await supabase.rpc('get_my_role');
    if (role !== 'admin') {
      return NextResponse.json({ error: 'Forbidden' }, { status: 403 });
    }

    const payload = await request.json();
    if (!payload.name || typeof payload.name !== 'string' || payload.name.trim().length === 0) {
      return NextResponse.json({ error: 'Key name is required' }, { status: 400 });
    }

    if (payload.name.length > 100) {
      return NextResponse.json({ error: 'Key name too long' }, { status: 400 });
    }

    // Generate cryptographically secure random key (32 bytes = 64 hex chars = 256 bits of entropy)
    const rawSecret = randomBytes(32).toString('hex');
    const prefix = rawSecret.substring(0, 8);
    const apiKey = `uehis_live_${rawSecret}`;

    // Hash using Node.js crypto — must match what verify_api_key() expects
    // The DB function uses: extensions.digest(p_key, 'sha256') → hex
    const hashedKey = createHash('sha256').update(apiKey).digest('hex');

    const { data, error } = await supabase
      .from('api_keys')
      .insert({
        user_id: user.id,
        name: payload.name.trim(),
        key_prefix: `uehis_live_${prefix}••••••••`,
        hashed_key: hashedKey
      })
      .select()
      .single();

    if (error) throw error;

    // Return the plaintext key exactly once — it cannot be recovered after this
    return NextResponse.json({
      ...data,
      plaintext_key: apiKey
    });
  } catch (error) {
    console.error('Error creating API key:', error);
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}

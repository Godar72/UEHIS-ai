import { NextResponse } from 'next/server';
import { createClient } from '@/lib/supabase/server';
import { rateLimiters, getClientIP, rateLimitResponse } from '@/lib/rate-limit';

export async function DELETE(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    // Rate limit: admin key management
    const ip = getClientIP(request);
    const rl = rateLimiters.apiKeyManagement(ip);
    if (!rl.allowed) return rateLimitResponse(rl.retryAfterMs);

    const { id } = await params;
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

    // Validate UUID format to prevent injection
    const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
    if (!uuidRegex.test(id)) {
      return NextResponse.json({ error: 'Invalid key ID' }, { status: 400 });
    }

    const { error } = await supabase
      .from('api_keys')
      .update({ revoked_at: new Date().toISOString() })
      .eq('id', id)
      .eq('user_id', user.id); // Ensure they can only revoke their own

    if (error) throw error;

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error('Error revoking API key:', error);
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}

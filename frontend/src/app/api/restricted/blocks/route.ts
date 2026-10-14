import { NextResponse } from 'next/server';
import { createClient } from '@/lib/supabase/server';
import { rateLimiters, getClientIP, rateLimitResponse } from '@/lib/rate-limit';

export async function GET(request: Request) {
  try {
    // Rate limit: restricted analytical endpoint
    const ip = getClientIP(request);
    const rl = rateLimiters.restrictedAnalytical(ip);
    if (!rl.allowed) return rateLimitResponse(rl.retryAfterMs);

    const supabase = await createClient();
    const { data: { user } } = await supabase.auth.getUser();

    if (!user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const { data: role } = await supabase.rpc('get_my_role');

    if (!role || (role !== 'admin' && role !== 'researcher')) {
      return NextResponse.json({ error: 'Forbidden: Insufficient permissions' }, { status: 403 });
    }

    // Since the researcher is authenticated, RLS will allow this select
    const { data: blocks, error } = await supabase
      .from('uehi_blocks')
      .select('block_id, uehi_score, risk_level')
      .limit(10);

    if (error) {
      return NextResponse.json({ error: error.message }, { status: 500 });
    }

    return NextResponse.json({ blocks });
  } catch (error) {
    console.error('Error fetching restricted data:', error);
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}

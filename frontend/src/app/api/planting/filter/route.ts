import { NextResponse } from 'next/server';
import { createClient } from '@/lib/supabase/server';

export async function POST(request: Request) {
  try {
    let user = null;
    let role = null;

    try {
      const supabase = await createClient();
      const { data } = await supabase.auth.getUser();
      user = data?.user;
      if (user) {
        const { data: roleData } = await supabase.rpc('get_my_role');
        role = roleData;
      }
    } catch (authErr) {
      // If cookie/session store is invalid or missing, treat as unauthenticated
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    if (!user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    // Verify researcher or admin role
    if (role !== 'researcher' && role !== 'admin') {
      return NextResponse.json({ error: 'Forbidden' }, { status: 403 });
    }

    const payload = await request.json();
    
    if (!payload.geometry || !payload.scenario_id) {
      return NextResponse.json({ error: 'Missing geometry or scenario_id' }, { status: 400 });
    }

    const pythonServiceUrl = process.env.PYTHON_SERVICE_URL || process.env.UEHIS_API_URL || 'http://127.0.0.1:8000';
    const internalKey = process.env.UEHIS_API_KEY || '';

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 120000);

    try {
      const response = await fetch(`${pythonServiceUrl.replace(/\/$/, '')}/planting/filter`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(internalKey ? { 'X-API-Key': internalKey } : {}),
        },
        body: JSON.stringify({
          geometry: payload.geometry,
          scenario_id: payload.scenario_id,
        }),
        signal: controller.signal,
      });

      clearTimeout(timeout);

      if (!response.ok) {
        const errorText = await response.text();
        console.error(`[PLANTING_FILTER_UPSTREAM_ERROR] Status: ${response.status}`, errorText);
        let errorData: any;
        try {
          errorData = JSON.parse(errorText);
        } catch {
          errorData = { error: 'Failed to filter planting units' };
        }
        return NextResponse.json(errorData, { status: response.status >= 500 ? 502 : response.status });
      }

      const result = await response.json();
      return NextResponse.json(result);
    } catch (fetchErr: any) {
      clearTimeout(timeout);
      if (fetchErr.name === 'AbortError') {
        console.error('[PLANTING_FILTER_TIMEOUT]');
        return NextResponse.json({ error: 'Analysis timed out' }, { status: 504 });
      }
      console.error('[PLANTING_FILTER_NETWORK_ERROR]', fetchErr);
      return NextResponse.json(
        { error: 'Upstream geospatial service unavailable' },
        { status: 502 }
      );
    }
  } catch (err) {
    console.error('Error filtering planting units:', err);
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}

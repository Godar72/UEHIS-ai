import { NextResponse } from 'next/server';
import { rateLimiters, getClientIP, rateLimitResponse } from '@/lib/rate-limit';

export async function POST(request: Request) {
  try {
    const ip = getClientIP(request);
    const rl = rateLimiters.studyArea(ip);
    if (!rl.allowed) return rateLimitResponse(rl.retryAfterMs);

    const payload = await request.json();
    
    // Validate geometry
    if (!payload.geometry) {
      return NextResponse.json({ error: 'Missing geometry' }, { status: 400 });
    }

    const pythonServiceUrl = process.env.PYTHON_SERVICE_URL || process.env.UEHIS_API_URL || 'http://127.0.0.1:8000';
    const mode = payload.mode || 'all';
    const internalKey = process.env.UEHIS_API_KEY || '';

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 120000);

    try {
      const response = await fetch(`${pythonServiceUrl.replace(/\/$/, '')}/study-area/aggregate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(internalKey ? { 'X-API-Key': internalKey } : {}),
        },
        body: JSON.stringify({
          geometry: payload.geometry,
          mode,
        }),
        signal: controller.signal,
      });

      clearTimeout(timeout);

      if (!response.ok) {
        const errorText = await response.text();
        console.error(`[STUDY_AREA_UPSTREAM_ERROR] Status: ${response.status}`, errorText);
        let errorData: any;
        try {
          errorData = JSON.parse(errorText);
        } catch {
          errorData = { error: 'Upstream study area aggregation failed' };
        }
        return NextResponse.json(errorData, { status: response.status >= 500 ? 502 : response.status });
      }

      const result = await response.json();
      return NextResponse.json(result);
    } catch (fetchErr: any) {
      clearTimeout(timeout);
      if (fetchErr.name === 'AbortError') {
        console.error(`[STUDY_AREA_TIMEOUT] Mode: ${mode}`);
        return NextResponse.json({ error: 'Analysis timed out' }, { status: 504 });
      }
      console.error('[STUDY_AREA_NETWORK_ERROR]', fetchErr);
      return NextResponse.json(
        { error: 'Upstream geospatial service unavailable' },
        { status: 502 }
      );
    }
  } catch (err) {
    console.error('Error processing study area:', err);
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}

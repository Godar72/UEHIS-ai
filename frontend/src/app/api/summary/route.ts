import { NextRequest, NextResponse } from 'next/server';
import { rateLimiters, getClientIP, rateLimitResponse } from '@/lib/rate-limit';

// Production blocks (5,309) are immutable baseline data; cache summary for 1 hour
let cachedSummary: any = null;
let cacheTimestamp = 0;
const CACHE_TTL_MS = 60 * 60 * 1000;

export async function GET(req: NextRequest) {
  try {
    const ip = getClientIP(req);
    const rl = rateLimiters.summary(ip);
    if (!rl.allowed) return rateLimitResponse(rl.retryAfterMs);

    if (cachedSummary && Date.now() - cacheTimestamp < CACHE_TTL_MS) {
      return NextResponse.json(cachedSummary);
    }
    
    const pythonServiceUrl = process.env.PYTHON_SERVICE_URL || process.env.UEHIS_API_URL || 'http://127.0.0.1:8000';
    const internalKey = process.env.UEHIS_API_KEY || '';

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 30000);

    try {
      const response = await fetch(`${pythonServiceUrl.replace(/\/$/, '')}/summary`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          ...(internalKey ? { 'X-API-Key': internalKey } : {}),
        },
        signal: controller.signal,
      });

      clearTimeout(timeout);

      if (!response.ok) {
        const errorText = await response.text();
        console.error(`[SUMMARY_UPSTREAM_ERROR] Status: ${response.status}`, errorText);
        return NextResponse.json(
          { error: 'Failed to fetch summary' },
          { status: response.status >= 500 ? 502 : response.status }
        );
      }

      const result = await response.json();
      cachedSummary = result;
      cacheTimestamp = Date.now();
      return NextResponse.json(result);
    } catch (fetchErr: any) {
      clearTimeout(timeout);
      if (fetchErr.name === 'AbortError') {
        console.error('[SUMMARY_TIMEOUT]');
        return NextResponse.json({ error: 'Summary timeout' }, { status: 504 });
      }
      console.error('[SUMMARY_NETWORK_ERROR]', fetchErr);
      return NextResponse.json(
        { error: 'Upstream summary service unavailable' },
        { status: 502 }
      );
    }
  } catch (err) {
    console.error('Error fetching summary:', err);
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}

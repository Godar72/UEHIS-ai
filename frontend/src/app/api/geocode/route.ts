import { NextResponse } from 'next/server';
import { rateLimiters, getClientIP, rateLimitResponse } from '@/lib/rate-limit';

export async function GET(request: Request) {
  const ip = getClientIP(request);
  const rl = rateLimiters.geocode(ip);
  if (!rl.allowed) return rateLimitResponse(rl.retryAfterMs);

  const { searchParams } = new URL(request.url);
  const q = searchParams.get('q');

  if (!q || q.trim().length < 2) {
    return NextResponse.json({ error: 'Query too short' }, { status: 400 });
  }

  if (q.length > 100) {
    return NextResponse.json({ error: 'Query too long' }, { status: 400 });
  }

  const apiKey = process.env.GEOAPIFY_API_KEY;
  if (!apiKey) {
    console.error('Missing GEOAPIFY_API_KEY environment variable');
    return NextResponse.json({ error: 'Location search is temporarily unavailable.' }, { status: 503 });
  }

  try {
    // Bias towards Pune: lon=73.8567, lat=18.5204
    // Filter to a 50km circle around Pune
    const filterParams = 'circle:73.8567,18.5204,50000';
    const biasParams = 'proximity:73.8567,18.5204';
    
    const apiUrl = new URL('https://api.geoapify.com/v1/geocode/autocomplete');
    apiUrl.searchParams.append('text', q.trim());
    apiUrl.searchParams.append('apiKey', apiKey);
    apiUrl.searchParams.append('filter', filterParams);
    apiUrl.searchParams.append('bias', biasParams);
    apiUrl.searchParams.append('limit', '5');

    // Geoapify allows temporary caching of responses for performance (up to 24 hours).
    const response = await fetch(apiUrl.toString(), {
      next: { revalidate: 3600 } // Cache identical queries for 1 hour
    });

    if (!response.ok) {
      if (response.status === 401 || response.status === 403) {
        console.error('Geoapify auth error');
      } else if (response.status === 429) {
        console.warn('Geoapify rate limit reached');
      } else {
        console.error(`Geoapify error: ${response.status}`);
      }
      throw new Error(`Geocoding provider returned ${response.status}`);
    }

    const data = await response.json();
    
    // Transform to a provider-independent internal structure
    const results = (data.features || []).map((feature: any) => {
      const props = feature.properties;
      
      // Determine a generic type string
      let typeStr = props.result_type || props.category || 'place';
      
      return {
        id: props.place_id,
        name: props.name || props.formatted.split(',')[0],
        type: typeStr,
        secondaryLabel: props.formatted,
        longitude: parseFloat(props.lon),
        latitude: parseFloat(props.lat),
        provider: 'geoapify'
      };
    });

    return NextResponse.json(results);
  } catch (error) {
    console.error('Geocoding error:', error);
    return NextResponse.json({ error: 'Location search is temporarily unavailable.' }, { status: 503 });
  }
}


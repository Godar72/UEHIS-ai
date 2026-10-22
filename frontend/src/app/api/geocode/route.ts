import { NextResponse } from 'next/server';
import { rateLimiters, getClientIP, rateLimitResponse } from '@/lib/rate-limit';

// Authoritative PMC + PCMC Evaluated Model Boundary (EPSG:32643 footprint in WGS84)
const PUNE_COVERAGE_BOUNDS = {
  minLat: 18.428852,
  maxLat: 18.621015,
  minLng: 73.749344,
  maxLng: 74.021411,
};

export interface GeocodeResult {
  id: string;
  name: string;
  type: string;
  secondaryLabel: string;
  longitude: number;
  latitude: number;
  provider: 'geoapify' | 'nominatim';
  inCoverage: boolean;
}

interface GeoapifyFeature {
  properties?: {
    place_id?: string | number;
    name?: string;
    formatted?: string;
    result_type?: string;
    category?: string;
    lat?: string | number;
    lon?: string | number;
  };
}

interface NominatimItem {
  place_id?: string | number;
  name?: string;
  display_name?: string;
  type?: string;
  category?: string;
  lat?: string;
  lon?: string;
}

function checkInCoverage(lat: number, lng: number): boolean {
  return (
    lat >= PUNE_COVERAGE_BOUNDS.minLat &&
    lat <= PUNE_COVERAGE_BOUNDS.maxLat &&
    lng >= PUNE_COVERAGE_BOUNDS.minLng &&
    lng <= PUNE_COVERAGE_BOUNDS.maxLng
  );
}

function normalizeResultType(rawType: string, category?: string): string {
  const t = (rawType || category || '').toLowerCase();
  if (['residential', 'neighbourhood', 'suburb', 'village', 'quarter', 'city_block'].includes(t)) {
    return 'Locality';
  }
  if (['secondary', 'primary', 'tertiary', 'trunk', 'road', 'street', 'highway', 'motorway'].includes(t)) {
    return 'Road';
  }
  if (['historic', 'attraction', 'museum', 'monument', 'ruins', 'tourism', 'place_of_worship', 'park'].includes(t)) {
    return 'Landmark';
  }
  if (['city', 'town', 'county', 'state', 'administrative'].includes(t)) {
    return 'Area';
  }
  return t ? t.charAt(0).toUpperCase() + t.slice(1) : 'Place';
}

async function searchGeoapify(query: string, apiKey: string): Promise<GeocodeResult[]> {
  const filterParams = 'circle:73.8567,18.5204,50000';
  const biasParams = 'proximity:73.8567,18.5204';

  const apiUrl = new URL('https://api.geoapify.com/v1/geocode/autocomplete');
  apiUrl.searchParams.append('text', query);
  apiUrl.searchParams.append('apiKey', apiKey);
  apiUrl.searchParams.append('filter', filterParams);
  apiUrl.searchParams.append('bias', biasParams);
  apiUrl.searchParams.append('limit', '6');

  const response = await fetch(apiUrl.toString(), {
    next: { revalidate: 3600 },
  });

  if (!response.ok) {
    throw new Error(`Geoapify error status: ${response.status}`);
  }

  const data = await response.json();
  const features: GeoapifyFeature[] = Array.isArray(data?.features) ? data.features : [];

  return features.map((feature: GeoapifyFeature) => {
    const props = feature.properties || {};
    const lat = typeof props.lat === 'number' ? props.lat : parseFloat(String(props.lat || 0));
    const lon = typeof props.lon === 'number' ? props.lon : parseFloat(String(props.lon || 0));
    return {
      id: String(props.place_id || `${lat}_${lon}`),
      name: props.name || props.formatted?.split(',')[0] || 'Unknown Location',
      type: normalizeResultType(props.result_type || '', props.category),
      secondaryLabel: props.formatted || '',
      longitude: lon,
      latitude: lat,
      provider: 'geoapify' as const,
      inCoverage: checkInCoverage(lat, lon),
    };
  });
}

async function searchNominatim(query: string): Promise<GeocodeResult[]> {
  // Nominatim OpenStreetMap Search with Pune/PCMC regional bias
  const apiUrl = new URL('https://nominatim.openstreetmap.org/search');
  apiUrl.searchParams.append('q', query);
  apiUrl.searchParams.append('format', 'jsonv2');
  apiUrl.searchParams.append('addressdetails', '1');
  apiUrl.searchParams.append('limit', '6');
  apiUrl.searchParams.append('countrycodes', 'in');
  // Regional Pune viewbox: minLon, maxLat, maxLon, minLat
  apiUrl.searchParams.append('viewbox', '73.65,18.75,74.15,18.35');
  apiUrl.searchParams.append('bounded', '0');

  const response = await fetch(apiUrl.toString(), {
    headers: {
      'User-Agent': 'UEHIS-Environmental-Platform/1.0 (https://uehis.duckdns.org; research@uehis.org)',
      'Accept': 'application/json',
    },
    next: { revalidate: 3600 },
  });

  if (!response.ok) {
    throw new Error(`Nominatim error status: ${response.status}`);
  }

  const items = await response.json();
  if (!Array.isArray(items)) {
    return [];
  }

  return (items as NominatimItem[]).map((item: NominatimItem) => {
    const lat = parseFloat(item.lat || '0');
    const lon = parseFloat(item.lon || '0');
    const displayName = item.display_name || '';
    const name = item.name || displayName.split(',')[0] || 'Unknown Location';

    return {
      id: String(item.place_id || `${lat}_${lon}`),
      name,
      type: normalizeResultType(item.type || '', item.category),
      secondaryLabel: displayName,
      longitude: lon,
      latitude: lat,
      provider: 'nominatim' as const,
      inCoverage: checkInCoverage(lat, lon),
    };
  });
}

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

  const cleanQuery = q.trim();
  const apiKey = process.env.GEOAPIFY_API_KEY;

  try {
    let results: GeocodeResult[] = [];

    // Attempt Geoapify first if configured
    if (apiKey && apiKey.trim().length > 0) {
      try {
        results = await searchGeoapify(cleanQuery, apiKey.trim());
      } catch (geoapifyErr) {
        console.warn('Geoapify failed, falling back to Nominatim OpenStreetMap:', geoapifyErr);
        results = await searchNominatim(cleanQuery);
      }
    } else {
      // Nominatim as standard open geocoder
      results = await searchNominatim(cleanQuery);
    }

    // Sort to prioritize locations inside Pune evaluated coverage boundary
    results.sort((a, b) => {
      if (a.inCoverage && !b.inCoverage) return -1;
      if (!a.inCoverage && b.inCoverage) return 1;
      return 0;
    });

    return NextResponse.json(results);
  } catch (error) {
    console.error('Geocoding search failure:', error);
    return NextResponse.json(
      { error: 'Location search is temporarily unavailable. Please verify network connectivity.' },
      { status: 503 }
    );
  }
}

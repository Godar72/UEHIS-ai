export const dynamic = 'force-dynamic';

interface CachedTile {
  buffer: Buffer | null;
  etag: string;
}

const tileCache = new Map<string, CachedTile>();
const MAX_CACHE_ENTRIES = 1500;

export async function GET(
  request: Request,
  { params }: { params: Promise<{ z: string; x: string; y: string }> }
) {
  try {
    const { z, x, y } = await params;
    const yClean = y.replace('.pbf', '');
    const cacheKey = `${z}/${x}/${yClean}`;
    const clientEtag = request.headers.get('if-none-match');

    if (tileCache.has(cacheKey)) {
      const cached = tileCache.get(cacheKey)!;
      if (clientEtag && clientEtag === cached.etag) {
        return new Response(null, {
          status: 304,
          headers: {
            'ETag': cached.etag,
            'Access-Control-Allow-Origin': '*',
            'Cache-Control': 'public, max-age=3600, stale-while-revalidate=86400'
          }
        });
      }

      if (!cached.buffer) {
        return new Response(null, {
          status: 204,
          headers: {
            'ETag': cached.etag,
            'Access-Control-Allow-Origin': '*',
            'Cache-Control': 'public, max-age=3600, stale-while-revalidate=86400'
          }
        });
      }

      return new Response(new Uint8Array(cached.buffer), {
        headers: {
          'Content-Type': 'application/vnd.mapbox-vector-tile',
          'ETag': cached.etag,
          'Access-Control-Allow-Origin': '*',
          'Cache-Control': 'public, max-age=3600, stale-while-revalidate=86400'
        }
      });
    }
    
    const SUPABASE_URL = process.env.SUPABASE_INTERNAL_URL || process.env.NEXT_PUBLIC_SUPABASE_URL;
    const ANON_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
    if (!SUPABASE_URL || !ANON_KEY) throw new Error('Missing Supabase credentials');

    const res = await fetch(`${SUPABASE_URL}/rest/v1/rpc/mvt_carbon_blocks?z=${z}&x=${x}&y=${yClean}`, {
      headers: {
        'apikey': ANON_KEY,
        'Authorization': `Bearer ${ANON_KEY}`,
        'Accept': 'application/json'
      },
      cache: 'no-store'
    });

    if (!res.ok) {
      return new Response(null, { status: res.status });
    }

    const hexString = await res.json();
    
    if (hexString === '\\x' || !hexString) {
      const etag = `W/"carbon-empty-${z}-${x}-${yClean}"`;
      if (tileCache.size >= MAX_CACHE_ENTRIES) {
        const firstKey = tileCache.keys().next().value;
        if (firstKey) tileCache.delete(firstKey);
      }
      tileCache.set(cacheKey, { buffer: null, etag });

      return new Response(null, { 
        status: 204,
        headers: {
          'ETag': etag,
          'Access-Control-Allow-Origin': '*',
          'Cache-Control': 'public, max-age=3600, stale-while-revalidate=86400'
        }
      });
    }

    // Convert PostgreSQL hex format ("\x1234AB...") to buffer
    const cleanHex = hexString.startsWith('\\x') ? hexString.slice(2) : hexString;
    const buffer = Buffer.from(cleanHex, 'hex');
    const etag = `W/"carbon-${z}-${x}-${yClean}-${buffer.length}"`;

    if (tileCache.size >= MAX_CACHE_ENTRIES) {
      const firstKey = tileCache.keys().next().value;
      if (firstKey) tileCache.delete(firstKey);
    }
    tileCache.set(cacheKey, { buffer, etag });

    return new Response(new Uint8Array(buffer), {
      headers: {
        'Content-Type': 'application/vnd.mapbox-vector-tile',
        'ETag': etag,
        'Access-Control-Allow-Origin': '*',
        'Cache-Control': 'public, max-age=3600, stale-while-revalidate=86400'
      }
    });
  } catch (error) {
    console.error('Error fetching MVT:', error);
    return new Response(null, { status: 500 });
  }
}

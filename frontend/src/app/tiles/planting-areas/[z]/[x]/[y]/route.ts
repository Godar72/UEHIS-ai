import { createClient } from '@/lib/supabase/server';
import { verifyTileAuth } from '@/lib/supabase/tile-auth';

interface CachedTile {
  buffer: Buffer | null;
  etag: string;
}

const tileCache = new Map<string, CachedTile>();
const MAX_CACHE_ENTRIES = 1000;

export async function GET(
  request: Request,
  { params }: { params: Promise<{ z: string; x: string; y: string }> }
) {
  try {
    const { z, x, y } = await params;
    const yClean = y.replace('.pbf', '');

    // Require authentication & researcher/admin role
    const authResult = await verifyTileAuth(request);
    if (!authResult.authorized) {
      return new Response(JSON.stringify({ error: authResult.error || 'Unauthorized' }), {
        status: authResult.status || 401,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    const cacheKey = `${z}/${x}/${yClean}`;
    const clientEtag = request.headers.get('if-none-match');

    // Check server in-memory tile cache for authenticated user
    if (tileCache.has(cacheKey)) {
      const cached = tileCache.get(cacheKey)!;
      if (clientEtag && clientEtag === cached.etag) {
        return new Response(null, {
          status: 304,
          headers: {
            'ETag': cached.etag,
            'Access-Control-Allow-Origin': '*',
            'Cache-Control': 'private, max-age=3600, stale-while-revalidate=86400'
          }
        });
      }

      if (!cached.buffer) {
        return new Response(null, {
          status: 204,
          headers: {
            'ETag': cached.etag,
            'Access-Control-Allow-Origin': '*',
            'Cache-Control': 'private, max-age=3600, stale-while-revalidate=86400'
          }
        });
      }

      return new Response(new Uint8Array(cached.buffer), {
        headers: {
          'Content-Type': 'application/vnd.mapbox-vector-tile',
          'ETag': cached.etag,
          'Access-Control-Allow-Origin': '*',
          'Cache-Control': 'private, max-age=3600, stale-while-revalidate=86400'
        }
      });
    }

    // Call RPC using the authenticated user's Supabase context (not anon key)
    const supabase = await createClient();
    const { data: hexString, error } = await supabase.rpc('mvt_planting_candidate_areas', {
      z: parseInt(z),
      x: parseInt(x),
      y: parseInt(yClean)
    });

    if (error) {
      console.error('MVT planting areas RPC error:', error);
      return new Response(null, { status: 500 });
    }

    if (!hexString || hexString === '\\x') {
      const etag = `W/"pa-empty-${z}-${x}-${yClean}"`;
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
          'Cache-Control': 'private, max-age=3600, stale-while-revalidate=86400'
        }
      });
    }

    const cleanHex = hexString.startsWith('\\x') ? hexString.slice(2) : hexString;
    const buffer = Buffer.from(cleanHex, 'hex');
    const etag = `W/"pa-${z}-${x}-${yClean}-${buffer.length}"`;

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
        'Cache-Control': 'private, max-age=3600, stale-while-revalidate=86400'
      }
    });
  } catch (error) {
    console.error('Error fetching planting areas MVT:', error);
    return new Response(null, { status: 500 });
  }
}

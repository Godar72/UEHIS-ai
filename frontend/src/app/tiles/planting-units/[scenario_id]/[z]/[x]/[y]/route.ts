import { createClient } from '@/lib/supabase/server';
import { verifyTileAuth } from '@/lib/supabase/tile-auth';

interface CachedTile {
  buffer: Buffer | null;
  etag: string;
}

const tileCache = new Map<string, CachedTile>();
const MAX_CACHE_ENTRIES = 2000;

export async function GET(
  request: Request,
  { params }: { params: Promise<{ scenario_id: string; z: string; x: string; y: string }> }
) {
  try {
    const { scenario_id, z, x, y } = await params;
    const yClean = y.replace('.pbf', '');

    // Require authentication & researcher/admin role
    const authResult = await verifyTileAuth(request);
    if (!authResult.authorized) {
      return new Response(JSON.stringify({ error: authResult.error || 'Unauthorized' }), {
        status: authResult.status || 401,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    // Map string scenarios to actual UUIDs
    const scenarioUUIDs: Record<string, string> = {
      '100k': '583a8cea-95ea-4909-bd9a-8dbdc3e2a4cd',
      '250k': 'b2d9a3f2-1a4c-4e8d-9b5a-1c8e3f2a7b6d',
      '500k': 'f4a2b1c3-3d5e-4f6a-8b7c-2d9e4f5a6b7c',
    };
    const actual_uuid = scenarioUUIDs[scenario_id.toLowerCase()] || scenario_id;
    const cacheKey = `${actual_uuid}/${z}/${x}/${yClean}`;
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
    const { data: hexString, error } = await supabase.rpc('mvt_planting_units', {
      scenario_id_param: actual_uuid,
      z: parseInt(z),
      x: parseInt(x),
      y: parseInt(yClean)
    });

    if (error) {
      console.error('MVT planting units RPC error:', error);
      return new Response(null, { status: 500 });
    }

    if (!hexString || hexString === '\\x') {
      const etag = `W/"pu-empty-${z}-${x}-${yClean}"`;
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
    const etag = `W/"pu-${actual_uuid.slice(0, 8)}-${z}-${x}-${yClean}-${buffer.length}"`;

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
    console.error('Error fetching planting units MVT:', error);
    return new Response(null, { status: 500 });
  }
}

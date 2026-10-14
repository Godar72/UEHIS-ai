import { NextResponse } from 'next/server';
import { createClient } from '@/lib/supabase/server';
import crypto from 'crypto';

interface PlantingUnitRecord {
  unit_id: string;
  geom?: unknown;
  verification_status?: string;
}

export const PU_NAMESPACE = '49e464c3-0db8-5061-a5ff-945f95238334';

export function uuidv5(namespace: string, name: string): string {
  const nsBytes = Buffer.from(namespace.replace(/-/g, ''), 'hex');
  const hash = crypto.createHash('sha1').update(nsBytes).update(name).digest();
  hash[6] = (hash[6] & 0x0f) | 0x50; // version 5
  hash[8] = (hash[8] & 0x3f) | 0x80; // variant
  const hex = hash.subarray(0, 16).toString('hex');
  return [
    hex.slice(0, 8),
    hex.slice(8, 12),
    hex.slice(12, 16),
    hex.slice(16, 20),
    hex.slice(20),
  ].join('-');
}

export function isUtm43n(x: number, y: number): boolean {
  // Valid projected bounds for UTM Zone 43N in the Pune study area:
  // Easting: 100,000 to 900,000 m (Pune dataset spans ~368,000 - 397,000 m)
  // Northing: 1,000,000 to 3,000,000 m (Pune dataset spans ~2,038,000 - 2,060,000 m)
  return (
    typeof x === 'number' &&
    typeof y === 'number' &&
    !isNaN(x) &&
    !isNaN(y) &&
    x >= 100000 &&
    x <= 900000 &&
    y >= 1000000 &&
    y <= 3000000
  );
}

export function parseCoordinates(geom: unknown): [number, number] | null {
  if (!geom) return null;
  // 1. GeoJSON object format: { type: 'Point', coordinates: [x, y] }
  if (typeof geom === 'object' && geom !== null && 'coordinates' in geom) {
    const obj = geom as { type?: string; coordinates?: unknown; crs?: { properties?: { name?: string } } };
    if (obj.crs?.properties?.name && !obj.crs.properties.name.includes('32643')) {
      return null;
    }
    const coords = obj.coordinates;
    if (Array.isArray(coords) && coords.length >= 2) {
      const x = Number(coords[0]);
      const y = Number(coords[1]);
      if (isUtm43n(x, y)) return [x, y];
    }
  }
  // 2. String representation (JSON, WKT, or PostGIS EWKB hex)
  if (typeof geom === 'string') {
    const str = geom.trim();
    if (str.startsWith('{')) {
      try {
        const parsed = JSON.parse(str);
        if (parsed.crs?.properties?.name && !parsed.crs.properties.name.includes('32643')) {
          return null;
        }
        if (parsed.coordinates && Array.isArray(parsed.coordinates) && parsed.coordinates.length >= 2) {
          const x = Number(parsed.coordinates[0]);
          const y = Number(parsed.coordinates[1]);
          if (isUtm43n(x, y)) return [x, y];
        }
      } catch {
        // Not valid JSON
      }
    }
    // Check WKT / EWKT: e.g. "SRID=32643;POINT(385000 2045000)" or "POINT(385000 2045000)"
    const sridMatch = str.match(/SRID\s*=\s*(\d+)\s*;/i);
    if (sridMatch && sridMatch[1] !== '32643') {
      return null; // Reject explicit non-32643 SRID
    }
    const wktMatch = str.match(/POINT\s*\(\s*([-\d.]+)\s+([-\d.]+)\s*\)/i);
    if (wktMatch) {
      const x = Number(wktMatch[1]);
      const y = Number(wktMatch[2]);
      if (isUtm43n(x, y)) return [x, y];
    }
    // Check PostGIS EWKB hex string
    if (/^[0-9a-fA-F]{42,}$/.test(str)) {
      try {
        const buf = Buffer.from(str, 'hex');
        const isLittleEndian = buf.readUInt8(0) === 1;
        const typeInt = isLittleEndian ? buf.readUInt32LE(1) : buf.readUInt32BE(1);
        const geomType = typeInt & 0x1f;
        if (geomType !== 1) return null; // Must be Point
        const hasSrid = (typeInt & 0x20000000) !== 0;
        if (hasSrid) {
          const srid = isLittleEndian ? buf.readUInt32LE(5) : buf.readUInt32BE(5);
          if (srid !== 32643 && srid !== 0) return null; // Reject non-32643 SRID
        }
        const coordOffset = hasSrid ? 9 : 5;
        if (buf.length >= coordOffset + 16) {
          const x = isLittleEndian ? buf.readDoubleLE(coordOffset) : buf.readDoubleBE(coordOffset);
          const y = isLittleEndian ? buf.readDoubleLE(coordOffset + 8) : buf.readDoubleBE(coordOffset + 8);
          if (isUtm43n(x, y)) return [x, y];
        }
      } catch {
        // Hex parse failed
      }
    }
  }
  return null;
}

export async function GET(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;

    if (!id || id === 'Unknown') {
      return NextResponse.json({ error: 'Invalid planting unit ID' }, { status: 400 });
    }

    // Support both canonical UUID and PU_... string identifier
    const isUUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(id);
    let resolvedUnitUuid: string | null = null;

    if (isUUID) {
      resolvedUnitUuid = id.toLowerCase();
    } else if (id.startsWith('PU_')) {
      if (!/^PU_[a-zA-Z0-9_-]+$/.test(id)) {
        return NextResponse.json({ error: 'Invalid planting unit ID format' }, { status: 400 });
      }
      resolvedUnitUuid = uuidv5(PU_NAMESPACE, id);
    } else {
      return NextResponse.json({ error: 'Invalid planting unit ID format' }, { status: 400 });
    }

    // Authenticate user via Supabase session
    let supabase;
    try {
      supabase = await createClient();
    } catch {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }
    const { data: { user } } = await supabase.auth.getUser();

    if (!user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    // Verify researcher or admin role
    const { data: role } = await supabase.rpc('get_my_role');
    if (role !== 'researcher' && role !== 'admin') {
      return NextResponse.json({ error: 'Forbidden' }, { status: 403 });
    }

    // Query planting_units using normalized columns: unit_id, geom, verification_status
    // Note: properties column does not exist in production schema.
    const { data: unitData, error: unitError } = await supabase
      .from('planting_units')
      .select('unit_id, geom, verification_status')
      .eq('unit_id', resolvedUnitUuid)
      .maybeSingle();

    if (unitError || !unitData) {
      return NextResponse.json({ error: 'Planting unit not found' }, { status: 404 });
    }

    // Resolve parent block ID from projected UTM (EPSG:32643) coordinates
    let parentBlockId: string | null = null;
    let easting: number | null = null;
    let northing: number | null = null;
    let authoritativeUehi: number | null = null;
    let authoritativeRisk: string | null = null;

    const coords = parseCoordinates(unitData.geom);
    if (coords) {
      [easting, northing] = coords;
      const bx = Math.floor(easting / 250) * 250;
      const by = Math.floor(northing / 250) * 250;
      parentBlockId = `PN_${bx}_${by}`;

      // Query authoritative score and risk from uehi_blocks
      const { data: blockData } = await supabase
        .from('uehi_blocks')
        .select('block_id, uehi_score, risk_level')
        .eq('block_id', parentBlockId)
        .maybeSingle();

      if (blockData) {
        authoritativeUehi = blockData.uehi_score !== undefined && blockData.uehi_score !== null
          ? Number(blockData.uehi_score)
          : null;
        authoritativeRisk = blockData.risk_level ?? null;
      }
    }

    // Return normalized unit record and properties
    // Note: distance_to_water_m and candidate_class are not persisted on planting_units in production schema.
    const enrichedProperties = {
      planting_unit_id: id.startsWith('PU_') ? id : unitData.unit_id,
      parent_block_id: parentBlockId,
      uehi_score: authoritativeUehi,
      risk_level: authoritativeRisk,
      opportunity_class: 'Not available',
      candidate_class: null,
      distance_to_water_m: null,
      ownership_status: 'Verification required',
      utility_status: 'Verification required',
      planting_permission_status: 'Verification required',
      verification_status: unitData.verification_status || 'required',
      easting,
      northing,
    };

    return NextResponse.json({
      unit_id: unitData.unit_id,
      properties: enrichedProperties,
    });
  } catch (error) {
    console.error('Failed to fetch planting unit detail:', error);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}

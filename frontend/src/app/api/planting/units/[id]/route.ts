import { NextResponse } from 'next/server';
import { createClient } from '@/lib/supabase/server';
import {
  PU_NAMESPACE,
  uuidv5,
  isUtm43n,
  isValidUtm43nCrs,
  parseCoordinates,
} from '../../../../../lib/planting-unit-utils';
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

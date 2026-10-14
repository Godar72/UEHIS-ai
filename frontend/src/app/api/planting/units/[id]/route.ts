import { NextResponse } from 'next/server';
import { createClient } from '@/lib/supabase/server';

interface PlantingUnitRecord {
  unit_id: string;
  geom?: {
    coordinates: number[];
  };
  properties?: Record<string, unknown>;
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

    // Authenticate user via Supabase session
    const supabase = await createClient();
    const { data: { user } } = await supabase.auth.getUser();

    if (!user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    // Verify researcher or admin role
    const { data: role } = await supabase.rpc('get_my_role');
    if (role !== 'researcher' && role !== 'admin') {
      return NextResponse.json({ error: 'Forbidden' }, { status: 403 });
    }

    // Support both UUID primary key and PU_... string identifier
    const isUUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(id);
    let unitData: PlantingUnitRecord | null = null;

    if (isUUID) {
      const { data, error } = await supabase
        .from('planting_units')
        .select('unit_id, properties, geom')
        .eq('unit_id', id)
        .maybeSingle();

      if (!error && data) {
        unitData = data;
      }
    }

    if (!unitData) {
      const { data, error } = await supabase
        .from('planting_units')
        .select('unit_id, properties, geom')
        .filter('properties->>planting_unit_id', 'eq', id)
        .limit(1)
        .maybeSingle();

      if (!error && data) {
        unitData = data;
      }
    }

    if (!unitData) {
      return NextResponse.json({ error: 'Planting unit not found' }, { status: 404 });
    }

    // Resolve parent block ID from projected UTM (EPSG:32643) coordinates
    let parentBlockId: string | null = null;
    let easting: number | null = null;
    let northing: number | null = null;
    let authoritativeUehi: number | null = null;
    let authoritativeRisk: string | null = null;

    const coordinates = unitData.geom?.coordinates;
    if (coordinates && coordinates.length >= 2) {
      easting = Number(coordinates[0]);
      northing = Number(coordinates[1]);
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

    const rawClass = unitData.properties?.candidate_class || unitData.properties?.candidate_category || '';
    let opportunityClass = 'Not available';
    if (typeof rawClass === 'string' && rawClass) {
      if (rawClass.includes('public_like')) {
        opportunityClass = 'Public-like open space';
      } else if (rawClass.includes('context_dependent')) {
        opportunityClass = 'Context-dependent';
      } else if (rawClass.includes('other_open_space')) {
        opportunityClass = 'Other open space';
      } else {
        opportunityClass = rawClass;
      }
    }

    const rawWaterDist = unitData.properties?.distance_to_water_m;
    const distanceToWaterM = rawWaterDist !== undefined && rawWaterDist !== null
      ? Math.round(Number(rawWaterDist) * 10) / 10
      : null;

    const enrichedProperties = {
      ...unitData.properties,
      parent_block_id: parentBlockId,
      uehi_score: authoritativeUehi,
      risk_level: authoritativeRisk,
      opportunity_class: opportunityClass,
      candidate_class: unitData.properties?.candidate_class || rawClass,
      distance_to_water_m: distanceToWaterM,
      ownership_status: 'Verification required',
      utility_status: 'Verification required',
      planting_permission_status: 'Verification required',
      easting,
      northing
    };

    return NextResponse.json({
      unit_id: unitData.unit_id,
      properties: enrichedProperties
    });
  } catch (error) {
    console.error('Failed to fetch planting unit detail:', error);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}

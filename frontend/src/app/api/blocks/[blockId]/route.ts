import { NextResponse } from 'next/server';
import { createAdminClient } from '@/lib/supabase/admin';
import { rateLimiters, getClientIP, rateLimitResponse } from '@/lib/rate-limit';

export async function GET(
  request: Request,
  { params }: { params: Promise<{ blockId: string }> }
) {
  try {
    // Rate limit: block detail
    const ip = getClientIP(request);
    const rl = rateLimiters.blockDetail(ip);
    if (!rl.allowed) return rateLimitResponse(rl.retryAfterMs);

    const { blockId } = await params;

    // Validate blockId format — should be alphanumeric + underscore/dash
    if (!blockId || !/^[A-Za-z0-9_-]{1,50}$/.test(blockId)) {
      return NextResponse.json({ error: 'Invalid block ID' }, { status: 400 });
    }

    const supabaseAdmin = createAdminClient();

    // Query full block detail via get_block_detail RPC
    const { data: blockDetail, error: blockError } = await supabaseAdmin
      .rpc('get_block_detail', { p_block_id: blockId });

    if (blockError || !blockDetail) {
      return NextResponse.json({ error: 'Block not found' }, { status: 404 });
    }

    // Query carbon details from carbon_blocks
    const { data: carbonBlock } = await supabaseAdmin
      .from('carbon_blocks')
      .select('canopy_area_m2, estimated_tree_count, above_ground_biomass_kg, standing_carbon_stock')
      .eq('block_id', blockId)
      .maybeSingle();

    const block = blockDetail;

    return NextResponse.json({
      block_id: block.block_id,
      uehi_score: block.uehi_score,
      risk_level: block.risk_level,
      factors: {
        ndvi: block.ndvi,
        tree_density: block.tree_density,
        impervious_surfaces: block.impervious_surfaces,
        temperature: block.temperature,
        population_exposure: block.population_exposure,
        aqi: block.pm25,
      },
      co2_tonnes: carbonBlock?.standing_carbon_stock ?? block.standing_carbon_stock ?? null,
      carbon_details: carbonBlock ? {
        canopy_area_m2: carbonBlock.canopy_area_m2 ?? null,
        estimated_tree_count: carbonBlock.estimated_tree_count ?? null,
        above_ground_biomass_kg: carbonBlock.above_ground_biomass_kg ?? null,
      } : null,
    });
  } catch (error) {
    console.error('Error in block API proxy:', error);
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}

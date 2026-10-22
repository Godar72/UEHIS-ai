import { NextResponse } from 'next/server';
import { createAdminClient } from '@/lib/supabase/admin';
import { createClient as createServerSupabaseClient } from '@/lib/supabase/server';
import { rateLimiters, getClientIP, rateLimitResponse } from '@/lib/rate-limit';

export interface BlockFactorAttributes {
  ndvi: number | null;
  tree_density: number | null;
  impervious_surfaces: number | null;
  temperature: number | null;
  population_exposure: number | null;
  aqi: number | null;
}

export interface BlockResolvedResponse {
  block_id: string;
  uehi_score: number | null;
  risk_level: string | null;
  factors: BlockFactorAttributes;
  co2_tonnes: number | null;
  carbon_details?: {
    canopy_area_m2: number | null;
    estimated_tree_count: number | null;
    above_ground_biomass_kg: number | null;
  } | null;
}

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

    let resolvedData: BlockResolvedResponse | null = null;
    let dataSource = '';
    const diagnosticErrors: string[] = [];

    // ── Tier 1: Supabase Admin Client via get_block_detail RPC ───────
    if (process.env.SUPABASE_SERVICE_ROLE_KEY) {
      try {
        const supabaseAdmin = createAdminClient();
        const { data: blockDetail, error: blockError } = await supabaseAdmin
          .rpc('get_block_detail', { p_block_id: blockId });

        if (!blockError && blockDetail) {
          const { data: carbonBlock } = await supabaseAdmin
            .from('carbon_blocks')
            .select('canopy_area_m2, estimated_tree_count, above_ground_biomass_kg, standing_carbon_stock')
            .eq('block_id', blockId)
            .maybeSingle();

          resolvedData = {
            block_id: blockDetail.block_id,
            uehi_score: blockDetail.uehi_score ?? null,
            risk_level: blockDetail.risk_level ?? null,
            factors: {
              ndvi: blockDetail.ndvi ?? null,
              tree_density: blockDetail.tree_density ?? null,
              impervious_surfaces: blockDetail.impervious_surfaces ?? null,
              temperature: blockDetail.temperature ?? null,
              population_exposure: blockDetail.population_exposure ?? null,
              aqi: blockDetail.pm25 ?? null,
            },
            co2_tonnes: carbonBlock?.standing_carbon_stock ?? blockDetail.standing_carbon_stock ?? null,
            carbon_details: carbonBlock ? {
              canopy_area_m2: carbonBlock.canopy_area_m2 ?? null,
              estimated_tree_count: carbonBlock.estimated_tree_count ?? null,
              above_ground_biomass_kg: carbonBlock.above_ground_biomass_kg ?? null,
            } : null,
          };
          dataSource = 'supabase-admin';
        } else if (blockError) {
          diagnosticErrors.push(`supabase_admin_rpc: ${blockError.message || blockError.code || 'unknown'}`);
        }
      } catch (adminErr) {
        diagnosticErrors.push(`supabase_admin_init: ${adminErr instanceof Error ? adminErr.message : 'failed'}`);
      }
    } else {
      diagnosticErrors.push('supabase_admin: SUPABASE_SERVICE_ROLE_KEY not configured');
    }

    // ── Tier 2: Internal Python Microservice (FastAPI + PostGIS) ────
    if (!resolvedData) {
      try {
        const pythonServiceUrl = process.env.PYTHON_SERVICE_URL || process.env.UEHIS_API_URL || 'http://127.0.0.1:8000';
        const internalKey = process.env.UEHIS_API_KEY || '';

        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 8000);

        const pyResponse = await fetch(`${pythonServiceUrl.replace(/\/$/, '')}/blocks/${encodeURIComponent(blockId)}`, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
            ...(internalKey ? { 'X-API-Key': internalKey } : {}),
          },
          signal: controller.signal,
        });

        clearTimeout(timeout);

        if (pyResponse.ok) {
          const pyData = await pyResponse.json();
          resolvedData = {
            block_id: pyData.block_id,
            uehi_score: pyData.uehi_score ?? null,
            risk_level: pyData.risk_level ?? null,
            factors: {
              ndvi: pyData.factors?.ndvi ?? null,
              tree_density: pyData.factors?.tree_density ?? null,
              impervious_surfaces: pyData.factors?.impervious_surfaces ?? null,
              temperature: pyData.factors?.temperature ?? null,
              population_exposure: pyData.factors?.population_exposure ?? null,
              aqi: pyData.factors?.aqi ?? null,
            },
            co2_tonnes: pyData.co2_tonnes ?? null,
            carbon_details: pyData.carbon_details ?? (pyData.agb_kg !== undefined ? {
              canopy_area_m2: null,
              estimated_tree_count: null,
              above_ground_biomass_kg: pyData.agb_kg,
            } : null),
          };
          dataSource = 'python-microservice';
        } else if (pyResponse.status === 404) {
          return NextResponse.json({ error: `Block "${blockId}" not found in Pune study area.` }, { status: 404 });
        } else {
          diagnosticErrors.push(`python_service_status_${pyResponse.status}`);
        }
      } catch (pyErr) {
        diagnosticErrors.push(`python_service: ${pyErr instanceof Error ? pyErr.name : 'unreachable'}`);
      }
    }

    // ── Tier 3: Supabase Authenticated / User Session Client ────────
    if (!resolvedData) {
      try {
        const supabaseUser = await createServerSupabaseClient();
        const { data: userBlock, error: userBlockError } = await supabaseUser
          .rpc('get_block_detail', { p_block_id: blockId });

        if (!userBlockError && userBlock) {
          resolvedData = {
            block_id: userBlock.block_id,
            uehi_score: userBlock.uehi_score ?? null,
            risk_level: userBlock.risk_level ?? null,
            factors: {
              ndvi: userBlock.ndvi ?? null,
              tree_density: userBlock.tree_density ?? null,
              impervious_surfaces: userBlock.impervious_surfaces ?? null,
              temperature: userBlock.temperature ?? null,
              population_exposure: userBlock.population_exposure ?? null,
              aqi: userBlock.pm25 ?? null,
            },
            co2_tonnes: userBlock.standing_carbon_stock ?? null,
            carbon_details: null,
          };
          dataSource = 'supabase-session';
        } else if (userBlockError) {
          diagnosticErrors.push(`supabase_user_rpc: ${userBlockError.message || userBlockError.code || 'unknown'}`);
        }
      } catch (userErr) {
        diagnosticErrors.push(`supabase_user_init: ${userErr instanceof Error ? userErr.message : 'failed'}`);
      }
    }

    // ── Tier 4: Public Supabase RPC (get_block_detail_public) ───────
    if (!resolvedData) {
      try {
        const supabaseUser = await createServerSupabaseClient();
        const { data: publicBlock, error: pubErr } = await supabaseUser
          .rpc('get_block_detail_public', { p_block_id: blockId });

        if (!pubErr && publicBlock) {
          resolvedData = {
            block_id: publicBlock.block_id,
            uehi_score: publicBlock.uehi_score ?? null,
            risk_level: publicBlock.risk_level ?? null,
            factors: {
              ndvi: null,
              tree_density: null,
              impervious_surfaces: null,
              temperature: null,
              population_exposure: null,
              aqi: null,
            },
            co2_tonnes: null,
            carbon_details: null,
          };
          dataSource = 'supabase-public-rpc';
        } else if (pubErr) {
          diagnosticErrors.push(`supabase_public_rpc: ${pubErr.message || pubErr.code || 'unknown'}`);
        }
      } catch (pubErr) {
        diagnosticErrors.push(`supabase_public_init: ${pubErr instanceof Error ? pubErr.message : 'failed'}`);
      }
    }

    // If resolved via any tier, return HTTP 200 with cache and provenance header
    if (resolvedData) {
      return NextResponse.json(resolvedData, {
        status: 200,
        headers: {
          'Cache-Control': 'public, max-age=300, stale-while-revalidate=600',
          'X-Data-Source': dataSource,
        },
      });
    }

    // If not found anywhere
    console.warn(`[BLOCK_API_DIAGNOSTIC] Block ${blockId} could not be resolved across tiers:`, diagnosticErrors.join(' | '));
    return NextResponse.json({ error: `Block "${blockId}" not found in Pune study area.` }, { status: 404 });

  } catch (error) {
    console.error('[BLOCK_API_FATAL] Unexpected error in block API route:', error instanceof Error ? error.message : error);
    return NextResponse.json({ error: 'Block analysis is temporarily unavailable.' }, { status: 500 });
  }
}

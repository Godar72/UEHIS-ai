import { NextResponse } from 'next/server';
import { createClient } from '@/lib/supabase/server';

export const dynamic = 'force-dynamic';

const VALID_ACTIVITY_TYPES = new Set([
  'viewed_block',
  'analyzed_study_area',
  'viewed_carbon',
  'viewed_scenario',
  'viewed_planting_opportunity',
  'exported_report',
  'research_saved',
]);

const VALID_CATEGORIES = new Set(['explore', 'carbon', 'analysis', 'planting']);
const VALID_ACTIONS = new Set(['viewed', 'analyzed', 'saved', 'exported']);
const VALID_ENTITY_TYPES = new Set(['block', 'study_area', 'ward', 'scenario', 'planting_unit', 'report', 'session']);

const ALLOWED_METADATA_KEYS = new Set([
  'block_id',
  'uehi_score',
  'risk_level',
  'ward_name',
  'location_name',
  'boundary_type',
  'mean_uehi',
  'total_blocks',
  'reopen_url',
  'scenario_id',
  'scenario_name',
  'unit_id',
  'opportunity_class',
  'format',
]);

function sanitizeMetadata(rawMeta: unknown): Record<string, unknown> {
  if (!rawMeta || typeof rawMeta !== 'object' || Array.isArray(rawMeta)) {
    return {};
  }
  const clean: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(rawMeta)) {
    if (ALLOWED_METADATA_KEYS.has(k)) {
      if (typeof v === 'string' && v.length <= 500) {
        clean[k] = v;
      } else if (typeof v === 'number' || typeof v === 'boolean') {
        clean[k] = v;
      } else if (Array.isArray(v) && v.every(item => typeof item === 'number' || typeof item === 'string')) {
        clean[k] = v.slice(0, 10);
      }
    }
  }
  return clean;
}

/**
 * GET /api/profile/activity
 * Retrieves the authenticated user's research activity with pagination & category filtering.
 */
export async function GET(request: Request) {
  try {
    const supabase = await createClient();
    const { data: { user }, error: authError } = await supabase.auth.getUser();

    if (authError || !user) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401, headers: { 'Cache-Control': 'private, no-store, max-age=0' } }
      );
    }

    const { searchParams } = new URL(request.url);
    const categoryParam = searchParams.get('category') || 'all';
    const pageParam = parseInt(searchParams.get('page') || '1', 10);
    const limitParam = parseInt(searchParams.get('limit') || '10', 10);
    const startDateParam = searchParams.get('startDate');
    const endDateParam = searchParams.get('endDate');

    const page = Number.isInteger(pageParam) && pageParam > 0 ? pageParam : 1;
    const limit = Number.isInteger(limitParam) && limitParam > 0 ? Math.min(limitParam, 50) : 10;
    const offset = (page - 1) * limit;

    // Check role for planting category access
    if (categoryParam === 'planting') {
      const { data: role } = await supabase.rpc('get_my_role');
      if (!role || !['researcher', 'admin'].includes(role)) {
        return NextResponse.json(
          { error: 'Forbidden: planting activity is restricted to authorized roles' },
          { status: 403, headers: { 'Cache-Control': 'private, no-store, max-age=0' } }
        );
      }
    }

    // Build query with RLS enforcement
    let query = supabase
      .from('user_activity')
      .select('id, activity_type, category, action_type, title, description, entity_type, entity_id, metadata, created_at', { count: 'exact' })
      .eq('user_id', user.id);

    if (categoryParam !== 'all' && VALID_CATEGORIES.has(categoryParam)) {
      query = query.eq('category', categoryParam);
    }

    if (startDateParam) {
      const start = new Date(startDateParam);
      if (!isNaN(start.getTime())) {
        query = query.gte('created_at', start.toISOString());
      }
    }

    if (endDateParam) {
      const end = new Date(endDateParam);
      if (!isNaN(end.getTime())) {
        query = query.lte('created_at', end.toISOString());
      }
    }

    query = query.order('created_at', { ascending: false }).range(offset, offset + limit - 1);

    const { data: activities, error: queryError, count } = await query;

    if (queryError) {
      console.error('Activity query error:', queryError);
      return NextResponse.json(
        { error: 'Failed to retrieve research activities' },
        { status: 500, headers: { 'Cache-Control': 'private, no-store, max-age=0' } }
      );
    }

    const total = count || 0;
    const hasMore = offset + (activities?.length || 0) < total;

    return NextResponse.json(
      {
        activities: activities || [],
        total,
        page,
        limit,
        hasMore,
      },
      {
        headers: {
          'Cache-Control': 'private, no-store, max-age=0',
        },
      }
    );
  } catch (error) {
    console.error('GET /api/profile/activity error:', error);
    return NextResponse.json(
      { error: 'Internal Server Error' },
      { status: 500, headers: { 'Cache-Control': 'private, no-store, max-age=0' } }
    );
  }
}

/**
 * POST /api/profile/activity
 * Records a verified research action for the authenticated user.
 */
export async function POST(request: Request) {
  try {
    const supabase = await createClient();
    const { data: { user }, error: authError } = await supabase.auth.getUser();

    if (authError || !user) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401, headers: { 'Cache-Control': 'private, no-store, max-age=0' } }
      );
    }

    const body = await request.json().catch(() => null);
    if (!body) {
      return NextResponse.json({ error: 'Invalid request body' }, { status: 400 });
    }

    const { activity_type, category, action_type, title, description, entity_type, entity_id, metadata } = body;

    // Validate activity type
    if (!activity_type || typeof activity_type !== 'string' || !VALID_ACTIVITY_TYPES.has(activity_type)) {
      return NextResponse.json({ error: 'Invalid or unsupported activity_type' }, { status: 400 });
    }

    // Validate category
    if (!category || typeof category !== 'string' || !VALID_CATEGORIES.has(category)) {
      return NextResponse.json({ error: 'Invalid category' }, { status: 400 });
    }

    // Validate action type
    const action = action_type && VALID_ACTIONS.has(action_type) ? action_type : 'viewed';

    // Validate title
    if (!title || typeof title !== 'string' || title.trim().length === 0 || title.length > 120) {
      return NextResponse.json({ error: 'Title is required (max 120 chars)' }, { status: 400 });
    }

    // Validate optional description
    const desc = typeof description === 'string' ? description.slice(0, 300) : null;

    // Validate optional entity type & id
    const entType = typeof entity_type === 'string' && VALID_ENTITY_TYPES.has(entity_type) ? entity_type : null;
    const entId = typeof entity_id === 'string' ? entity_id.slice(0, 100) : null;

    // Clean metadata
    const cleanMeta = sanitizeMetadata(metadata);

    // Enforce role authorization for privileged planting activities
    if (category === 'planting' || activity_type === 'viewed_planting_opportunity') {
      const { data: role } = await supabase.rpc('get_my_role');
      if (!role || !['researcher', 'admin'].includes(role)) {
        return NextResponse.json(
          { error: 'Forbidden: planting activity requires researcher or admin role' },
          { status: 403 }
        );
      }
    }

    // Call secure record_user_activity RPC
    const { data: result, error: rpcError } = await supabase.rpc('record_user_activity', {
      p_activity_type: activity_type,
      p_category: category,
      p_action_type: action,
      p_title: title.trim(),
      p_description: desc,
      p_entity_type: entType,
      p_entity_id: entId,
      p_metadata: cleanMeta,
    });

    if (rpcError) {
      console.error('record_user_activity RPC error:', rpcError);
      return NextResponse.json({ error: 'Failed to record activity' }, { status: 500 });
    }

    return NextResponse.json({
      success: true,
      deduplicated: result?.deduplicated || false,
      id: result?.id,
    });
  } catch (error) {
    console.error('POST /api/profile/activity error:', error);
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}

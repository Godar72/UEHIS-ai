/**
 * UEHIS Research Activity Recording Service
 * Provides typed, centralized, asynchronous activity recording with in-memory deduplication.
 * Designed to ensure scientific and map operations are never blocked or degraded if recording fails.
 */

export interface RecordActivityParams {
  activity_type:
    | 'viewed_block'
    | 'analyzed_study_area'
    | 'viewed_carbon'
    | 'viewed_scenario'
    | 'viewed_planting_opportunity'
    | 'exported_report'
    | 'research_saved';
  category: 'explore' | 'carbon' | 'analysis' | 'planting';
  action_type?: 'viewed' | 'analyzed' | 'saved' | 'exported';
  title: string;
  description?: string;
  entity_type?: 'block' | 'study_area' | 'ward' | 'scenario' | 'planting_unit' | 'report' | 'session';
  entity_id?: string;
  metadata?: Record<string, unknown>;
}

// Client-side in-memory deduplication map (key -> timestamp)
const recentActivities = new Map<string, number>();
const CLIENT_DEDUP_WINDOW_MS = 30_000; // 30 seconds

export async function recordActivity(params: RecordActivityParams): Promise<void> {
  try {
    if (typeof window === 'undefined') return;

    // Build deduplication key
    const dedupKey = `${params.activity_type}:${params.entity_id || 'none'}`;
    const now = Date.now();
    const lastRecorded = recentActivities.get(dedupKey);

    if (lastRecorded && now - lastRecorded < CLIENT_DEDUP_WINDOW_MS) {
      return; // Skip repeated client request within deduplication window
    }

    recentActivities.set(dedupKey, now);

    // Evict old entries periodically
    if (recentActivities.size > 200) {
      for (const [k, time] of recentActivities.entries()) {
        if (now - time > CLIENT_DEDUP_WINDOW_MS) {
          recentActivities.delete(k);
        }
      }
    }

    // Fire non-blocking request to the server activity endpoint
    const response = await fetch('/api/profile/activity', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        ...params,
        action_type: params.action_type || 'viewed',
      }),
    });

    if (!response.ok && process.env.NODE_ENV === 'development') {
      const err = await response.json().catch(() => ({}));
      console.debug('[UEHIS Activity Notice]:', err);
    }
  } catch (err) {
    if (process.env.NODE_ENV === 'development') {
      console.debug('[UEHIS Activity Exception]:', err);
    }
  }
}

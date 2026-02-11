import { ref, onMounted } from 'vue';
import { API_BASE_URL } from '../config';

// ── Types ────────────────────────────────────────────────────────

export interface TierSummary {
  cost: number;
  input_tokens: number;
  output_tokens: number;
  events: number;
}

export interface AgentSummary {
  cost: number;
  input_tokens: number;
  output_tokens: number;
  events: number;
  tier: string;
}

export interface CostSummary {
  period: string;
  total_cost: number;
  total_input_tokens: number;
  total_output_tokens: number;
  event_count: number;
  session_count: number;
  by_tier: Record<string, TierSummary>;
  by_agent: Record<string, AgentSummary>;
}

export interface DailySummary extends CostSummary {
  date: string;
}

export interface CostProjection {
  projection_days: number;
  avg_daily_cost: number;
  projected_total: number;
  confidence: 'no_data' | 'low' | 'medium' | 'high';
  based_on_days: number;
  tier_breakdown: Record<string, { avg_daily: number; projected: number }>;
}

// ── Composable ───────────────────────────────────────────────────

export function useCostTracking() {
  const summary = ref<CostSummary | null>(null);
  const dailyBreakdown = ref<DailySummary[]>([]);
  const projection = ref<CostProjection | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);

  async function fetchSummary(period: string = 'week') {
    loading.value = true;
    error.value = null;
    try {
      const res = await fetch(`${API_BASE_URL}/api/costs/summary?period=${period}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      summary.value = await res.json();
    } catch (err: any) {
      error.value = err.message || 'Failed to fetch cost summary';
      summary.value = null;
    } finally {
      loading.value = false;
    }
  }

  async function fetchDailyBreakdown(days: number = 7) {
    loading.value = true;
    error.value = null;
    try {
      const res = await fetch(`${API_BASE_URL}/api/costs/daily?days=${days}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      dailyBreakdown.value = await res.json();
    } catch (err: any) {
      error.value = err.message || 'Failed to fetch daily breakdown';
      dailyBreakdown.value = [];
    } finally {
      loading.value = false;
    }
  }

  async function fetchProjection(days: number = 7) {
    loading.value = true;
    error.value = null;
    try {
      const res = await fetch(`${API_BASE_URL}/api/costs/projection?days=${days}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      projection.value = await res.json();
    } catch (err: any) {
      error.value = err.message || 'Failed to fetch projection';
      projection.value = null;
    } finally {
      loading.value = false;
    }
  }

  async function fetchAll(period: string = 'week', days: number = 7) {
    loading.value = true;
    error.value = null;
    try {
      const [summaryRes, dailyRes, projRes] = await Promise.allSettled([
        fetch(`${API_BASE_URL}/api/costs/summary?period=${period}`),
        fetch(`${API_BASE_URL}/api/costs/daily?days=${days}`),
        fetch(`${API_BASE_URL}/api/costs/projection?days=${days}`),
      ]);

      if (summaryRes.status === 'fulfilled' && summaryRes.value.ok) {
        summary.value = await summaryRes.value.json();
      }
      if (dailyRes.status === 'fulfilled' && dailyRes.value.ok) {
        dailyBreakdown.value = await dailyRes.value.json();
      }
      if (projRes.status === 'fulfilled' && projRes.value.ok) {
        projection.value = await projRes.value.json();
      }
    } catch (err: any) {
      error.value = err.message || 'Failed to fetch cost data';
    } finally {
      loading.value = false;
    }
  }

  return {
    summary,
    dailyBreakdown,
    projection,
    loading,
    error,
    fetchSummary,
    fetchDailyBreakdown,
    fetchProjection,
    fetchAll,
  };
}

/**
 * Cost Tracking Module for Observability Server
 *
 * Reads cost_tracking.jsonl from ~/.claude/logs/ and provides
 * summary, daily breakdown, and projection APIs.
 */

import { homedir } from 'node:os';
import { join } from 'node:path';

// ── Types ────────────────────────────────────────────────────────

export interface CostEntry {
  timestamp: string;
  epoch_ms: number;
  session_id: string;
  model: string;
  tier: string;
  input_tokens: number;
  output_tokens: number;
  cost_usd: number;
  agent_name: string;
  event_type: string;
  tool_name: string;
  metadata?: Record<string, any>;
}

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

// ── Constants ────────────────────────────────────────────────────

const COST_LOG_PATH = join(homedir(), '.claude', 'logs', 'cost_tracking.jsonl');

// ── Core Functions ───────────────────────────────────────────────

/**
 * Read and parse all entries from the cost tracking JSONL file.
 */
async function readEntries(): Promise<CostEntry[]> {
  try {
    const file = Bun.file(COST_LOG_PATH);
    if (!(await file.exists())) {
      return [];
    }
    const text = await file.text();
    const entries: CostEntry[] = [];
    for (const line of text.split('\n')) {
      const trimmed = line.trim();
      if (!trimmed) continue;
      try {
        entries.push(JSON.parse(trimmed));
      } catch {
        // skip malformed lines
      }
    }
    return entries;
  } catch {
    return [];
  }
}

/**
 * Filter entries by time range.
 */
function filterByTime(
  entries: CostEntry[],
  since?: string,
  until?: string
): CostEntry[] {
  return entries.filter((e) => {
    if (since && e.timestamp < since) return false;
    if (until && e.timestamp > until) return false;
    return true;
  });
}

/**
 * Build a cost summary from a list of entries.
 */
function buildSummary(entries: CostEntry[], period: string): CostSummary {
  const byTier: Record<string, TierSummary> = {};
  const byAgent: Record<string, AgentSummary> = {};
  const sessions = new Set<string>();
  let totalCost = 0;
  let totalInput = 0;
  let totalOutput = 0;

  for (const e of entries) {
    const tier = e.tier || 'unknown';
    const agent = e.agent_name || 'unknown';

    totalCost += e.cost_usd || 0;
    totalInput += e.input_tokens || 0;
    totalOutput += e.output_tokens || 0;
    sessions.add(e.session_id);

    if (!byTier[tier]) {
      byTier[tier] = { cost: 0, input_tokens: 0, output_tokens: 0, events: 0 };
    }
    byTier[tier].cost += e.cost_usd || 0;
    byTier[tier].input_tokens += e.input_tokens || 0;
    byTier[tier].output_tokens += e.output_tokens || 0;
    byTier[tier].events += 1;

    if (!byAgent[agent]) {
      byAgent[agent] = { cost: 0, input_tokens: 0, output_tokens: 0, events: 0, tier };
    }
    byAgent[agent].cost += e.cost_usd || 0;
    byAgent[agent].input_tokens += e.input_tokens || 0;
    byAgent[agent].output_tokens += e.output_tokens || 0;
    byAgent[agent].events += 1;
  }

  // Round costs
  totalCost = Math.round(totalCost * 1e6) / 1e6;
  for (const t of Object.values(byTier)) {
    t.cost = Math.round(t.cost * 1e6) / 1e6;
  }
  for (const a of Object.values(byAgent)) {
    a.cost = Math.round(a.cost * 1e6) / 1e6;
  }

  return {
    period,
    total_cost: totalCost,
    total_input_tokens: totalInput,
    total_output_tokens: totalOutput,
    event_count: entries.length,
    session_count: sessions.size,
    by_tier: byTier,
    by_agent: byAgent,
  };
}

// ── Public API ───────────────────────────────────────────────────

/**
 * Get cost summary for a given period.
 */
export async function getCostSummary(
  period: 'today' | 'yesterday' | 'week' | 'month' | 'all' = 'week'
): Promise<CostSummary> {
  const entries = await readEntries();
  const now = new Date();

  let since: string | undefined;
  let until: string | undefined;

  if (period === 'today') {
    since = new Date(now.getFullYear(), now.getMonth(), now.getDate()).toISOString();
  } else if (period === 'yesterday') {
    const yd = new Date(now.getFullYear(), now.getMonth(), now.getDate() - 1);
    since = yd.toISOString();
    until = new Date(now.getFullYear(), now.getMonth(), now.getDate()).toISOString();
  } else if (period === 'week') {
    since = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000).toISOString();
  } else if (period === 'month') {
    since = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000).toISOString();
  }
  // 'all' => no filter

  const filtered = filterByTime(entries, since, until);
  return buildSummary(filtered, period);
}

/**
 * Get daily cost breakdown for the last N days.
 */
export async function getDailyBreakdown(days: number = 7): Promise<DailySummary[]> {
  const entries = await readEntries();
  const now = new Date();
  const result: DailySummary[] = [];

  for (let i = 0; i < days; i++) {
    const dayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate() - i);
    const dayEnd = new Date(dayStart.getTime() + 24 * 60 * 60 * 1000);
    const sinceStr = dayStart.toISOString();
    const untilStr = dayEnd.toISOString();

    const dayEntries = filterByTime(entries, sinceStr, untilStr);
    const summary = buildSummary(dayEntries, dayStart.toISOString().slice(0, 10));

    result.push({
      ...summary,
      date: dayStart.toISOString().slice(0, 10),
    });
  }

  return result;
}

/**
 * Get cost projection for the next N days based on recent usage.
 */
export async function getCostProjection(days: number = 7): Promise<CostProjection> {
  const daily = await getDailyBreakdown(7);

  const activeDays = daily.filter((d) => d.total_cost > 0);

  if (activeDays.length === 0) {
    return {
      projection_days: days,
      avg_daily_cost: 0,
      projected_total: 0,
      confidence: 'no_data',
      based_on_days: 0,
      tier_breakdown: {},
    };
  }

  const avgDaily =
    activeDays.reduce((sum, d) => sum + d.total_cost, 0) / activeDays.length;
  const projected = Math.round(avgDaily * days * 1e4) / 1e4;

  // Tier breakdown
  const tierTotals: Record<string, number> = {};
  for (const d of activeDays) {
    for (const [tierName, tierData] of Object.entries(d.by_tier)) {
      tierTotals[tierName] = (tierTotals[tierName] || 0) + tierData.cost;
    }
  }

  const tierBreakdown: Record<string, { avg_daily: number; projected: number }> = {};
  for (const [tierName, total] of Object.entries(tierTotals)) {
    const avg = total / activeDays.length;
    tierBreakdown[tierName] = {
      avg_daily: Math.round(avg * 1e4) / 1e4,
      projected: Math.round(avg * days * 1e4) / 1e4,
    };
  }

  const confidence: CostProjection['confidence'] =
    activeDays.length >= 5 ? 'high' : activeDays.length >= 3 ? 'medium' : 'low';

  return {
    projection_days: days,
    avg_daily_cost: Math.round(avgDaily * 1e4) / 1e4,
    projected_total: projected,
    confidence,
    based_on_days: activeDays.length,
    tier_breakdown: tierBreakdown,
  };
}

/**
 * Record a cost entry (called from POST /api/costs endpoint).
 */
export async function recordCostEntry(entry: Partial<CostEntry>): Promise<CostEntry> {
  const now = new Date();
  const full: CostEntry = {
    timestamp: entry.timestamp || now.toISOString(),
    epoch_ms: entry.epoch_ms || now.getTime(),
    session_id: entry.session_id || 'unknown',
    model: entry.model || 'unknown',
    tier: entry.tier || resolveTier(entry.model || ''),
    input_tokens: entry.input_tokens || 0,
    output_tokens: entry.output_tokens || 0,
    cost_usd: entry.cost_usd || 0,
    agent_name: entry.agent_name || '',
    event_type: entry.event_type || '',
    tool_name: entry.tool_name || '',
  };

  // Calculate cost if not provided
  if (full.cost_usd === 0 && (full.input_tokens > 0 || full.output_tokens > 0)) {
    full.cost_usd = calculateCost(full.input_tokens, full.output_tokens, full.model);
  }

  const { appendFile, mkdir } = await import('node:fs/promises');
  const { dirname } = await import('node:path');
  await mkdir(dirname(COST_LOG_PATH), { recursive: true });
  await appendFile(COST_LOG_PATH, JSON.stringify(full) + '\n');

  return full;
}

// ── Helpers ──────────────────────────────────────────────────────

const PRICING: Record<string, { input: number; output: number }> = {
  haiku: { input: 0.25, output: 1.25 },
  sonnet: { input: 3.0, output: 15.0 },
  opus: { input: 15.0, output: 75.0 },
};

function resolveTier(model: string): string {
  const lower = model.toLowerCase();
  if (lower.includes('haiku')) return 'haiku';
  if (lower.includes('sonnet')) return 'sonnet';
  if (lower.includes('opus')) return 'opus';
  return 'unknown';
}

function calculateCost(inputTokens: number, outputTokens: number, model: string): number {
  const tier = resolveTier(model);
  const pricing = PRICING[tier] || PRICING.sonnet;
  const inputCost = (inputTokens / 1_000_000) * pricing.input;
  const outputCost = (outputTokens / 1_000_000) * pricing.output;
  return Math.round((inputCost + outputCost) * 1e6) / 1e6;
}

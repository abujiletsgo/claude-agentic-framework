<template>
  <div class="p-6">
    <!-- Header -->
    <div class="flex items-center justify-between mb-6">
      <div class="flex items-center gap-3">
        <div class="w-8 h-8 rounded-lg bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center shadow-md">
          <span class="text-sm text-white font-bold">$</span>
        </div>
        <div>
          <h2 class="text-base font-semibold text-slate-900 dark:text-white">Cost Tracker</h2>
          <p class="text-xs text-slate-500 dark:text-slate-400">Multi-model tier usage</p>
        </div>
      </div>
      <div class="flex items-center gap-2">
        <select
          v-model="selectedPeriod"
          @change="refresh"
          class="text-xs px-3 py-1.5 rounded-lg bg-white/80 dark:bg-slate-700/80 border border-slate-200 dark:border-slate-600 text-slate-700 dark:text-slate-300 focus:outline-none focus:ring-2 focus:ring-emerald-500/50"
        >
          <option value="today">Today</option>
          <option value="yesterday">Yesterday</option>
          <option value="week">Last 7 Days</option>
          <option value="month">Last 30 Days</option>
          <option value="all">All Time</option>
        </select>
        <button
          @click="refresh"
          :disabled="loading"
          class="p-1.5 rounded-lg bg-white/80 dark:bg-slate-700/80 border border-slate-200 dark:border-slate-600 text-slate-500 dark:text-slate-400 hover:text-emerald-600 dark:hover:text-emerald-400 transition-colors disabled:opacity-50"
          title="Refresh"
        >
          <svg class="w-4 h-4" :class="{ 'animate-spin': loading }" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
        </button>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading && !summary" class="flex items-center justify-center py-12">
      <div class="flex items-center gap-3 text-slate-500 dark:text-slate-400">
        <svg class="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
        </svg>
        <span class="text-sm">Loading cost data...</span>
      </div>
    </div>

    <!-- No Data State -->
    <div v-else-if="!loading && (!summary || summary.event_count === 0)" class="text-center py-12">
      <div class="w-16 h-16 mx-auto mb-4 rounded-2xl bg-slate-100 dark:bg-slate-800 flex items-center justify-center">
        <span class="text-2xl">$</span>
      </div>
      <p class="text-sm text-slate-500 dark:text-slate-400 mb-2">No cost data yet</p>
      <p class="text-xs text-slate-400 dark:text-slate-500">Cost tracking data will appear here as agents run</p>
    </div>

    <!-- Main Content -->
    <div v-else class="space-y-6">
      <!-- Summary Cards -->
      <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div class="bg-gradient-to-br from-emerald-50 to-teal-50 dark:from-emerald-900/20 dark:to-teal-900/20 rounded-xl p-3 border border-emerald-200/50 dark:border-emerald-700/30">
          <p class="text-xs text-emerald-600 dark:text-emerald-400 font-medium mb-1">Total Cost</p>
          <p class="text-lg font-bold text-emerald-900 dark:text-emerald-100">{{ formatCost(summary?.total_cost || 0) }}</p>
        </div>
        <div class="bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 rounded-xl p-3 border border-blue-200/50 dark:border-blue-700/30">
          <p class="text-xs text-blue-600 dark:text-blue-400 font-medium mb-1">Events</p>
          <p class="text-lg font-bold text-blue-900 dark:text-blue-100">{{ (summary?.event_count || 0).toLocaleString() }}</p>
        </div>
        <div class="bg-gradient-to-br from-purple-50 to-violet-50 dark:from-purple-900/20 dark:to-violet-900/20 rounded-xl p-3 border border-purple-200/50 dark:border-purple-700/30">
          <p class="text-xs text-purple-600 dark:text-purple-400 font-medium mb-1">Sessions</p>
          <p class="text-lg font-bold text-purple-900 dark:text-purple-100">{{ summary?.session_count || 0 }}</p>
        </div>
        <div class="bg-gradient-to-br from-amber-50 to-orange-50 dark:from-amber-900/20 dark:to-orange-900/20 rounded-xl p-3 border border-amber-200/50 dark:border-amber-700/30">
          <p class="text-xs text-amber-600 dark:text-amber-400 font-medium mb-1">Tokens</p>
          <p class="text-lg font-bold text-amber-900 dark:text-amber-100">{{ formatTokens((summary?.total_input_tokens || 0) + (summary?.total_output_tokens || 0)) }}</p>
        </div>
      </div>

      <!-- Tier Breakdown -->
      <div v-if="summary?.by_tier && Object.keys(summary.by_tier).length > 0">
        <h3 class="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-3">By Model Tier</h3>
        <div class="space-y-2">
          <div
            v-for="tierName in tierOrder"
            :key="tierName"
            v-show="summary.by_tier[tierName]"
            class="flex items-center gap-3"
          >
            <!-- Tier badge -->
            <div
              class="w-16 text-center px-2 py-1 rounded-md text-xs font-semibold"
              :class="tierBadgeClass(tierName)"
            >
              {{ tierName }}
            </div>
            <!-- Bar -->
            <div class="flex-1 h-6 bg-slate-100 dark:bg-slate-800 rounded-md overflow-hidden relative">
              <div
                class="h-full rounded-md transition-all duration-500"
                :class="tierBarClass(tierName)"
                :style="{ width: tierBarWidth(tierName) + '%' }"
              ></div>
              <span class="absolute inset-0 flex items-center px-2 text-xs font-medium text-slate-700 dark:text-slate-300">
                {{ formatCost(summary.by_tier[tierName]?.cost || 0) }}
                <span class="ml-auto text-slate-400 dark:text-slate-500">
                  {{ summary.by_tier[tierName]?.events || 0 }} events
                </span>
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- Daily Chart (simple bar visualization) -->
      <div v-if="dailyBreakdown.length > 0">
        <h3 class="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-3">Daily Costs</h3>
        <div class="flex items-end gap-1 h-24">
          <div
            v-for="day in reversedDaily"
            :key="day.date"
            class="flex-1 flex flex-col items-center gap-1"
          >
            <div
              class="w-full rounded-t-md bg-gradient-to-t from-emerald-500 to-teal-400 dark:from-emerald-600 dark:to-teal-500 transition-all duration-300 min-h-[2px]"
              :style="{ height: dailyBarHeight(day.total_cost) + '%' }"
              :title="`${day.date}: ${formatCost(day.total_cost)}`"
            ></div>
            <span class="text-[9px] text-slate-400 dark:text-slate-500 truncate w-full text-center">
              {{ day.date.slice(5) }}
            </span>
          </div>
        </div>
      </div>

      <!-- Projection -->
      <div v-if="projection && projection.confidence !== 'no_data'" class="bg-slate-50 dark:bg-slate-800/50 rounded-xl p-4 border border-slate-200/50 dark:border-slate-700/30">
        <div class="flex items-center gap-2 mb-2">
          <h3 class="text-sm font-semibold text-slate-700 dark:text-slate-300">7-Day Projection</h3>
          <span
            class="px-1.5 py-0.5 rounded text-[10px] font-medium"
            :class="confidenceBadgeClass(projection.confidence)"
          >
            {{ projection.confidence }}
          </span>
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <p class="text-xs text-slate-500 dark:text-slate-400">Avg Daily</p>
            <p class="text-sm font-bold text-slate-900 dark:text-white">{{ formatCost(projection.avg_daily_cost) }}</p>
          </div>
          <div>
            <p class="text-xs text-slate-500 dark:text-slate-400">Projected Total</p>
            <p class="text-sm font-bold text-slate-900 dark:text-white">{{ formatCost(projection.projected_total) }}</p>
          </div>
        </div>
        <div v-if="Object.keys(projection.tier_breakdown).length > 0" class="mt-3 pt-3 border-t border-slate-200 dark:border-slate-700">
          <div class="flex gap-4">
            <div v-for="(data, tier) in projection.tier_breakdown" :key="tier" class="text-xs">
              <span class="font-medium text-slate-500 dark:text-slate-400">{{ tier }}:</span>
              <span class="ml-1 text-slate-700 dark:text-slate-300">{{ formatCost(data.projected) }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Top Agents -->
      <div v-if="topAgents.length > 0">
        <h3 class="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-3">Top Agents by Cost</h3>
        <div class="space-y-1.5">
          <div
            v-for="agent in topAgents.slice(0, 8)"
            :key="agent.name"
            class="flex items-center gap-2 text-xs"
          >
            <span class="w-32 truncate font-medium text-slate-600 dark:text-slate-400" :title="agent.name">{{ agent.name }}</span>
            <div
              class="px-1.5 py-0.5 rounded text-[10px] font-semibold"
              :class="tierBadgeClass(agent.tier)"
            >
              {{ agent.tier }}
            </div>
            <div class="flex-1 h-3 bg-slate-100 dark:bg-slate-800 rounded overflow-hidden">
              <div
                class="h-full rounded bg-emerald-400 dark:bg-emerald-500 transition-all duration-300"
                :style="{ width: agentBarWidth(agent.cost) + '%' }"
              ></div>
            </div>
            <span class="w-16 text-right text-slate-500 dark:text-slate-400 font-mono">{{ formatCost(agent.cost) }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Error State -->
    <div v-if="error" class="mt-4 p-3 bg-red-50 dark:bg-red-900/20 rounded-xl border border-red-200/50 dark:border-red-700/30">
      <p class="text-xs text-red-600 dark:text-red-400">{{ error }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { useCostTracking } from '../composables/useCostTracking';
import type { CostSummary, DailySummary, CostProjection } from '../composables/useCostTracking';

const {
  summary,
  dailyBreakdown,
  projection,
  loading,
  error,
  fetchAll,
} = useCostTracking();

const selectedPeriod = ref('week');

const tierOrder = ['opus', 'sonnet', 'haiku', 'unknown'];

// ── Computed ─────────────────────────────────────────────────────

const reversedDaily = computed(() => {
  return [...dailyBreakdown.value].reverse();
});

const topAgents = computed(() => {
  if (!summary.value?.by_agent) return [];
  return Object.entries(summary.value.by_agent)
    .map(([name, data]) => ({ name, ...data }))
    .sort((a, b) => b.cost - a.cost);
});

const maxDailyCost = computed(() => {
  if (dailyBreakdown.value.length === 0) return 1;
  return Math.max(...dailyBreakdown.value.map(d => d.total_cost), 0.001);
});

const maxTierCost = computed(() => {
  if (!summary.value?.by_tier) return 1;
  return Math.max(...Object.values(summary.value.by_tier).map(t => t.cost), 0.001);
});

const maxAgentCost = computed(() => {
  if (topAgents.value.length === 0) return 1;
  return topAgents.value[0]?.cost || 0.001;
});

// ── Methods ──────────────────────────────────────────────────────

function refresh() {
  fetchAll(selectedPeriod.value, 7);
}

function formatCost(cost: number): string {
  if (cost < 0.01) return `$${cost.toFixed(4)}`;
  if (cost < 1) return `$${cost.toFixed(3)}`;
  return `$${cost.toFixed(2)}`;
}

function formatTokens(tokens: number): string {
  if (tokens >= 1_000_000) return `${(tokens / 1_000_000).toFixed(1)}M`;
  if (tokens >= 1_000) return `${(tokens / 1_000).toFixed(1)}K`;
  return tokens.toString();
}

function tierBarWidth(tier: string): number {
  const cost = summary.value?.by_tier[tier]?.cost || 0;
  return Math.max((cost / maxTierCost.value) * 100, 2);
}

function dailyBarHeight(cost: number): number {
  return Math.max((cost / maxDailyCost.value) * 100, 3);
}

function agentBarWidth(cost: number): number {
  return Math.max((cost / maxAgentCost.value) * 100, 2);
}

function tierBadgeClass(tier: string): string {
  switch (tier) {
    case 'opus':
      return 'bg-red-100 dark:bg-red-900/40 text-red-700 dark:text-red-300';
    case 'sonnet':
      return 'bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300';
    case 'haiku':
      return 'bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-300';
    default:
      return 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400';
  }
}

function tierBarClass(tier: string): string {
  switch (tier) {
    case 'opus':
      return 'bg-gradient-to-r from-red-400 to-rose-500';
    case 'sonnet':
      return 'bg-gradient-to-r from-blue-400 to-indigo-500';
    case 'haiku':
      return 'bg-gradient-to-r from-green-400 to-emerald-500';
    default:
      return 'bg-gradient-to-r from-slate-300 to-slate-400';
  }
}

function confidenceBadgeClass(confidence: string): string {
  switch (confidence) {
    case 'high':
      return 'bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-300';
    case 'medium':
      return 'bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-300';
    case 'low':
      return 'bg-red-100 dark:bg-red-900/40 text-red-700 dark:text-red-300';
    default:
      return 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400';
  }
}

// ── Lifecycle ────────────────────────────────────────────────────

onMounted(() => {
  refresh();
});
</script>

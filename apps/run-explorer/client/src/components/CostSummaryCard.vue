<script setup lang="ts">
import type { CostSummary } from '@/composables/useCosts'

defineProps<{
  summary: CostSummary | null
  loading: boolean
}>()

function formatCost(cost: number): string {
  return '$' + cost.toFixed(4)
}

function formatTokens(tokens: number): string {
  if (tokens >= 1_000_000) return (tokens / 1_000_000).toFixed(1) + 'M'
  if (tokens >= 1_000) return (tokens / 1_000).toFixed(1) + 'K'
  return String(tokens)
}

const periodLabels: Record<string, string> = {
  week: 'This week',
  day: 'Today',
  month: 'This month',
}
</script>

<template>
  <div class="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-4 shadow-sm">
    <div class="flex items-center justify-between mb-3">
      <h3 class="text-sm font-semibold text-slate-700 dark:text-slate-300">Cost Summary</h3>
      <span v-if="summary" class="text-xs text-slate-400 dark:text-slate-500">
        {{ periodLabels[summary.period] ?? summary.period }}
      </span>
    </div>

    <div v-if="loading" class="flex items-center gap-2 text-slate-400 dark:text-slate-500">
      <svg class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
      </svg>
      <span class="text-xs">Loading…</span>
    </div>

    <div v-else-if="summary" class="grid grid-cols-3 gap-3">
      <div class="text-center">
        <div class="text-lg font-bold text-emerald-600 dark:text-emerald-400 tabular-nums">
          {{ formatCost(summary.totalCost) }}
        </div>
        <div class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">Total cost</div>
      </div>
      <div class="text-center border-x border-slate-200 dark:border-slate-700">
        <div class="text-lg font-bold text-violet-600 dark:text-violet-400 tabular-nums">
          {{ formatTokens(summary.totalTokens) }}
        </div>
        <div class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">Tokens</div>
      </div>
      <div class="text-center">
        <div class="text-lg font-bold text-blue-600 dark:text-blue-400 tabular-nums">
          {{ summary.sessionCount }}
        </div>
        <div class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">Sessions</div>
      </div>
    </div>

    <div v-else class="text-xs text-slate-400 dark:text-slate-500">No cost data available</div>
  </div>
</template>

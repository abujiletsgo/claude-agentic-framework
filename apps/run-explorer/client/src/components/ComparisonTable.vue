<script setup lang="ts">
import type { ComparisonResult } from '@shared/types'

defineProps<{
  result: ComparisonResult
}>()

interface MetricRow {
  label: string
  valueA: string
  valueB: string
  winner: 'a' | 'b' | 'tie' | null
}

function buildRows(result: ComparisonResult): MetricRow[] {
  const { metrics } = result
  return [
    {
      label: 'Wall Clock',
      valueA: formatSeconds(metrics.wallClockSeconds.a),
      valueB: formatSeconds(metrics.wallClockSeconds.b),
      winner: metrics.wallClockSeconds.winner,
    },
    {
      label: 'Token Estimate',
      valueA: formatTokens(metrics.tokenEstimate.a),
      valueB: formatTokens(metrics.tokenEstimate.b),
      winner: metrics.tokenEstimate.winner,
    },
    {
      label: 'Quality Score',
      valueA: metrics.qualityScore.a !== null ? String(metrics.qualityScore.a) : '—',
      valueB: metrics.qualityScore.b !== null ? String(metrics.qualityScore.b) : '—',
      winner: metrics.qualityScore.winner,
    },
  ]
}

function formatSeconds(s: number): string {
  const m = Math.floor(s / 60)
  return m > 0 ? `${m}m ${Math.round(s % 60)}s` : `${Math.round(s)}s`
}

function formatTokens(t: number): string {
  return t >= 1000 ? `${(t / 1000).toFixed(1)}k` : String(t)
}
</script>

<template>
  <div class="overflow-x-auto rounded-2xl border border-slate-200 dark:border-slate-700">
    <table class="w-full text-sm">
      <thead>
        <tr class="border-b border-slate-200 dark:border-slate-700 bg-slate-50/80 dark:bg-slate-800/50">
          <th class="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wide w-1/4">Metric</th>
          <th
            :class="[
              'px-4 py-3 text-center text-xs font-medium uppercase tracking-wide',
              result.metrics.wallClockSeconds.winner === 'a'
                ? 'text-emerald-600 dark:text-emerald-400 font-semibold border-l-2 border-emerald-400'
                : 'text-slate-500'
            ]"
          >
            Run A
            <span v-if="result.metrics.wallClockSeconds.winner === 'a'" class="ml-1">🏆</span>
          </th>
          <th
            :class="[
              'px-4 py-3 text-center text-xs font-medium uppercase tracking-wide',
              result.metrics.wallClockSeconds.winner === 'b'
                ? 'text-emerald-600 dark:text-emerald-400 font-semibold border-l-2 border-emerald-400'
                : 'text-slate-500'
            ]"
          >
            Run B
            <span v-if="result.metrics.wallClockSeconds.winner === 'b'" class="ml-1">🏆</span>
          </th>
        </tr>
      </thead>
      <tbody class="divide-y divide-slate-100 dark:divide-slate-700/50">
        <tr v-for="row in buildRows(result)" :key="row.label" class="hover:bg-slate-50/50 dark:hover:bg-slate-700/10">
          <td class="px-4 py-3 text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide">
            {{ row.label }}
          </td>
          <!-- Value A -->
          <td
            :class="[
              'px-4 py-3 text-center text-sm tabular-nums',
              row.winner === 'a'
                ? 'bg-emerald-50 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-300 font-semibold border-l-2 border-emerald-400'
                : 'text-slate-500 dark:text-slate-400'
            ]"
          >
            {{ row.valueA }}
          </td>
          <!-- Value B -->
          <td
            :class="[
              'px-4 py-3 text-center text-sm tabular-nums',
              row.winner === 'b'
                ? 'bg-emerald-50 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-300 font-semibold border-l-2 border-emerald-400'
                : 'text-slate-500 dark:text-slate-400'
            ]"
          >
            {{ row.valueB }}
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

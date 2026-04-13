<script setup lang="ts">
import type { RunStatus } from '@shared/types'

const props = defineProps<{
  status: RunStatus
}>()

const statusConfig: Record<RunStatus, { pill: string; dot: string; text: string; label: string }> = {
  PASS: {
    pill: 'bg-emerald-50 border-emerald-200 dark:bg-emerald-900/20 dark:border-emerald-700',
    dot: 'bg-emerald-500',
    text: 'text-emerald-700 dark:text-emerald-300',
    label: 'Pass',
  },
  FAIL: {
    pill: 'bg-red-50 border-red-200 dark:bg-red-900/20 dark:border-red-700',
    dot: 'bg-red-500',
    text: 'text-red-700 dark:text-red-300',
    label: 'Fail',
  },
  IN_PROGRESS: {
    pill: 'bg-amber-50 border-amber-200 dark:bg-amber-900/20 dark:border-amber-700',
    dot: 'bg-amber-500 animate-pulse',
    text: 'text-amber-700 dark:text-amber-300',
    label: 'Running',
  },
  UNKNOWN: {
    pill: 'bg-slate-100 border-slate-200 dark:bg-slate-700/40 dark:border-slate-600',
    dot: 'bg-slate-400',
    text: 'text-slate-600 dark:text-slate-400',
    label: 'Unknown',
  },
}

const config = statusConfig[props.status] ?? statusConfig.UNKNOWN
</script>

<template>
  <span :class="['inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold border', config.pill, config.text]">
    <span :class="['w-1.5 h-1.5 rounded-full flex-shrink-0', config.dot]"></span>
    {{ config.label }}
  </span>
</template>

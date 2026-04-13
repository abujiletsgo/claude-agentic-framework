<script setup lang="ts">
import type { OrchEvent } from '@shared/types'

const props = defineProps<{
  status: OrchEvent['status']
}>()

const statusConfig: Record<OrchEvent['status'], { pill: string; dot: string; text: string; label: string }> = {
  'domain-claim': {
    pill: 'bg-violet-100 dark:bg-violet-900/30',
    dot: 'bg-violet-500',
    text: 'text-violet-700 dark:text-violet-300',
    label: 'domain-claim',
  },
  broadcast: {
    pill: 'bg-amber-100 dark:bg-amber-900/30',
    dot: 'bg-amber-500',
    text: 'text-amber-700 dark:text-amber-300',
    label: 'broadcast',
  },
  running: {
    pill: 'bg-blue-100 dark:bg-blue-900/30',
    dot: 'bg-blue-500',
    text: 'text-blue-700 dark:text-blue-300',
    label: 'running',
  },
  done: {
    pill: 'bg-emerald-100 dark:bg-emerald-900/30',
    dot: 'bg-emerald-500',
    text: 'text-emerald-700 dark:text-emerald-300',
    label: 'done',
  },
  question: {
    pill: 'bg-orange-100 dark:bg-orange-900/30',
    dot: 'bg-orange-500',
    text: 'text-orange-700 dark:text-orange-300',
    label: 'question',
  },
  memory: {
    pill: 'bg-slate-100 dark:bg-slate-700',
    dot: 'bg-slate-400',
    text: 'text-slate-600 dark:text-slate-300',
    label: 'memory',
  },
}

const config = statusConfig[props.status] ?? statusConfig.memory
</script>

<template>
  <span :class="['inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold', config.pill, config.text]">
    <span :class="['w-1.5 h-1.5 rounded-full flex-shrink-0', config.dot]"></span>
    {{ config.label }}
  </span>
</template>

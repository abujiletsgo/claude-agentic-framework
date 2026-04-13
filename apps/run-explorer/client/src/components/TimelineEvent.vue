<script setup lang="ts">
import type { OrchEvent } from '@shared/types'
import EventStatusBadge from '@/components/EventStatusBadge.vue'

defineProps<{
  event: OrchEvent
}>()

function relativeTime(ts: string): string {
  const diff = Date.now() - new Date(ts).getTime()
  const s = Math.floor(diff / 1000)
  if (s < 60) return `${s}s ago`
  const m = Math.floor(s / 60)
  if (m < 60) return `${m}m ago`
  return `${Math.floor(m / 60)}h ago`
}

const dotColor: Record<OrchEvent['status'], string> = {
  'domain-claim': 'bg-violet-500',
  broadcast: 'bg-amber-500',
  running: 'bg-blue-500',
  done: 'bg-emerald-500',
  question: 'bg-orange-500',
  memory: 'bg-slate-400',
}
</script>

<template>
  <div class="flex gap-3 py-2">
    <!-- Vertical line + dot -->
    <div class="flex flex-col items-center flex-shrink-0">
      <div :class="['w-2 h-2 rounded-full mt-1 flex-shrink-0', dotColor[event.status] ?? 'bg-slate-400']"></div>
      <div class="flex-1 w-px border-l-2 border-slate-200 dark:border-slate-700 mt-1"></div>
    </div>

    <!-- Content -->
    <div class="flex-1 pb-3">
      <!-- Header row -->
      <div class="flex flex-wrap items-center gap-2 mb-1">
        <EventStatusBadge :status="event.status" />
        <span class="font-mono text-xs text-slate-500 dark:text-slate-400">{{ event.agent }}</span>
        <span
          v-if="event.wave !== undefined"
          class="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300"
        >wave {{ event.wave }}</span>
        <span
          class="ml-auto text-xs text-slate-400 dark:text-slate-500 tabular-nums"
          :title="event.ts"
        >{{ relativeTime(event.ts) }}</span>
      </div>
      <!-- Summary -->
      <p class="text-sm text-slate-700 dark:text-slate-300">{{ event.summary }}</p>
    </div>
  </div>
</template>

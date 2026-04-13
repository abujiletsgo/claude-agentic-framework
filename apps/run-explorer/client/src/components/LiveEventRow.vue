<script setup lang="ts">
import { ref, computed } from 'vue'
import type { LiveEvent } from '@/composables/useLiveEvents'

const props = defineProps<{
  event: LiveEvent
}>()

const expanded = ref(false)

function relativeTime(ts: number): string {
  const diff = Date.now() - ts
  const s = Math.floor(diff / 1000)
  if (s < 60) return `${s}s ago`
  const m = Math.floor(s / 60)
  if (m < 60) return `${m}m ago`
  return `${Math.floor(m / 60)}h ago`
}

const dotColor = computed(() => {
  const type = props.event.hook_event_type.toLowerCase()
  if (type.includes('stop')) return 'bg-emerald-500'
  if (type.includes('start')) return 'bg-blue-500'
  if (type.includes('error') || type.includes('fail')) return 'bg-red-500'
  if (type.includes('pre')) return 'bg-amber-500'
  if (type.includes('post')) return 'bg-violet-500'
  if (type.includes('user')) return 'bg-orange-500'
  return 'bg-slate-400'
})

const displayText = computed(() => {
  if (props.event.summary) return props.event.summary
  try {
    const parsed = JSON.parse(props.event.payload)
    const str = JSON.stringify(parsed)
    return str.length > 80 ? str.slice(0, 80) + '…' : str
  } catch {
    return props.event.payload.slice(0, 80) + (props.event.payload.length > 80 ? '…' : '')
  }
})

const formattedPayload = computed(() => {
  try {
    return JSON.stringify(JSON.parse(props.event.payload), null, 2)
  } catch {
    return props.event.payload
  }
})

const shortSessionId = computed(() => {
  return props.event.session_id.slice(0, 8)
})
</script>

<template>
  <div
    class="border border-slate-200 dark:border-slate-700 rounded-lg overflow-hidden transition-colors duration-150"
    :class="expanded ? 'bg-slate-50 dark:bg-slate-800/60' : 'bg-white dark:bg-slate-800/30 hover:bg-slate-50 dark:hover:bg-slate-800/50'"
  >
    <!-- Row header -->
    <button
      class="w-full text-left flex items-start gap-3 px-4 py-3 cursor-pointer"
      @click="expanded = !expanded"
    >
      <!-- Colored dot -->
      <span class="flex-shrink-0 mt-1.5">
        <span :class="['inline-block w-2 h-2 rounded-full', dotColor]"></span>
      </span>

      <!-- Main content -->
      <div class="flex-1 min-w-0">
        <div class="flex flex-wrap items-center gap-2 mb-0.5">
          <span class="text-xs font-medium text-slate-700 dark:text-slate-300 font-mono">
            {{ event.hook_event_type }}
          </span>
          <span class="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-mono bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300">
            {{ shortSessionId }}
          </span>
          <span v-if="event.source_app" class="inline-flex items-center px-1.5 py-0.5 rounded text-xs bg-violet-50 text-violet-700 dark:bg-violet-900/30 dark:text-violet-300">
            {{ event.source_app }}
          </span>
          <span class="ml-auto text-xs text-slate-400 dark:text-slate-500 tabular-nums flex-shrink-0">
            {{ relativeTime(event.timestamp) }}
          </span>
        </div>
        <p class="text-sm text-slate-600 dark:text-slate-400 truncate">{{ displayText }}</p>
      </div>

      <!-- Expand chevron -->
      <span class="flex-shrink-0 text-slate-400 dark:text-slate-500 mt-0.5 transition-transform duration-150" :class="expanded ? 'rotate-180' : ''">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
        </svg>
      </span>
    </button>

    <!-- Expanded payload -->
    <div v-if="expanded" class="px-4 pb-4 border-t border-slate-200 dark:border-slate-700 pt-3">
      <pre class="text-xs font-mono text-slate-700 dark:text-slate-300 bg-slate-100 dark:bg-slate-900/50 rounded-lg p-3 overflow-x-auto whitespace-pre-wrap break-all">{{ formattedPayload }}</pre>
    </div>
  </div>
</template>

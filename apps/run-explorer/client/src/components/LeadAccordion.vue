<script setup lang="ts">
import { ref } from 'vue'
import type { LeadSummary } from '@shared/types'
import StatusBadge from '@/components/StatusBadge.vue'
import { API_BASE_URL } from '@/config'

const props = defineProps<{
  lead: LeadSummary
  runId: string
}>()

const expanded = ref(false)
const content = ref<string | null>(null)
const loadingContent = ref(false)
const contentError = ref<string | null>(null)

async function toggleExpand() {
  expanded.value = !expanded.value
  if (expanded.value && content.value === null && !loadingContent.value) {
    loadingContent.value = true
    contentError.value = null
    try {
      const res = await fetch(`${API_BASE_URL}/api/runs/${props.runId}/leads/${props.lead.name}`)
      if (!res.ok) {
        contentError.value = `Failed to load output (${res.status})`
        return
      }
      const data = await res.json() as { content: string }
      content.value = data.content
    } catch (e) {
      contentError.value = e instanceof Error ? e.message : 'Failed to load lead output'
    } finally {
      loadingContent.value = false
    }
  }
}

// Split content into prompt and results sections for structured rendering
function parseSection(raw: string, header: string): string | null {
  const re = new RegExp(`^##\\s+${header}\\s*$`, 'm')
  const match = re.exec(raw)
  if (!match) return null
  const start = match.index + match[0].length
  // Find next ## heading or end of string
  const rest = raw.slice(start)
  const nextHeader = rest.match(/^##\s+/m)
  return nextHeader ? rest.slice(0, nextHeader.index).trim() : rest.trim()
}
</script>

<template>
  <div class="glass-card overflow-hidden">
    <button
      class="w-full flex items-center justify-between px-5 py-4 text-left hover:bg-slate-50/50 dark:hover:bg-slate-700/20 transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-violet-500"
      @click="toggleExpand"
      :aria-expanded="expanded"
    >
      <div class="flex items-center gap-3">
        <!-- Lead avatar initials -->
        <div class="w-7 h-7 rounded-lg bg-violet-100 dark:bg-violet-900/30 flex items-center justify-center flex-shrink-0">
          <span class="text-xs font-bold text-violet-700 dark:text-violet-300">
            {{ lead.name.split('-').map(p => p[0]?.toUpperCase() ?? '').slice(0, 2).join('') }}
          </span>
        </div>
        <div>
          <div class="text-sm font-semibold text-slate-800 dark:text-slate-200 tracking-tight">{{ lead.name }}</div>
          <div class="text-xs text-slate-500 dark:text-slate-400">Wave {{ lead.wave }}</div>
        </div>
      </div>
      <div class="flex items-center gap-3">
        <StatusBadge :status="lead.status" />
        <svg
          :class="['w-4 h-4 text-slate-400 transition-transform duration-200', expanded ? 'rotate-180' : '']"
          fill="none" stroke="currentColor" viewBox="0 0 24 24"
        >
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
        </svg>
      </div>
    </button>

    <div v-if="expanded" class="px-5 pb-5 pt-1 border-t border-slate-100 dark:border-slate-700/50">
      <!-- Loading state -->
      <div v-if="loadingContent" class="flex items-center gap-2 py-4">
        <div class="w-4 h-4 border-2 border-violet-500 border-t-transparent rounded-full animate-spin"></div>
        <span class="text-sm text-slate-400 dark:text-slate-500">Loading...</span>
      </div>

      <!-- Error state -->
      <p v-else-if="contentError" class="text-sm text-red-600 dark:text-red-400 py-2">{{ contentError }}</p>

      <!-- Content -->
      <template v-else-if="content">
        <!-- Prompt section -->
        <div v-if="parseSection(content, 'Prompt')" class="mb-4">
          <h3 class="text-xs font-semibold uppercase tracking-wider text-violet-600 dark:text-violet-400 mb-2">Prompt</h3>
          <pre class="whitespace-pre-wrap text-xs text-slate-600 dark:text-slate-400 font-mono bg-slate-50 dark:bg-slate-900/50 rounded-xl p-4 overflow-auto max-h-64">{{ parseSection(content, 'Prompt') }}</pre>
        </div>

        <!-- Results section -->
        <div v-if="parseSection(content, 'Results')">
          <h3 class="text-xs font-semibold uppercase tracking-wider text-emerald-600 dark:text-emerald-400 mb-2">Results</h3>
          <pre class="whitespace-pre-wrap text-xs text-slate-600 dark:text-slate-400 font-mono bg-slate-50 dark:bg-slate-900/50 rounded-xl p-4 overflow-auto max-h-96">{{ parseSection(content, 'Results') }}</pre>
        </div>

        <!-- Fallback: no structured sections found -->
        <div v-if="!parseSection(content, 'Prompt') && !parseSection(content, 'Results')">
          <pre class="whitespace-pre-wrap text-xs text-slate-600 dark:text-slate-400 font-mono bg-slate-50 dark:bg-slate-900/50 rounded-xl p-4 overflow-auto">{{ content }}</pre>
        </div>
      </template>

      <p v-else class="text-sm text-slate-400 dark:text-slate-500 italic">No content available for this lead.</p>
    </div>
  </div>
</template>

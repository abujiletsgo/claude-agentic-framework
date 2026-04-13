<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import type { Run, RunStatus } from '@shared/types'
import { useRuns } from '@/composables/useRuns'
import StatusBadge from '@/components/StatusBadge.vue'
import SkeletonRow from '@/components/SkeletonRow.vue'
import EmptyState from '@/components/EmptyState.vue'

const router = useRouter()
const { runs, loading, error, refresh } = useRuns()

const searchQuery = ref('')
const activeStatuses = ref<Set<RunStatus>>(new Set())

const allStatuses: RunStatus[] = ['PASS', 'FAIL', 'IN_PROGRESS', 'UNKNOWN']

function toggleStatus(s: RunStatus) {
  if (activeStatuses.value.has(s)) {
    activeStatuses.value.delete(s)
  } else {
    activeStatuses.value.add(s)
  }
  // trigger reactivity
  activeStatuses.value = new Set(activeStatuses.value)
}

const filteredRuns = computed(() => {
  let result = [...runs.value].sort((a, b) => new Date(b.startTime).getTime() - new Date(a.startTime).getTime())
  if (searchQuery.value.trim()) {
    const q = searchQuery.value.toLowerCase()
    result = result.filter(r => r.id.toLowerCase().includes(q))
  }
  if (activeStatuses.value.size > 0) {
    result = result.filter(r => activeStatuses.value.has(r.status))
  }
  return result
})

function formatDate(iso: string): string {
  const d = new Date(iso)
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) + ', ' +
    d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false })
}

function formatDuration(ms: number | null | undefined): string {
  if (ms == null) return '—'
  const s = Math.floor(ms / 1000)
  const m = Math.floor(s / 60)
  return m > 0 ? `${m}m ${s % 60}s` : `${s}s`
}

function navigateToRun(id: string) {
  router.push(`/runs/${id}`)
}

const statusLabels: Record<RunStatus, string> = {
  PASS: 'Pass',
  FAIL: 'Fail',
  IN_PROGRESS: 'Running',
  UNKNOWN: 'Unknown',
}
</script>

<template>
  <div class="space-y-6 fade-in">
    <!-- Page header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-xl font-semibold text-slate-900 dark:text-white tracking-tight">Orchestration Runs</h1>
        <p class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">Browse and inspect past runs</p>
      </div>
      <button
        class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors duration-200 focus-visible:ring-2 focus-visible:ring-violet-500 focus-visible:ring-offset-2"
        :disabled="loading"
        @click="refresh"
        aria-label="Refresh runs"
      >
        <svg class="w-4 h-4" :class="{ 'animate-spin': loading }" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
        </svg>
        Refresh
      </button>
    </div>

    <!-- Filters -->
    <div class="glass-card p-4 space-y-3">
      <!-- Search -->
      <div class="relative">
        <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
        <input
          v-model="searchQuery"
          type="text"
          placeholder="Search by run ID..."
          class="w-full pl-9 pr-4 py-2 text-sm bg-transparent border border-slate-200 dark:border-slate-600 rounded-xl text-slate-700 dark:text-slate-300 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent transition-all duration-200"
        />
      </div>

      <!-- Status filter pills -->
      <div class="flex items-center gap-2 flex-wrap">
        <span class="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide">Status:</span>
        <button
          v-for="s in allStatuses"
          :key="s"
          :class="[
            'px-2.5 py-0.5 rounded-full text-xs font-semibold border transition-all duration-200 focus-visible:ring-2 focus-visible:ring-violet-500 focus-visible:ring-offset-1',
            activeStatuses.has(s)
              ? 'bg-violet-600 border-violet-600 text-white'
              : 'bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-600 text-slate-600 dark:text-slate-400 hover:border-violet-400'
          ]"
          @click="toggleStatus(s)"
        >
          {{ statusLabels[s] }}
        </button>
      </div>
    </div>

    <!-- Error state -->
    <div v-if="error" class="glass-card p-6 text-center">
      <p class="text-sm text-red-600 dark:text-red-400 mb-3">{{ error }}</p>
      <button
        class="px-4 py-2 rounded-xl bg-violet-600 hover:bg-violet-700 text-white text-sm font-medium transition-colors duration-200"
        @click="refresh"
      >
        Retry
      </button>
    </div>

    <!-- Run table -->
    <div v-else class="glass-card overflow-hidden">
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead class="bg-slate-50/80 dark:bg-slate-800/50 sticky top-0 z-10">
            <tr>
              <th class="px-4 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide">Run ID</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide">Status</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide">Leads</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide">Started</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide">Waves</th>
              <th class="px-4 py-3"></th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100 dark:divide-slate-700/50">
            <!-- Skeleton rows while loading -->
            <template v-if="loading">
              <SkeletonRow v-for="i in 5" :key="i" />
            </template>

            <!-- Empty state (no runs at all) -->
            <template v-else-if="runs.length === 0">
              <tr>
                <td colspan="6">
                  <EmptyState
                    title="No runs yet"
                    description="Orchestration runs will appear here once you launch one."
                    icon="inbox"
                  />
                </td>
              </tr>
            </template>

            <!-- Empty state (filtered to zero) -->
            <template v-else-if="filteredRuns.length === 0">
              <tr>
                <td colspan="6">
                  <EmptyState
                    title="No matching runs"
                    description="Try adjusting your search or filters."
                    icon="search"
                    cta-label="Clear filters"
                    @cta="searchQuery = ''; activeStatuses = new Set()"
                  />
                </td>
              </tr>
            </template>

            <!-- Populated rows -->
            <template v-else>
              <tr
                v-for="run in filteredRuns"
                :key="run.id"
                class="group hover:bg-slate-50/80 dark:hover:bg-slate-700/30 transition-colors duration-150 cursor-pointer"
                @click="navigateToRun(run.id)"
              >
                <td class="px-4 py-3 text-sm text-slate-700 dark:text-slate-300 font-mono">
                  {{ run.id.slice(0, 8) }}
                </td>
                <td class="px-4 py-3">
                  <StatusBadge :status="run.status" />
                </td>
                <td class="px-4 py-3 text-sm text-slate-600 dark:text-slate-400">
                  {{ run.leadCount }} lead{{ run.leadCount !== 1 ? 's' : '' }}
                </td>
                <td class="px-4 py-3 text-xs text-slate-400 dark:text-slate-500 font-mono tabular-nums">
                  {{ formatDate(run.startTime) }}
                </td>
                <td class="px-4 py-3 text-sm text-slate-600 dark:text-slate-400 tabular-nums">
                  {{ run.waveCount }}
                </td>
                <td class="px-4 py-3 text-right">
                  <svg class="w-4 h-4 text-slate-300 dark:text-slate-600 group-hover:text-violet-500 transition-colors ml-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
                  </svg>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

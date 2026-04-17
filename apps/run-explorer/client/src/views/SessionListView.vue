<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter, RouterLink } from 'vue-router'
import { useSessions } from '@/composables/useSessions'

const router = useRouter()
const { sessions, loading, error, refresh } = useSessions()

const projects = computed(() =>
  [...new Set(sessions.value.map(s => s.project).filter(Boolean))].sort()
)
const selectedProject = ref<string | null>(null)
const filteredSessions = computed(() =>
  selectedProject.value
    ? sessions.value.filter(s => s.project === selectedProject.value)
    : sessions.value
)

function formatDate(iso: string): string {
  const d = new Date(iso)
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) + ', ' +
    d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false })
}

function formatDuration(seconds: number | undefined): string {
  if (seconds === undefined) return '—'
  if (seconds < 60) return `${seconds}s`
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${m}m ${s}s`
}

function navigateToSession(id: string) {
  router.push(`/sessions/${id}`)
}
</script>

<template>
  <div class="space-y-6 fade-in">
    <!-- Page header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-xl font-semibold text-slate-900 dark:text-white tracking-tight">Sessions</h1>
        <p class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">All recorded Claude Code conversations</p>
      </div>
      <button
        class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors duration-200 focus-visible:ring-2 focus-visible:ring-violet-500 focus-visible:ring-offset-2"
        :disabled="loading"
        @click="refresh"
        aria-label="Refresh sessions"
      >
        <svg class="w-4 h-4" :class="{ 'animate-spin': loading }" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
        </svg>
        Refresh
      </button>
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

    <!-- Empty state -->
    <div v-else-if="!loading && sessions.length === 0" class="glass-card p-12 text-center">
      <div class="w-12 h-12 rounded-2xl bg-slate-100 dark:bg-slate-800 flex items-center justify-center mx-auto mb-4">
        <svg class="w-6 h-6 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
        </svg>
      </div>
      <p class="text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">No sessions yet</p>
      <p class="text-xs text-slate-500 dark:text-slate-400">Sessions will appear here once the session_recorder hook fires.</p>
    </div>

    <!-- Project filter + Sessions table -->
    <template v-else>
      <div class="flex items-center gap-3 mb-4">
        <label class="text-sm text-gray-500">Project</label>
        <select v-model="selectedProject"
          class="text-sm border border-gray-200 rounded-md px-3 py-1.5 bg-white text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500">
          <option :value="null">All projects</option>
          <option v-for="p in projects" :key="p" :value="p">{{ p }}</option>
        </select>
        <button v-if="selectedProject" @click="selectedProject = null"
          class="text-xs text-gray-400 hover:text-gray-600">Clear</button>
      </div>

      <div class="glass-card overflow-hidden">
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead class="bg-slate-50/80 dark:bg-slate-800/50 sticky top-0 z-10">
              <tr>
                <th class="px-4 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide">Started</th>
                <th class="px-4 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide">Project</th>
                <th class="px-4 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide">Prompts</th>
                <th class="px-4 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide">Duration</th>
                <th class="px-4 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide">Status</th>
                <th class="px-4 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide">Orch Run</th>
                <th class="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100 dark:divide-slate-700/50">
              <!-- Skeleton rows while loading -->
              <template v-if="loading">
                <tr v-for="i in 5" :key="i" class="animate-pulse">
                  <td class="px-4 py-3"><div class="h-3.5 bg-slate-200 dark:bg-slate-700 rounded w-32"></div></td>
                  <td class="px-4 py-3"><div class="h-3.5 bg-slate-200 dark:bg-slate-700 rounded w-24"></div></td>
                  <td class="px-4 py-3"><div class="h-3.5 bg-slate-200 dark:bg-slate-700 rounded w-8"></div></td>
                  <td class="px-4 py-3"><div class="h-3.5 bg-slate-200 dark:bg-slate-700 rounded w-16"></div></td>
                  <td class="px-4 py-3"><div class="h-3.5 bg-slate-200 dark:bg-slate-700 rounded w-14"></div></td>
                  <td class="px-4 py-3"></td>
                  <td class="px-4 py-3"></td>
                </tr>
              </template>
              <template v-else>
                <tr
                  v-for="session in filteredSessions"
                  :key="session.id"
                  class="group hover:bg-slate-50/80 dark:hover:bg-slate-700/30 transition-colors duration-150 cursor-pointer"
                  @click="navigateToSession(session.id)"
                >
                  <td class="px-4 py-3 text-xs text-slate-400 dark:text-slate-500 font-mono tabular-nums">{{ formatDate(session.startTime) }}</td>
                  <td class="px-4 py-3 text-sm text-slate-700 dark:text-slate-300">{{ session.project ?? '—' }}</td>
                  <td class="px-4 py-3 text-sm text-slate-600 dark:text-slate-400 tabular-nums">{{ session.promptCount }}</td>
                  <td class="px-4 py-3 text-xs text-slate-500 dark:text-slate-400 font-mono tabular-nums">{{ formatDuration(session.durationSeconds) }}</td>
                  <td class="px-4 py-3">
                    <span
                      :class="[
                        'inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold',
                        session.status === 'active'
                          ? 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400'
                          : 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-400'
                      ]"
                    >
                      {{ session.status === 'active' ? 'Active' : 'Ended' }}
                    </span>
                  </td>
                  <td class="px-4 py-3" @click.stop>
                    <RouterLink
                      v-if="session.orchRunId"
                      :to="`/runs/${session.orchRunId}`"
                      class="text-xs font-mono text-violet-600 dark:text-violet-400 hover:underline"
                    >
                      {{ session.orchRunId }}
                    </RouterLink>
                    <span v-else class="text-xs text-slate-400">—</span>
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
    </template>
  </div>
</template>
